# AI Job Hunter CRM

AI Job Hunter CRM is planned as a local-first, privacy-aware application for organizing a job search and supporting truthful, grounded application materials.

## Problem Statement

Job seekers often keep job postings, application status, notes, and resume-tailoring work scattered across files, spreadsheets, and browser tabs. That makes it hard to track progress and avoid unsupported or inaccurate application content.

## Planned Solution

The project will grow incrementally into a local CRM for job searching. Planned future milestones may add candidate profile management, job storage, explainable matching, resume suggestions, cover-letter generation, interview preparation, application tracking, analytics, and a controlled fictional-data demo.

Those later features are not implemented yet.

## Current Milestone 2 Functionality

Milestone 2 provides only:

- a minimal FastAPI backend
- `GET /health` for application liveness
- `GET /ready` for PostgreSQL readiness
- lazy application settings loaded from environment variables or `.env`
- a synchronous SQLAlchemy Engine and session factory
- Alembic migration setup
- one empty baseline migration
- tests for health, readiness, and a real PostgreSQL `SELECT 1`

No CRM tables, domain models, CRUD routes, AI providers, frontend, analytics, scraping, authentication, or demo mode are implemented yet.

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

Milestone 2 expects PostgreSQL to be reachable on host port `5433`.

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

The current baseline migration is intentionally empty and creates no CRM tables.

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
