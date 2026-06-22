# AGENTS.md

## Project

This repository contains **AI Job Hunter CRM**, a local-first, privacy-aware job-search management application.

The project is being developed incrementally through approved milestones.

The system will eventually support:

* candidate profile management
* job-posting storage and parsing
* skill extraction and normalization
* transparent job-match scoring
* optional semantic similarity
* truthful resume-tailoring suggestions
* grounded cover-letter generation
* interview-question generation
* application tracking
* Kanban workflows
* job-search analytics
* private local operation
* a controlled public portfolio demo using fictional data

Do not assume that all planned features are currently approved or implemented.

---

## Milestone-First Workflow

Work on only one milestone at a time.

Before proposing or making changes:

1. Read this `AGENTS.md` file.
2. Read the active milestone specification in:

```text
docs/milestones/milestone-XX.md
```

3. Inspect the existing repository.
4. Identify what already exists.
5. Compare the repository against the active milestone.
6. Propose a limited implementation plan.
7. Wait for approval before editing, unless explicitly instructed to begin implementation.

The active milestone specification is the source of truth for scope.

Do not implement future milestones.

Do not add features merely because they appear in the README, project roadmap, repository structure, or comments.

---

## Scope Control

Only modify files required for the active milestone.

Do not:

* implement several milestones together
* create future database models early
* create future APIs early
* add unused abstractions
* add unused services
* create speculative architecture
* install dependencies for future milestones
* refactor unrelated code
* rename unrelated files
* modify unrelated documentation
* add stretch goals before the MVP is stable

When a useful improvement is outside the active milestone, mention it as a future recommendation instead of implementing it.

---

## Repository Inspection

Before editing:

* inspect the repository tree
* read relevant existing files
* inspect current tests
* inspect configuration files
* inspect existing naming conventions
* identify the current dependency set
* identify whether the working tree already contains user changes

Never overwrite user work without explaining the risk.

Do not assume a file is unused without checking imports, tests, documentation, and references.

---

## Planning Requirements

Before editing, provide a plan containing:

1. What currently exists
2. Which files need to change or be created
3. The proposed implementation
4. Tests to add or update
5. Database changes, if any
6. Privacy risks
7. Public-demo risks
8. Dependencies to add, if any
9. Assumptions or unclear requirements

Do not edit files until the user approves the plan unless the user explicitly instructs you to implement immediately.

---

## Code Quality

Write code that is understandable to a beginner-to-intermediate Python developer.

Prefer:

* clear names
* small functions
* explicit behavior
* type hints
* docstrings where useful
* simple control flow
* predictable return values
* separation of responsibilities
* deterministic logic where possible

Avoid:

* unnecessary design patterns
* premature abstractions
* excessive inheritance
* hidden side effects
* clever one-liners
* unexplained metaprogramming
* large functions with multiple responsibilities
* deeply nested logic
* duplicated business rules

Follow the existing repository style and naming conventions.

---

## Architecture Rules

Maintain clear separation between:

* API routes
* request and response schemas
* database models
* database sessions
* business services
* AI providers
* matching logic
* frontend code
* private data
* public-demo data

Do not place business logic directly inside API routes when a service layer exists.

Do not place database queries directly inside frontend code.

Do not make the Streamlit frontend access PostgreSQL directly once the FastAPI API layer exists, unless an approved milestone explicitly requires it.

Keep external-provider integrations behind provider interfaces once provider abstractions are introduced.

Do not introduce a vector database until the active milestone justifies it.

---

## Database Rules

Database work must use the approved database architecture.

When database features are introduced:

* use PostgreSQL
* use SQLAlchemy ORM
* use Alembic migrations
* keep ORM models separate from Pydantic schemas
* use explicit relationships
* use clear foreign keys
* preserve referential integrity
* avoid destructive migrations without approval
* do not silently delete user data
* do not modify migration history after it has been applied unless explicitly approved
* add indexes only when justified
* explain database relationships clearly

Every database schema change must include:

* model changes
* migration changes
* test updates
* documentation of the change

Never use real personal data in migration files, tests, seeds, fixtures, screenshots, or public-demo files.

---

## API Rules

FastAPI routes should:

* use clear resource-oriented paths
* use correct HTTP methods
* validate input using Pydantic
* return explicit response schemas when appropriate
* use meaningful HTTP status codes
* handle expected errors cleanly
* avoid leaking internal exceptions
* avoid exposing secrets or private data
* remain small and delegate business logic to services

