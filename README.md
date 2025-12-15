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
- React 18, TypeScript, Vite, TailwindCSS, React Router

**Backend**
- Python 3.11, FastAPI microservices, AsyncPG (PostgreSQL), httpx
- Optional integrations: Firebase Admin, Azure Blob Storage, Linguee API

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

## Testing
- Full suite (uses pytest.ini coverage):  
  `./venv/bin/python -m pytest -v`
- Integration-only:  
  `./venv/bin/python -m pytest tests/test_integration_services.py -v`
- DB modules only:  
  `./venv/bin/python -m pytest tests/test_database_modules.py -v`
- Jobs tests (ensure PYTHONPATH set if needed):  
  `PYTHONPATH=jobs/src ./venv/bin/python -m pytest tests/test_jobs.py -v`

Coverage target is enforced at 70%+; current suite reaches ~87% when run from the venv as above.

## Local development (quickstart)
1) Install backend deps per service and test deps:  
   `pip install -r requirements-test.txt` and each service’s `requirements.txt`
2) Run locally with Docker Compose: `docker-compose up --build`
3) Frontend dev server (from `frontend/`): `npm install && npm run dev`

## Service highlights
- **Auth Service:** Firebase token verification, DB user sync, legacy endpoints return 410 to steer clients to modern flow.
- **User Service:** Profile read/update, stats, account deletion. Depends on auth-service for token verification.
- **Translation Service:** Linguee lookup, caching, vocabulary CRUD with per-user “vocabulary book” auto-creation.
- **Book Service:** Triggers Azure Container Jobs, stores story content/covers in Blob Storage, tracks books in Postgres.
