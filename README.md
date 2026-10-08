# Language Learning App - AI-Powered Story Platform

A full-stack language learning application that generates personalized AI stories in multiple languages, helping users learn through immersive reading experiences.

## Live Demo

**Access the application:** [https://frontend.victoriousbay-46f7c8cf.westeurope.azurecontainerapps.io/](https://frontend.victoriousbay-46f7c8cf.westeurope.azurecontainerapps.io/)

## Features

- **AI Story Generation**: Generate custom stories in 6+ languages (Spanish, French, German, Italian, Japanese, Chinese)
- **Adaptive Difficulty**: Stories tailored to your language level (A1-C1)
- **Genre Selection**: Choose from Fantasy, Sci-Fi, Adventure, Mystery, and Slice of Life
- **Interactive Reading**: Click on words for instant translations
- **Vocabulary Tracking**: Automatically saves words you look up
- **Progress Tracking**: Monitor your reading progress and favorite books
- **Beautiful UI**: Modern, responsive design with smooth animations

## Architecture

### Microservices (runtime view)
```
                      ┌───────────────────────────┐
                      │     Frontend (React/TS)   │
                      └─────────────┬─────────────┘
                                    │ REST/HTTPS
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐         ┌────────▼────────┐         ┌────────▼────────┐
│ Auth Service   │         │ User Service    │         │ Book Service    │
│ FastAPI + JWT  │         │ Profiles/Stats  │         │ Story trigger   │
└───────┬────────┘         └────────┬────────┘         └────────┬────────┘
        │                           │                           │
        │ ◄──── token verify ───────┘                           │ 
        │                           │                           │
        │                 ┌─────────▼─────────┐                 │
        │                 │ Translation Svc   │                 │
        │                 │ Linguee + Vocab   │                 │
        │                 └─────────┬─────────┘                 │
        ├───────────────────────────┼───────────────────────────┤
        │  Shared Postgres (users, user_books, vocabulary, etc.)│
        └───────────────────────────┼───────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ Azure Container Jobs (stories)│ ◄── Book Service
                    └───────────────┬───────────────┘
                                    │
                           ┌────────▼────────┐
                           │ Azure Blob      │ ◄── Book content
                           └─────────────────┘
```

### Request flows
- **Auth**: Frontend sends Firebase ID token → Auth Service verifies (Firebase Admin) → syncs/returns user from Postgres.
- **User**: Frontend calls User Service → User Service calls Auth Service `/api/auth/token/verify` → reads/updates Postgres.
- **Translation/Vocab**: Frontend calls Translation Service with Bearer token → Translation Service verifies via Auth → fetches Linguee API → caches → stores vocab in Postgres (auto-creates per-user vocab book).
- **Story generation**: Frontend calls Book Service → Book Service uploads prompt to Blob + triggers Azure Container Job → job writes story chunks to Blob (and can write to Postgres if enabled) → Book Service serves story content.

### Technology Stack
**Frontend**
- React 19, TypeScript, Vite, TailwindCSS, React Router

**Backend**
- Python 3.11, FastAPI microservices, AsyncPG (PostgreSQL), httpx
- Firebase Admin for authentication, Azure Blob Storage/jobs for generated stories, Linguee API for translations

**Cloud**
- Azure Container Apps (services + jobs)
- Azure Blob Storage (text)
- Azure Database for PostgreSQL
- Azure Container Registry

## Repository structure (high level)
```
frontend/                React app
services/
  auth-service/          FastAPI auth + Firebase integration
  user-service/          Profile, stats, user deletion
  translation-service/   Translations, vocabulary, Linguee integration
  book-service/          Story generation orchestration + Azure jobs/blob
jobs/                    Background job workers/pollers
tests/                   Unit + integration tests (see tests/README.md)
documentation/           Project docs, sprints, DoD
docker-compose.yml       Local microservice + Postgres wiring
```

## Local development on Windows

Use Node.js 22.12 or newer and Docker Desktop with its Linux engine running. Run commands from the repository root in PowerShell. The npm scripts also work on macOS/Linux with Docker Engine and the Compose plugin; use `npm` in place of `npm.cmd` there. Python is installed inside the service containers; a separate local Python installation is only needed for native development or Python tests.

Install the locked frontend dependencies:

```powershell
npm.cmd run install-all
```

Create local configuration files if they do not already exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item env.example .env }
if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
```

The root `.env` configures Compose. `frontend/.env.local` configures Vite's public API addresses. Compose does not automatically read a root `.env.local`. The local PostgreSQL username/password are development defaults from `docker-compose.yml`.

For authenticated API requests, supply a Firebase Admin service account from the same Firebase project as `frontend/src/firebase.ts`. In the terminal that will start Compose, read your downloaded service account file into the supported environment variable:

```powershell
$env:FIREBASE_SERVICE_ACCOUNT_KEY = Get-Content -Raw -LiteralPath 'C:\path\firebase-service-account.json'
```

This command does not print the key. Keep service account credentials out of frontend environment files and source control. Native Python services also accept an absolute `FIREBASE_SERVICE_ACCOUNT_PATH`; Compose uses the JSON variable above and does not mount that host path. Without Admin credentials the containers can start, but the auth API cannot verify users. Browser sign-in still depends on the configured Firebase project, enabled sign-in provider, and authorized localhost domain.

Start the services and frontend:

```powershell
npm.cmd run dev
```

This checks Docker, builds and starts PostgreSQL plus the four API services in the background, waits for their health checks, then starts Vite. Open `http://localhost:5173`. The terminal stays open while Vite runs. Press Ctrl+C to stop Vite; stop the background API/database containers separately with `npm.cmd run services:down`. That command preserves the database volume.

