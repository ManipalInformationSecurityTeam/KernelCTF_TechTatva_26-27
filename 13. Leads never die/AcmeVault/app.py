import json
import os
from datetime import timedelta
from functools import wraps
from urllib.parse import unquote

import python_jwt
from flask import Flask, flash, redirect, render_template, request, url_for, make_response
from jwcrypto import jwk
from jwcrypto.jws import JWS


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET", "change-this-in-deployment"),
    SESSION_COOKIE_NAME="flask_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)

INVESTIGATOR_ID = os.environ.get("INVESTIGATOR_ID", "INV-2047")
INVESTIGATOR_PASSWORD = os.environ.get("INVESTIGATOR_PASSWORD")
RESTRICTED_FLAG = os.environ.get("RESTRICTED_FLAG")

if not INVESTIGATOR_PASSWORD:
    raise RuntimeError("Set INVESTIGATOR_PASSWORD in the server environment.")
if not RESTRICTED_FLAG:
    raise RuntimeError("Set RESTRICTED_FLAG in the server environment.")

AUTH_COOKIE = "auth_token"
JWT_ALGORITHM = "PS256"
ISSUER = "acme-identity-gateway"
AUDIENCE = "acme-investigation-portal"

# Server-side only. The player never receives this key unless the application
# explicitly serializes something derived from it (which this app never does).
private_jwk_json = os.environ.get("JWT_PRIVATE_JWK")
if private_jwk_json:
    PRIVATE_KEY = jwk.JWK.from_json(private_jwk_json)
else:
    PRIVATE_KEY = jwk.JWK.generate(kty="RSA", size=2048)

PUBLIC_KEY = jwk.JWK.from_json(PRIVATE_KEY.export_public())


def create_session_token():
    """Create the normal signed investigator session token."""
    claims = {
        "sub": INVESTIGATOR_ID,
        "role": "investigator",
        "clearance": 2,
        "case_access": ["CASE-184", "CASE-920", "CASE-314"],
        "iss": ISSUER,
        "aud": AUDIENCE,
        "session_version": 4,
    }
    return python_jwt.generate_jwt(
        claims,
        PRIVATE_KEY,
        JWT_ALGORITHM,
        timedelta(hours=2),
    )


def _decode_cookie_token(token):
    return unquote(token)


def authenticate_token(token):
    """
    Authentication parser.

    This path gives the raw cookie directly to jwcrypto. It accepts the
    JSON/compact JWS representations understood by that implementation and
    verifies the cryptographic signature before returning the authenticated
    payload.
    """
    try:
        token = _decode_cookie_token(token)
        verifier = JWS()
        verifier.allowed_algs = [JWT_ALGORITHM]
        verifier.deserialize(token, PUBLIC_KEY)
        claims = json.loads(verifier.payload.decode("utf-8"))

        if claims.get("sub") != INVESTIGATOR_ID:
            return None
        if claims.get("iss") != ISSUER:
            return None
        if claims.get("aud") != AUDIENCE:
            return None
        return claims
    except Exception:
        return None


def parse_claims_for_authorization(token):
    """
    Authorization parser.

    Intentionally uses the vulnerable python-jwt 3.3.3 verification path on
    the exact same raw cookie string used by authentication. The historical
    compact-vs-JSON parsing differential can make the returned claims differ
    from the payload authenticated by the JWS parser.
    """
    try:
        token = _decode_cookie_token(token)
        _, claims = python_jwt.verify_jwt(token, PUBLIC_KEY, [JWT_ALGORITHM])
        return claims
    except Exception:
        return None


def authorize_addendum(token, case_id):
    """Authorization parser path for sealed case addenda."""
    claims = parse_claims_for_authorization(token)
    if not claims:
        return False

    role = claims.get("role", "investigator")
    clearance = claims.get("clearance", 0)
    case_access = claims.get("case_access", [])

    return (
        role == "admin"
        and clearance >= 4
        and case_id in case_access
    )


