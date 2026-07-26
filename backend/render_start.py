#!/usr/bin/env python3
"""
Render start script for the Sentinel AI backend.

Render provides DATABASE_URL as postgres:// but our app uses SQLAlchemy with
the asyncpg driver, which requires postgresql+asyncpg://.  This script
rewrites the URL, runs Alembic migrations, then starts Uvicorn.
"""

import os
import re
import subprocess
import sys


def main() -> None:
    # ── Rewrite DATABASE_URL for asyncpg ──────────────────────────────────
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        db_url = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", db_url)
        os.environ["DATABASE_URL"] = db_url
        print(f"[render-start] DATABASE_URL driver rewritten to asyncpg")

    # ── Run Alembic migrations ────────────────────────────────────────────
    print("[render-start] Running database migrations …")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
    )
    if result.returncode != 0:
        print("[render-start] ⚠ Migrations failed – starting server anyway")

    # ── Start Uvicorn ─────────────────────────────────────────────────────
    port = os.environ.get("PORT", "8000")
    print(f"[render-start] Starting Uvicorn on port {port} …")
    os.execvp(
        sys.executable,
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", port,
        ],
    )


if __name__ == "__main__":
    main()
