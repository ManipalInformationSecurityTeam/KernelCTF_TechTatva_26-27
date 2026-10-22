#!/usr/bin/env python3
"""Order Matters local challenge site; Python standard-library web server."""
from __future__ import annotations
import base64, binascii, hashlib, hmac, json, mimetypes, os, secrets, sqlite3, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
PRIVATE = ROOT / "private" / "challenge_manifest.json"
DB_PATH = Path(os.environ.get("ORDER_MATTERS_DB", ROOT / "instance" / "order_matters.sqlite3"))
HOST = os.environ.get("ORDER_MATTERS_HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
PORT = int(os.environ.get("ORDER_MATTERS_PORT", os.environ.get("PORT", "8000")))
COOKIE_SECURE = os.environ.get("ORDER_MATTERS_HTTPS", "").lower() == "true"
MAX_ENTRIES = 9
SELECTION_RESPONSE_BYTES = 2048
STATE_RESPONSE_BASE_BYTES = 4096
STATE_RESPONSE_BYTES_PER_ENTRY = 1024

# On a public deployment, supply the private manifest as a dashboard secret instead
# of committing the file. Local/organizer runs can use private/challenge_manifest.json.
manifest_b64 = os.environ.get("ORDER_MATTERS_MANIFEST_B64", "").strip()
if manifest_b64:
    try:
        MANIFEST = json.loads(base64.b64decode(manifest_b64, validate=True).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit("ORDER_MATTERS_MANIFEST_B64 is not valid base64-encoded UTF-8 JSON") from exc
elif PRIVATE.exists():
    MANIFEST = json.loads(PRIVATE.read_text(encoding="utf-8"))
else:
    raise SystemExit("Missing private challenge manifest. Set ORDER_MATTERS_MANIFEST_B64 to its base64-encoded JSON.")
BOXES = MANIFEST["boxes"]
ROUTE = MANIFEST["route"]
FRAGMENTS = MANIFEST["fragments_hex"]
TRUE_NOTES = MANIFEST["true_notes"]
DECOY_NOTES = MANIFEST["decoy_notes"]
DECOY_SALT = secrets.token_bytes(32)


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS runs (
      sid TEXT PRIMARY KEY,
      csrf TEXT NOT NULL,
      history TEXT NOT NULL,
      stage INTEGER NOT NULL DEFAULT 0,
      poisoned INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    con.commit()
    return con


def new_run(sid: str | None = None):
    sid = sid or secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    con = connect_db()
    con.execute("INSERT OR REPLACE INTO runs(sid, csrf, history, stage, poisoned) VALUES(?,?,?,?,?)",
                (sid, csrf, "[]", 0, 0))
    con.commit()
    row = con.execute("SELECT * FROM runs WHERE sid=?", (sid,)).fetchone()
    con.close()
    return sid, row


def parse_sid(cookie_header: str) -> str | None:
    try:
        cookie = SimpleCookie(); cookie.load(cookie_header or "")
        morsel = cookie.get("om_session")
        return morsel.value if morsel else None
    except Exception:
        return None


def get_run(sid: str | None):
    if sid:
        con = connect_db()
        row = con.execute("SELECT * FROM runs WHERE sid=?", (sid,)).fetchone()
        con.close()
        if row is not None:
            return sid, row, False
    sid, row = new_run()
    return sid, row, True


def safe_state(row):
    history = json.loads(row["history"])
    # Never disclose route, stage, poison state, key, nonce, or expected fragment mapping.
    return {
        "csrf_token": row["csrf"],
        "history": history,
        "opened_count": len(history),
        "entry_limit": MAX_ENTRIES,
        "boxes": [{"id": code, **value, "opened": any(x["box"] == code for x in history)}
                   for code, value in sorted(BOXES.items())],
    }


def fragment_size_for_position(position: int) -> int:
    return len(bytes.fromhex(FRAGMENTS[min(position, len(FRAGMENTS)-1)]))


def make_decoy(sid: str, position: int, box: str, prior_path: list[str]) -> tuple[str, str]:
    # Derive well-shaped decoy bytes and text from the path, without exposing any status bit.
    path_material = ">".join(prior_path + [box]).encode("ascii")
    seed = hmac.new(DECOY_SALT, sid.encode() + b"|" + str(position).encode() + b"|" + path_material, hashlib.sha256).digest()
    need = fragment_size_for_position(position)
    block = bytearray()
    counter = 0
    while len(block) < need:
        block.extend(hmac.new(seed, counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    fragment = bytes(block[:need]).hex()
    notes = DECOY_NOTES.get(box) or DECOY_NOTES["O"]
    note_index = seed[0] % len(notes)
    # Path-salted suffix makes repeat routes branch-dependent, while still reading as a field note.
    note = notes[note_index]
    return fragment, note


class Handler(BaseHTTPRequestHandler):
    server_version = "AEB-Archive/2.4"
    sys_version = ""

    def log_message(self, fmt, *args):
        if os.environ.get("ORDER_MATTERS_LOG", "").lower() == "true":
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-DNS-Prefetch-Control", "off")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if COOKIE_SECURE:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        super().end_headers()

    def _reply(self, status: int, body: bytes, content_type="application/json; charset=utf-8", extra_headers=None, cookie_sid=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items(): self.send_header(k, v)
        if cookie_sid:
            self.send_header("Set-Cookie", f"om_session={cookie_sid}; Path=/; HttpOnly; SameSite=Lax" + ("; Secure" if COOKIE_SECURE else ""))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, obj, cookie_sid=None, pad_to=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        # Normalize successful selection/state response sizes so observation length does not
        # reveal whether a selection matched the hidden route.
        if pad_to is not None and len(body) < pad_to:
            body += b" " * (pad_to - len(body))
        self._reply(status, body, cookie_sid=cookie_sid)

    def _session(self):
        sid, row, is_new = get_run(parse_sid(self.headers.get("Cookie", "")))
        return sid, row, sid if is_new else None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            sid, row, cookie_sid = self._session()
            data = (WEB / "index.html").read_bytes()
            self._reply(200, data, "text/html; charset=utf-8", cookie_sid=cookie_sid)
            return
        if path == "/api/state":
            sid, row, cookie_sid = self._session()
            opened = len(json.loads(row["history"]))
            target_size = STATE_RESPONSE_BASE_BYTES + opened * STATE_RESPONSE_BYTES_PER_ENTRY
            self._json(200, safe_state(row), cookie_sid=cookie_sid, pad_to=target_size)
            return
        if path.startswith("/static/"):
            rel = unquote(path[len("/static/"):])
            target = (WEB / "static" / rel).resolve()
            static_root = (WEB / "static").resolve()
            if static_root not in target.parents or not target.is_file():
                self._json(404, {"error": "Not found."}); return
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self._reply(200, target.read_bytes(), ctype)
            return
        # In particular, never map /private, /tools, /instance or project-root files to disk.
        self._json(404, {"error": "Not found."})

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 64 * 1024: return None
            body = self.rfile.read(length)
            obj = json.loads(body.decode("utf-8"))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _csrf_valid(self, row):
        got = self.headers.get("X-CSRF-Token", "")
        return bool(got) and hmac.compare_digest(got, row["csrf"])

    def do_POST(self):
        path = urlparse(self.path).path
        sid = parse_sid(self.headers.get("Cookie", ""))
        if not sid:
            self._json(400, {"error": "Session expired. Reload the casefile."}); return
        con = connect_db()
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM runs WHERE sid=?", (sid,)).fetchone()
        if row is None:
            con.rollback(); con.close(); self._json(400, {"error": "Session expired. Reload the casefile."}); return
        body = self._read_json()
        if not self._csrf_valid(row):
            con.rollback(); con.close(); self._json(403, {"error": "Request token expired. Reload the casefile."}); return
        if body is None:
            con.rollback(); con.close(); self._json(400, {"error": "Invalid request body."}); return

        if path != "/api/select":
            con.rollback(); con.close(); self._json(404, {"error": "Not found."}); return
        box = body.get("box")
        if not isinstance(box, str) or box not in BOXES:
            con.rollback(); con.close(); self._json(400, {"error": "Unknown exhibit."}); return

        history = json.loads(row["history"])
        existing = next((item for item in history if item["box"] == box), None)
        if existing is not None:
            con.rollback(); con.close(); self._json(200, existing, pad_to=SELECTION_RESPONSE_BYTES)
            return
        if len(history) >= MAX_ENTRIES:
            con.rollback(); con.close(); self._json(409, {"error": "The nine-entry file is closed. Previously selected boxes can still be reopened."}); return

        position = len(history)
        prior_boxes = [item["box"] for item in history]
        expected = ROUTE[position]
        clean = (not row["poisoned"] and box == expected and position < len(ROUTE))
        # Do equivalent decoy work on every selection so the response branch is less useful
        # as a timing oracle. Only the selected record's final content is returned.
        decoy_fragment, decoy_observation = make_decoy(sid, position, box, prior_boxes)
        if clean:
            fragment = FRAGMENTS[position]
            observation = TRUE_NOTES[box]
            next_stage = int(row["stage"]) + 1
            poisoned = 0
        else:
            fragment, observation = decoy_fragment, decoy_observation
            next_stage = int(row["stage"])
            poisoned = 1
        entry = {
            "box": box,
            "title": BOXES[box]["title"],
            "subtitle": BOXES[box]["subtitle"],
            "observation": observation,
            "fragment": fragment,
            "ordinal": position + 1,
        }
        history.append(entry)
        con.execute("UPDATE runs SET history=?, stage=?, poisoned=? WHERE sid=?",
                    (json.dumps(history, ensure_ascii=False), next_stage, poisoned, sid))
        con.commit(); con.close()
        self._json(200, entry, pad_to=SELECTION_RESPONSE_BYTES)


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 62)
    print(" ORDER MATTERS | Archives & Evidence Bureau | Case 18-42")
    print(f" Local site: http://{HOST}:{PORT}")
    print(" PCAP is distributed separately with the challenge.")
    print(" No flag submission or flag reveal is implemented on this site.")
    print(" Keep this terminal open. Press Ctrl+C to stop.")
    print("=" * 62)
    try: httpd.serve_forever()
    except KeyboardInterrupt: print("\nArchive server stopped.")
    finally: httpd.server_close()

if __name__ == "__main__": main()
