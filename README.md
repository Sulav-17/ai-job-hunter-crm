# AI Job Hunter CRM

AI Job Hunter CRM is planned as a local-first, privacy-aware application for organizing a job search and supporting truthful, grounded application materials.

## Problem Statement

Job seekers often keep job postings, application status, notes, and resume-tailoring work scattered across files, spreadsheets, and browser tabs. That makes it hard to track progress and avoid unsupported or inaccurate application content.

## Planned Solution

The project will grow incrementally into a local CRM for job searching. Planned future milestones may add candidate profile management, job storage, explainable matching, resume suggestions, cover-letter generation, interview preparation, application tracking, analytics, and a controlled fictional-data demo.

Those later features are not implemented yet.

## Current Milestone 3 Functionality

Milestone 3 provides:

- a minimal FastAPI backend
- `GET /health` for application liveness
- `GET /ready` for PostgreSQL readiness
- lazy application settings loaded from environment variables or `.env`
- a synchronous SQLAlchemy Engine and session factory
- Alembic migration setup
- a PostgreSQL-backed `candidate_profiles` table
- candidate profile CRUD endpoints
- tests for health, readiness, database connectivity, schema validation, and candidate API behavior

Resume parsing, skills, jobs, applications, matching, AI generation, frontend functionality, analytics, authentication, and demo mode are not implemented yet.

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

The baseline migration is intentionally empty. The second migration creates only the `candidate_profiles` table.

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
