#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Ensure .env exists ───────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "No .env found — copying from .env.example"
  cp .env.example .env
  echo "Please edit .env and add your ANTHROPIC_API_KEY, then re-run this script."
  exit 1
fi

# ── 2. Python virtual environment ───────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate

# Install requirements if needed (check by testing for fastapi)
if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing Python dependencies..."
  pip install -q -r backend/requirements.txt
fi

# ── 3. Start backend in background ──────────────────────────────────────────
echo "Starting backend (logs → /tmp/shiftready-backend.log)..."
cd "$SCRIPT_DIR/backend"
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload \
  > /tmp/shiftready-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
cd "$SCRIPT_DIR"

# ── 4. Start frontend ────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         ShiftReady is starting up        ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Frontend : http://localhost:5173         ║"
echo "║  Backend  : http://localhost:8000         ║"
echo "║  API docs : http://localhost:8000/docs    ║"
echo "║  Backend log: /tmp/shiftready-backend.log ║"
echo "╚══════════════════════════════════════════╝"
echo ""

npm run dev