def login_required(view):
    """Require a valid authenticated auth_token cookie."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = request.cookies.get(AUTH_COOKIE)
        if not token:
            return redirect(url_for("login"))

        claims = authenticate_token(token)
        if not claims:
            return redirect(url_for("login"))

        return view(claims, token, *args, **kwargs)

    return wrapped


# The following IDs are deliberately interleaved through the six-file list.
# This mapping stays server-side and is never sent to the browser.
SEALED_ADDENDUM_CASES = {"CASE-7319", "CASE-4412", "CASE-5827"}
FLAG_CASE_ID = "CASE-7319"


# Only information intentionally available in the primary dossier.
# No secret flag, private addendum text, or "this is the real clue" marker lives here.
PUBLIC_CASES = {
    "CASE-920": {
        "subject": "Daniel Kade",
        "role": "Lab Operations Manager",
        "status": "OPEN",
        "classification": "STANDARD",
        "victim": "Dr. Elias Verran",
        "location": "ACME Research Annex / Archive Room 4B",
        "time": "23:41",
        "summary": "Controlled the building's maintenance schedule and knew the annex better than anyone.",
        "motive": "Verran had discovered that maintenance invoices were being used to conceal unapproved equipment purchases.",
        "alibi": "Generator-room maintenance logs show Kade remained in the basement from 23:29 to 23:56.",
        "evidence": "His access card opened the maintenance corridor, but not Archive Room 4B during the relevant window.",
        "statements": [
            "INTERVIEW 01 — Kade says Verran was difficult, but insists the two had agreed to settle the invoice dispute the next morning.",
            "LOG 02 — Generator-room sensor recorded a continuous maintenance session between 23:29 and 23:56.",
            "NOTE 03 — A duplicate archive badge was reported missing two days before the murder. Its replacement was logged under a different record format; the two records described the same badge differently.",
            "ARCHIVE CROSS-REF 04 — A maintenance ticket from four days before the murder mentions an unresolved compatibility check in the systems group. No operator is named in this file.",
        ],
        "analyst_note": "Kade had access, but the recorded timeline is difficult to reconcile with the murder window. ARCHIVE NOTE — An older maintenance export was converted between two record formats before being filed.",
    },
    "CASE-7319": {
        "subject": "Evan Rook",
        "role": "Systems Engineer",
        "status": "OPEN",
        "classification": "STANDARD",
        "victim": "Dr. Elias Verran",
        "location": "ACME Research Annex / Archive Room 4B",
        "time": "23:41",
        "summary": "Senior systems engineer who maintained the archive gateway and had recently fallen out with Verran.",
        "motive": "Verran had scheduled a review of unexplained changes made to the archive authentication gateway.",
        "alibi": "Rook claimed he remained in the systems room until midnight. Archive access telemetry places his badge at Room 4B at 23:36.",
        "evidence": "Fine machine oil matching the systems-room maintenance bench was found on the victim's sleeve. Rook was the last engineer logged against that bench.",
        "statements": [
            "INTERVIEW 01 — Rook denies entering Archive Room 4B after 22:00, despite a door event tied to his credentials at 23:36.",
            "INTERVIEW 02 — Asked whether he had noticed anything unusual in the archive tools, Rook laughed and said: 'Pythons get scrambled when you make the same thing two different ways.' The interviewer marked it as irrelevant.",
            "TIMELINE 03 — Verran's final outgoing message, sent at 23:37, begins: 'Evan, we need to talk about the verifier before morning.'",
            "ARCHIVE CROSS-REF 04 — The compatibility check mentioned in other files was opened from the systems group at 21:18 on the night of the murder.",
            "EVIDENCE 04 — Some restricted information may exist outside this primary record. The archive index does not reproduce supporting material here.",
        ],
        "analyst_note": "The public evidence puts Rook near the archive at the critical moment, but the technical records deserve a closer reading. ARCHIVE NOTE — A compatibility test was logged four days before the murder; the operator described it only as a format-conversion check.",
    },
    "CASE-184": {
        "subject": "Mara Voss",
        "role": "Forensic Accountant",
        "status": "OPEN",
        "classification": "STANDARD",
        "victim": "Dr. Elias Verran",
        "location": "ACME Research Annex / Archive Room 4B",
        "time": "23:41",
        "summary": "Former finance lead. Strong motive, but her movements are well documented.",
        "motive": "Verran had reported irregular expense claims connected to Voss's department.",
        "alibi": "Hotel lobby cameras place Voss off-site from 22:52 until 00:14.",
        "evidence": "A receipt and lobby access record place her roughly 6 km from the annex at the estimated time of death.",
        "statements": [
            "INTERVIEW 01 — Voss admits arguing with Verran that afternoon, but denies returning to the annex.",
            "TIMELINE 02 — Vehicle toll data places Voss on the northbound road at 23:17.",
            "EVIDENCE 03 — The victim's desk calendar contains a note: 'Audit review moved to 09:00 tomorrow.' On the back: 'Same event, two ledgers.'",
        ],
        "analyst_note": "RECORD INDEX — A clipping about a Python security issue from September 2022 was found among Verran’s notes. Beside it, he had written: ‘Ask how the older tools read it.’ No further context was recorded.",
    },
    "CASE-5827": {
        "subject": "Rohan Pike",
        "role": "Research Assistant",
        "status": "OPEN",
        "classification": "STANDARD",
        "victim": "Dr. Elias Verran",
        "location": "ACME Research Annex / Archive Room 4B",
        "time": "23:41",
        "summary": "Junior researcher whose work Verran had accused of copying from an internal project.",
        "motive": "Verran had threatened to report Pike for using restricted research material in a personal project.",
        "alibi": "Dormitory network records and a recorded video call place Pike away from campus from 23:12 onward.",
        "evidence": "Pike possessed a spare laboratory key, but the key does not open Archive Room 4B.",
        "statements": [
            "INTERVIEW 01 — Pike admits taking a copy of Verran's notebook weeks earlier but returned it before the murder.",
            "LOG 02 — Dormitory network authentication shows Pike remained connected to the same room throughout the murder window.",
            "NOTE 03 — Pike's notebook contains a line about 'the same numbers in two files' followed by a doodled snake. No obvious connection to the murder was noted.",
            "EVIDENCE 04 — Some restricted information may exist outside this primary record. The archive index does not reproduce supporting material here.",
        ],
        "analyst_note": "Pike's motive is real, but the electronic and physical evidence gives him a strong alibi. ARCHIVE NOTE — Pike repeatedly wrote that two files could look identical to a person while behaving differently to software.",
    },
    "CASE-314": {
        "subject": "Priya Sen",
        "role": "Investigative Journalist",
        "status": "OPEN",
        "classification": "STANDARD",
        "victim": "Dr. Elias Verran",
        "location": "ACME Research Annex / Archive Room 4B",
        "time": "23:41",
        "summary": "Had been pressuring Verran to release evidence of a corporate security dispute.",
        "motive": "Verran refused to hand over internal documents before his legal review was complete.",
        "alibi": "Sen left campus through the east gate at 21:06 and appeared on a live broadcast at 21:42.",
        "evidence": "Phone location and broadcast metadata place Sen away from the annex throughout the night.",
        "statements": [
            "INTERVIEW 01 — Sen confirms that Verran promised her a document packet the following morning.",
            "TIMELINE 02 — East-gate camera places Sen in a rideshare at 21:06.",
            "NOTE 03 — Sen's source described the archive gateway as 'two doors for the same key', but she treated it as a metaphor.",
            "ARCHIVE CROSS-REF 04 — The phrase appears again in an internal maintenance discussion dated four days before the murder.",
        ],
        "analyst_note": "Sen had motive, but the known timeline puts her off-site well before the murder. SOURCE NOTE — One archived interview uses the phrase 'two doors for the same key' when describing a software gateway.",
    },
    "CASE-4412": {
        "subject": "Leena Hart",
        "role": "Security Contractor",
        "status": "OPEN",
        "classification": "STANDARD",
        "victim": "Dr. Elias Verran",
        "location": "ACME Research Annex / Archive Room 4B",
        "time": "23:41",
        "summary": "Recently removed from the ACME security contract after credentials were mishandled.",
        "motive": "Verran supported the contract termination and planned to give a negative recommendation.",
        "alibi": "Hart's badge was used at the front entrance at 23:24, but lobby footage shows her leaving the property at 23:27.",
        "evidence": "A taxi receipt and phone call record place Hart in transit shortly after leaving the annex.",
        "statements": [
            "INTERVIEW 01 — Hart admits confronting Verran earlier that evening about the contract termination.",
            "LOG 02 — Her contractor badge was inactive for Archive Room 4B and the maintenance corridor.",
            "NOTE 03 — Hart mentions that a Python script once converted badge exports between vendor formats; she calls the change 'annoying, not interesting.'",
            "EVIDENCE 04 — Some restricted information may exist outside this primary record. The archive index does not reproduce supporting material here.",
        ],
        "analyst_note": "Hart had an emotional motive, but the physical timeline does not fit the murder window. ARCHIVE NOTE — Her old badge-export utility was written in Python and once had to support both a legacy and a newer vendor format.",
    },
}


# Private evidence. This dictionary is intentionally never passed to a template
# until authorization succeeds for the requested case.
PRIVATE_CASE_DATA = {
    "CASE-7319": {
        "title": "ARCHIVE GATEWAY / TECHNICAL ADDENDUM",
        "text": "Recovered terminal note, 00:12: 'The gateway accepts the same session in more than one form. The verifier checks one view; the downstream record path can read another. Do not normalize them independently.'",
        "evidence": "A maintenance ticket shows Rook tested a compatibility path that accepted both the ordinary compact token and its JSON form four days before the murder.",
    },
    "CASE-4412": {
        "title": "SECURITY OPERATIONS / ADDENDUM",
        "text": "Badge reconciliation memo: Hart's old automation converted raw access logs into JSON before the security team archived them. The script was rewritten when the vendor changed formats, and the conversion produced no new physical-access events.",
        "evidence": "The audit trail shows Hart's badge inactive in Archive Room 4B throughout the relevant period. The addendum does not place her at the scene. SO CLOSE, YET SO FAR — the technical lead does not survive contact with the physical timeline.",
    },
    "CASE-5827": {
        "title": "RESEARCH NOTEBOOK / ADDENDUM",
        "text": "Recovered notebook excerpt: several experiments were represented twice for compatibility. Pike complained that the records looked the same to a person but behaved differently to the software that consumed them.",
        "evidence": "The notebook concerns data-processing experiments and contains no evidence tying Pike to the murder scene or ACME authentication systems. SO CLOSE, YET SO FAR — interesting formatting behavior, wrong trail.",
    },
}

assert SEALED_ADDENDUM_CASES == set(PRIVATE_CASE_DATA)
assert set(PUBLIC_CASES) == {"CASE-184", "CASE-920", "CASE-314"} | SEALED_ADDENDUM_CASES
# The restricted-case membership itself is kept server-side; the shared archive
# notice is intentionally identical for every dossier at render time.


@app.after_request
def security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        investigator_id = request.form.get("investigator_id", "").strip()
        password = request.form.get("password", "")
        if investigator_id == INVESTIGATOR_ID and password == INVESTIGATOR_PASSWORD:
            response = make_response(redirect(url_for("dashboard")))
            response.set_cookie(
                AUTH_COOKIE,
                create_session_token(),
                httponly=True,
                secure=app.config["SESSION_COOKIE_SECURE"],
                samesite="Lax",
                max_age=2 * 60 * 60,
            )
            return response
        flash("Invalid investigator credentials.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    response = make_response(redirect(url_for("login")))
    response.delete_cookie(AUTH_COOKIE)
    return response


@app.route("/dashboard")
@login_required
def dashboard(claims, token):
    return render_template(
        "dashboard.html",
        claims=claims,
        total_cases=len(PUBLIC_CASES),
        victim_name="Dr. Elias Verran",
    )


@app.route("/suspects")
@login_required
def suspects(claims, token):
    # The player gets only innocuous card metadata. There is no addendum flag,
    # lock marker, hidden title, or private-data identifier in this response.
    public_cards = {
        case_id: {
            "subject": case["subject"],
            "role": case["role"],
            "classification": case["classification"],
        }
        for case_id, case in PUBLIC_CASES.items()
    }
    return render_template(
        "suspects.html",
        claims=claims,
        cases=public_cards,
        victim_name="Dr. Elias Verran",
    )


@app.route("/suspect/<case_id>")
@login_required
def suspect(claims, token, case_id):
    public_case = PUBLIC_CASES.get(case_id)
    if not public_case:
        return render_template("404.html"), 404

    render_case = dict(public_case)
    # The vague note exists only as EVIDENCE 04 inside the three relevant
    # public dossiers. It is intentionally absent from the suspect cards.
    # Private addendum contents are not added to the response until authorized.
    addendum_unlocked = False

    if case_id in SEALED_ADDENDUM_CASES:
        addendum_unlocked = authorize_addendum(token, case_id)
        if addendum_unlocked:
            render_case["addendum"] = dict(PRIVATE_CASE_DATA[case_id])
            if case_id == FLAG_CASE_ID:
                render_case["flag"] = RESTRICTED_FLAG

    return render_template(
        "case.html",
        claims=claims,
        case=render_case,
        case_id=case_id,
        victim_name="Dr. Elias Verran",
        addendum_unlocked=addendum_unlocked,
    )


@app.route("/archive/verify", methods=["GET", "POST"])
def archive_verify():
    # Harmless dead end: deliberately does not reveal implementation details.
    response = make_response("Archive verification unavailable. Reference: E17\n", 410)
    response.headers["X-Archive-Reference"] = "E17"
    return response


@app.route("/robots.txt")
def robots():
    return make_response("User-agent: *\nDisallow: /archive/verify\n", 200, {"Content-Type": "text/plain; charset=utf-8"})


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
