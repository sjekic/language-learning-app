# Microservices overview (see root README for full details)

This directory hosts the four FastAPI services. The root `README.md` is the source of truth for architecture, flows, setup, and testing. This file is a concise orientation aligned with the current code.

## Runtime shape (current code)
- **Auth Service (:8001)**: Verifies Firebase ID tokens, syncs/reads users in Postgres. Legacy `/api/auth/signup` and `/api/auth/login` return 410 (deprecated).
- **User Service (:8002)**: Profile/stat endpoints; calls Auth `/api/auth/token/verify` for every request; reads/writes Postgres.
- **Translation Service (:8004)**: Linguee lookup + vocab CRUD; calls Auth `/api/auth/token/verify`; caches results; stores vocabulary (and auto-creates per-user vocab book) in Postgres.
- **Book Service (:8003)**: Story generation orchestrator; triggers Azure Container Jobs and writes to Blob when Azure env vars are present and `DEV_MODE` is false; in dev-mode it skips Azure. Currently does not call Auth in code.

Shared Postgres tables in `database/init.sql`: `users`, `books`, `user_books`, `vocabulary`. (There is no `auth_credentials` table in this codebase.)

## Health & docs (local defaults)
```
Health:       http://localhost:8001/ | 8002/ | 8003/ | 8004/
OpenAPI docs: http://localhost:8001/docs
              http://localhost:8002/docs
              http://localhost:8003/docs
              http://localhost:8004/docs
```

## For everything else
- Architecture diagrams, request flows, tech stack: see `../README.md`.
- Database schema: `../database/init.sql`.
- Tests and commands: `../tests/README.md`.
