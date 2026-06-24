# AI Job Hunter CRM

AI Job Hunter CRM is planned as a local-first, privacy-aware application for organizing a job search and supporting truthful, grounded application materials.

## Problem Statement

Job seekers often keep job postings, application status, notes, and resume-tailoring work scattered across files, spreadsheets, and browser tabs. That makes it hard to track progress and avoid unsupported or inaccurate application content.

## Planned Solution

The project will grow incrementally into a local CRM for job searching. Planned future milestones may add candidate profile management, job storage, explainable matching, resume suggestions, cover-letter generation, interview preparation, application tracking, analytics, and a controlled fictional-data demo.

Those later features are not implemented yet.

## Current Milestone 10 Functionality

Milestone 10 provides:

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
- deterministic, explainable candidate-job match scoring
- persisted match results and per-skill match details
- PostgreSQL-backed application tracking
- status-change history for each application
- PostgreSQL pgvector-backed candidate and job embeddings
- local Ollama embedding-provider support
- persisted semantic candidate-job similarity results
- a PostgreSQL-backed `tailoring_results` table
- local Ollama text-generation provider support behind an injectable interface
- text-only tailoring endpoints for saved candidate/job pairs
- grounded tailored summaries, resume-bullet suggestions, cover-letter drafts, keywords, and warnings
- stale-result detection based on source hashes, deterministic match context, provider/model identity, and prompt version
- tests for health, readiness, database connectivity, schema validation, candidate API behavior, job API behavior, and deterministic parsing behavior

File generation, interview preparation, frontend functionality, Kanban workflows, analytics, reminders, email, authentication, scraping, search, filtering, pagination, file exports, cloud AI providers, and demo mode are not implemented yet.

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
- pgvector
- local Ollama embeddings
- local Ollama text generation

## PostgreSQL Prerequisite

The application expects PostgreSQL with pgvector support to be reachable on host port `5433`.

Use a PostgreSQL 17 image that includes pgvector. Do not replace an existing database volume without a backup.

One local container shape is:

```powershell
docker run --name ai-job-hunter-crm-postgres -e POSTGRES_USER=jobhunter -e POSTGRES_PASSWORD=jobhunter_dev -e POSTGRES_DB=jobhunter -p 5433:5432 -d <postgres-17-pgvector-image>
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
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_TIMEOUT_SECONDS=60
GENERATION_PROVIDER=ollama
GENERATION_MODEL=qwen3:4b
GENERATION_TIMEOUT_SECONDS=120
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

The baseline migration is intentionally empty. The second migration creates only the `candidate_profiles` table. The third migration creates only the `job_postings` table. The fourth migration creates only job parsing tables: `skills`, `job_skills`, and `job_parse_results`. The fifth migration creates only candidate parsing tables: `candidate_skills` and `candidate_parse_results`. The sixth migration creates only match scoring tables: `match_results` and `match_skill_details`. The seventh migration creates only application tracking tables: `applications` and `application_status_history`. The eighth migration enables the pgvector extension when needed and creates only embedding and semantic similarity tables: `candidate_embeddings`, `job_embeddings`, and `semantic_match_results`. The ninth migration creates only `tailoring_results`.

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

## Deterministic Match Scoring

Match scoring compares one parsed candidate with one parsed job using deterministic Python logic only. It does not use LLMs, embeddings, semantic similarity, external AI APIs, or scraping.

Matching endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/candidates/{candidate_id}/jobs/{job_id}/match` | Calculate and persist the current match result |
| `GET` | `/candidates/{candidate_id}/jobs/{job_id}/match-result` | Retrieve the last saved match result |

The scorer uses these base weights:

- required skills: `55`
- preferred skills: `15`
- experience: `20`
- education: `10`

Only applicable dimensions participate. Missing dimensions are excluded and remaining weights are normalized to total `100` using deterministic half-up rounding. If rounded weights leave a remainder, the adjustment priority is required skills, preferred skills, experience, then education; negative remainders are removed in reverse priority.

Experience uses parsed candidate years first, then profile years. A zero-year job requirement scores `100` and does not divide by zero. Education is scored using the stored education levels only; the scorer does not infer or modify candidate or job data.

Saved match results can become stale. Updating or re-parsing a candidate or job does not automatically recalculate existing matches. Use the `POST` match endpoint again to refresh the saved calculation.

Match responses include component scores, applicable weights, matched and missing required skills, matched and missing preferred skills, experience comparison, education comparison, scoring version, and calculation timestamp. Responses do not include `resume_text` or raw job descriptions.

## Application Tracking

