# Portfolio Case Study

## Problem

Job seekers often track applications, requirements, tailoring notes, and follow-up
status across disconnected tools. That makes it harder to compare fit, maintain
truthful application materials, and see progress at a glance.

## Solution

AI Job Hunter CRM is a full-stack job-search workspace with FastAPI, PostgreSQL,
pgvector, local Ollama integrations, and Streamlit. It stores candidate and job
records, extracts skills deterministically, calculates explainable matches, stores
separate semantic similarity, generates grounded tailoring suggestions, and tracks
applications through a Kanban-style workflow.

## Architecture

The application uses Streamlit for the product UI, FastAPI for API contracts,
SQLAlchemy services for business logic, PostgreSQL 17 + pgvector for persistence,
and optional local Ollama for private AI workflows. Public demo mode reads
precomputed fictional data and does not require Ollama.

## Major Features

- Candidate and job CRUD in local mode.
- Deterministic candidate and job parsing.
- Shared normalized skill catalog.
- Required/preferred skill classification.
- Explainable deterministic match scoring.
- Separate semantic similarity with pgvector-backed embeddings.
- Evidence-backed tailoring suggestions validated against résumé text.
- Application tracking with status history.
- Read-only fictional demo mode.
- Docker and CI support.

## Deterministic Versus Semantic Matching

Deterministic scoring produces explainable component scores and missing skills.
Semantic similarity is stored separately and never presented as objective truth or
mixed into a hidden hybrid score.

## Evidence-Backed Tailoring

Tailoring output is structured and validated. Resume bullets require supporting
evidence that appears in the candidate résumé text. The system adds a human-review
warning and avoids fabricating experience, education, certifications, tools, or
metrics.

## Privacy Design

Local mode is private and writable. Demo mode is read-only, fictional, and stored
in a separate database volume. The frontend uses `/app-info` from the backend as
the authoritative mode indicator, while the backend enforces read-only demo rules.

## Technical Challenges

- Keeping deterministic and semantic scores separate.
- Adding pgvector while preserving PostgreSQL 17.
- Detecting stale source hashes.
- Validating generated output against evidence.
- Supporting local Ollama without requiring it for the public demo.
- Keeping Streamlit navigation and demo read-only state synchronized.
- Designing safe seed/reset behavior without `TRUNCATE` or broad deletes.

## Testing Strategy

The test suite covers schemas, parsing, matching, embeddings, tailoring validation,
readiness, API workflows, database behavior, demo restrictions, and deterministic
demo seed/reset behavior. Automated tests use fictional data and fake providers.

## Verified Results

Local Milestone 12 verification recorded:

- 10 Alembic migrations through `20260625_0010`;
- 5 application statuses;
- 3 Docker services: PostgreSQL, backend, frontend;
- 215 automated tests passing in the full suite.

Final release notes should include exact Docker and fresh-database verification
outputs from the publishing machine. Do not claim user adoption, placement rates,
time savings, revenue, ATS success, or accuracy percentages.

## Limitations

- No authentication.
- No scraping or automatic applications.
- No email or reminders.
- No DOCX/PDF export.
- No cloud AI provider integration.
- No production deployment automation.

## Future Improvements

- Authentication and private hosted workspaces.
- Job-board integrations with explicit user control.
- Notifications and reminders.
- Résumé version history.
- Export workflows.
- Company research support.

## Resume Bullets

- Built a FastAPI and PostgreSQL 17 CRM with SQLAlchemy, Alembic migrations, and
  pgvector-backed semantic similarity for a local-first job-search workflow.
- Implemented deterministic parsing and explainable candidate-job scoring with
  required/preferred skills, experience, education, and transparent missing-skill output.
- Integrated optional local Ollama providers behind interfaces for embeddings and
  structured tailoring while preserving a no-Ollama read-only public demo path.
- Designed evidence validation for generated résumé bullets and cover letters to
  prevent fabricated experience and unsupported claims.
- Delivered a Streamlit dashboard, Dockerized services, CI checks, and automated
  tests for local/private and fictional demo modes.
