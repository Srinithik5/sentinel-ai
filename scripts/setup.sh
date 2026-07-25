```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created .env from .env.example"
fi
echo "Installing frontend dependencies..."
(cd "$ROOT_DIR/frontend" && npm install)
echo "Setting up backend virtual environment..."
(cd "$ROOT_DIR/backend" && python3 -m venv .venv && \
  .venv/bin/pip install --upgrade pip && \
  .venv/bin/pip install -r requirements.txt -r requirements-dev.txt)
echo "Installing AI engine dependencies..."
(cd "$ROOT_DIR/ai-engine" && python3 -m venv .venv && \
  .venv/bin/pip install --upgrade pip && \
  .venv/bin/pip install -r requirements.txt)
echo "Setup complete."