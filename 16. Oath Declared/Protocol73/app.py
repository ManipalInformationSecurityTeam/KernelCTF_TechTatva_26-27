from __future__ import annotations

import hashlib
import os
import random
import secrets
import threading
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from werkzeug.utils import secure_filename

from checks import check_requirement
from docx_parser import extract_docx
from requirements import REQUIREMENTS

BASE_DIR = Path(__file__).resolve().parent

def _load_local_env(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries from the app directory for local runs.

    Existing environment variables win in production. In development, the file is
    deliberately easy to edit so organizers can change the flag without chasing
    working-directory issues.
    """
    env_path = path or (BASE_DIR / ".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if ((value.startswith('"') and value.endswith('"')) or
                (value.startswith("'") and value.endswith("'"))):
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_local_env()
P73_ENV = os.environ.get("P73_ENV", "development").casefold()
MASTER_COUNT = len(REQUIREMENTS)
REQUIRED_COUNT = min(int(os.environ.get("P73_REQUIRED_COUNT", "120")), MASTER_COUNT)
UPLOAD_MAX = 6 * 1024 * 1024
MAX_RENDER_BODY_CHARS = 256_000

# Parsing a compliance-sized DOCX (thousands of words, headings, lists, tables,
# ...) through python-docx is the single most expensive thing this app does per
# request. Players very commonly resubmit byte-identical files (retrying without
# changing anything, or load-testing tools that replay the same payload), so a
# small content-addressed cache turns those repeats into a dict hit instead of a
# full re-parse. This is a per-worker-process, in-memory cache with no TTL: it is
# correct forever because extract_docx() is a pure function of the file bytes.
_PARSE_CACHE_MAX = int(os.environ.get("P73_PARSE_CACHE_MAX", "256"))
_parse_cache: "OrderedDict[bytes, dict]" = OrderedDict()
_parse_cache_lock = threading.Lock()


def parse_docx_cached(data: bytes) -> dict:
    digest = hashlib.sha256(data).digest()
    with _parse_cache_lock:
        cached = _parse_cache.get(digest)
        if cached is not None:
            _parse_cache.move_to_end(digest)
            return cached
    parsed = extract_docx(data)
    with _parse_cache_lock:
        _parse_cache[digest] = parsed
        _parse_cache.move_to_end(digest)
        while len(_parse_cache) > _PARSE_CACHE_MAX:
            _parse_cache.popitem(last=False)
    return parsed

_secret = os.environ.get("P73_FLASK_SECRET")
if os.environ.get("P73_ENV", "development").casefold() == "production" and not _secret:
    raise RuntimeError("P73_FLASK_SECRET must be set in production")

app = Flask(__name__)
app.secret_key = _secret or "protocol73-development-secret-change-me"
app.config.update(
    MAX_CONTENT_LENGTH=UPLOAD_MAX,
    MAX_FORM_MEMORY_SIZE=64 * 1024,
    MAX_FORM_PARTS=20,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Secure cookies are production-only. This prevents an accidental
    # P73_SECURE_COOKIE=1 from breaking local HTTP testing.
    SESSION_COOKIE_SECURE=(P73_ENV == "production" and os.environ.get("P73_SECURE_COOKIE", "1") == "1"),
    SESSION_REFRESH_EACH_REQUEST=False,
)

def get_flag() -> str:
    """Return the configured flag. In development, re-read .env so edits are immediate."""
    if P73_ENV != "production":
        local = BASE_DIR / ".env"
        if local.is_file():
            for raw in local.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if line.startswith("P73_FLAG="):
                    value = line.split("=", 1)[1].strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                        value = value[1:-1]
                    return value
    return os.environ.get("P73_FLAG", "FLAG{SET_P73_FLAG_IN_ENV}")



@app.after_request
def harden_dynamic_responses(response):
    if request.endpoint in {"index", "review_page", "upload", "flag_page"}:
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


REQUIREMENT_BY_ID = {r.id: r for r in REQUIREMENTS}
EARLY_KEY = {r.id for r in REQUIREMENTS if r.group == "breadcrumb_early"}
MID_BREADCRUMBS = [r.id for r in REQUIREMENTS if r.group == "breadcrumb_mid"]
LATE_BREADCRUMBS = [r.id for r in REQUIREMENTS if r.group == "breadcrumb_late"]
DOC_ID = next(r.id for r in REQUIREMENTS if r.value == "document" and r.group == "breadcrumb_early")
AUDIT_ID = next(r.id for r in REQUIREMENTS if r.value == "audit" and r.group == "breadcrumb_early")
REVIEW_ID = next(r.id for r in REQUIREMENTS if r.value == "review" and r.group == "breadcrumb_early")
COMPLETE_ID = next(r.id for r in REQUIREMENTS if r.value == "complete editorial review" and r.group == "breadcrumb_early")
SSTI_ID = next(r.id for r in REQUIREMENTS if r.value == "SSTI" and r.group == "breadcrumb_early")
JINJA_ID = next(r.id for r in REQUIREMENTS if r.value == "{{ }}" and r.group == "breadcrumb_early")


@lru_cache(maxsize=8192)
def build_order(seed: str) -> list[str]:
    """Create a deterministic per-session order from the requirement bank.

    The intended exploit vocabulary is seeded into the first 20 in exploit order:
    document -> audit -> review -> complete editorial review. Their exact positions
    are randomized and separated so the sequence never appears as 1-2-3-4. SSTI and
    Jinja are also randomized somewhere in the first 20.
    """
    rng = random.Random(seed)
    all_ids = [r.id for r in REQUIREMENTS]

    forced = set(EARLY_KEY) | set(MID_BREADCRUMBS) | set(LATE_BREADCRUMBS)
    if REQUIRED_COUNT < max(100, len(forced)):
        raise RuntimeError("P73_REQUIRED_COUNT is too small for the configured breadcrumb plan")

    non_breadcrumb = [rid for rid in all_ids if rid not in forced]
    selected = list(forced)
    selected.extend(rng.sample(non_breadcrumb, REQUIRED_COUNT - len(selected)))

    slots: list[str | None] = [None] * REQUIRED_COUNT

    # Four-step exploit vocabulary chain, in order, all within the first 20.
    valid_quads = [
        (a, b, c, d)
        for a in range(20)
        for b in range(a + 2, 20)
        for c in range(b + 2, 20)
        for d in range(c + 2, 20)
    ]
    a, b, c, d = rng.choice(valid_quads)
    slots[a], slots[b], slots[c], slots[d] = DOC_ID, AUDIT_ID, REVIEW_ID, COMPLETE_ID

    remaining_early_slots = [i for i in range(20) if slots[i] is None]
    core_extra = [SSTI_ID, JINJA_ID]
    rng.shuffle(core_extra)
    for pos, rid in zip(rng.sample(remaining_early_slots, 2), core_extra):
        slots[pos] = rid

    # Remaining breadcrumbs are deliberately less front-loaded.
    mid_pool = [rid for rid in MID_BREADCRUMBS if rid not in {DOC_ID, AUDIT_ID, REVIEW_ID, COMPLETE_ID}]
    mid_slots = rng.sample(range(20, min(100, REQUIRED_COUNT)), len(mid_pool))
    rng.shuffle(mid_pool)
    for pos, rid in zip(mid_slots, mid_pool):
        slots[pos] = rid

    late_pool = LATE_BREADCRUMBS[:]
    late_slots = rng.sample(range(100, REQUIRED_COUNT), len(late_pool))
    rng.shuffle(late_pool)
    for pos, rid in zip(late_slots, late_pool):
        slots[pos] = rid

    placed = {rid for rid in slots if rid is not None}
    remaining = [rid for rid in selected if rid not in placed]
    rng.shuffle(remaining)
    for i in range(REQUIRED_COUNT):
        if slots[i] is None:
            slots[i] = remaining.pop()

    order = [rid for rid in slots if rid is not None]
    assert len(order) == REQUIRED_COUNT and len(set(order)) == REQUIRED_COUNT
    core = [DOC_ID, AUDIT_ID, REVIEW_ID, COMPLETE_ID, SSTI_ID, JINJA_ID]
    assert set(core).issubset(order[:20])
    assert order.index(DOC_ID) < order.index(AUDIT_ID) < order.index(REVIEW_ID) < order.index(COMPLETE_ID)
    assert order.index(AUDIT_ID) - order.index(DOC_ID) >= 2
    assert order.index(REVIEW_ID) - order.index(AUDIT_ID) >= 2
    assert order.index(COMPLETE_ID) - order.index(REVIEW_ID) >= 2
    assert all(rid in order[:100] for rid in MID_BREADCRUMBS)
    assert all(rid in order[100:] for rid in LATE_BREADCRUMBS)
    return order


def system_logs(document_detail: str, audit_detail: str, review_detail: str, completion_detail: str) -> list[dict[str, str]]:
    """Render understated log sentences with stage labels embedded naturally."""
    stages = ("document", "audit", "review", "complete editorial review")
    entries = []
    for sentence, stage in zip((document_detail, audit_detail, review_detail, completion_detail), stages):
        sentence = " ".join(sentence.replace(";", ".").split())
        if sentence and sentence[-1] not in ".!?":
            sentence += "."
        index = sentence.lower().find(stage)
        if index < 0:
            # Keep the required stage wording visible without turning it into a heading.
            sentence = f"{sentence.rstrip('.')} during {stage}."
            index = sentence.lower().find(stage)
        entries.append({
            "before": sentence[:index],
            "step": sentence[index:index + len(stage)],
            "after": sentence[index + len(stage):],
        })
    return entries


def first_session() -> None:
    seed = secrets.token_hex(12)
    session.clear()
    session.update({
        "seed": seed,
        "cursor": 0,
        "attempts": 0,
        "filename": "",
        "flag_issued": False,
        "notice": None,
        "logs": system_logs(
            "The document reference was retained for this session",
            "Variance remained within tolerance during the audit",
            "No exception was recorded when the queue entered review",
            "Clearance remains pending until complete editorial review is recorded",
        ),
    })


def order_for_session() -> list[str]:
    seed = session.get("seed")
    if not seed:
        return []
    return build_order(seed)


def current_requirement():
    order = order_for_session()
    cursor = int(session.get("cursor", 0))
    if cursor >= len(order):
        return None
    return REQUIREMENT_BY_ID[order[cursor]]


def set_feedback(kind: str, message: str, logs: list[dict[str, str]]) -> None:
    session["notice"] = {"kind": kind, "message": message}
    session["logs"] = logs


class Review:
    """Ephemeral per-request review view backed by signed session state."""

    def __init__(self, seed: str, cursor: int, attempts: int, filename: str, flag_issued: bool):
        self.seed = seed
        self.cursor = cursor
        self.attempts = attempts
        self.filename = filename
        self.editorial_review_token: str | None = None
        self.editorial_complete = flag_issued
        self.flag_issued = flag_issued

    def complete_editorial_review(self) -> str:
        self.editorial_review_token = "ER-" + secrets.token_hex(8).upper()
        self.editorial_complete = True
        self.flag_issued = True
        return get_flag()

    def __repr__(self) -> str:
        return "<EditorialReview action=complete_editorial_review state=AVAILABLE>"


def load_review() -> Review | None:
    seed = session.get("seed")
    if not seed:
        return None
    return Review(
        seed=seed,
        cursor=int(session.get("cursor", 0)),
        attempts=int(session.get("attempts", 0)),
        filename=str(session.get("filename", "")),
        flag_issued=bool(session.get("flag_issued", False)),
    )


def save_review(review: Review) -> None:
    session.update({
        "cursor": review.cursor,
        "attempts": review.attempts,
        "filename": review.filename,
        "flag_issued": review.flag_issued,
    })


class DocumentView:
    def __init__(self, review_obj: Review):
        self.audit = AuditView(review_obj)

    def __repr__(self) -> str:
        return "<SubmittedDocument audit=AVAILABLE>"


class AuditView:
    def __init__(self, review_obj: Review):
        self.review = review_obj

    def __repr__(self) -> str:
        return "<AuditRecord review=AVAILABLE>"


class ProtocolSandbox(SandboxedEnvironment):
    """Allow only the exact object path and callable intended by the challenge."""

    SAFE_ATTRS = {
        DocumentView: {"audit"},
        AuditView: {"review"},
        Review: {"complete_editorial_review"},
    }

    def is_safe_attribute(self, obj, attr, value):
        allowed = self.SAFE_ATTRS.get(type(obj), set())
        return attr in allowed

    def is_safe_callable(self, obj):
        return getattr(obj, "__name__", "") == "complete_editorial_review" and isinstance(getattr(obj, "__self__", None), Review)


VULN_ENV = ProtocolSandbox(autoescape=False, undefined=StrictUndefined, cache_size=128)
VULN_ENV.globals.clear()
FIRST_RENDER_TEMPLATE = VULN_ENV.from_string(
    "PROTOCOL 73 // INTERNAL EDITORIAL RECORD\n\n"
    "SUBMITTED DOCUMENT\n-----------------------------\n"
    "{{ submitted_text }}\n"
)
# CHALLENGE HINT: this output is rendered a second time. A harmless expression
# such as {{ 7*7 }} visibly evaluates to 49; the review object's nested structure
# is intentionally discoverable through the generated audit copy.


def run_vulnerable_report_renderer(review: Review, submitted_text: str) -> str:
    """Intentional second-order SSTI: submitted document text is rendered twice."""
    document = DocumentView(review)
    try:
        first = FIRST_RENDER_TEMPLATE.render(submitted_text=submitted_text)
        second = VULN_ENV.from_string(first).render(document=document)
    except Exception as exc:
        second = f"PROTOCOL 73 // EDITORIAL RENDER REJECTED\n{type(exc).__name__}"
    return second


@app.get("/")
def index():
    if load_review() is not None:
        return redirect(url_for("review_page"))
    first_session()
    return redirect(url_for("review_page"))


@app.get("/review")
def review_page():
    review = load_review()
    if not review:
        return redirect(url_for("index"))
    if review.flag_issued:
        return redirect(url_for("flag_page"))

    req = current_requirement()
    if req is None:
        review.flag_issued = True
        save_review(review)
        return redirect(url_for("flag_page"))

    notice = session.pop("notice", None)
    logs = session.pop("logs", [])
    return render_template(
        "review.html",
        requirement=req,
        position=review.cursor + 1,
        total_required=REQUIRED_COUNT,
        filename=review.filename,
        notice=notice,
        logs=logs,
    )


@app.post("/upload")
def upload():
    review = load_review()
    if not review:
        return redirect(url_for("index"))
    if review.flag_issued:
        return redirect(url_for("flag_page"))

    req = current_requirement()
    if req is None:
        return redirect(url_for("flag_page"))

    review.attempts += 1
    position = review.cursor + 1
    file = request.files.get("document")

    if not file or not file.filename:
        set_feedback("fail", "DOCUMENT REQUIRED — RETRY", system_logs(
            "The document was not received and intake remains idle",
            "The ledger entry was retained during the audit",
            "The current position remains in review",
            "A retry remains available while complete editorial review is pending",
        ))
        save_review(review)
        return redirect(url_for("review_page"))

    if not file.filename.lower().endswith(".docx"):
        set_feedback("fail", "INVALID FORMAT — DOCX REQUIRED", system_logs(
            "The document payload was registered and its format was noted",
            "The ledger entry was retained during the audit",
            "The current position remains in review",
            "A retry remains available while complete editorial review is pending",
        ))
        save_review(review)
        return redirect(url_for("review_page"))

    filename = secure_filename(file.filename) or "declaration.docx"
    try:
        upload_bytes = file.read(UPLOAD_MAX + 1)
        if len(upload_bytes) > UPLOAD_MAX:
            raise ValueError("Upload exceeds size limit")
        parsed = parse_docx_cached(upload_bytes)
        if len(parsed.get("text", "")) > MAX_RENDER_BODY_CHARS:
            raise ValueError("DOCX body exceeds rendering limit")
        report = run_vulnerable_report_renderer(review, parsed["text"])
        # Show the second-pass output directly to the player. This is intentionally
        # visible: {{ 7*7 }} should visibly become 49, making the SSTI behavior
        # discoverable rather than requiring blind exploitation.
        render_preview = report
        if len(render_preview) > 8000:
            render_preview = render_preview[:8000] + "\n\n[OUTPUT TRUNCATED FOR DISPLAY]"

        review.filename = filename

        if review.flag_issued:
            notice = {"kind": "pass", "message": "CLEARANCE ISSUED"}
            logs = system_logs(
                "The document reference was retained after the payload was registered",
                "Variance remained within tolerance during the audit",
                "No exception was raised while the queue entered review",
                "The session remains sealed after complete editorial review",
            )
            save_review(review)
            return render_template(
                "review.html",
                requirement=None,
                position=position,
                total_required=REQUIRED_COUNT,
                filename=review.filename,
                notice=notice,
                logs=logs,
                render_preview=render_preview,
                clearance=True,
            )

        actual_pass = check_requirement(req.id, parsed)
        if actual_pass:
            review.cursor += 1
            logs = system_logs(
                "The document reference was retained after the payload was registered",
                "Variance remained within tolerance during the audit",
                "No exception was raised while the queue entered review",
                "The cycle remains active while complete editorial review is pending",
            )
            notice = {"kind": "pass", "message": f"CONDITION {position:03d} SATISFIED"}
            if review.cursor >= REQUIRED_COUNT:
                review.flag_issued = True
                notice = {"kind": "pass", "message": "CLEARANCE ISSUED"}
                save_review(review)
                return redirect(url_for("flag_page"))
        else:
            logs = system_logs(
                "The document reference was retained after the payload was registered",
                "Variance remained within tolerance during the audit",
                "No exception was raised while the queue entered review",
                "A retry remains available while complete editorial review is pending",
            )
            notice = {"kind": "fail", "message": f"CONDITION {position:03d} NOT SATISFIED — RETRY"}

        save_review(review)
        return render_template(
            "review.html",
            requirement=current_requirement(),
            position=review.cursor + 1,
            total_required=REQUIRED_COUNT,
            filename=review.filename,
            notice=notice,
            logs=logs,
            render_preview=render_preview,
            clearance=False,
        )
    except Exception:
        set_feedback("fail", "DOCUMENT COULD NOT BE PARSED — RETRY", system_logs(
            "The document reference was retained after the payload was registered",
            "The ledger entry remains intact during the audit",
            "An exception was noted while the item remained in review",
            "A retry remains available while complete editorial review is pending",
        ))
        save_review(review)
        return redirect(url_for("review_page"))


@app.get("/flag")
def flag_page():
    review = load_review()
    if not review or not review.flag_issued:
        return redirect(url_for("review_page"))
    response = app.response_class(get_flag() + "\n", mimetype="text/plain")
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
