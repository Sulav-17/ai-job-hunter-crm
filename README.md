# AI Job Hunter CRM

AI Job Hunter CRM is planned as a local-first, privacy-aware application for organizing a job search and supporting truthful, grounded application materials.

## Problem Statement

Job seekers often keep job postings, application status, notes, and resume-tailoring work scattered across files, spreadsheets, and browser tabs. That makes it hard to track progress and avoid unsupported or inaccurate application content.

## Planned Solution

The project will grow incrementally into a local CRM for job searching. Planned future milestones may add candidate profile management, job storage, explainable matching, resume suggestions, cover-letter generation, interview preparation, application tracking, analytics, and a controlled fictional-data demo.

Those later features are not implemented in Milestone 1.

## Current Milestone 1 Functionality

Milestone 1 provides only:

- a minimal Python backend package
- a FastAPI application in `backend/main.py`
- a `GET /health` endpoint
- one automated pytest test for the health endpoint

The health endpoint returns:

```json
{"status": "ok"}
```

## Initial Technology Stack

- Python
- FastAPI
- Uvicorn
- HTTPX
- pytest
- python-dotenv

No database, AI provider, frontend, Docker setup, scraping, authentication, or demo mode is implemented yet.

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

## Run The API

```powershell
python -m uvicorn backend.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

## Run Tests

```powershell
python -m pytest -q
```
