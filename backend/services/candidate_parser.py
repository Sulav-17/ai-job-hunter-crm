from dataclasses import dataclass
import re

from backend.services.parser_utils import (
    EDUCATION_RANKS,
    iter_education_matches,
    iter_skill_text_matches,
)

PARSER_VERSION = "candidate-deterministic-v1"


@dataclass(frozen=True)
class ParsedCandidateSkill:
    name: str
    normalized_name: str
    evidence_text: str


@dataclass(frozen=True)
class ParsedCandidate:
    parser_version: str
    skills: tuple[ParsedCandidateSkill, ...]
    parsed_years_experience: int | None
    education_level: str | None


def parse_candidate_resume(resume_text: str) -> ParsedCandidate:
    return ParsedCandidate(
        parser_version=PARSER_VERSION,
        skills=extract_candidate_skills(resume_text),
        parsed_years_experience=extract_explicit_years_experience(resume_text),
        education_level=extract_candidate_education_level(resume_text),
    )


def extract_candidate_skills(resume_text: str) -> tuple[ParsedCandidateSkill, ...]:
    earliest_by_skill: dict[str, ParsedCandidateSkill] = {}
    starts_by_skill: dict[str, int] = {}

    for match in iter_skill_text_matches(resume_text):
        normalized_name = match.entry.normalized_name
        if normalized_name in starts_by_skill and starts_by_skill[normalized_name] <= match.start:
            continue

        starts_by_skill[normalized_name] = match.start
        earliest_by_skill[normalized_name] = ParsedCandidateSkill(
            name=match.entry.name,
            normalized_name=normalized_name,
            evidence_text=match.evidence_text,
        )

    return tuple(
        sorted(
            earliest_by_skill.values(),
            key=lambda skill: (skill.normalized_name, skill.name),
        ),
    )


def extract_explicit_years_experience(resume_text: str) -> int | None:
    patterns = (
        r"\b(?:over|more than)\s+(\d{1,2})\s+years?(?:\s+of\s+experience)?\b",
        r"\b(\d{1,2})\+?\s+years?\s+of\s+experience\b",
    )
    years: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, resume_text, flags=re.IGNORECASE):
            years.append(int(match.group(1)))

    if not years:
        return None

    return max(years)


def extract_candidate_education_level(resume_text: str) -> str | None:
    matches = iter_education_matches(resume_text)
    if not matches:
        return None

    return max(
        (match.education_level for match in matches),
        key=lambda education_level: EDUCATION_RANKS[education_level],
    )
