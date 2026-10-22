#!/usr/bin/env python3
import socketserver
import subprocess
import os

PORT = 1337
# The player executable beside this script is reference-only.
# Run the interactive server executable from the project directory.
BINARY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RSP")
CHALLENGE_DIR = os.path.dirname(os.path.abspath(__file__))

class CTFHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            # Fork child process with stdin/stdout mapped directly to socket fd
            proc = subprocess.Popen(
                [BINARY],
                stdin=self.rfile,
                stdout=self.wfile,
                stderr=self.wfile,
                cwd=CHALLENGE_DIR
            )
            proc.wait(timeout=30)
        except Exception:
            pass

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"[*] Serving RSP challenge on port {PORT}...")
    server = ThreadedTCPServer(("0.0.0.0", PORT), CTFHandler)
    server.serve_forever()
