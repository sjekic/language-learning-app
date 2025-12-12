#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"

AUTH_SERVICE_PORT="${AUTH_SERVICE_PORT:-8001}"
USER_SERVICE_PORT="${USER_SERVICE_PORT:-8002}"
BOOK_SERVICE_PORT="${BOOK_SERVICE_PORT:-8003}"
TRANSLATION_SERVICE_PORT="${TRANSLATION_SERVICE_PORT:-8004}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

load_env_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$f"
    set +a
  fi
}

# Load env vars (both supported; .env.local wins if both define same key)
load_env_file "$ROOT_DIR/.env"
load_env_file "$ROOT_DIR/.env.local"

export AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:${AUTH_SERVICE_PORT}}"
export VITE_AUTH_SERVICE_URL="${VITE_AUTH_SERVICE_URL:-$AUTH_SERVICE_URL}"
export VITE_USER_SERVICE_URL="${VITE_USER_SERVICE_URL:-http://localhost:${USER_SERVICE_PORT}}"
export VITE_BOOK_SERVICE_URL="${VITE_BOOK_SERVICE_URL:-http://localhost:${BOOK_SERVICE_PORT}}"
export VITE_TRANSLATION_SERVICE_URL="${VITE_TRANSLATION_SERVICE_URL:-http://localhost:${TRANSLATION_SERVICE_PORT}}"

# Other services call auth-service internally
export AUTH_SERVICE_URL="${AUTH_SERVICE_URL}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd npm
require_cmd "$PYTHON_BIN"

if ! "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
  echo "Python module 'uvicorn' not found for $PYTHON_BIN." >&2
  echo "Install deps for each service (see services/README.md) or ensure your venv is active." >&2
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set." >&2
  echo "Create a root .env.local (recommended) or .env and set DATABASE_URL (Azure Postgres is fine)." >&2
  echo "Example template: env.example" >&2
  exit 1
fi

check_port_free() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "Port $port is already in use. Stop the process using it, or override the port env var." >&2
      exit 1
    fi
  fi
}

check_port_free "$AUTH_SERVICE_PORT"
check_port_free "$USER_SERVICE_PORT"
check_port_free "$BOOK_SERVICE_PORT"
check_port_free "$TRANSLATION_SERVICE_PORT"
check_port_free "$FRONTEND_PORT"

pids=()

cleanup() {
  local code=$?
  if [[ ${#pids[@]} -gt 0 ]]; then
    echo ""
    echo "Stopping services..."
    for pid in "${pids[@]}"; do
      kill "$pid" >/dev/null 2>&1 || true
    done
  fi
  exit "$code"
}

trap cleanup INT TERM EXIT

start_uvicorn() {
  local name="$1"
  local dir="$2"
  local port="$3"

  echo "Starting $name on :$port"
  (
    cd "$ROOT_DIR/$dir"
    exec "$PYTHON_BIN" -m uvicorn main:app \
      --reload \
      --host 0.0.0.0 \
      --port "$port"
  ) &
  pids+=("$!")
}

start_uvicorn "auth-service" "services/auth-service" "$AUTH_SERVICE_PORT"
start_uvicorn "user-service" "services/user-service" "$USER_SERVICE_PORT"
start_uvicorn "book-service" "services/book-service" "$BOOK_SERVICE_PORT"
start_uvicorn "translation-service" "services/translation-service" "$TRANSLATION_SERVICE_PORT"

echo ""
echo "Starting frontend (Vite) on :$FRONTEND_PORT"
echo "  VITE_AUTH_SERVICE_URL=$VITE_AUTH_SERVICE_URL"
echo "  VITE_USER_SERVICE_URL=$VITE_USER_SERVICE_URL"
echo "  VITE_BOOK_SERVICE_URL=$VITE_BOOK_SERVICE_URL"
echo "  VITE_TRANSLATION_SERVICE_URL=$VITE_TRANSLATION_SERVICE_URL"
echo ""

cd "$ROOT_DIR/frontend"
exec npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"