Application tracking links one candidate to one job with a current status and a status-change history. It does not apply to jobs automatically, send email, schedule reminders, provide Kanban UI, or add analytics.

Allowed application statuses:

- `saved`
- `applied`
- `interview`
- `rejected`
- `offer`

Application endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/applications` | Create an application and initial status-history row |
| `GET` | `/applications` | List applications newest first |
| `GET` | `/applications/{application_id}` | Retrieve one application |
| `PATCH` | `/applications/{application_id}` | Partially update one application |
| `DELETE` | `/applications/{application_id}` | Delete one application |
| `GET` | `/applications/{application_id}/status-history` | Retrieve status history oldest first |

Creating an application defaults to `saved` when status is omitted. Each candidate-job pair can have only one application record. Creating a duplicate returns:

```json
{"detail": "Application already exists for this candidate and job"}
```

Status changes append one history row. Patching the same status again does not add duplicate history. Updating only notes or timestamps does not add history.

When status changes to `applied`, `applied_at` is automatically set only if it is not supplied in the PATCH and the stored value is currently null. Explicit `applied_at` values, including explicit null, are preserved. Creating an application does not invent `applied_at`.

List responses intentionally exclude notes. Application responses do not include candidate resume text, professional summaries, raw job descriptions, parsing evidence, matching evidence, or generated content.

## Local Embeddings And Semantic Similarity

Embeddings use a small provider abstraction. The default provider is local Ollama using:

```text
POST {OLLAMA_BASE_URL}/api/embed
```

Default local settings:

```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_TIMEOUT_SECONDS=60
```

Embedding endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/candidates/{candidate_id}/embedding` | Create or refresh candidate embedding metadata |
| `GET` | `/candidates/{candidate_id}/embedding` | Retrieve candidate embedding metadata |
| `POST` | `/jobs/{job_id}/embedding` | Create or refresh job embedding metadata |
| `GET` | `/jobs/{job_id}/embedding` | Retrieve job embedding metadata |
| `POST` | `/candidates/{candidate_id}/jobs/{job_id}/semantic-match` | Calculate and persist semantic similarity |
| `GET` | `/candidates/{candidate_id}/jobs/{job_id}/semantic-match-result` | Retrieve the last saved semantic result |

Candidate embedding source is built from labeled `headline`, `professional_summary`, and `resume_text` sections. Candidate `resume_text` is required. Job embedding source is built from labeled `title`, `company`, and `description` sections. Source text is normalized deterministically and hashed with SHA-256.

Embedding metadata responses include IDs, provider/model identity, dimensions, source hash, embedded timestamp, and stale status. They never return raw vectors, resume text, professional summaries, job descriptions, parser evidence, matching evidence, or generated content.

Semantic similarity is stored separately from deterministic match scoring. It does not change deterministic match weights or results. Saved semantic results may become stale if source text or embedding model changes; use the POST semantic endpoint to recalculate after refreshing embeddings.

## AI Tailoring Assistant

Tailoring uses a text-generation provider abstraction. The default provider is local Ollama using:

```text
POST {OLLAMA_BASE_URL}/api/generate
```

Default local settings:

```env
GENERATION_PROVIDER=ollama
GENERATION_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://localhost:11434
GENERATION_TIMEOUT_SECONDS=120
```

Tailoring endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/candidates/{candidate_id}/jobs/{job_id}/tailoring` | Generate or reuse text-only tailoring output |
| `GET` | `/candidates/{candidate_id}/jobs/{job_id}/tailoring-result` | Retrieve the last saved tailoring result |

Generation requires an existing candidate, an existing job, nonblank candidate `resume_text`, a candidate parse result, and a job parse result. It does not require semantic similarity. The service builds deterministic candidate source, job source, and match context, hashes each with SHA-256, and marks saved results stale when source hashes, match-context hash, provider/model identity, or prompt version differ.

Tailoring responses include only structured generated text, keywords, warnings, hashes, timestamps, and stale status. They do not return raw resume text, professional summary source, raw job descriptions, prompts, provider payloads, vectors, or embeddings.

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

Run match scoring tests:

```powershell
python -m pytest -q tests/unit/test_match_scorer.py tests/integration/test_matching_api.py
```

Run application tracking tests:

```powershell
python -m pytest -q tests/unit/test_application_schemas.py tests/integration/test_applications_api.py
```

Run embedding and semantic similarity tests:

```powershell
python -m pytest -q tests/unit/test_embedding_sources.py tests/unit/test_semantic_similarity.py tests/integration/test_embeddings_api.py
```
