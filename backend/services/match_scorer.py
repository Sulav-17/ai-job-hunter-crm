from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


SCORING_VERSION = "deterministic-match-v1"

BASE_WEIGHTS = {
    "required_skills": 55,
    "preferred_skills": 15,
    "experience": 20,
    "education": 10,
}
WEIGHT_REMAINDER_PRIORITY = (
    "required_skills",
    "preferred_skills",
    "experience",
    "education",
)

EDUCATION_RANKS = {
    "high_school": 1,
    "diploma": 2,
    "associate": 3,
    "unspecified_degree": 4,
    "bachelor": 5,
    "master": 6,
    "doctorate": 7,
}


@dataclass(frozen=True)
class MatchSkillInput:
    skill_id: int | None
    name: str
    normalized_name: str

    @property
    def identity(self) -> tuple[str, int | str]:
        if self.skill_id is not None:
            return ("id", self.skill_id)
        return ("normalized_name", self.normalized_name)


@dataclass(frozen=True)
class CandidateMatchInput:
    skills: tuple[MatchSkillInput, ...]
    parsed_years_experience: int | None
    profile_years_experience: int | None
    education_level: str | None


@dataclass(frozen=True)
class JobMatchInput:
    required_skills: tuple[MatchSkillInput, ...]
    preferred_skills: tuple[MatchSkillInput, ...]
    minimum_years_experience: int | None
    education_requirement: str | None


@dataclass(frozen=True)
class SkillMatchOutput:
    skill_id: int | None
    name: str
    normalized_name: str
    requirement_type: str
    matched: bool


@dataclass(frozen=True)
class ApplicableWeights:
    required_skills: int | None
    preferred_skills: int | None
    experience: int | None
    education: int | None


@dataclass(frozen=True)
class MatchScoreResult:
    overall_score: int
    required_skill_score: int | None
    preferred_skill_score: int | None
    experience_score: int | None
    education_score: int | None
    applicable_weights: ApplicableWeights
    matched_required_count: int
    total_required_count: int
    matched_preferred_count: int
    total_preferred_count: int
    candidate_years_used: int | None
    required_years: int | None
    candidate_education_level: str | None
    required_education_level: str | None
    scoring_version: str
    skill_details: tuple[SkillMatchOutput, ...]


def calculate_match_score(
    candidate: CandidateMatchInput,
    job: JobMatchInput,
) -> MatchScoreResult:
    candidate_skill_identities = {skill.identity for skill in candidate.skills}

    required_details = _build_skill_details(
        job.required_skills,
        "required",
        candidate_skill_identities,
    )
    preferred_details = _build_skill_details(
        job.preferred_skills,
        "preferred",
        candidate_skill_identities,
    )

    total_required_count = len(required_details)
    matched_required_count = sum(1 for detail in required_details if detail.matched)
    total_preferred_count = len(preferred_details)
    matched_preferred_count = sum(1 for detail in preferred_details if detail.matched)

    required_skill_score = _percentage_or_none(
        matched_required_count,
        total_required_count,
    )
    preferred_skill_score = _percentage_or_none(
        matched_preferred_count,
        total_preferred_count,
    )
    candidate_years_used = _candidate_years_used(candidate)
    experience_score = _score_experience(
        candidate_years_used,
        job.minimum_years_experience,
    )
    education_score = _score_education(
        candidate.education_level,
        job.education_requirement,
    )

    component_scores = {
        "required_skills": required_skill_score,
        "preferred_skills": preferred_skill_score,
        "experience": experience_score,
        "education": education_score,
    }
    applicable_weights = _normalize_applicable_weights(component_scores)
    overall_score = _score_overall(component_scores, applicable_weights)

    return MatchScoreResult(
        overall_score=overall_score,
        required_skill_score=required_skill_score,
        preferred_skill_score=preferred_skill_score,
        experience_score=experience_score,
        education_score=education_score,
        applicable_weights=applicable_weights,
        matched_required_count=matched_required_count,
        total_required_count=total_required_count,
        matched_preferred_count=matched_preferred_count,
        total_preferred_count=total_preferred_count,
        candidate_years_used=candidate_years_used,
        required_years=job.minimum_years_experience,
        candidate_education_level=candidate.education_level,
        required_education_level=job.education_requirement,
        scoring_version=SCORING_VERSION,
        skill_details=tuple(required_details + preferred_details),
    )