Vite uses port 5173 because the APIs allow that local origin. If this app is already running there, keep that frontend and run only `npm.cmd run services:up`, or stop its existing terminal with Ctrl+C before starting `npm.cmd run dev`. An occupied port now produces an explicit error instead of silently switching to a URL that the APIs reject.

Useful commands:

| Command | Purpose |
| --- | --- |
| `npm.cmd run services:check` | Check the Docker Linux engine and Compose without starting containers |
| `npm.cmd run services:up` | Build/start API services and PostgreSQL, then wait for health |
| `npm.cmd run services:logs` | Follow API/database logs |
| `npm.cmd run services:down` | Stop the API services and PostgreSQL |
| `npm.cmd run dev:frontend` | Start Vite alone for UI work |

API health endpoints are `http://localhost:8001/` through `http://localhost:8004/`; API documentation is at `/docs` on each port. If startup times out, inspect `docker compose ps` and `npm.cmd run services:logs` before retrying. Services already started remain available for inspection.

### Docker and Vite startup messages

If Docker reports `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`, the CLI cannot reach Docker Desktop's Linux engine. Start Docker Desktop, wait for the engine to report ready, ensure Linux containers are selected, then rerun `npm.cmd run services:check`. If Desktop cannot start its WSL backend, resolve the error shown by Docker Desktop/WSL first. A wrong Docker context, permissions, or a `DOCKER_HOST` override can also prevent connection; the preflight preserves Docker's original error so these remain distinguishable. `docker compose config --quiet` checks configuration syntax only and does not prove the engine is running.

Vite printing `ready` and a Local URL means the frontend development server started successfully. A `baseline-browser-mapping` message about outdated browser data is a dependency-data warning; it does not mean Docker or Vite failed to start. Keep dependency updates in the frontend lockfile and run `npm.cmd ci --prefix frontend` after pulling them. API access can still fail if services or credentials are missing.

### What local startup provides

Compose starts the database and API services. It does not provision Firebase or Azure resources, and it does not run the background workers in `jobs/`. Translation lookups require access to the external Linguee API.

`DEV_MODE=true` is the local default for book-service. It skips Azure operations and returns a story ID, but status stays `processing`; it does **not** create a completed offline story. Full story generation requires configured Azure Blob Storage, running generation workers, and their model-provider credentials. Setting `DEV_MODE=false` alone does not supply those dependencies. See [jobs/README.md](jobs/README.md) for worker configuration.

For native Python development, use Python 3.11 with a virtual environment, install each service's requirements, and provide a reachable PostgreSQL `DATABASE_URL` plus Firebase credentials. The existing `scripts/dev-fullstack.sh` launcher requires Bash and does not start PostgreSQL. The root npm workflow above uses Compose and works directly from PowerShell.

## Testing

The startup preflight tests use Node's built-in test runner and do not require Docker:

```powershell
npm.cmd run test:startup
```

After installing frontend dependencies, run `npm.cmd --prefix frontend run build` and `npm.cmd --prefix frontend run lint`.

For Python tests, activate a Python 3.11 virtual environment and install `requirements-test.txt`, all four service requirements, and `jobs/requirements.txt`. See [tests/README.md](tests/README.md) for service-specific commands and the existing import-isolation limitation. Use `python -m pytest` so the test runner uses that environment. `pytest.ini` enforces a 70% coverage threshold for its configured scope; inspect the actual report from your run rather than assuming a historical percentage. Python dependencies are separate from `npm run install-all`.

## Service highlights
- **Auth Service:** Firebase token verification, DB user sync, legacy endpoints return 410 to steer clients to modern flow.
- **User Service:** Profile read/update, stats, account deletion. Depends on auth-service for token verification.
- **Translation Service:** Linguee lookup, caching, vocabulary CRUD with per-user “vocabulary book” auto-creation.
- **Book Service:** Triggers Azure Container Jobs, stores story content/covers in Blob Storage, tracks books in Postgres.
