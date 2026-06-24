from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.session import get_database_session
from backend.schemas.tailoring import TailoringGenerateRequest, TailoringResultResponse
from backend.services import tailoring_service
from backend.services.generation_provider import GenerationProvider
from backend.services.ollama_generation_provider import OllamaGenerationProvider

router = APIRouter(prefix="/candidates", tags=["tailoring"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_generation_provider() -> GenerationProvider:
    settings = get_settings()
    return OllamaGenerationProvider(
        model_name=settings.generation_model,
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.generation_timeout_seconds,
    )


GenerationProviderDependency = Annotated[
    GenerationProvider,
    Depends(get_generation_provider),
]


@router.post(
    "/{candidate_id}/jobs/{job_id}/tailoring",
    response_model=TailoringResultResponse,
)
def generate_tailoring(
    candidate_id: int,
    job_id: int,
    db: DatabaseSession,
    provider: GenerationProviderDependency,
    request: TailoringGenerateRequest = Body(
        default_factory=TailoringGenerateRequest,
    ),
):
    try:
        return tailoring_service.generate_tailoring_result(
            db,
            candidate_id,
            job_id,
            request,
            provider,
        )
    except tailoring_service.CandidateNotFoundError as exc:
        raise _not_found("Candidate not found") from exc
    except tailoring_service.JobNotFoundError as exc:
        raise _not_found("Job not found") from exc
    except tailoring_service.CandidateResumeTextRequiredError as exc:
        raise _conflict("Candidate resume text is required") from exc
    except tailoring_service.CandidateUnparsedError as exc:
        raise _conflict("Candidate must be parsed before tailoring") from exc
    except tailoring_service.JobUnparsedError as exc:
        raise _conflict("Job must be parsed before tailoring") from exc
    except tailoring_service.GenerationProviderUnavailableError as exc:
        raise _bad_gateway("Generation provider unavailable") from exc
    except tailoring_service.GenerationProviderInvalidOutputError as exc:
        raise _bad_gateway("Generation provider returned invalid output") from exc


@router.get(
    "/{candidate_id}/jobs/{job_id}/tailoring-result",
    response_model=TailoringResultResponse,
)
def get_tailoring_result(
    candidate_id: int,
    job_id: int,
    db: DatabaseSession,
    provider: GenerationProviderDependency,
):
    try:
        return tailoring_service.get_tailoring_result(
            db,
            candidate_id,
            job_id,
            provider,
        )
    except tailoring_service.CandidateNotFoundError as exc:
        raise _not_found("Candidate not found") from exc
    except tailoring_service.JobNotFoundError as exc:
        raise _not_found("Job not found") from exc
    except tailoring_service.TailoringResultNotFoundError as exc:
        raise _not_found("Tailoring result not found") from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _bad_gateway(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
