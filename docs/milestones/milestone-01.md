# Milestone 1 — Repository Foundation and FastAPI Health Check

## Status

Approved for planning and implementation.

## Goal

Create the initial repository foundation for AI Job Hunter CRM and prove that a minimal FastAPI application can run locally and pass one automated endpoint test.

## Included Scope

* Create the minimal project structure required for this milestone.
* Create a Python backend package.
* Create a FastAPI application in `backend/main.py`.
* Add `GET /health`.
* Return exactly:

```json
{"status": "ok"}
```

* Add one pytest test for the health endpoint.
* Verify both the HTTP status code and JSON body.
* Create `.gitignore`.
* Create `.env.example`.
* Create `requirements.txt`.
* Create a basic `README.md`.
* Preserve and follow `AGENTS.md`.
* Run the relevant test.
* Report all changed files.

## Excluded Scope

Do not add:

* PostgreSQL
* SQLAlchemy
* Alembic
* database models or sessions
* candidate profiles
* job records
* CRUD routes
* job parsing
* skill extraction
* matching or scoring
* embeddings
* vector databases
* LLM providers
* Streamlit
* Kanban functionality
* application analytics
* Docker
* Docker Compose
* demo-mode implementation
* seed data
* job-board scraping
* automated job applications
* authentication

## Required Structure

```text
ai-job-hunter-crm/
├── backend/
│   ├── __init__.py
│   └── main.py
├── docs/
│   └── milestones/
│       └── milestone-01.md
├── tests/
│   └── test_health.py
├── .env.example
├── .gitignore
├── AGENTS.md
├── README.md
└── requirements.txt
```

Do not create empty future architecture directories unless they are required to make this milestone work.

## FastAPI Requirements

The application must:

* expose a FastAPI object named `app`
* use `backend/main.py`
* provide `GET /health`
* return HTTP 200
* return exactly `{"status": "ok"}`
* contain no database or external-service dependency

## Test Requirements

Use FastAPI `TestClient` and pytest.

The test must verify:

* `response.status_code == 200`
* `response.json() == {"status": "ok"}`

The test must not require a running external server.

## Dependency Scope

Install only the initial packages needed for this milestone:

* FastAPI
* Uvicorn
* HTTPX
* pytest
* python-dotenv

Do not install PostgreSQL, SQLAlchemy, Alembic, Sentence Transformers, Streamlit, Docker-related Python packages, or LLM SDKs.

## Environment Requirements

`.env.example` may document basic non-secret application settings, but the application does not need an environment configuration layer yet.

Never create or commit a real `.env` file containing secrets.

## Privacy Requirements

* Do not add a real résumé.
* Do not add a real candidate profile.
* Do not add real job applications.
* Do not add personal notes.
* Add ignore rules for likely private local-data directories.
* Use no real personal data in examples.

## README Requirements

The initial README should include:

* project name
* problem statement
* planned solution
* current Milestone 1 functionality
* initial technology stack
* setup instructions
* API run command
* test command
* health endpoint
* clear note that later features are planned and not yet implemented

Do not claim unimplemented features as completed.

## Acceptance Criteria

Milestone 1 is complete only when:

1. The virtual environment is active.
2. Initial dependencies install successfully.
3. `python -m pytest -q` passes.
4. Exactly one health test exists and passes.
5. `python -m uvicorn backend.main:app --reload` starts the API.
6. `GET /health` returns HTTP 200.
7. The response is exactly `{"status": "ok"}`.
8. No future milestone is implemented.
9. No secrets or personal data are tracked.
10. Codex summarizes every modified file.
11. The user manually verifies the endpoint.
12. The user creates the Git commit rather than Codex.

## Suggested Commit Message

```text
chore: initialize AI Job Hunter CRM foundation
```
