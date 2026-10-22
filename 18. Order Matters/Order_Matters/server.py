"""Backward-compatible launcher. The application implementation lives in app.py."""
from app import *  # noqa: F401,F403

if __name__ == "__main__":
    main()
