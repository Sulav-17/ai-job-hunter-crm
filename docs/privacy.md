# Privacy and Security

AI Job Hunter CRM is local-first because résumé text, application notes, and job
search activity can be sensitive.

## Local Mode

`APP_MODE=local` is the full private application. It may store:

- résumé text;
- candidate profile details;
- job descriptions;
- application notes and status history;
- embeddings;
- semantic match results;
- tailoring outputs.

These records live in the configured PostgreSQL database. The application has no
authentication, so local mode must not be exposed publicly.

## Local Ollama

Optional live embedding and tailoring use local Ollama. No cloud AI provider is
required. Operators are responsible for installing models and keeping Ollama
private.

Recommended local models:

- `nomic-embed-text`
- `qwen3:4b`

## Demo Mode

`APP_MODE=demo` is for public portfolio browsing. It must use a separate demo
database and the volume `ai_job_hunter_demo_postgres_data`. Demo records are
fictional and public HTTP writes are blocked.

Demo mode does not call Ollama during browsing. Semantic and tailoring outputs are
precomputed and labeled honestly.

## Secrets

Never commit:

- `.env`;
- database passwords beyond fictional examples;
- API keys;
- cloud credentials;
- private résumé or job files;
- screenshots containing private data.

The frontend receives only safe `/app-info` metadata. It never receives database
credentials, provider configuration, file paths, or secrets.

## Logs and API Responses

The seed/reset command reports counts and seed version only. It does not log résumé
text, job descriptions, vectors, prompts, or generated content.

Public list responses avoid raw résumé text and full job descriptions where the API
schema is designed that way. Detail endpoints in local mode can display private
source text because local mode is private.

## Limitations

No software can guarantee absolute security. Operators remain responsible for:

- network exposure;
- database credentials;
- Docker volume handling;
- backups;
- public deployment configuration;
- screenshots and portfolio materials.
