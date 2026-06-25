from fastapi import Depends, FastAPI

from backend.api.routes.applications import router as applications_router
from backend.api.routes.candidate_parsing import router as candidate_parsing_router
from backend.api.routes.candidates import router as candidates_router
from backend.api.routes.embeddings import router as embeddings_router
from backend.api.routes.job_parsing import router as job_parsing_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.matching import router as matching_router
from backend.api.routes.tailoring import router as tailoring_router
from backend.core.config import Settings, get_settings
from backend.core.mode import app_info_payload
from backend.database.health import check_database_ready

app = FastAPI(title="AI Job Hunter CRM")
app.include_router(applications_router)
app.include_router(candidates_router)
app.include_router(candidate_parsing_router)
app.include_router(embeddings_router)
app.include_router(jobs_router)
app.include_router(job_parsing_router)
app.include_router(matching_router)
app.include_router(tailoring_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/app-info")
def app_info(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return app_info_payload(settings)


@app.get("/ready")
def readiness_check(
    database_status: dict[str, str] = Depends(check_database_ready),
) -> dict[str, str]:
    return database_status
