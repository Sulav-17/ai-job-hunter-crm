from __future__ import annotations

from dataclasses import dataclass

DEMO_SEED_VERSION = "demo:v1"
DEMO_EMBEDDING_MODEL = "demo:precomputed-embedding-v1"
DEMO_TAILORING_MODEL = "demo:precomputed-tailoring-v1"


@dataclass(frozen=True)
class DemoCandidate:
    seed_key: str
    full_name: str
    headline: str
    location: str
    professional_summary: str
    years_experience: int
    resume_text: str


@dataclass(frozen=True)
class DemoJob:
    seed_key: str
    title: str
    company: str
    location: str
    employment_type: str
    work_mode: str
    source_url: str
    description: str
    application_status: str
    application_notes: str


@dataclass(frozen=True)
class DemoDataset:
    candidate: DemoCandidate
    jobs: tuple[DemoJob, ...]


DEMO_CANDIDATE = DemoCandidate(
    seed_key=f"{DEMO_SEED_VERSION}:candidate:main",
    full_name="Mira Quill",
    headline="Fictional Data Platform Analyst",
    location="Fictional Harbor, CA",
    professional_summary=(
        "Fictional portfolio candidate who builds local-first analytics workflows, "
        "documents data quality decisions, and communicates findings to product teams."
    ),
    years_experience=6,
    resume_text=(
        "Mira Quill is a fictional candidate for the AI Job Hunter CRM public demo. "
        "Contact: mira.quill@example.invalid, 555-0100. "
        "Built Python dashboards with SQL and Power BI for Lumen Orchard Labs. "
        "Created FastAPI services with PostgreSQL and Docker for the Clockwork Atlas project. "
        "Designed Pandas and NumPy data quality checks for fictional reporting workflows. "
        "Documented REST APIs and GitHub review notes for cross-functional teams. "
        "More than 6 years of experience in data analysis and data engineering. "
        "Bachelor's degree completed at North Pier University, a fictional institution."
    ),
)


DEMO_JOBS = (
    DemoJob(
        seed_key=f"{DEMO_SEED_VERSION}:job:data-platform-engineer",
        title="Data Platform Engineer",
        company="Northstar Fictional Systems",
        location="Remote",
        employment_type="full_time",
        work_mode="remote",
        source_url="https://example.invalid/jobs/data-platform-engineer",
        application_status="saved",
        application_notes="Demo saved opportunity for a strong platform fit.",
        description=(
            "Requirements: Python, SQL, PostgreSQL, FastAPI, and Docker with 5+ years "
            "of experience. Bachelor's degree required. Preferred qualifications: "
            "Power BI, GitHub, and REST APIs are nice to have for this fictional role."
        ),
    ),
    DemoJob(
        seed_key=f"{DEMO_SEED_VERSION}:job:analytics-engineer",
        title="Analytics Engineer",
        company="Blue Lantern Demo Co.",
        location="Fictional Harbor, CA",
        employment_type="full_time",
        work_mode="hybrid",
        source_url="https://example.invalid/jobs/analytics-engineer",
        application_status="applied",
        application_notes="Fictional application submitted after reviewing SQL-heavy requirements.",
        description=(
            "Requirements: SQL, Python, dbt, and data analysis with 4+ years of experience. "
            "Bachelor's degree required. Preferred qualifications: Power BI, Tableau, "
            "and Git are helpful for this fictional analytics team."
        ),
    ),
    DemoJob(
        seed_key=f"{DEMO_SEED_VERSION}:job:business-intelligence-analyst",
        title="Business Intelligence Analyst",
        company="Cedar Kite Labs",
        location="Toronto, ON",
        employment_type="contract",
        work_mode="remote",
        source_url="https://example.invalid/jobs/bi-analyst",
        application_status="interview",
        application_notes="Demo interview stage with fictional BI stakeholders.",
        description=(
            "Requirements: Power BI, SQL, Excel, and data analysis with 3+ years of "
            "experience. College diploma or Bachelor's degree required. Preferred "
            "qualifications: Python and stakeholder documentation for a fictional BI group."
        ),
    ),
    DemoJob(
        seed_key=f"{DEMO_SEED_VERSION}:job:ml-reporting-specialist",
        title="Machine Learning Reporting Specialist",
        company="Orbit Grove Studio",
        location="Remote",
        employment_type="temporary",
        work_mode="remote",
        source_url="https://example.invalid/jobs/ml-reporting-specialist",
        application_status="rejected",
        application_notes="Fictional rejection used to demonstrate status history.",
        description=(
            "Requirements: Machine Learning, Scikit-learn, Python, Pandas, and NumPy "
            "with 5+ years of experience. Master's degree required. Preferred "
            "qualifications: PostgreSQL, Docker, and clear experiment reporting."
        ),
    ),
    DemoJob(
        seed_key=f"{DEMO_SEED_VERSION}:job:api-data-analyst",
        title="API Data Analyst",
        company="Maple Circuit Works",
        location="New York, NY",
        employment_type="full_time",
        work_mode="on_site",
        source_url="https://example.invalid/jobs/api-data-analyst",
        application_status="offer",
        application_notes="Fictional offer stage for Kanban demonstration only.",
        description=(
            "Requirements: REST APIs, FastAPI, SQL, GitHub, and Agile delivery with "
            "6+ years of experience. Bachelor's degree required. Preferred qualifications: "
            "PostgreSQL, Docker, and Power BI for this fictional API reporting role."
        ),
    ),
)


DEMO_DATASET = DemoDataset(candidate=DEMO_CANDIDATE, jobs=DEMO_JOBS)
