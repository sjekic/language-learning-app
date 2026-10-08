# Story Generation Reliability and Local Startup Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute these approved tasks. Keep all commits local.

**Goal:** Restore the story job pipeline, prevent lost triggers and incomplete published stories, and make local startup actionable on Windows.

**Architecture:** Keep FastAPI, Azure Blob triggers and the existing manifest/chapter/assembly stages. Pollers own trigger selection and acknowledgement; workers process an explicit validated payload. Use in-memory storage and deterministic model responses to test the full pipeline without cloud calls. Keep development setup and dependency maintenance separate from job behavior.

**Tech stack:** Python 3.11, pytest/unittest, Azure Blob Storage, FastAPI, React/TypeScript, Vite, Docker Compose, npm.

## Constraints

- The user approved the proposed contribution and also requested help with Docker startup and npm warnings.
- No GitHub push, remote branch, deployment, paid model call or cloud job execution.
- Preserve the existing staged deletions of `backend/package.json`, `backend/package-lock.json`, and `backend/server.js`. Exclude them from every contribution commit.
- Never print credential values or include local environment files in commits.
- Keep each commit coherent, with its relevant regression tests. Closely coupled trigger contract and acknowledgement changes may share a commit.

## Tasks

- [x] Establish a Python 3.11 virtual environment and baseline existing tests; capture existing failures separately.
- [x] Reproduce current batch rejection, premature acknowledgement and partial assembly using offline regression tests.
- [x] In `jobs/src/`, accept current chapter batches and legacy single-chapter triggers. Validate chapter bounds and pass the exact selected trigger to the worker.
- [x] Centralize trigger processing and acknowledgement. Retain triggers on failure, avoid processing another trigger by accident, and handle competing workers using finite renewable leases.
- [x] Reuse valid persisted manifests/chapters on retries and use deterministic downstream trigger names. Surface downstream enqueue failures and orchestrator timeouts.
- [x] Require every expected valid chapter before final publication. Reject missing, empty, wrong-story or wrong-number chapters.
- [x] Cover successful ten-chapter generation and failure/retry scenarios in `tests/test_job_pipeline.py`; update `tests/test_jobs.py` to assert real payload/output behavior.
- [x] Document the job contract, retry limitations and offline test commands in `jobs/README.md`.
- [x] Diagnose/start the local Docker engine and verify Linux-container readiness.
- [x] Fix Compose health checks, remove obsolete `version`, forward explicit Firebase configuration, and provide cross-platform root startup/preflight commands.
- [x] Update `README.md` and `env.example` with Windows startup, frontend-only use, credential requirements and the limitations of development-mode story generation.
- [x] Inspect frontend npm audit; apply compatible fixes and refresh browser support data. Verify lock consistency, production build and audit; report any unrelated lint failures.
- [x] Review changes, run targeted and broad validation, create scoped local commits, and confirm the user's staged deletions are unchanged.

## Acceptance checks

1. A manifest-generated batch is accepted by the actual poller and writes its assigned chapters.
2. Multiple triggers cannot redirect a worker to another selected story; a competing lease holder does not duplicate processing.
3. A failed model/storage call leaves its trigger retryable; completed valid chapters are reused on retry.
4. Failed downstream trigger writes and orchestrator timeouts cannot acknowledge unfinished work.
5. Final output contains all expected ordered chapter texts and a completed status only after validation succeeds.
6. `docker compose config --quiet` succeeds; startup preflight explains a missing Docker engine and preserves actionable failure information.
7. Local service health endpoints respond when the engine and declared prerequisites are available. Missing Firebase or cloud-job configuration remains explicitly documented.
8. Frontend dependency audit and build are rerun after lockfile changes. Dependency changes remain compatible with the existing app.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_jobs.py tests/test_job_pipeline.py --no-cov -v
.\.venv\Scripts\python.exe -m pytest -v
docker compose config --quiet
docker compose ps
npm.cmd run build --prefix frontend
npm.cmd run lint --prefix frontend
npm.cmd audit --prefix frontend
git diff --check
git status --short
```

The full pytest run is also used to identify existing service-import isolation failures. Record limitations honestly rather than masking failures or reducing the coverage threshold.

## Results (2026-10-08)

- The focused jobs suite passed 55 tests, including a ten-chapter pipeline and failure/retry cases. Initial regressions reproduced the defects before implementation.
- The full Python suite passed 179 tests with 87.20% service coverage; the existing 70% threshold remains unchanged. Two existing dependency/fixture deprecation warnings remain. This passing run does not eliminate the previously identified service-test import-isolation debt.
- Seven startup preflight tests passed. Compose configuration, Node script syntax, Bash script syntax and whitespace checks passed.
- Started Docker Desktop's Linux engine and built/started all five local containers. PostgreSQL and the four APIs reported healthy.
- Exercised the root `npm run dev` workflow. Vite served `http://localhost:5173` with HTTP 200; ports 8001-8004 returned HTTP 200 and allowed the frontend's localhost origin. Vite now rejects an occupied port instead of silently moving to an origin the APIs disallow.
- Frontend `npm ci` succeeded and reported zero vulnerabilities, down from 24. The lockfile refresh stays within existing direct-dependency major versions. A documented Firestore-only override selects patched gRPC 1.14.5; see `frontend/DEPENDENCIES.md`.
- Frontend production build and lint passed. Six pre-existing lint errors were resolved through a small separate typing/auth-module cleanup; no lint rules were disabled. Firebase App, Auth and Firestore module imports also passed without network calls.
- Independent review checked job retry/lease behavior, startup configuration and dependency override scope. Review findings on queue starvation, known lease loss and Vite port fallback were fixed before completion.
- Implementation, startup, dependency and lint changes are separate local commits. The existing staged backend deletions were excluded. No remote changes or deployments were performed.

### Remaining configuration and verification limits

Firebase Admin credentials are required for authenticated APIs. Local book-service development mode intentionally remains a stub that returns a processing status; real generation requires Azure Blob Storage, scheduled workers and model credentials. No live Firebase sign-in or paid model call was exercised. Azure lease timing/network behavior was tested with fakes, not against a live cloud account; job execution remains at least once as documented in `jobs/README.md`.
