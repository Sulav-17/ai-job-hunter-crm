# AI Job Hunter CRM

AI Job Hunter CRM is planned as a local-first, privacy-aware application for organizing a job search and supporting truthful, grounded application materials.

## Problem Statement

Job seekers often keep job postings, application status, notes, and resume-tailoring work scattered across files, spreadsheets, and browser tabs. That makes it hard to track progress and avoid unsupported or inaccurate application content.

## Planned Solution

The project will grow incrementally into a local CRM for job searching. Planned future milestones may add candidate profile management, job storage, explainable matching, resume suggestions, cover-letter generation, interview preparation, application tracking, analytics, and a controlled fictional-data demo.

Those later features are not implemented yet.

## Current Milestone 6 Functionality

Milestone 6 provides:

- a minimal FastAPI backend
- `GET /health` for application liveness
- `GET /ready` for PostgreSQL readiness
- lazy application settings loaded from environment variables or `.env`
- a synchronous SQLAlchemy Engine and session factory
- Alembic migration setup
- a PostgreSQL-backed `candidate_profiles` table
- candidate profile CRUD endpoints
- a PostgreSQL-backed `job_postings` table
- job posting CRUD endpoints for manually entered fictional or local job data
- deterministic parsing of saved job descriptions
- normalized skill extraction with aliases
- required versus preferred skill classification
- minimum years-of-experience extraction
- basic education-requirement extraction
- persisted parse results and job-skill associations
- deterministic parsing of saved candidate resume text
- persisted candidate parse results and candidate-skill associations
- tests for health, readiness, database connectivity, schema validation, candidate API behavior, job API behavior, and deterministic parsing behavior

Candidate-job matching, applications, AI generation, embeddings, frontend functionality, analytics, authentication, scraping, search, filtering, pagination, and demo mode are not implemented yet.

## Technology Stack

- Python
- FastAPI
- Uvicorn
- HTTPX and HTTPX2
- pytest
- python-dotenv
- pydantic-settings
- SQLAlchemy
- Psycopg 3
- Alembic
- PostgreSQL

## PostgreSQL Prerequisite

The application expects PostgreSQL to be reachable on host port `5433`.

One local container option is:

```powershell
docker run --name ai-job-hunter-crm-postgres -e POSTGRES_USER=jobhunter -e POSTGRES_PASSWORD=jobhunter_dev -e POSTGRES_DB=jobhunter -p 5433:5432 -d postgres:16
```

Start and stop the container:

```powershell
docker start ai-job-hunter-crm-postgres
docker stop ai-job-hunter-crm-postgres
```

Docker Compose is not part of this milestone.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a local `.env` file from `.env.example` if needed:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://jobhunter:jobhunter_dev@localhost:5433/jobhunter
```

The `.env` file is ignored by git and should not contain hosted or personal credentials.

## Migrations

Apply migrations:

```powershell
python -m alembic upgrade head
```

Show the current migration:

```powershell
python -m alembic current
```

The baseline migration is intentionally empty. The second migration creates only the `candidate_profiles` table. The third migration creates only the `job_postings` table. The fourth migration creates only job parsing tables: `skills`, `job_skills`, and `job_parse_results`. The fifth migration creates only candidate parsing tables: `candidate_skills` and `candidate_parse_results`.

## Run The API

```powershell
python -m uvicorn backend.main:app --reload
```

Application liveness:

```text
GET http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

Database readiness:

```text
GET http://127.0.0.1:8000/ready
```

When PostgreSQL is available:

```json
{"status": "ready", "database": "ok"}
```

When PostgreSQL is unavailable:

```json
{"detail": "Database unavailable"}
```

## Candidate Profiles

Candidate profiles currently include:

- `id`
- `full_name`
- `headline`
- `location`
- `professional_summary`
- `years_experience`
- `resume_text`
- `created_at`
- `updated_at`

`years_experience` must be between `0` and `80` when provided. List responses intentionally exclude `professional_summary` and `resume_text`.

