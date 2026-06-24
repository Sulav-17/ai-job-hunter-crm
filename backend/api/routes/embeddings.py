from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.session import get_database_session
from backend.schemas.embedding import (
    CandidateEmbeddingResponse,
    JobEmbeddingResponse,
    SemanticMatchResponse,
)
from backend.services import embedding_service
from backend.services.embedding_provider import EmbeddingProvider
from backend.services.ollama_embedding_provider import OllamaEmbeddingProvider

router = APIRouter(tags=["embeddings"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    return OllamaEmbeddingProvider(
        model_name=settings.embedding_model,
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.embedding_timeout_seconds,
    )


EmbeddingProviderDependency = Annotated[
    EmbeddingProvider,
    Depends(get_embedding_provider),
]


@router.post(
    "/candidates/{candidate_id}/embedding",
    response_model=CandidateEmbeddingResponse,
)
def create_candidate_embedding(
    candidate_id: int,
    db: DatabaseSession,
    provider: EmbeddingProviderDependency,
):
    try:
        return embedding_service.create_or_update_candidate_embedding(
            db,
            candidate_id,
            provider,
        )
    except embedding_service.CandidateNotFoundError as exc:
        raise _not_found("Candidate not found") from exc
    except embedding_service.CandidateResumeTextRequiredError as exc:
        raise _conflict("Candidate resume text is required") from exc
    except embedding_service.EmbeddingProviderUnavailableError as exc:
        raise _bad_gateway("Embedding provider unavailable") from exc


@router.get(
    "/candidates/{candidate_id}/embedding",
    response_model=CandidateEmbeddingResponse,
)
def get_candidate_embedding(
    candidate_id: int,
    db: DatabaseSession,
    provider: EmbeddingProviderDependency,
):
    try:
        return embedding_service.get_candidate_embedding_metadata(
            db,
            candidate_id,
            provider,
        )
    except embedding_service.CandidateNotFoundError as exc:
        raise _not_found("Candidate not found") from exc
    except embedding_service.CandidateEmbeddingNotFoundError as exc:
        raise _not_found("Candidate embedding not found") from exc


@router.post("/jobs/{job_id}/embedding", response_model=JobEmbeddingResponse)
def create_job_embedding(
    job_id: int,
    db: DatabaseSession,
    provider: EmbeddingProviderDependency,
):
    try:
        return embedding_service.create_or_update_job_embedding(db, job_id, provider)
    except embedding_service.JobNotFoundError as exc:
        raise _not_found("Job not found") from exc
    except embedding_service.EmbeddingProviderUnavailableError as exc:
        raise _bad_gateway("Embedding provider unavailable") from exc


@router.get("/jobs/{job_id}/embedding", response_model=JobEmbeddingResponse)
def get_job_embedding(
    job_id: int,
    db: DatabaseSession,
    provider: EmbeddingProviderDependency,
):
    try:
        return embedding_service.get_job_embedding_metadata(db, job_id, provider)
    except embedding_service.JobNotFoundError as exc:
        raise _not_found("Job not found") from exc
    except embedding_service.JobEmbeddingNotFoundError as exc:
        raise _not_found("Job embedding not found") from exc


@router.post(
    "/candidates/{candidate_id}/jobs/{job_id}/semantic-match",
    response_model=SemanticMatchResponse,
)
def calculate_semantic_match(
    candidate_id: int,
    job_id: int,
    db: DatabaseSession,
    provider: EmbeddingProviderDependency,
):
    try:
        return embedding_service.calculate_and_persist_semantic_match(
            db,
            candidate_id,
            job_id,
            provider,
        )
    except embedding_service.CandidateNotFoundError as exc:
        raise _not_found("Candidate not found") from exc
    except embedding_service.JobNotFoundError as exc:
        raise _not_found("Job not found") from exc
    except embedding_service.CandidateEmbeddingMissingOrStaleError as exc:
        raise _conflict("Candidate embedding is missing or stale") from exc
    except embedding_service.JobEmbeddingMissingOrStaleError as exc:
        raise _conflict("Job embedding is missing or stale") from exc
    except embedding_service.EmbeddingIncompatibilityError as exc:
        raise _conflict("Candidate and job embeddings are incompatible") from exc


@router.get(
    "/candidates/{candidate_id}/jobs/{job_id}/semantic-match-result",
    response_model=SemanticMatchResponse,
)
def get_semantic_match_result(
    candidate_id: int,
    job_id: int,
    db: DatabaseSession,
):
    try:
        return embedding_service.get_semantic_match_result(db, candidate_id, job_id)
    except embedding_service.CandidateNotFoundError as exc:
        raise _not_found("Candidate not found") from exc
    except embedding_service.JobNotFoundError as exc:
        raise _not_found("Job not found") from exc
    except embedding_service.SemanticMatchResultNotFoundError as exc:
        raise _not_found("Semantic match result not found") from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _bad_gateway(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
