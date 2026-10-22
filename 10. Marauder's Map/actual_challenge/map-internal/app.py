"""
map-internal -- the internal-only service reachable at the end of the
SSRF chain.

Deliberately NOT exposed to the host machine. It only lives on the
Docker-internal network, reachable by other containers under the
hostname 'map-internal' on port 5001.

Routes:
  GET /                                 -> banner
  GET /people                           -> internal personnel recon (flavor)
  GET /archive                          -> lists archive rooms (locked)
  GET /archive/room-of-requirement      -> requires ?phrase=..., returns the flag
"""

from flask import Flask, request

app = Flask(__name__)

FLAG = "kernel{7h3_m4p_r3m3mb3rs_wh4t_y0u_h1d3}"
ARCHIVE_PHRASE = "mischief managed"

WRONG_PHRASE_LINES = [
    "The wall remains a wall. The Room of Requirement did not recognise that phrase.",
    "Nothing happens. Somewhere, Filch smiles.",
    "The stone stays stone. Try remembering your own ending.",
]


def _text(body, status=200):
    return (body, status, {"Content-Type": "text/plain"})



@app.route("/")
def index():
    return _text(
        "map-internal service. Castle infrastructure only.\n"
        "Not for owls that don't know where they're going.\n\n"
        "Available internal routes:\n"
        "  /people   - Internal personnel index\n"
        "  /archive  - Archive rooms and restricted records\n"
    )


@app.route("/people")
def people():
    return _text(
        "Internal personnel index (partial):\n"
        "- H. Granger -- status: withheld from public map (see castle DB)\n"
        "- Filch -- grounds, nights\n"
        "- Peeves -- unaffiliated, unmanageable\n"
        "\nThis index does not contain the flag. Keep looking.\n"
    )


@app.route("/archive")
def archive():
    return _text(
        "Archive rooms:\n"
        "  /archive/room-of-requirement  (requires ?phrase=...)\n"
    )


@app.route("/archive/room-of-requirement")
def room_of_requirement():
    phrase = (request.args.get("phrase") or "").strip().lower()

    if not phrase:
        return _text(
            "The door does not appear. You must know what to ask it for.",
            400,
        )

    if phrase != ARCHIVE_PHRASE:
        import random
        return _text(random.choice(WRONG_PHRASE_LINES), 403)

    return _text(
        "The wall dissolves into a doorway.\n"
        "Inside, a single shelf, and a single parchment:\n\n"
        f"{FLAG}\n\n"
        "Mischief, it turns out, has been managed.\n"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