Do not create endpoints that are not required by the active milestone.

Do not implement automated job applications.

Do not implement job-board scraping unless an approved future milestone explicitly requires it.

---

## Pydantic Rules

Use separate schemas when their responsibilities differ, such as:

* create schemas
* update schemas
* response schemas
* internal service models

Do not expose database-only fields unnecessarily.

Validate:

* required fields
* text length
* enum values
* URLs when relevant
* salary boundaries when relevant
* job-description size limits
* public-demo input restrictions

Avoid accepting unrestricted arbitrary dictionaries when a structured schema is appropriate.

---

## Matching and Scoring Rules

Matching must be explainable.

Prefer deterministic scoring before semantic or LLM-based scoring.

A match result should eventually expose:

* total score
* component scores
* scoring weights
* matched skills
* missing skills
* matched qualifications
* missing qualifications
* reasoning that can be traced to stored candidate and job data

Do not hide important scoring logic inside prompts.

Do not present semantic similarity as objective truth.

Do not invent candidate skills, qualifications, employment history, achievements, or experience.

Do not award points for information that does not exist in the candidate profile.

Changes to scoring weights require tests and documentation.

---

## AI Generation Rules

Paid APIs must remain optional.

The project must remain completable using:

* deterministic logic
* mock providers
* local models
* optional Ollama integrations

When AI providers are introduced:

* use a provider interface
* keep provider-specific code isolated
* use structured outputs
* validate provider responses
* handle provider failures
* provide deterministic or mock fallbacks where required
* never expose API keys
* never log secrets
* never place secrets in prompts or tests

Generated content must remain grounded in actual candidate information.

The system must not:

* fabricate work experience
* fabricate education
* fabricate certifications
* fabricate metrics
* fabricate technical skills
* claim tools the candidate has never used
* invent company knowledge
* invent job responsibilities
* invent achievements

Resume suggestions may rephrase or prioritize existing experience, but must not create false experience.

Cover letters must be based only on verified candidate and job information.

Interview questions may be generated from the job requirements, but suggested answers must remain grounded in real candidate experience.

---

## Privacy Rules

Privacy is a core architecture requirement.

The project must preserve separation between:

### Private Local Mode

May contain:

* real resume information
* real candidate data
* real applications
* private notes
* persistent PostgreSQL records
* local AI use
* optional hosted AI use selected by the user

### Controlled Public Demo Mode

Must use:

* fictional candidate information
* fictional or safe sample jobs
* demo-only data
* limited job-description input
* resettable state
* temporary storage where possible
* mock, local, or strictly limited AI generation
* clear privacy notices

The public demo must not contain:

* the owner’s real resume
* real application history
* real personal notes
* private contact information
* unrestricted file uploads
* unrestricted paid API calls
* permanent storage of visitor resumes
* permanent storage of personal information
* automated job applications
* job-board scraping
* exposed environment variables
* exposed API keys

Never copy data from private files into demo files.

Never use real candidate data as test fixtures or seed data.

---

## Demo-Mode Rules

Demo data must be visibly fictional.

Demo features must support resetting to a known seeded state.

When demo reset functionality is introduced:

* reset only demo data
* never reset private data
* require an explicit demo-mode context
* make destructive behavior clear
* test reset behavior
* preserve separation between private and demo database environments

Public-demo inputs should eventually include:

* input-size restrictions
* safe text validation
* clear privacy notices
* no permanent storage where avoidable
* limited generation functionality

---

## Dependency Rules

Add dependencies only when required by the active milestone.

Before adding a dependency:

1. Explain why it is needed.
2. Confirm that the standard library or an existing dependency is insufficient.
3. Add it to the appropriate dependency file.
4. Keep versions compatible with the project’s supported Python version.
5. Avoid overlapping libraries that solve the same problem.
6. Update setup documentation when needed.

Do not install all planned technologies at the start of the project.

Do not introduce:

* Sentence Transformers
* pgvector
* ChromaDB
* Ollama clients
* hosted AI SDKs
* Streamlit
* Docker-related dependencies
* PostgreSQL drivers
* SQLAlchemy
* Alembic

until the active milestone requires them.

---

## Environment and Secret Rules

Never hardcode:

* API keys
* database passwords
* tokens
* credentials
* private URLs
* personal information

Never commit `.env`.

Use `.env.example` to document environment-variable names with dummy or blank values.

Do not include real secrets in:

* source code
* tests
* fixtures
* documentation
* screenshots
* logs
* example commands
* seed files
* Git history

