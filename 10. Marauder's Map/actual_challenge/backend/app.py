"""
Marauder's Map -- CTF backend.

Serves the built React frontend (../marauders-map, built to ./dist by
the Docker image) and exposes two intentionally vulnerable endpoints:

  POST /api/accio   -> SQL injection (string-built query against SQLite).
                        Exactly two columns are selected (name, note), so
                        the intended UNION-based extraction is a
                        two-column UNION. The WHERE clause filters on
                        `visible=1`; that filter is also bypassable
                        in-line (no UNION required) to surface Hermione's
                        suppressed row.

  POST /api/owl      -> SSRF. {"address": ...} is fetched server-side.
                        A naive blocklist stops loopback literals but
                        not the internal service's plain hostname on
                        the shared docker network.

Everything else here is scaffolding: witty Marauder-voiced copy and
static file serving. Do not "fix" the vulnerabilities without
understanding that's the point -- this app should never be deployed
anywhere but a sandboxed CTF environment.
"""

import os
import random
import sqlite3

import requests
from flask import Flask, jsonify, request, send_from_directory

DB_PATH = os.path.join(os.path.dirname(__file__), "castle.db")
DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")

# ---------------------------------------------------------------------------
# Marauder-voiced copy pools
# ---------------------------------------------------------------------------

EMPTY_QUERY_LINES = [
    "Messrs. Moony, Wormtail, Padfoot and Prongs require you to actually type a name, radish-brain.",
    "The map cannot locate 'nobody in particular'. Do try again.",
    "Prongs suggests you ask for someone who exists. Wormtail suggests you ask for someone at all.",
]

NO_RESULTS_LINES = [
    "Padfoot has sniffed every corridor twice. No one by that name is currently in the castle, the country, or Peeves' good graces.",
    "Moony regrets to inform you that the person you seek is either exceptionally well-hidden or exceptionally made-up.",
    "The ink searched high and low, through the kitchens and the broom cupboards, and found absolutely nothing. Try harder, or try someone real.",
    "Wormtail checked under every floorboard. Nothing. (He would know.)",
]

HERMIONE_HINT_LINES = [
    "The map hesitates. There is a name it half-remembers, and a silence where her dot should be. Someone filed her away somewhere this map was never meant to show.",
]

MALFORMED_LINES = [
    "Prongs regrets that your handwriting is, frankly, unreadable by magical means.",
    "The quill refuses to transcribe that. Try words it recognises as words.",
]

SERVER_ERROR_LINES = [
    "Something in the ink has gone spectacularly wrong, and Moony is too polite to say what.",
    "The map has folded itself in embarrassment. Give it a moment.",
    "Padfoot knocked something over. We're not sure what. We're not sure it was supposed to be knockable.",
]

OWL_REFUSED_LINES = [
    "The owl takes one look at that address, hoots with disdain, and refuses to leave the owlery.",
    "Wormtail whispers that owls don't fly in circles back to the castle's own cellars. Suspicious of you for asking, frankly.",
    "That address smells like home. The owl is not falling for it.",
]

OWL_LOST_LINES = [
    "The owl returns hours later, exhausted, having found absolutely nowhere by that name.",
    "No such place exists on any map the owl recognises -- and owls recognise quite a lot of places.",
]

OWL_FAILED_LINES = [
    "The owl got halfway there, thought better of it, and came home empty-taloned.",
    "Something out there did not want to be found. The owl respects that, mostly.",
]

SUCCESS_LINES = [
    "The ink surges. Something that was hidden is hidden no longer.",
]


def pick(lines):
    return random.choice(lines)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Static frontend (built by `npm run build` in ../marauders-map, copied
# into ./dist by the Docker image)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------------------
# "Accio" people-search. SQL INJECTION LIVES HERE.
# ---------------------------------------------------------------------------

@app.route("/api/accio", methods=["POST"])
def accio_search():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")

    if not isinstance(query, str):
        return jsonify(success=False, message=pick(MALFORMED_LINES)), 400

    query = query.strip()
    if not query:
        return jsonify(success=False, message=pick(EMPTY_QUERY_LINES)), 400

    if len(query) > 300:
        return jsonify(success=False, message=pick(MALFORMED_LINES)), 400

    # --- VULNERABLE BY DESIGN -------------------------------------------
    # The query is concatenated directly into the SQL string.
    #   - The `visible=1` filter can be bypassed in-line, e.g.
    #       ' OR visible=0 --
    #     to surface Hermione's suppressed row without any UNION.
    #   - Exactly two columns are selected, so a two-column UNION, e.g.
    #       zzzz' UNION SELECT hostname, note FROM map_services --
    #       zzzz' UNION SELECT content, 'note' FROM map_notes --
    #       zzzz' UNION SELECT name, type FROM sqlite_master --
    #     can reach tables this endpoint was never meant to expose.
    sql = (
        "SELECT name, note FROM characters "
        "WHERE visible=1 AND name LIKE '%" + query + "%'"
    )

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except sqlite3.Error:
        return jsonify(success=False, message=pick(SERVER_ERROR_LINES)), 500
    # ----------------------------------------------------------------------

    if not rows:
        hint = None
        if "hermione" in query.lower() or "granger" in query.lower():
            hint = pick(HERMIONE_HINT_LINES)
        return jsonify(
            success=False,
            message=hint or pick(NO_RESULTS_LINES),
        )

    results = [{"name": r[0], "note": r[1]} for r in rows]

    revealed_hidden = any(
        "hermione granger" in (r["name"] or "").lower()
        or "map-internal" in (r["note"] or "").lower()
        or "mischief managed" in (r["note"] or "").lower()
        for r in results
    )

    return jsonify(
        success=True,
        message=pick(SUCCESS_LINES) if revealed_hidden else None,
        revealed_hidden=revealed_hidden,
        results=results,
    )


# ---------------------------------------------------------------------------
# "Send an Owl" -- the messaging feature. SSRF LIVES HERE.
# ---------------------------------------------------------------------------

# A naive blocklist. It stops the *obvious* loopback addresses, but has
# no idea that 'map-internal' is also, for all practical purposes,
# "home" -- it's just another plain hostname on the same internal
# docker network.
BLOCKED_SUBSTRINGS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.",
    "[::1]",
]


def fetch_address(address):
    """Shared SSRF sink. Returns a dict suitable for jsonify(**result)."""
    if not isinstance(address, str) or not address.strip():
        return {"success": False, "message": pick(MALFORMED_LINES), "status": 400}

    address = address.strip()

    if not (address.startswith("http://") or address.startswith("https://")):
        return {"success": False, "message": pick(MALFORMED_LINES), "status": 400}

    lowered = address.lower()
    if any(term in lowered for term in BLOCKED_SUBSTRINGS):
        return {"success": False, "message": pick(OWL_REFUSED_LINES), "status": 403}

    # --- VULNERABLE BY DESIGN -------------------------------------------
    # The server fetches whatever address it's given. The blocklist above
    # blocks loopback literals, but not internal service names on the
    # docker-internal network (e.g. 'map-internal').
    try:
        resp = requests.get(address, timeout=4)
        body = resp.text[:4000]
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": pick(OWL_LOST_LINES), "status": 502}
    except requests.exceptions.RequestException:
        return {"success": False, "message": pick(OWL_FAILED_LINES), "status": 502}
    # ----------------------------------------------------------------------

    flag_found = "kernel{" in body

    return {
        "success": True,
        "message": pick(SUCCESS_LINES) if flag_found else None,
        "status_code": resp.status_code,
        "body": body,
        "status": 200,
    }


@app.route("/api/owl", methods=["POST"])
def owl():
    """Public SSRF endpoint: POST /api/owl {"address": ...} fetches server-side."""
    data = request.get_json(silent=True) or {}
    address = data.get("address", "")
    result = fetch_address(address)
    status = result.pop("status")
    return jsonify(**result), status


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify(success=False, message="There is no such corridor on this map. Yet."), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify(success=False, message=pick(SERVER_ERROR_LINES)), 500


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        import seed
        seed.seed()
    app.run(host="0.0.0.0", port=5000, debug=False)
