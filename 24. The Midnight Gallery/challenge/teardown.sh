#!/usr/bin/env bash
# Stop and remove the challenge containers.
set -euo pipefail
cd "$(dirname "$0")"
docker compose down