When configuration code is introduced, read values through environment variables or approved configuration objects.

---

## Testing Rules

Add or update tests for meaningful behavior.

Use:

* unit tests for deterministic services
* API tests for route contracts
* integration tests for database behavior
* regression tests for fixed bugs
* evaluation cases for scoring and generation workflows

Tests must:

* be deterministic
* avoid paid APIs
* avoid external network calls
* avoid real personal data
* avoid reliance on the user’s private local database
* clean up created records
* use fictional fixtures
* verify both successful and failure behavior where relevant

Mock external providers.

Do not weaken assertions merely to make a failing test pass.

Do not delete valid tests without explaining why.

After implementation:

* run the most relevant targeted tests
* run the full suite when practical
* report exact commands
* report exact results
* report skipped or failing tests honestly

---

## Formatting and Linting

Use the repository’s configured formatting, linting, and type-checking tools.

Do not add new formatting or linting tools unless the active milestone requires them or the user approves them.

After implementation, run configured checks when available.

Do not make unrelated formatting changes across the repository.

---

## Documentation Rules

Documentation must reflect actual implemented behavior.

Do not claim future features are complete.

Update documentation when the active milestone changes:

* setup
* commands
* architecture
* API behavior
* environment variables
* database schema
* privacy behavior
* demo-mode behavior
* known limitations

Milestone specifications belong in:

```text
docs/milestones/
```

Architecture documentation belongs in:

```text
docs/
```

Do not remove milestone history.

---

## Git Rules

Do not commit unless explicitly instructed.

Do not push unless explicitly instructed.

Do not rewrite Git history.

Do not use destructive Git commands without explicit approval.

Avoid:

```text
git reset --hard
git clean -fd
git checkout -- .
git push --force
```

Before implementation, check the working tree when possible.

After implementation, summarize modified files.

Suggest a clear commit message, but leave the commit to the user unless explicitly told otherwise.

Do not include:

* `.env`
* `.venv`
* caches
* local databases
* private resumes
* uploaded private documents
* generated private application content
* local model files
* temporary demo data
* secrets

---

## File Modification Rules

Before changing a file:

* read it
* understand its role
* inspect related tests
* preserve existing conventions

Do not modify unrelated files.

Do not replace an entire file when a small focused change is sufficient.

Do not remove comments, documentation, or behavior without justification.

Do not create duplicate utilities when an existing implementation can be reused.

Summarize every created, modified, or deleted file after implementation.

---

## Error Handling

Handle expected errors explicitly.

Prefer clear domain errors over raw exceptions.

Do not expose stack traces, database credentials, provider responses, or private data through API responses.

Do not silently swallow exceptions.

Log useful operational information without logging secrets or personal data.

Do not add complex logging infrastructure before the approved milestone requires it.

---

## Security Rules

Treat all pasted job descriptions and uploaded content as untrusted input.

When relevant milestones are implemented:

* validate text length
* validate file type
* restrict upload size
* sanitize filenames
* prevent path traversal
* avoid executing generated code
* avoid evaluating arbitrary expressions
* avoid unrestricted HTML rendering
* avoid SQL built from string concatenation
* use ORM queries or parameterized SQL
* restrict CORS deliberately
* protect destructive reset operations
* avoid exposing internal IDs unnecessarily

Do not add authentication until an approved milestone requires it.

Do not pretend demo mode provides production-grade security.

---

## Forbidden Features Unless Explicitly Approved

Do not implement:

* automated job applications
* browser automation
* LinkedIn scraping
* Indeed scraping
* job-board scraping
* CAPTCHA bypassing
* email ingestion
* calendar integration
* salary APIs
* Chrome extensions
* real authentication
* multi-user support
* subscriptions
* payments
* production-scale infrastructure
* unrestricted public AI generation
* automatic résumé submission
* automatic messaging to recruiters

Mention these only as future possibilities when relevant.

---

## Final Implementation Report

After completing an approved milestone, report:

1. Summary of the implementation
2. Every created file
3. Every modified file
4. Every deleted file
5. Tests added or updated
6. Commands run
7. Exact test results
8. Database changes
9. Migration changes
10. Dependency changes
11. Privacy considerations
12. Demo-mode considerations
13. Deviations from the approved plan
14. Remaining limitations
15. Suggested manual verification steps
16. Suggested commit message

Confirm explicitly:

* only the active milestone was implemented
* no real personal data was added
* no secrets were added
* private and demo concerns remain separated
* no commit was created unless requested
