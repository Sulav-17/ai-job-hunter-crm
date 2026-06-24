from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.candidate import CandidateProfile
from backend.models.embedding import (
    CandidateEmbedding,
    JobEmbedding,
    SemanticMatchResult,
)
from backend.models.job import JobPosting
from backend.schemas.embedding import (
    CandidateEmbeddingResponse,
    JobEmbeddingResponse,
    SemanticMatchResponse,
)
from backend.services.embedding_provider import EmbeddingProvider, EmbeddingProviderError
from backend.services.semantic_similarity import (
    EmbeddingCompatibilityError,
    MissingCandidateResumeTextError,
    VectorValidationError,
    build_candidate_embedding_source,
    build_job_embedding_source,
    cosine_similarity,
    ensure_compatible_embeddings,
    semantic_score_from_similarity,
    source_hash,
    validate_embedding_vector,
)


class CandidateNotFoundError(ValueError):
    pass


class JobNotFoundError(ValueError):
    pass


class CandidateResumeTextRequiredError(ValueError):
    pass


class CandidateEmbeddingNotFoundError(ValueError):
    pass


class JobEmbeddingNotFoundError(ValueError):
    pass


class CandidateEmbeddingMissingOrStaleError(ValueError):
    pass


class JobEmbeddingMissingOrStaleError(ValueError):
    pass


class EmbeddingProviderUnavailableError(RuntimeError):
    pass


class EmbeddingIncompatibilityError(ValueError):
    pass


class SemanticMatchResultNotFoundError(ValueError):
    pass


def create_or_update_candidate_embedding(
    db: Session,
    candidate_id: int,
    provider: EmbeddingProvider,
) -> CandidateEmbeddingResponse:
    candidate = _get_candidate_or_raise(db, candidate_id)
    source_text = _candidate_source_or_raise(candidate)
    hash_value = source_hash(source_text)
    current_embedding = _get_candidate_embedding(db, candidate_id)

    if _embedding_is_current(current_embedding, provider.model_identity, hash_value):
        return _candidate_embedding_response(
            current_embedding,
            stale=False,
        )

    vector = _embed_source_or_raise(provider, source_text)

    try:
        if current_embedding is None:
            current_embedding = CandidateEmbedding(candidate_id=candidate_id)
            db.add(current_embedding)

        current_embedding.model_name = provider.model_identity
        current_embedding.dimensions = vector.dimensions
        current_embedding.source_hash = hash_value
        current_embedding.embedding = list(vector.values)
        current_embedding.embedded_at = func.now()
        db.commit()
        db.refresh(current_embedding)
    except SQLAlchemyError:
        db.rollback()
        raise

    return _candidate_embedding_response(current_embedding, stale=False)


def get_candidate_embedding_metadata(
    db: Session,
    candidate_id: int,
    provider: EmbeddingProvider,
) -> CandidateEmbeddingResponse:
    candidate = _get_candidate_or_raise(db, candidate_id)
    embedding = _get_candidate_embedding(db, candidate_id)
    if embedding is None:
        raise CandidateEmbeddingNotFoundError("Candidate embedding not found")

    stale = _candidate_embedding_stale(candidate, embedding, provider.model_identity)
    return _candidate_embedding_response(embedding, stale=stale)


def create_or_update_job_embedding(
    db: Session,
    job_id: int,
    provider: EmbeddingProvider,
) -> JobEmbeddingResponse:
    job = _get_job_or_raise(db, job_id)
    source_text = _job_source(job)
    hash_value = source_hash(source_text)
    current_embedding = _get_job_embedding(db, job_id)

    if _embedding_is_current(current_embedding, provider.model_identity, hash_value):
        return _job_embedding_response(current_embedding, stale=False)

    vector = _embed_source_or_raise(provider, source_text)

    try:
        if current_embedding is None:
            current_embedding = JobEmbedding(job_id=job_id)
            db.add(current_embedding)

        current_embedding.model_name = provider.model_identity
        current_embedding.dimensions = vector.dimensions
        current_embedding.source_hash = hash_value
        current_embedding.embedding = list(vector.values)
        current_embedding.embedded_at = func.now()
        db.commit()
        db.refresh(current_embedding)
    except SQLAlchemyError:
        db.rollback()
        raise

    return _job_embedding_response(current_embedding, stale=False)


