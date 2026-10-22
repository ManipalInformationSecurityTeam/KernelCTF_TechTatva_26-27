#!/usr/bin/env bash
# Deploy The Midnight Gallery with Docker and verify the full chain.
#   ./deploy.sh              serves on port 8080
#   PORT=9000 ./deploy.sh    serves on port 9000
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8080}"

command -v docker >/dev/null 2>&1 || { echo "Docker is required: https://docs.docker.com/get-docker/"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required (docker compose)."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required for the verification step."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required for the readiness check."; exit 1; }

echo "Building and starting the containers..."
docker compose up -d --build

echo "Waiting for the gateway on port ${PORT}..."
for _ in $(seq 1 60); do
  if curl -fs -o /dev/null -H "X-Forwarded-For: 127.0.0.1" "http://127.0.0.1:${PORT}/"; then
    break
  fi
  sleep 1
done

echo "Verifying the full solve chain..."
if python3 solve/solve.py "http://127.0.0.1:${PORT}"; then
  echo
  echo "DEPLOYED. Players connect to: http://<this-server-address>:${PORT}"
else
  echo
  echo "Verification FAILED. Check logs with: docker compose logs"
  exit 1
fi
