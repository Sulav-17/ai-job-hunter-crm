# AI Job Hunter CRM v1.0.0

Recommended version: `v1.0.0`

Recommended tag: `v1.0.0`

Recommended release title: `AI Job Hunter CRM v1.0.0`

## Summary

AI Job Hunter CRM v1.0.0 is a portfolio-ready local-first job-search CRM with a
fictional read-only public demo mode. It includes candidate/job management,
deterministic parsing, explainable scoring, pgvector-backed semantic similarity,
evidence-backed tailoring, application tracking, Docker support, CI configuration,
and final documentation.

## Verified Metrics

Update this section from final command output before publishing a release:

- Alembic head: `20260625_0010 (head)`
- Application statuses: 5
- Database migrations: 10
- Docker services: PostgreSQL, backend, frontend
- Full test suite: `215 passed in 13.18s` during final local Milestone 12 verification

Do not add unverifiable adoption, accuracy, placement, revenue, ATS, or time-saved
claims.

## Release Checklist

- Full pytest suite passes.
- Alembic current reports `20260625_0010 (head)`.
- `docker compose config` succeeds.
- Backend image builds.
- Frontend image builds.
- Local Compose starts without destroying `ai_job_hunter_postgres_data`.
- Demo Compose uses `ai_job_hunter_demo_postgres_data`.
- Fresh demo database migrates and seeds.
- `/health`, `/ready`, and `/app-info` pass.
- Streamlit returns HTTP 200.
- Demo browsing works without Ollama.
- No real personal data or secrets are tracked.
- Screenshots use fictional demo data only.

## Suggested GitHub Release Description

AI Job Hunter CRM v1.0.0 finalizes the project as a local-first, privacy-aware
job-search CRM with a safe public portfolio demo. The release includes FastAPI,
Streamlit, PostgreSQL 17 + pgvector, deterministic matching, local Ollama provider
interfaces, evidence-backed tailoring validation, Docker Compose workflows, CI,
and documentation.

## Suggested Final Commit

```text
chore: finalize demo, Docker and release documentation
```

## Manual Actions Not Performed

- No commit.
- No push.
- No tag.
- No deployment.
- No GitHub release creation.
- No screenshot capture.
