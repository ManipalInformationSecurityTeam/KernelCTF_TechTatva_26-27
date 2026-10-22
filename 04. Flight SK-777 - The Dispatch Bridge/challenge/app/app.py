#!/usr/bin/env python3
"""SkyNet Dispatch Bridge: crew portal challenge (flight SK-777).

Run:  python3 app/app.py          then open http://localhost:8080
Env:  PORT (default 8080), BIND (default 127.0.0.1)
"""
import os
import secrets

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "templates"),
    static_folder=os.path.join(BASE, "static"),
)
# Random per process: session cookies cannot be forged even if the source is read.
# Run with a single worker process (see DEPLOY.md) so every request sees the same key.
app.secret_key = secrets.token_hex(32)

VALID_ROLES = ["cabin_crew", "ground_staff", "flight_captain", "flight_engineer"]
REQUIRED_UA = "Webex-Desktop-Pro/2.0"
FLAG = "kernel{sk777_h34d3r_sp00f_c4ptain}"

MANIFESTS = {
    "manifest_SK102.json": {
        "flight_number": "SK-102",
        "status": "CLEARED",
        "required_role": "cabin_crew",
        "required_user_agent": "Standard",
    },
    "manifest_SK777.json": {
        "flight_number": "SK-777",
        "status": "RESTRICTED_CARGO",
        "required_role": "flight_captain",
        "required_user_agent": REQUIRED_UA,
    },
}
FLIGHTS = {"SK-102", "SK-777"}


@app.route("/robots.txt")
def robots():
    body = "User-agent: *\nDisallow: /flight-manifests/\n"
    return body, 200, {"Content-Type": "text/plain"}


@app.route("/flight-manifests/")
def open_directory():
    links = "".join(
        f'<a href="/flight-manifests/{name}">{name}</a><br>' for name in MANIFESTS
    )
    return (
        '<body style="background:#fff;font-family:monospace;padding:20px">'
        f"<h1>Index of /flight-manifests/</h1><hr>{links}<hr>"
        "<address>SkyNet File Server</address></body>"
    )


@app.route("/flight-manifests/<filename>")
def serve_manifest(filename):
    if filename not in MANIFESTS:
        return jsonify({"error": "File not found"}), 404
    return jsonify(MANIFESTS[filename])


@app.route("/")
def dashboard():
    if "role" not in session:
        session["role"] = "cabin_crew"
        session["flight_id"] = "SK-102"
    return render_template("dashboard.html", session=session)


@app.route("/api/v1/session/select-flight", methods=["POST"])
def update_session():
    # DELIBERATE VULNERABILITY: the role and flight are taken straight from the
    # request body. The server never checks that this crew member may hold them.
    role = request.form.get("role", "cabin_crew")
    flight_id = request.form.get("flight_id", "SK-102")

    if role not in VALID_ROLES:
        return jsonify({
            "error": "InvalidRoleException",
            "message": f"Role '{role}' is not recognized. Recognized SkyNet roles: {VALID_ROLES}",
        }), 400
    if flight_id not in FLIGHTS:
        return jsonify({"error": "UnknownFlight", "message": f"Flight '{flight_id}' not found."}), 404

    session["flight_id"] = flight_id
    session["role"] = role
    return redirect(url_for("dashboard"))


@app.route("/api/v1/webex/briefing/<flight_id>")
def get_briefing(flight_id):
    if session.get("flight_id") != flight_id:
        return jsonify({"error": "Session mismatch. Access Denied."}), 403
    if session.get("role") != "flight_captain":
        return jsonify({"error": "Insufficient privileges. Captain role required."}), 403
    if request.headers.get("User-Agent", "") != REQUIRED_UA:
        return jsonify({
            "error": "Forbidden",
            "message": "Access restricted. You must use the official Webex Desktop application.",
        }), 403

    if flight_id == "SK-777":
        return jsonify({
            "status": "success",
            "clearance": "verified",
            "briefing_data": f"Flight SK-777 cleared for pushback. Cargo verified. FLAG: {FLAG}",
        }), 200
    return jsonify({"status": "success", "briefing_data": "Standard briefing data."}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    bind = os.environ.get("BIND", "127.0.0.1")
    app.run(host=bind, port=port, debug=False, use_reloader=False)
