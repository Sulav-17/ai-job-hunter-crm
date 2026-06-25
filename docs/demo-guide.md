# Demo Guide

The public demo is intentionally read-only. It is designed for recruiter browsing,
not for public data entry.

## Run Demo Mode

```powershell
docker compose -f docker-compose.demo.yml up --build
```

Open:

- frontend: <http://127.0.0.1:8501>
- API docs: <http://127.0.0.1:8000/docs>
- app info: <http://127.0.0.1:8000/app-info>

Expected `/app-info`:

```json
{
  "app_mode": "demo",
  "read_only": true,
  "demo_data": true,
  "notice": "This demonstration contains fictional, precomputed data."
}
```

## Demo Data

The seed creates:

- one fictional candidate;
- five fictional jobs;
- applications across `saved`, `applied`, `interview`, `rejected`, and `offer`;
- candidate and job parse results;
- deterministic match results;
- precomputed demo embeddings;
- precomputed semantic match results;
- precomputed tailoring results;
- application status history.

All names, companies, contact details, locations, résumé text, job descriptions,
application notes, and generated content are invented.

## Read-Only Behavior

Demo mode blocks public HTTP writes:

- candidate/job/application create, update, delete;
- parsing;
- embedding generation;
- deterministic match persistence;
- semantic match calculation;
- tailoring generation/regeneration;
- status updates.

Safe GET browsing remains available.

## Reset

Seed:

```powershell
python -m scripts.seed_demo
```

Reset:

```powershell
python -m scripts.seed_demo --reset
```

Reset deletes only demo-marked candidate, job, and application roots. It does not
use `TRUNCATE`, does not delete shared skills, and does not delete non-demo roots.

## Volumes

Local/private volume:

```text
ai_job_hunter_postgres_data
```

Demo volume:

```text
ai_job_hunter_demo_postgres_data
```

Do not use `docker compose down -v` against the local stack unless you intend to
remove private local data.

## Ollama

The demo does not require Ollama. Matching, semantic results, and tailoring are
precomputed and labeled as such. Do not expose Ollama publicly.

## Recruiter Demo Script

1. Introduce the problem: job seekers juggle jobs, requirements, tailoring, and status tracking.
2. Show the fictional candidate profile and parsed résumé skills.
3. Open a fictional job and show parsed requirements.
4. Show deterministic matching and missing skills.
5. Show semantic similarity separately.
6. Show evidence-backed tailoring bullets and warnings.
7. Show the Kanban board and status history.
8. Explain local private mode versus fictional read-only demo mode.
9. Briefly mention FastAPI, PostgreSQL + pgvector, local Ollama support, Docker, and tests.