def get_job_embedding_metadata(
    db: Session,
    job_id: int,
    provider: EmbeddingProvider,
) -> JobEmbeddingResponse:
    job = _get_job_or_raise(db, job_id)
    embedding = _get_job_embedding(db, job_id)
    if embedding is None:
        raise JobEmbeddingNotFoundError("Job embedding not found")

    stale = _job_embedding_stale(job, embedding, provider.model_identity)
    return _job_embedding_response(embedding, stale=stale)


def calculate_and_persist_semantic_match(
    db: Session,
    candidate_id: int,
    job_id: int,
    provider: EmbeddingProvider,
) -> SemanticMatchResponse:
    candidate = _get_candidate_or_raise(db, candidate_id)
    job = _get_job_or_raise(db, job_id)
    candidate_embedding = _current_candidate_embedding_or_raise(
        candidate,
        _get_candidate_embedding(db, candidate_id),
        provider.model_identity,
    )
    job_embedding = _current_job_embedding_or_raise(
        job,
        _get_job_embedding(db, job_id),
        provider.model_identity,
    )

    try:
        ensure_compatible_embeddings(
            candidate_model_name=candidate_embedding.model_name,
            candidate_dimensions=candidate_embedding.dimensions,
            job_model_name=job_embedding.model_name,
            job_dimensions=job_embedding.dimensions,
        )
    except EmbeddingCompatibilityError as exc:
        raise EmbeddingIncompatibilityError(
            "Candidate and job embeddings are incompatible",
        ) from exc

    similarity = cosine_similarity(
        candidate_embedding.embedding,
        job_embedding.embedding,
    )
    score = semantic_score_from_similarity(similarity)

    try:
        result = db.scalar(
            select(SemanticMatchResult).where(
                SemanticMatchResult.candidate_id == candidate_id,
                SemanticMatchResult.job_id == job_id,
            ),
        )
        if result is None:
            result = SemanticMatchResult(
                candidate_id=candidate_id,
                job_id=job_id,
            )
            db.add(result)

        result.cosine_similarity = Decimal(str(similarity))
        result.semantic_score = score
        result.model_name = candidate_embedding.model_name
        result.candidate_source_hash = candidate_embedding.source_hash
        result.job_source_hash = job_embedding.source_hash
        result.calculated_at = func.now()
        db.commit()
        db.refresh(result)
    except SQLAlchemyError:
        db.rollback()
        raise

    return _semantic_match_response(result)


