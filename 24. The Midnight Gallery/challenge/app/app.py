#!/usr/bin/env python3
"""The Midnight Gallery - staging gateway (challenge app service)."""
import html
import json
import os
import secrets
import socket
import sqlite3
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("GALLERY_PORT", "8080"))
DIAG_URL = os.environ.get("DIAG_URL", "http://diag:9000/ping")
BIND = os.environ.get("GALLERY_BIND", "127.0.0.1")

FETCH_HEADER = "X-Gallery-Fetch"
FETCH_TOKEN = secrets.token_hex(16)
# Issued once a request passes the gate, so the session keeps working without the header.
GATEWAY_TOKEN = secrets.token_hex(16)

# Four shards, joined in order to form the flag:
#   kernel{1_h1dd3n_2_un10n_3_sh3ll_4_m4st3rp13c3}
# Shard 3 lives in the diagnostics service. Shard 2 lives in the secrets table.
SHARD1 = "kernel{1_h1dd3n_"
SHARD2 = "2_un10n_"
SHARD4 = "4_m4st3rp13c3}"

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

_real_getaddrinfo = socket.getaddrinfo
def _resolve_gallery_local(host, *args, **kwargs):
    if host == "gallery.local":
        host = "127.0.0.1"
    return _real_getaddrinfo(host, *args, **kwargs)
socket.getaddrinfo = _resolve_gallery_local

# Ignore system proxy settings for internal calls
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

DB_LOCK = threading.Lock()
DB = sqlite3.connect(":memory:", check_same_thread=False)
DB.executescript(f"""
CREATE TABLE artworks (id INTEGER, title TEXT, artist TEXT);
INSERT INTO artworks VALUES
  (1, 'Phantom Canvas', 'Unknown'),
  (2, 'Neon Reverie', 'M. Strauss'),
  (3, 'Study in Potassium Cyanide', 'K. Vane'),
  (4, 'Untitled (Provenance #14)', 'Estate of H. Lindqvist');
CREATE TABLE secrets (id INTEGER, shard TEXT, notes TEXT);
INSERT INTO secrets VALUES (1, '{SHARD2}', 'Archive node 2 of 4');
""")

STYLE = """
body {
  background: #0e0e0e;
  color: #c8c8c8;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  padding: 40px 24px;
}
.wrap {
  max-width: 720px;
  margin: 0 auto;
}
header {
  border-bottom: 1px solid #242424;
  padding-bottom: 14px;
  margin-bottom: 28px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
header .brand {
  font-size: 19px;
  color: #e8e8e8;
  letter-spacing: 0.04em;
}
header nav a {
  color: #8c8c8c;
  text-decoration: none;
  margin-left: 20px;
  font-size: 13px;
  font-family: "Courier New", monospace;
}
header nav a:hover {
  color: #e0e0e0;
}
h1, h2 {
  font-weight: normal;
  color: #e2e2e2;
  font-size: 16px;
  margin: 24px 0 10px 0;
}
p {
  color: #8a8a8a;
  margin: 6px 0 14px 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0 24px 0;
}
th, td {
  border-bottom: 1px solid #1f1f1f;
  padding: 9px 8px;
  text-align: left;
  font-size: 13px;
}
th {
  color: #777777;
  font-weight: normal;
  font-family: "Courier New", monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
input {
  background: #141414;
  border: 1px solid #2c2c2c;
  color: #d4d4d4;
  font-family: "Courier New", monospace;
  font-size: 12px;
  padding: 6px 10px;
}
button {
  background: #1c1c1c;
  border: 1px solid #333333;
  color: #c8c8c8;
  font-family: "Courier New", monospace;
  font-size: 12px;
  padding: 6px 14px;
  cursor: pointer;
}
button:hover {
  background: #262626;
  color: #ffffff;
}
pre {
  background: #121212;
  border: 1px solid #242424;
  padding: 12px;
  color: #b0b0b0;
  font-family: "Courier New", monospace;
  font-size: 12px;
  overflow-x: auto;
}
.featured {
  background: #131313;
  border: 1px solid #222222;
  padding: 14px 16px;
  margin-bottom: 24px;
  font-family: "Courier New", monospace;
  font-size: 12px;
  color: #b8b8b8;
}
footer {
  margin-top: 40px;
  border-top: 1px solid #1f1f1f;
  padding-top: 12px;
  font-size: 11px;
  font-family: "Courier New", monospace;
  color: #555555;
  display: flex;
  justify-content: space-between;
}
"""

