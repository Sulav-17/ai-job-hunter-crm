from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import math
import numbers
import re
from collections.abc import Iterable, Sequence


class MissingCandidateResumeTextError(ValueError):
    pass


class VectorValidationError(ValueError):
    pass


class EmbeddingCompatibilityError(ValueError):
    pass


@dataclass(frozen=True)
class EmbeddingVector:
    values: tuple[float, ...]

    @property
    def dimensions(self) -> int:
        return len(self.values)


def normalize_source_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def build_candidate_embedding_source(
    *,
    headline: str | None,
    professional_summary: str | None,
    resume_text: str | None,
) -> str:
    if resume_text is None or normalize_source_text(resume_text) == "":
        raise MissingCandidateResumeTextError("Candidate resume text is required")

    return _join_labeled_sections(
        (
            ("Headline", headline),
            ("Professional Summary", professional_summary),
            ("Resume Text", resume_text),
        ),
    )


def build_job_embedding_source(
    *,
    title: str,
    company: str,
    description: str,
) -> str:
    return _join_labeled_sections(
        (
            ("Title", title),
            ("Company", company),
            ("Description", description),
        ),
    )


def source_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def validate_embedding_vector(values: object) -> EmbeddingVector:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise VectorValidationError("Embedding vector must be a numeric sequence")

    vector: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise VectorValidationError("Embedding vector values must be numeric")
        float_value = float(value)
        if not math.isfinite(float_value):
            raise VectorValidationError("Embedding vector values must be finite")
        vector.append(float_value)

    if not vector:
        raise VectorValidationError("Embedding vector cannot be empty")

    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0:
        raise VectorValidationError("Embedding vector norm must be greater than zero")

    return EmbeddingVector(tuple(vector))


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    left_vector = validate_embedding_vector(left)
    right_vector = validate_embedding_vector(right)
    if left_vector.dimensions != right_vector.dimensions:
        raise EmbeddingCompatibilityError("Embedding dimensions do not match")

    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left_vector.values, right_vector.values)
    )
    left_norm = math.sqrt(sum(value * value for value in left_vector.values))
    right_norm = math.sqrt(sum(value * value for value in right_vector.values))
    return dot_product / (left_norm * right_norm)


def semantic_score_from_similarity(similarity: float) -> int:
    if not math.isfinite(similarity):
        raise VectorValidationError("Cosine similarity must be finite")
    clamped = max(0.0, min(1.0, similarity))
    value = Decimal(str(clamped)) * Decimal(100)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def ensure_compatible_embeddings(
    *,
    candidate_model_name: str,
    candidate_dimensions: int,
    job_model_name: str,
    job_dimensions: int,
) -> None:
    if candidate_model_name != job_model_name:
        raise EmbeddingCompatibilityError("Embedding models do not match")
    if candidate_dimensions != job_dimensions:
        raise EmbeddingCompatibilityError("Embedding dimensions do not match")


def _join_labeled_sections(sections: Sequence[tuple[str, str | None]]) -> str:
    lines: list[str] = []
    for label, value in sections:
        if value is None:
            continue
        normalized_value = normalize_source_text(value)
        if normalized_value == "":
            continue
        lines.append(f"{label}: {normalized_value}")
    return "\n".join(lines)
