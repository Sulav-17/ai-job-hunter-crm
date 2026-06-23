from fastapi import Depends, FastAPI

from backend.database.health import check_database_ready

app = FastAPI(title="AI Job Hunter CRM")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness_check(
    database_status: dict[str, str] = Depends(check_database_ready),
) -> dict[str, str]:
    return database_status