NAV_BAR = """
<header>
  <span class="brand">The Midnight Gallery</span>
  <nav>
    <a href="/">Catalog</a>
    <a href="/api/v1/redirect?to=archive.php">Archive</a>
  </nav>
</header>
"""

PAGE = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>"
    "<style>" + STYLE + "</style></head>"
    "<body><div class='wrap'>" + NAV_BAR + "{body}</div></body></html>"
)

DASHBOARD = """
<!-- INTERNAL TOOLS DIRECTORY (HIDDEN) -->
<!-- /admin/diagnostics -->
<!-- /preview -->
<p>Staging status: the Masterpiece is split across 4 shards. Vault endpoint: /internal/vault (accepts only requests the server makes to itself).</p>

<h2>Featured Lot</h2>
<div class="featured" id="feed">Loading catalog lot...</div>

<h2>Current Autumn Consignments</h2>
<table>
  <tr><th>Lot</th><th>Title</th><th>Artist / Attribution</th><th>Estimate</th></tr>
  <tr><td>01</td><td>Phantom Canvas</td><td>Unknown</td><td>14.5 XMR</td></tr>
  <tr><td>02</td><td>Neon Reverie</td><td>M. Strauss</td><td>8.2 XMR</td></tr>
  <tr><td>03</td><td>Study in Potassium Cyanide</td><td>K. Vane</td><td>22.0 XMR</td></tr>
  <tr><td>04</td><td>Untitled (Provenance #14)</td><td>Estate of H. Lindqvist</td><td>19.0 XMR</td></tr>
</table>

<footer>
  <span>Private Viewing by Appointment</span>
  <span>Escrow Relay v1.4</span>
</footer>

<script>
fetch('/api/v1/artworks?id=1').then(r => r.json()).then(d => {
  const el = document.getElementById('feed');
  if (d.error) {
    el.innerText = d.error + " - " + (d.detail || "");
  } else if (d.shard) {
    // This displays the flag and internal origin if id=0 is intercepted
    el.innerText = d.artifact + " | Shard: " + d.shard + " | Origin: " + d.internal_origin;
  } else {
    el.innerText = "Lot 0" + d.id + ": " + d.artifact + " (prev_id: " + d.prev_id + ")";
  }
});
</script>
"""

DIAG_FORM = """<h1>Node Diagnostics</h1>
<form method="POST" action="/admin/diagnostics">
  <label>Host <input name="ip" value="127.0.0.1"></label>
  <button>Ping</button>
</form>"""

PREVIEW_FORM = """<h1>Preview Fetcher</h1>
<form method="GET" action="/api/v1/fetch_preview">
  <label>URL <input name="url" size="50"></label>
  <button>Fetch</button>
</form>"""


def esc(value):
    return html.escape(str(value))


