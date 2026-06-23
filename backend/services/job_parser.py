from dataclasses import dataclass
import re

from backend.services.skill_catalog import SkillCatalogEntry, get_catalog_entries

PARSER_VERSION = "deterministic-v1"
MAX_EVIDENCE_LENGTH = 240
REQUIREMENT_REQUIRED = "required"
REQUIREMENT_PREFERRED = "preferred"

PREFERRED_INDICATORS = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "asset",
    "bonus",
    "desirable",
    "would be an asset",
    "considered an asset",
    "preferred qualifications",
)
REQUIRED_INDICATORS = (
    "required",
    "must have",
    "must-have",
    "minimum qualifications",
    "requirements",
    "required qualifications",
    "mandatory",
)

EDUCATION_RANKS = {
    "high_school": 1,
    "diploma": 2,
    "associate": 3,
    "bachelor": 4,
    "unspecified_degree": 4,
    "master": 5,
    "doctorate": 6,
}
EDUCATION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("doctorate", (r"\bph\.?d\b", r"\bdoctorate\b", r"\bdoctoral degree\b")),
    ("master", (r"\bmaster'?s degree\b", r"\bmasters degree\b", r"\bmba\b")),
    (
        "bachelor",
        (
            r"\bbachelor'?s degree\b",
            r"\bbachelors degree\b",
            r"\bundergraduate degree\b",
        ),
    ),
    ("associate", (r"\bassociate degree\b",)),
    ("diploma", (r"\bcollege diploma\b", r"\bdiploma\b")),
    ("high_school", (r"\bhigh school diploma\b",)),
    (
        "unspecified_degree",
        (
            r"\buniversity degree\b",
            r"\bdegree in [a-z][a-z\s]+ or related field\b",
        ),
    ),
)


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    normalized_name: str
    requirement_type: str
    evidence_text: str


@dataclass(frozen=True)
class ParsedJob:
    parser_version: str
    required_skills: tuple[ParsedSkill, ...]
    preferred_skills: tuple[ParsedSkill, ...]
    minimum_years_experience: int | None
    education_requirement: str | None


@dataclass(frozen=True)
class _SkillMatch:
    entry: SkillCatalogEntry
    requirement_type: str
    evidence_text: str
    start: int


def parse_job_description(description: str) -> ParsedJob:
    matches = _find_skill_matches(description)
    required_skills = tuple(
        _sort_skills(match for match in matches if match.requirement_type == "required")
    )
    preferred_skills = tuple(
        _sort_skills(match for match in matches if match.requirement_type == "preferred")
    )

    return ParsedJob(
        parser_version=PARSER_VERSION,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        minimum_years_experience=extract_minimum_years_experience(description),
        education_requirement=extract_education_requirement(description),
    )


def _sort_skills(matches) -> list[ParsedSkill]:
    parsed = [
        ParsedSkill(
            name=match.entry.name,
            normalized_name=match.entry.normalized_name,
            requirement_type=match.requirement_type,
            evidence_text=match.evidence_text,
        )
        for match in matches
    ]
    return sorted(
        parsed,
        key=lambda skill: (
            skill.requirement_type,
            skill.normalized_name,
            skill.name,
        ),
    )


def _find_skill_matches(description: str) -> list[_SkillMatch]:
    seen: dict[tuple[str, str], _SkillMatch] = {}

    for entry in get_catalog_entries():
        for alias in entry.aliases:
            pattern = _compile_alias_pattern(alias)
            for match in pattern.finditer(description):
                evidence = _extract_evidence(description, match.start(), match.end())
                requirement_type = _classify_requirement(description, match.start(), match.end())
                key = (entry.normalized_name, requirement_type)
                existing = seen.get(key)
                candidate = _SkillMatch(
                    entry=entry,
                    requirement_type=requirement_type,
                    evidence_text=evidence,
                    start=match.start(),
                )
                if existing is None or candidate.start < existing.start:
                    seen[key] = candidate

    return sorted(
        seen.values(),
        key=lambda match: (
            match.requirement_type,
            match.entry.normalized_name,
            match.entry.name,
            match.start,
        ),
    )


def _compile_alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )


def _extract_evidence(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)

    line = text[line_start:line_end]
    relative_start = start - line_start
    relative_end = end - line_start

    sentence_start = max(
        line.rfind(".", 0, relative_start),
        line.rfind("!", 0, relative_start),
        line.rfind("?", 0, relative_start),
        line.rfind(";", 0, relative_start),
    )
    if sentence_start == -1:
        sentence_start = 0
    else:
        sentence_start += 1

    sentence_ends = [
        position
        for position in (
            line.find(".", relative_end),
            line.find("!", relative_end),
            line.find("?", relative_end),
            line.find(";", relative_end),
        )
        if position != -1
    ]
    sentence_end = min(sentence_ends) + 1 if sentence_ends else len(line)

    snippet = _normalize_whitespace(line[sentence_start:sentence_end])
    if len(snippet) <= MAX_EVIDENCE_LENGTH:
        return snippet

    match_text = _normalize_whitespace(text[start:end])
    half_window = max((MAX_EVIDENCE_LENGTH - len(match_text) - 5) // 2, 20)
    snippet_start = max(start - half_window, 0)
    snippet_end = min(end + half_window, len(text))
    return _normalize_whitespace(text[snippet_start:snippet_end])[:MAX_EVIDENCE_LENGTH]


def _classify_requirement(text: str, start: int, end: int) -> str:
    context = _extract_evidence(text, start, end).casefold()
    if any(indicator in context for indicator in PREFERRED_INDICATORS):
        return REQUIREMENT_PREFERRED
    return REQUIREMENT_REQUIRED


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_minimum_years_experience(description: str) -> int | None:
    matches: list[tuple[str, int]] = []
    patterns = (
        r"\b(?:at least|minimum of|minimum)\s+(\d{1,2})\+?\s+years?\b",
        r"\b(\d{1,2})\s*-\s*\d{1,2}\s+years?\b",
        r"(?<!-)\b(\d{1,2})\+?\s+years?(?:\s+of\s+experience)?\b",
    )

    for pattern in patterns:
        for match in re.finditer(pattern, description, flags=re.IGNORECASE):
            years = int(match.group(1))
            requirement_type = _classify_requirement(
                description,
                match.start(),
                match.end(),
            )
            matches.append((requirement_type, years))

    if not matches:
        return None

    required_years = [years for requirement_type, years in matches if requirement_type == "required"]
    if required_years:
        return max(required_years)

    return max(years for _, years in matches)


def extract_education_requirement(description: str) -> str | None:
    matches: list[tuple[str, str]] = []
    for education_level, patterns in EDUCATION_PATTERNS:
        for pattern in patterns:
            for match in re.finditer(pattern, description, flags=re.IGNORECASE):
                requirement_type = _classify_requirement(
                    description,
                    match.start(),
                    match.end(),
                )
                matches.append((requirement_type, education_level))

    if not matches:
        return None

    required_levels = [level for requirement_type, level in matches if requirement_type == "required"]
    if required_levels:
        return max(required_levels, key=lambda level: EDUCATION_RANKS[level])

    return max((level for _, level in matches), key=lambda level: EDUCATION_RANKS[level])
