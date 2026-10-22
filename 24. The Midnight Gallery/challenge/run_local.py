#!/usr/bin/env python3
"""Cross-platform launcher for app.py and diag_service.py."""
import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_SCRIPT = os.path.join(ROOT, "app", "app.py")
DIAG_SCRIPT = os.path.join(ROOT, "diag", "diag_service.py")


def main():
    env = os.environ.copy()
    env["DIAG_PORT"] = "9999"  # Add this line
    env["DIAG_URL"] = "http://127.0.0.1:9999/ping"  # Change this from 9000
    env["GALLERY_BIND"] = "127.0.0.1"
    env["DIAG_BIND"] = "127.0.0.1"

    diag_proc = subprocess.Popen([sys.executable, DIAG_SCRIPT], env=env)
    app_proc = subprocess.Popen([sys.executable, APP_SCRIPT], env=env)

    def shutdown(*_args):
        for p in (app_proc, diag_proc):
            if p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=2)
                except Exception:
                    p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            if diag_proc.poll() is not None or app_proc.poll() is not None:
                shutdown()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