def is_blocked_target(host):
    """Refuse any target that is, or resolves to, a loopback address.

    The gateway's own name is the one exception: it is how Step 5 reaches the vault.
    Every other name is resolved, so an alias that points at 127.0.0.1 is refused too.
    """
    host = host.lower().strip("[]")
    if host == "gallery.local":
        return False
    if host in LOOPBACK_HOSTS:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True  # cannot resolve: refuse rather than guess
    for info in infos:
        ip = info[4][0]
        if ip.startswith("127.") or ip in ("0.0.0.0", "::1", "::"):
            return True
    return False


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Threaded server with a hard cap on concurrent requests.

    Requests beyond the cap get an immediate 503 instead of a new thread.
    The CRLF relay needs raw response bytes, so this stays on the standard library.
    """
    daemon_threads = True
    MAX_CONCURRENT = 64
    _slots = None

    def process_request(self, request, client_address):
        if BoundedThreadingHTTPServer._slots is None:
            BoundedThreadingHTTPServer._slots = threading.BoundedSemaphore(self.MAX_CONCURRENT)
        if not BoundedThreadingHTTPServer._slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return

        def worker():
            try:
                self.process_request_thread(request, client_address)
            finally:
                BoundedThreadingHTTPServer._slots.release()

        threading.Thread(target=worker, daemon=True).start()

class Handler(BaseHTTPRequestHandler):
    server_version = "MidnightGallery/1.0"
    sys_version = ""
    timeout = 10  # drop idle or slow connections after 10 seconds


    def _has_xff(self):
        xff = self.headers.get("X-Forwarded-For", "")
        return xff.split(",")[0].strip() == "127.0.0.1"

    def _has_cookie(self, target_key, target_val):
        for part in self.headers.get("Cookie", "").split(";"):
            key, _, value = part.partition("=")
            # Tolerate spaces around the name and value, as hand-edited headers often have them.
            if key.strip() == target_key and value.strip() == target_val:
                return True
        return False

    def trusted_internal(self):
        # Internal traffic only: either the request came in from an internal address
        # on this request, or the session already passed that check earlier.
        return self._has_xff() or self._has_cookie("gateway_auth", GATEWAY_TOKEN)

    def gateway_cookie_header(self):
        if self._has_xff() and not self._has_cookie("gateway_auth", GATEWAY_TOKEN):
            return f"gateway_auth={GATEWAY_TOKEN}; Path=/"
        return None

    def has_curator(self):
        return self._has_cookie("access_tier", "curator")

    def send_body(self, code, ctype, body, extra_headers=None):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        cookie = self.gateway_cookie_header()
        if cookie:
            self.send_header("Set-Cookie", cookie)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, obj, extra_headers=None):
        self.send_body(code, "application/json", json.dumps(obj), extra_headers=extra_headers)

    def send_html(self, code, title, body):
        html_doc = PAGE.replace("{title}", esc(title)).replace("{body}", body)
        self.send_body(code, "text/html; charset=utf-8", html_doc)

    def read_form(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace")
        return urllib.parse.parse_qs(raw)

    def gate_denied(self):
        self.send_body(403, "text/plain",
                       "403 Forbidden: this gateway only accepts requests from internal "
                       "IP addresses. External requests are rejected.\n")

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)

        if url.path == "/internal/vault":
            return self.vault()

        if not self.trusted_internal():
            return self.gate_denied()

        routes = {
            "/": lambda: self.send_html(200, "The Midnight Gallery", DASHBOARD),
            "/home": lambda: self.send_html(200, "The Midnight Gallery", DASHBOARD),
            "/api/v1/redirect": lambda: self.relay(q.get("to", [""])[0]),
            "/api/v1/artworks": lambda: self.artworks(q.get("id", [""])[0]),
            "/archive.php": lambda: self.archive(q.get("search", [""])[0]),
            "/admin/diagnostics": lambda: self.send_html(200, "Node Diagnostics", DIAG_FORM),
            "/preview": lambda: self.send_html(200, "Preview Fetcher", PREVIEW_FORM),
            "/api/v1/fetch_preview": lambda: self.fetch_preview(q.get("url", [""])[0]),
        }
        handler = routes.get(url.path)
        if handler is None:
            return self.send_json(404, {"error": "404 Not Found"})
        handler()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if not self.trusted_internal():
            return self.gate_denied()
        if url.path != "/admin/diagnostics":
            return self.send_json(404, {"error": "404 Not Found"})

        ip = self.read_form().get("ip", [""])[0]
        try:
            req = urllib.request.Request(
                DIAG_URL,
                data=urllib.parse.urlencode({"ip": ip}).encode(),
                method="POST",
            )
            with NO_PROXY_OPENER.open(req, timeout=15) as resp:
                output = resp.read().decode("utf-8", "replace")
        except Exception as exc:
            output = f"diagnostics node unreachable: {exc}"
        self.send_html(200, "Node Diagnostics", DIAG_FORM + f"<pre>{esc(output)}</pre>")

    def relay(self, to):
        host = self.headers.get("Host", f"localhost:{PORT}")
        self.send_response_only(302, "Found")
        self.flush_headers()
        cookie = self.gateway_cookie_header()
        cookie_line = f"Set-Cookie: {cookie}\r\n" if cookie else ""
        self.wfile.write(f"Location: http://{host}/{to}\r\n{cookie_line}\r\n".encode("utf-8"))

    def artworks(self, aid):
        if not aid.isdigit():
            return self.send_json(400, {"error": "400 Bad Request", "detail": "id must be an integer"})
        aid_int = int(aid)
        if aid_int == 0:
            if not self.has_curator():
                return self.send_json(403, {
                    "error": "403 Forbidden",
                    "detail": "Genesis record restricted. Requires cookie access_tier=curator.",
                })
            return self.send_json(200, {
                "status": "success",
                "artifact": "Genesis Record",
                "shard": SHARD1,
                "internal_origin": f"http://gallery.local:{PORT}",
            })

        with DB_LOCK:
            row = DB.execute("SELECT id, title FROM artworks WHERE id = ?", (aid_int,)).fetchone()
        if row is None:
            return self.send_json(404, {"error": "404 Not Found", "detail": "No artwork with that id"})
        return self.send_json(200, {
            "status": "success",
            "id": row[0],
            "artifact": row[1],
            "prev_id": row[0] - 1,
        })

    def archive(self, search):
        sql = f"SELECT id, title, artist FROM artworks WHERE title LIKE '%{search}%'"
        error, rows = None, []
        try:
            with DB_LOCK:
                rows = DB.execute(sql).fetchall()
        except sqlite3.Error as exc:
            error = str(exc)

        table_rows = "".join(
            f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td></tr>" for r in rows
        )
        error_html = f"<p>SQL Error: {esc(error)}</p>" if error else ""
        body = (
            "<h1>Auction Archive</h1>"
            f'<form method="GET" action="/archive.php"><input name="search" value="{esc(search)}" placeholder="Search title..."><button>Filter</button></form>'
            f"{error_html}"
            f"<table><tr><th>ID</th><th>Title</th><th>Artist</th></tr>{table_rows}</table>"
            "<footer><span>Archive Index</span><span>SQLite 3</span></footer>"
        )
        self.send_html(200, "Auction Archive", body)

    def fetch_preview(self, target):
        if not target:
            return self.send_json(400, {"error": "Missing url parameter"})
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme not in ("http", "https"):
            return self.send_json(400, {"error": "Protocol not allowed"})
        if is_blocked_target(parsed.hostname or ""):
            return self.send_json(403, {"error": "Blocked: internal address detected"})
        try:
            req = urllib.request.Request(target, headers={FETCH_HEADER: FETCH_TOKEN})
            with NO_PROXY_OPENER.open(req, timeout=5) as resp:
                status = resp.status
                content = resp.read(4096).decode("utf-8", "replace")
        except Exception as exc:
            return self.send_json(502, {"error": f"Upstream fetch failed: {exc}"})
        self.send_json(200, {"status": status, "url": target, "content": content})

    def vault(self):
        if self.client_address[0] != "127.0.0.1" or self.headers.get(FETCH_HEADER) != FETCH_TOKEN:
            return self.send_json(404, {"error": "404 Not Found"})
        self.send_json(200, {"shard": SHARD4})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer.allow_reuse_address = True
    BoundedThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