def get_semantic_match_result(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> SemanticMatchResponse:
    _get_candidate_or_raise(db, candidate_id)
    _get_job_or_raise(db, job_id)
    result = db.scalar(
        select(SemanticMatchResult).where(
            SemanticMatchResult.candidate_id == candidate_id,
            SemanticMatchResult.job_id == job_id,
        ),
    )
    if result is None:
        raise SemanticMatchResultNotFoundError("Semantic match result not found")
    return _semantic_match_response(result)


def _get_candidate_or_raise(db: Session, candidate_id: int) -> CandidateProfile:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError("Candidate not found")
    return candidate


def _get_job_or_raise(db: Session, job_id: int) -> JobPosting:
    job = db.get(JobPosting, job_id)
    if job is None:
        raise JobNotFoundError("Job not found")
    return job


def _get_candidate_embedding(
    db: Session,
    candidate_id: int,
) -> CandidateEmbedding | None:
    return db.scalar(
        select(CandidateEmbedding).where(
            CandidateEmbedding.candidate_id == candidate_id,
        ),
    )


def _get_job_embedding(db: Session, job_id: int) -> JobEmbedding | None:
    return db.scalar(select(JobEmbedding).where(JobEmbedding.job_id == job_id))


def _candidate_source_or_raise(candidate: CandidateProfile) -> str:
    try:
        return build_candidate_embedding_source(
            headline=candidate.headline,
            professional_summary=candidate.professional_summary,
            resume_text=candidate.resume_text,
        )
    except MissingCandidateResumeTextError as exc:
        raise CandidateResumeTextRequiredError(
            "Candidate resume text is required",
        ) from exc


def _job_source(job: JobPosting) -> str:
    return build_job_embedding_source(
        title=job.title,
        company=job.company,
        description=job.description,
    )


def _embed_source_or_raise(provider: EmbeddingProvider, source_text: str):
    try:
        provider_vector = provider.embed(source_text)
        return validate_embedding_vector(provider_vector)
    except (EmbeddingProviderError, VectorValidationError) as exc:
        raise EmbeddingProviderUnavailableError(
            "Embedding provider unavailable",
        ) from exc


def _embedding_is_current(
    embedding: CandidateEmbedding | JobEmbedding | None,
    model_identity: str,
    hash_value: str,
) -> bool:
    return (
        embedding is not None
        and embedding.model_name == model_identity
        and embedding.source_hash == hash_value
    )


def _candidate_embedding_stale(
    candidate: CandidateProfile,
    embedding: CandidateEmbedding,
    model_identity: str,
) -> bool:
    try:
        hash_value = source_hash(_candidate_source_or_raise(candidate))
    except CandidateResumeTextRequiredError:
        return True
    return not _embedding_is_current(embedding, model_identity, hash_value)


def _job_embedding_stale(
    job: JobPosting,
    embedding: JobEmbedding,
    model_identity: str,
) -> bool:
    hash_value = source_hash(_job_source(job))
    return not _embedding_is_current(embedding, model_identity, hash_value)


def _current_candidate_embedding_or_raise(
    candidate: CandidateProfile,
    embedding: CandidateEmbedding | None,
    model_identity: str,
) -> CandidateEmbedding:
    if embedding is None or _candidate_embedding_stale(candidate, embedding, model_identity):
        raise CandidateEmbeddingMissingOrStaleError(
            "Candidate embedding is missing or stale",
        )
    return embedding


def _current_job_embedding_or_raise(
    job: JobPosting,
    embedding: JobEmbedding | None,
    model_identity: str,
) -> JobEmbedding:
    if embedding is None or _job_embedding_stale(job, embedding, model_identity):
        raise JobEmbeddingMissingOrStaleError(
            "Job embedding is missing or stale",
        )
    return embedding


def _candidate_embedding_response(
    embedding: CandidateEmbedding,
    stale: bool,
) -> CandidateEmbeddingResponse:
    return CandidateEmbeddingResponse(
        candidate_id=embedding.candidate_id,
        model_name=embedding.model_name,
        dimensions=embedding.dimensions,
        source_hash=embedding.source_hash,
        embedded_at=embedding.embedded_at,
        stale=stale,
    )


def _job_embedding_response(
    embedding: JobEmbedding,
    stale: bool,
) -> JobEmbeddingResponse:
    return JobEmbeddingResponse(
        job_id=embedding.job_id,
        model_name=embedding.model_name,
        dimensions=embedding.dimensions,
        source_hash=embedding.source_hash,
        embedded_at=embedding.embedded_at,
        stale=stale,
    )


def _semantic_match_response(result: SemanticMatchResult) -> SemanticMatchResponse:
    return SemanticMatchResponse(
        candidate_id=result.candidate_id,
        job_id=result.job_id,
        cosine_similarity=float(result.cosine_similarity),
        semantic_score=result.semantic_score,
        model_name=result.model_name,
        candidate_source_hash=result.candidate_source_hash,
        job_source_hash=result.job_source_hash,
        calculated_at=result.calculated_at,
    )
