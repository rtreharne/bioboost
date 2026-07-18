#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8011}"
WORKERS="${WEB_CONCURRENCY:-1}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

cd "$ROOT_DIR"

exec "$ROOT_DIR/.venv/bin/gunicorn" config.wsgi:application \
  --bind "127.0.0.1:${PORT}" \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  --reload \
  --reload-extra-file "$ROOT_DIR/.env"
