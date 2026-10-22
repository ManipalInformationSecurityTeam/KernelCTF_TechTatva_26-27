#!/usr/bin/env python3
"""Internal diagnostics microservice (cross-platform Linux & Windows)."""
import os
import re
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("DIAG_PORT", "9000"))
BIND = os.environ.get("DIAG_BIND", "127.0.0.1")
# Commands run in this folder, so `ls` shows shard3.txt and `cat shard3.txt` reads it,
# on Linux, Windows, and inside the container alike.
HERE = os.path.dirname(os.path.abspath(__file__))


def run_ping_command(ip_input):
    if os.name == "nt":
        full_cmd = f"ping -n 1 {ip_input}"
        full_cmd = full_cmd.replace(";", "&")
        full_cmd = re.sub(r"\bcat\b", "type", full_cmd)
        full_cmd = re.sub(r"\bls\b", "dir", full_cmd)
    else:
        full_cmd = f"ping -c 1 -W 1 {ip_input}"

    try:
        proc = subprocess.run(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            text=True,
            cwd=HERE,
        )
        return proc.stdout
    except subprocess.TimeoutExpired:
        return "ping: request timed out\n"
    except Exception as exc:
        return f"error: {exc}\n"


class DiagHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ping":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace")
        params = urllib.parse.parse_qs(raw)
        ip = params.get("ip", ["127.0.0.1"])[0]

        output = run_ping_command(ip).encode("utf-8", "replace")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer((BIND, PORT), DiagHandler).serve_forever()
