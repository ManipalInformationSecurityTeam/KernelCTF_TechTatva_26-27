#!/usr/bin/env bash
# Stops the stack, wipes the seeded DB and rebuilds images from scratch.
set -euo pipefail
cd "$(dirname "$0")"
docker compose down -v
docker compose build --no-cache
echo "Reset complete. Run 'docker compose up' to start fresh."
