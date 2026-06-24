from fastapi import Depends, FastAPI

from backend.api.routes.candidate_parsing import router as candidate_parsing_router
from backend.api.routes.candidates import router as candidates_router
from backend.api.routes.job_parsing import router as job_parsing_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.matching import router as matching_router
from backend.database.health import check_database_ready

app = FastAPI(title="AI Job Hunter CRM")
app.include_router(candidates_router)
app.include_router(candidate_parsing_router)
app.include_router(jobs_router)
app.include_router(job_parsing_router)
app.include_router(matching_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness_check(
    database_status: dict[str, str] = Depends(check_database_ready),
) -> dict[str, str]:
    return database_status