Candidate endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/candidates` | Create a candidate profile |
| `GET` | `/candidates` | List candidate summaries |
| `GET` | `/candidates/{candidate_id}` | Retrieve one candidate profile |
| `PATCH` | `/candidates/{candidate_id}` | Partially update one candidate profile |
| `DELETE` | `/candidates/{candidate_id}` | Delete one candidate profile |

Example fictional request:

```json
{
  "full_name": "Avery Stone",
  "headline": "Data Analyst",
  "location": "Toronto, ON",
  "professional_summary": "Fictional analyst profile for local testing.",
  "years_experience": 4,
  "resume_text": "Fictional resume text. Do not use real resume content in examples."
}
```

## Job Postings

Job postings currently include:

- `id`
- `title`
- `company`
- `location`
- `employment_type`
- `work_mode`
- `source_url`
- `description`
- `created_at`
- `updated_at`

`description` must contain 50 to 50,000 characters after trimming. List responses intentionally exclude `description` and `source_url`.

Valid `employment_type` values:

- `full_time`
- `part_time`
- `contract`
- `internship`
- `temporary`
- `other`

Valid `work_mode` values:

- `remote`
- `hybrid`
- `on_site`

Job endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/jobs` | Create a job posting |
| `GET` | `/jobs` | List job posting summaries |
| `GET` | `/jobs/{job_id}` | Retrieve one job posting |
| `PATCH` | `/jobs/{job_id}` | Partially update one job posting |
| `DELETE` | `/jobs/{job_id}` | Delete one job posting |

Example fictional request:

```json
{
  "title": "Data Analyst",
  "company": "Northstar Labs",
  "location": "Toronto, ON",
  "employment_type": "full_time",
  "work_mode": "hybrid",
  "source_url": "https://example.com/jobs/data-analyst",
  "description": "This fictional role supports internal reporting workflows, stakeholder communication, and careful documentation for local testing."
}
```

## Deterministic Job Parsing

The parser uses deterministic Python logic only. It does not use LLMs, embeddings, semantic similarity, external AI APIs, or job-board scraping.

Parser outputs include:

- required skills
- preferred skills
- normalized canonical skill names
- short evidence snippets
- minimum years of experience
- basic education requirement
- parser version
- parsed timestamp

Parsing endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/jobs/{job_id}/parse` | Parse the saved job description and persist the result |
| `GET` | `/jobs/{job_id}/parse-result` | Retrieve the current saved parse result |

Example fictional workflow:

```powershell
python -m alembic upgrade head
python -m uvicorn backend.main:app --reload
```

Create a fictional job with `POST /jobs`, then parse it:

```text
POST /jobs/1/parse
GET /jobs/1/parse-result
```

Parser limitations:

- only recognizes skills in the code-defined catalog
- uses aliases and boundary-safe regular expressions, not fuzzy matching
- extracts only supported years-of-experience patterns
- extracts only supported education phrases
- does not score candidate fit
- does not parse candidate resumes
- does not infer unstated skills, education, or experience

## Deterministic Candidate Parsing

The candidate parser uses deterministic Python logic only. It parses the saved `resume_text` on a candidate profile and does not accept arbitrary resume text through the API.

Candidate parser outputs include:

- normalized candidate skills
- short evidence snippets
- explicitly stated years of experience
- basic education level
- parser version
- parsed timestamp

Candidate parsing endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/candidates/{candidate_id}/parse` | Parse the saved candidate resume text and persist the result |
| `GET` | `/candidates/{candidate_id}/parse-result` | Retrieve the current saved candidate parse result |

Missing or blank resume text returns:

```json
{"detail": "Candidate resume text is required"}
```

Candidate parser limitations:

- only recognizes skills in the code-defined catalog
- extracts only explicit supported years-of-experience phrases
- extracts only supported education phrases
- does not calculate experience from date ranges
- does not modify the original candidate profile
- does not match candidates to jobs
- does not use LLMs, embeddings, or semantic similarity

## Run Tests

Run the full suite:

```powershell
python -m pytest -q
```

Run only the non-integration readiness tests:

```powershell
python -m pytest -q tests/test_readiness.py
```

Run the PostgreSQL integration test:

```powershell
python -m pytest -q tests/integration/test_database.py
```

Run candidate tests:

```powershell
python -m pytest -q tests/unit/test_candidate_schemas.py tests/integration/test_candidates_api.py
```

Run job tests:

```powershell
python -m pytest -q tests/unit/test_job_schemas.py tests/integration/test_jobs_api.py
```

Run parser tests:

```powershell
python -m pytest -q tests/unit/test_skill_catalog.py tests/unit/test_job_parser.py tests/integration/test_job_parsing_api.py
```

Run candidate parser tests:

```powershell
python -m pytest -q tests/unit/test_candidate_parser.py tests/integration/test_candidate_parsing_api.py
```
