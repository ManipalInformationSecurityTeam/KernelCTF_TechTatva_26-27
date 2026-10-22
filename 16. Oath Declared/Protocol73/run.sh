#!/usr/bin/env bash
set -euo pipefail
: "${P73_FLASK_SECRET:?Set P73_FLASK_SECRET before starting Protocol 73}"
DEFAULT_WORKERS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT:-5000}" \
  --workers "${P73_WORKERS:-$DEFAULT_WORKERS}" \
  --worker-class gthread \
  --threads "${P73_THREADS:-1}" \
  --timeout "${P73_TIMEOUT:-45}" \
  --graceful-timeout 10 \
  --keep-alive 5 \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --access-logfile -
