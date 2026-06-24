import pytest

from backend.services.semantic_similarity import (
    EmbeddingCompatibilityError,
    cosine_similarity,
    ensure_compatible_embeddings,
    semantic_score_from_similarity,
)


def test_cosine_similarity_calculation() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_score_clamping() -> None:
    assert semantic_score_from_similarity(-0.12) == 0
    assert semantic_score_from_similarity(1.2) == 100


def test_decimal_half_up_conversion() -> None:
    assert semantic_score_from_similarity(0.8241) == 82
    assert semantic_score_from_similarity(0.825) == 83


def test_dimension_mismatch() -> None:
    with pytest.raises(EmbeddingCompatibilityError):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])

    with pytest.raises(EmbeddingCompatibilityError):
        ensure_compatible_embeddings(
            candidate_model_name="ollama:nomic-embed-text",
            candidate_dimensions=2,
            job_model_name="ollama:nomic-embed-text",
            job_dimensions=3,
        )


def test_model_mismatch() -> None:
    with pytest.raises(EmbeddingCompatibilityError):
        ensure_compatible_embeddings(
            candidate_model_name="ollama:nomic-embed-text",
            candidate_dimensions=2,
            job_model_name="ollama:other-model",
            job_dimensions=2,
        )


def test_repeated_output_is_deterministic() -> None:
    first_similarity = cosine_similarity([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    second_similarity = cosine_similarity([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])

    assert first_similarity == second_similarity
    assert semantic_score_from_similarity(first_similarity) == (
        semantic_score_from_similarity(second_similarity)
    )
