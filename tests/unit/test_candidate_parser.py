from backend.services.candidate_parser import (
    extract_candidate_education_level,
    extract_candidate_skills,
    extract_explicit_years_experience,
    parse_candidate_resume,
)


def _skill_names(skills) -> list[str]:
    return [skill.name for skill in skills]


def test_candidate_parser_extracts_aliases_and_canonical_skills() -> None:
    result = parse_candidate_resume("Built dashboards with postgres, PowerBI, and sklearn.")

    assert _skill_names(result.skills) == ["PostgreSQL", "Power BI", "Scikit-learn"]


def test_candidate_parser_uses_boundary_safe_matching() -> None:
    result = parse_candidate_resume("Reporting and cloud work. Used R and C for analysis.")

    assert _skill_names(result.skills) == ["C", "R"]


def test_candidate_parser_protects_short_skill_false_positives() -> None:
    result = parse_candidate_resume("Reporting cloud workflows without standalone letters.")

    assert result.skills == ()


def test_candidate_parser_removes_duplicate_skills() -> None:
    result = parse_candidate_resume("Python, python, PYTHON, and PostgreSQL/postgres.")

    assert _skill_names(result.skills) == ["PostgreSQL", "Python"]


def test_candidate_parser_orders_skills_deterministically() -> None:
    result = parse_candidate_resume("SQL, Python, AWS, and Docker.")

    assert [skill.normalized_name for skill in result.skills] == [
        "aws",
        "docker",
        "python",
        "sql",
    ]


def test_candidate_parser_uses_earliest_evidence() -> None:
    result = parse_candidate_resume(
        "Python for automation. Later used Python for analytics."
    )

    python = result.skills[0]
    assert python.name == "Python"
    assert python.evidence_text == "Python for automation."


def test_candidate_parser_evidence_is_bounded() -> None:
    result = parse_candidate_resume(
        "Python for data work. " + "Fictional filler sentence. " * 80
    )

    assert "Python" in result.skills[0].evidence_text
    assert len(result.skills[0].evidence_text) <= 240


def test_candidate_experience_extraction_supports_explicit_phrases() -> None:
    assert extract_explicit_years_experience("5 years of experience with SQL.") == 5
    assert extract_explicit_years_experience("5+ years of experience with Python.") == 5
    assert extract_explicit_years_experience("Over 6 years in analytics.") == 6
    assert extract_explicit_years_experience("More than 7 years of experience.") == 7


def test_candidate_experience_extraction_uses_highest_explicit_value() -> None:
    text = "3 years of experience with SQL and more than 6 years with reporting."

    assert extract_explicit_years_experience(text) == 6


def test_candidate_experience_extraction_ignores_date_ranges() -> None:
    text = "Worked from 2019-2024 and 2020 to 2025. Senior analyst."

    assert extract_explicit_years_experience(text) is None


def test_candidate_education_extraction_uses_highest_level() -> None:
    text = "College diploma plus a bachelor's degree and MBA."

    assert extract_candidate_education_level(text) == "master"


def test_candidate_education_extraction_returns_none_when_absent() -> None:
    assert extract_candidate_education_level("Completed analytics projects.") is None


def test_candidate_parser_output_is_deterministic() -> None:
    text = (
        "Python, SQL, and Power BI. "
        "More than 5 years of experience. Bachelor's degree."
    )

    assert parse_candidate_resume(text) == parse_candidate_resume(text)
