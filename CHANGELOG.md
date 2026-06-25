# Changelog

## v1.0.0 - Recommended

### Added

- Local/private and read-only demo application modes.
- Safe `/app-info` endpoint for backend-authoritative mode metadata.
- Demo-mode backend write restrictions.
- Demo markers for candidate, job, and application root records.
- Deterministic fictional demo dataset and idempotent seed/reset CLI.
- Precomputed demo embeddings, semantic results, and tailoring results.
- Docker support for PostgreSQL 17 + pgvector, FastAPI, and Streamlit.
- Separate demo Docker database and volume.
- GitHub Actions CI workflow.
- Final README, architecture, privacy, demo, screenshot, and case-study docs.

### Changed

- Frontend displays demo notices and hides unsafe write/provider controls in demo mode.
- API responses for candidate, job, and application roots include a safe `is_demo` flag.

### Security and Privacy

- Demo mode is read-only through public HTTP routes.
- Demo reset remains CLI/container-startup only.
- Demo data uses fictional records and a separate database volume.

### Excluded

- Authentication, scraping, automatic applications, email, payments, cloud AI, DOCX/PDF export, and new matching algorithms remain intentionally out of scope.
