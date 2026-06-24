from backend.services.match_scorer import (
    CandidateMatchInput,
    JobMatchInput,
    MatchSkillInput,
    calculate_match_score,
)


def skill(skill_id: int, name: str, normalized_name: str) -> MatchSkillInput:
    return MatchSkillInput(
        skill_id=skill_id,
        name=name,
        normalized_name=normalized_name,
    )


def candidate(
    skills: tuple[MatchSkillInput, ...] = (),
    parsed_years_experience: int | None = None,
    profile_years_experience: int | None = None,
    education_level: str | None = None,
) -> CandidateMatchInput:
    return CandidateMatchInput(
        skills=skills,
        parsed_years_experience=parsed_years_experience,
        profile_years_experience=profile_years_experience,
        education_level=education_level,
    )


def job(
    required_skills: tuple[MatchSkillInput, ...] = (),
    preferred_skills: tuple[MatchSkillInput, ...] = (),
    minimum_years_experience: int | None = None,
    education_requirement: str | None = None,
) -> JobMatchInput:
    return JobMatchInput(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        minimum_years_experience=minimum_years_experience,
        education_requirement=education_requirement,
    )


def test_exact_required_skill_score() -> None:
    result = calculate_match_score(
        candidate(skills=(skill(1, "Python", "python"), skill(2, "SQL", "sql"))),
        job(required_skills=(skill(1, "Python", "python"), skill(2, "SQL", "sql"))),
    )

    assert result.required_skill_score == 100
    assert result.matched_required_count == 2
    assert result.total_required_count == 2
    assert result.overall_score == 100


def test_exact_preferred_skill_score() -> None:
    result = calculate_match_score(
        candidate(skills=(skill(3, "Power BI", "power_bi"),)),
        job(preferred_skills=(skill(3, "Power BI", "power_bi"),)),
    )

    assert result.preferred_skill_score == 100
    assert result.matched_preferred_count == 1
    assert result.total_preferred_count == 1
    assert result.overall_score == 100


def test_partial_and_zero_skill_matches() -> None:
    result = calculate_match_score(
        candidate(skills=(skill(1, "Python", "python"),)),
        job(
            required_skills=(
                skill(1, "Python", "python"),
                skill(2, "SQL", "sql"),
            ),
            preferred_skills=(skill(3, "Docker", "docker"),),
        ),
    )

    assert result.required_skill_score == 50
    assert result.preferred_skill_score == 0
    assert result.matched_required_count == 1
    assert result.matched_preferred_count == 0


def test_experience_full_score() -> None:
    result = calculate_match_score(
        candidate(parsed_years_experience=5),
        job(minimum_years_experience=3),
    )

    assert result.experience_score == 100
    assert result.candidate_years_used == 5
    assert result.required_years == 3


def test_experience_proportional_score() -> None:
    result = calculate_match_score(
        candidate(parsed_years_experience=2),
        job(minimum_years_experience=3),
    )

    assert result.experience_score == 67
    assert result.overall_score == 67


def test_profile_years_fallback() -> None:
    result = calculate_match_score(
        candidate(profile_years_experience=4),
        job(minimum_years_experience=5),
    )

    assert result.experience_score == 80
    assert result.candidate_years_used == 4


def test_missing_candidate_experience_scores_zero() -> None:
    result = calculate_match_score(candidate(), job(minimum_years_experience=2))

    assert result.experience_score == 0
    assert result.candidate_years_used is None


def test_zero_required_years_scores_full_without_candidate_years() -> None:
    result = calculate_match_score(candidate(), job(minimum_years_experience=0))

    assert result.experience_score == 100
    assert result.overall_score == 100


def test_education_equal_and_above_score_full() -> None:
    equal = calculate_match_score(
        candidate(education_level="bachelor"),
        job(education_requirement="bachelor"),
    )
    above = calculate_match_score(
        candidate(education_level="master"),
        job(education_requirement="bachelor"),
    )

    assert equal.education_score == 100
    assert above.education_score == 100


