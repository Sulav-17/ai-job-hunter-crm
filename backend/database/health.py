from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.database.session import session_scope


def check_database_ready() -> dict[str, str]:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1")).scalar_one()
    except (ValidationError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return {"status": "ready", "database": "ok"}
