import pytest

from backend.services.semantic_similarity import (
    MissingCandidateResumeTextError,
    VectorValidationError,
    build_candidate_embedding_source,
    build_job_embedding_source,
    source_hash,
    validate_embedding_vector,
)


def test_candidate_source_construction_is_deterministic() -> None:
    source = build_candidate_embedding_source(
        headline="  Fictional Analyst  ",
        professional_summary="Builds   local reporting workflows.",
        resume_text="Uses Python and SQL in fictional projects.",
    )

    assert source == (
        "Headline: Fictional Analyst\n"
        "Professional Summary: Builds local reporting workflows.\n"
        "Resume Text: Uses Python and SQL in fictional projects."
    )
    assert source == build_candidate_embedding_source(
        headline="Fictional Analyst",
        professional_summary="Builds local reporting workflows.",
        resume_text="Uses Python and SQL in fictional projects.",
    )


def test_candidate_source_requires_nonblank_resume_text() -> None:
    with pytest.raises(MissingCandidateResumeTextError):
        build_candidate_embedding_source(
            headline="Fictional Analyst",
            professional_summary="Fictional summary.",
            resume_text="   ",
        )


def test_job_source_construction_is_deterministic() -> None:
    source = build_job_embedding_source(
        title="  Fictional Data Analyst ",
        company="Northstar   Labs",
        description="Build dashboards\nand document decisions.",
    )

    assert source == (
        "Title: Fictional Data Analyst\n"
        "Company: Northstar Labs\n"
        "Description: Build dashboards and document decisions."
    )


def test_source_hash_uses_exact_normalized_source() -> None:
    source = "Resume Text: Fictional source"

    assert source_hash(source) == source_hash(source)
    assert source_hash(source) != source_hash("Resume Text: Different fictional source")
    assert len(source_hash(source)) == 64


def test_valid_vector_acceptance() -> None:
    vector = validate_embedding_vector([1, 2.5, -3])

    assert vector.values == (1.0, 2.5, -3.0)
    assert vector.dimensions == 3


def test_empty_vector_rejection() -> None:
    with pytest.raises(VectorValidationError):
        validate_embedding_vector([])


def test_boolean_and_non_numeric_vector_rejection() -> None:
    with pytest.raises(VectorValidationError):
        validate_embedding_vector([True, 1.0])

    with pytest.raises(VectorValidationError):
        validate_embedding_vector([1.0, "2"])


def test_nan_and_infinite_vector_rejection() -> None:
    with pytest.raises(VectorValidationError):
        validate_embedding_vector([1.0, float("nan")])

    with pytest.raises(VectorValidationError):
        validate_embedding_vector([1.0, float("inf")])


def test_zero_norm_vector_rejection() -> None:
    with pytest.raises(VectorValidationError):
        validate_embedding_vector([0.0, 0.0])