def _build_skill_details(
    job_skills: tuple[MatchSkillInput, ...],
    requirement_type: str,
    candidate_skill_identities: set[tuple[str, int | str]],
) -> list[SkillMatchOutput]:
    details = [
        SkillMatchOutput(
            skill_id=skill.skill_id,
            name=skill.name,
            normalized_name=skill.normalized_name,
            requirement_type=requirement_type,
            matched=skill.identity in candidate_skill_identities,
        )
        for skill in job_skills
    ]
    return sorted(details, key=lambda detail: (detail.normalized_name, detail.name))


def _percentage_or_none(matched_count: int, total_count: int) -> int | None:
    if total_count == 0:
        return None
    return _round_half_up(Decimal(matched_count) * Decimal(100) / Decimal(total_count))


def _candidate_years_used(candidate: CandidateMatchInput) -> int | None:
    if candidate.parsed_years_experience is not None:
        return candidate.parsed_years_experience
    return candidate.profile_years_experience


def _score_experience(
    candidate_years: int | None,
    required_years: int | None,
) -> int | None:
    if required_years is None:
        return None
    if required_years == 0:
        return 100
    if candidate_years is None:
        return 0
    if candidate_years >= required_years:
        return 100
    return _round_half_up(Decimal(candidate_years) * Decimal(100) / Decimal(required_years))


def _score_education(
    candidate_education_level: str | None,
    required_education_level: str | None,
) -> int | None:
    if required_education_level is None:
        return None
    if candidate_education_level is None:
        return 0

    candidate_rank = EDUCATION_RANKS.get(candidate_education_level)
    required_rank = EDUCATION_RANKS.get(required_education_level)
    if candidate_rank is None or required_rank is None:
        return 0
    if candidate_rank >= required_rank:
        return 100
    return 0


def _normalize_applicable_weights(
    component_scores: dict[str, int | None],
) -> ApplicableWeights:
    applicable_components = [
        name for name in WEIGHT_REMAINDER_PRIORITY if component_scores[name] is not None
    ]
    if not applicable_components:
        return ApplicableWeights(None, None, None, None)

    total_base_weight = sum(BASE_WEIGHTS[name] for name in applicable_components)
    normalized = {
        name: _round_half_up(
            Decimal(BASE_WEIGHTS[name]) * Decimal(100) / Decimal(total_base_weight),
        )
        for name in applicable_components
    }

    remainder = 100 - sum(normalized.values())
    if remainder > 0:
        for name in WEIGHT_REMAINDER_PRIORITY:
            if name in normalized and remainder > 0:
                normalized[name] += 1
                remainder -= 1
    elif remainder < 0:
        for name in reversed(WEIGHT_REMAINDER_PRIORITY):
            if name in normalized and normalized[name] > 0 and remainder < 0:
                normalized[name] -= 1
                remainder += 1

    return ApplicableWeights(
        required_skills=normalized.get("required_skills"),
        preferred_skills=normalized.get("preferred_skills"),
        experience=normalized.get("experience"),
        education=normalized.get("education"),
    )


def _score_overall(
    component_scores: dict[str, int | None],
    applicable_weights: ApplicableWeights,
) -> int:
    weight_values = {
        "required_skills": applicable_weights.required_skills,
        "preferred_skills": applicable_weights.preferred_skills,
        "experience": applicable_weights.experience,
        "education": applicable_weights.education,
    }
    if all(weight is None for weight in weight_values.values()):
        return 0

    weighted_total = Decimal(0)
    for component_name, component_score in component_scores.items():
        weight = weight_values[component_name]
        if component_score is not None and weight is not None:
            weighted_total += Decimal(component_score) * Decimal(weight)
    return _round_half_up(weighted_total / Decimal(100))


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