def test_education_below_and_missing_score_zero() -> None:
    below = calculate_match_score(
        candidate(education_level="associate"),
        job(education_requirement="bachelor"),
    )
    missing = calculate_match_score(candidate(), job(education_requirement="bachelor"))

    assert below.education_score == 0
    assert missing.education_score == 0


def test_excluded_dimensions_have_null_scores_and_weights() -> None:
    result = calculate_match_score(
        candidate(skills=(skill(1, "Python", "python"),)),
        job(required_skills=(skill(1, "Python", "python"),)),
    )

    assert result.preferred_skill_score is None
    assert result.experience_score is None
    assert result.education_score is None
    assert result.applicable_weights.required_skills == 100
    assert result.applicable_weights.preferred_skills is None
    assert result.applicable_weights.experience is None
    assert result.applicable_weights.education is None


def test_normalized_applicable_weights() -> None:
    result = calculate_match_score(
        candidate(
            skills=(skill(1, "Python", "python"), skill(3, "Docker", "docker")),
            parsed_years_experience=3,
        ),
        job(
            required_skills=(skill(1, "Python", "python"),),
            preferred_skills=(skill(3, "Docker", "docker"),),
            minimum_years_experience=3,
        ),
    )

    assert result.applicable_weights.required_skills == 61
    assert result.applicable_weights.preferred_skills == 17
    assert result.applicable_weights.experience == 22
    assert result.applicable_weights.education is None


def test_rounding_remainder_handling_uses_priority() -> None:
    result = calculate_match_score(
        candidate(
            skills=(skill(1, "Python", "python"),),
            parsed_years_experience=3,
            education_level="bachelor",
        ),
        job(
            required_skills=(skill(1, "Python", "python"),),
            minimum_years_experience=3,
            education_requirement="bachelor",
        ),
    )

    assert result.applicable_weights.required_skills == 65
    assert result.applicable_weights.experience == 24
    assert result.applicable_weights.education == 11
    assert result.applicable_weights.preferred_skills is None


def test_no_comparable_requirements_scores_zero() -> None:
    result = calculate_match_score(candidate(), job())

    assert result.overall_score == 0
    assert result.required_skill_score is None
    assert result.preferred_skill_score is None
    assert result.experience_score is None
    assert result.education_score is None
    assert result.applicable_weights.required_skills is None
    assert result.applicable_weights.preferred_skills is None
    assert result.applicable_weights.experience is None
    assert result.applicable_weights.education is None


def test_half_up_rounding_for_component_scores() -> None:
    result = calculate_match_score(
        candidate(skills=(skill(1, "Python", "python"),)),
        job(
            required_skills=(
                skill(1, "Python", "python"),
                skill(2, "SQL", "sql"),
                skill(3, "Docker", "docker"),
                skill(4, "AWS", "aws"),
                skill(5, "Excel", "excel"),
                skill(6, "Tableau", "tableau"),
                skill(7, "Power BI", "power_bi"),
                skill(8, "FastAPI", "fastapi"),
            ),
        ),
    )

    assert result.required_skill_score == 13
    assert result.overall_score == 13


def test_deterministic_skill_ordering() -> None:
    result = calculate_match_score(
        candidate(skills=(skill(2, "SQL", "sql"),)),
        job(
            required_skills=(
                skill(3, "Python", "python"),
                skill(1, "AWS", "aws"),
                skill(2, "SQL", "sql"),
            ),
            preferred_skills=(
                skill(5, "Tableau", "tableau"),
                skill(4, "Power BI", "power_bi"),
            ),
        ),
    )

    assert [
        detail.normalized_name for detail in result.skill_details
    ] == ["aws", "python", "sql", "power_bi", "tableau"]


def test_repeated_scoring_equivalence() -> None:
    candidate_input = candidate(
        skills=(skill(1, "Python", "python"),),
        parsed_years_experience=3,
        education_level="bachelor",
    )
    job_input = job(
        required_skills=(skill(1, "Python", "python"),),
        minimum_years_experience=3,
        education_requirement="bachelor",
    )

    assert calculate_match_score(candidate_input, job_input) == calculate_match_score(
        candidate_input,
        job_input,
    )
