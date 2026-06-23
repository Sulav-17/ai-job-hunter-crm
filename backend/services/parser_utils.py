from dataclasses import dataclass
import re

from backend.services.skill_catalog import SkillCatalogEntry, get_catalog_entries

MAX_EVIDENCE_LENGTH = 240

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
class SkillTextMatch:
    entry: SkillCatalogEntry
    evidence_text: str
    start: int
    end: int


@dataclass(frozen=True)
class EducationTextMatch:
    education_level: str
    start: int
    end: int


def iter_skill_text_matches(text: str) -> list[SkillTextMatch]:
    matches: list[SkillTextMatch] = []
    for entry in get_catalog_entries():
        for alias in entry.aliases:
            pattern = compile_alias_pattern(alias)
            for match in pattern.finditer(text):
                matches.append(
                    SkillTextMatch(
                        entry=entry,
                        evidence_text=extract_evidence(text, match.start(), match.end()),
                        start=match.start(),
                        end=match.end(),
                    ),
                )

    return sorted(
        matches,
        key=lambda match: (
            match.start,
            match.entry.normalized_name,
            match.entry.name,
        ),
    )


def compile_alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )


def extract_evidence(text: str, start: int, end: int) -> str:
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

    snippet = normalize_whitespace(line[sentence_start:sentence_end])
    if len(snippet) <= MAX_EVIDENCE_LENGTH:
        return snippet

    match_text = normalize_whitespace(text[start:end])
    half_window = max((MAX_EVIDENCE_LENGTH - len(match_text) - 5) // 2, 20)
    snippet_start = max(start - half_window, 0)
    snippet_end = min(end + half_window, len(text))
    return normalize_whitespace(text[snippet_start:snippet_end])[:MAX_EVIDENCE_LENGTH]


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def iter_education_matches(text: str) -> list[EducationTextMatch]:
    matches: list[EducationTextMatch] = []
    for education_level, patterns in EDUCATION_PATTERNS:
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                matches.append(
                    EducationTextMatch(
                        education_level=education_level,
                        start=match.start(),
                        end=match.end(),
                    ),
                )

    return sorted(
        matches,
        key=lambda match: (
            match.start,
            EDUCATION_RANKS[match.education_level],
            match.education_level,
        ),
    )
