"""WSGI entry point for production servers.

Run from the challenge/ folder:
    gunicorn -w 1 --threads 8 -b 127.0.0.1:8000 wsgi:app
"""
from app.app import app  # noqa: F401
