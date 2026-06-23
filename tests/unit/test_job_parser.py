from backend.services.job_parser import (
    extract_education_requirement,
    extract_minimum_years_experience,
    parse_job_description,
)


def _skill_names(skills) -> list[str]:
    return [skill.name for skill in skills]


def test_parser_matches_skills_case_insensitively() -> None:
    result = parse_job_description("Requirements: PYTHON, sql, and Power BI.")

    assert _skill_names(result.required_skills) == ["Power BI", "Python", "SQL"]
    assert result.preferred_skills == ()


def test_parser_uses_boundary_safe_matching() -> None:
    result = parse_job_description(
        "This reporting role works on cloud dashboards. Requirements: R and C."
    )

    assert _skill_names(result.required_skills) == ["C", "R"]


def test_parser_matches_punctuation_aliases_safely() -> None:
    result = parse_job_description("Requirements: Node.js, React.js, and REST APIs.")

    assert _skill_names(result.required_skills) == ["Node.js", "React", "REST APIs"]


def test_parser_deduplicates_aliases_for_same_skill() -> None:
    result = parse_job_description("Requirements: PostgreSQL, postgres, and postgresql.")

    assert _skill_names(result.required_skills) == ["PostgreSQL"]


def test_parser_classifies_required_and_preferred_skills() -> None:
    result = parse_job_description(
        "Requirements: Python and SQL.\n"
        "Preferred qualifications: Tableau and Power BI are nice to have."
    )

    assert _skill_names(result.required_skills) == ["Python", "SQL"]
    assert _skill_names(result.preferred_skills) == ["Power BI", "Tableau"]


def test_parser_defaults_explicit_skill_mentions_to_required() -> None:
    result = parse_job_description("The team uses Docker and GitHub.")

    assert _skill_names(result.required_skills) == ["Docker", "GitHub"]
    assert result.preferred_skills == ()


def test_parser_keeps_separate_required_and_preferred_evidence() -> None:
    result = parse_job_description(
        "Requirements: Python for data workflows.\n"
        "Preferred: Python experience with Pandas is a bonus."
    )

    assert _skill_names(result.required_skills) == ["Python"]
    assert _skill_names(result.preferred_skills) == ["Pandas", "Python"]


def test_evidence_snippets_are_short_and_contextual() -> None:
    result = parse_job_description(
        "Requirements: Python for pipelines and SQL for reporting. "
        + "Extra filler text. " * 80
    )

    python_skill = next(skill for skill in result.required_skills if skill.name == "Python")
    assert "Python" in python_skill.evidence_text
    assert len(python_skill.evidence_text) <= 240
    assert len(python_skill.evidence_text) < len("Extra filler text. " * 80)


def test_experience_extraction_uses_range_lower_bound() -> None:
    assert extract_minimum_years_experience("Requires 2-4 years of experience.") == 2


def test_experience_extraction_uses_highest_required_minimum() -> None:
    description = (
        "Requirements: at least 3 years of experience with reporting. "
        "Minimum of 5 years of experience with SQL. "
        "Preferred: 8 years of experience with dashboards."
    )

    assert extract_minimum_years_experience(description) == 5


def test_experience_extraction_uses_preferred_when_no_required_exists() -> None:
    assert extract_minimum_years_experience("Preferred: 4+ years with Tableau.") == 4


def test_experience_extraction_returns_none_when_absent() -> None:
    assert extract_minimum_years_experience("Senior analyst role with Python.") is None


def test_education_extraction_prefers_highest_required_level() -> None:
    description = (
        "Requirements: bachelor's degree in analytics. "
        "Preferred: master's degree in statistics."
    )

    assert extract_education_requirement(description) == "bachelor"


def test_education_extraction_detects_master_and_diploma() -> None:
    assert extract_education_requirement("Minimum qualifications: MBA required.") == "master"
    assert extract_education_requirement("Requirements: college diploma.") == "diploma"


def test_education_extraction_returns_none_when_absent() -> None:
    assert extract_education_requirement("Experience with SQL and dashboards.") is None


def test_parser_output_is_deterministic_for_same_text() -> None:
    description = (
        "Requirements: SQL, Python, and 3+ years of experience. "
        "Preferred: Power BI and bachelor's degree."
    )

    first = parse_job_description(description)
    second = parse_job_description(description)

    assert first == second
