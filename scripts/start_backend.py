from __future__ import annotations

import os
import subprocess
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.config import get_settings
from backend.services.demo_seed import seed_demo_dataset
from backend.database.session import session_scope


def main() -> None:
    settings = get_settings()
    _wait_for_database(settings.database_url)
    _run_alembic_upgrade()
    _seed_demo_if_configured(settings.app_mode, settings.demo_seed_on_startup)
    port = os.getenv("PORT", "8000")
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    )


def _wait_for_database(database_url: str) -> None:
    deadline = time.monotonic() + 60
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except SQLAlchemyError as exc:
            last_error = exc
            time.sleep(1)
        finally:
            engine.dispose()
    raise RuntimeError("Database did not become ready") from last_error


def _run_alembic_upgrade() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )


def _seed_demo_if_configured(app_mode: str, seed_on_startup: bool) -> None:
    if not seed_on_startup:
        return
    if app_mode != "demo":
        raise RuntimeError("DEMO_SEED_ON_STARTUP=true is only allowed in APP_MODE=demo")
    with session_scope() as session:
        report = seed_demo_dataset(session)
    print(f"Demo seed complete: {report.as_dict()}")


if __name__ == "__main__":
    main()
