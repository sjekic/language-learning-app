**Sprint 1**

Roles: PO: Sofiia; SM: Oliver; Devs: Michail, Vako, Simonida, Denis  
Backlog snapshot: define architecture (frontend \+ 4 FastAPI services \+ jobs), draft initial README and env vars, Docker Compose skeleton, stub story generation (DEV\_MODE), set up repo structure.  
Review outcomes: architecture diagram and Compose up; FastAPI stubs reachable; frontend boots with placeholder pages. Stakeholders accepted scope; asked for clearer test/deploy instructions next sprint.  
Retro outcomes/agreements: keep env/config in README early; pair on infra tasks; ensure each service has a health endpoint.

**Sprint 2**

Roles: PO: Oliver; SM: Michail; Devs: Sofiia, Vako, Simonida, Denis  
Backlog snapshot: Auth service (Firebase/JWT), User service (profile/stats), DB schema init, basic pytest for auth/user, CI skeleton.  
Review outcomes: Auth/User endpoints working locally; DB schema applied; basic unit tests running.   
Feedback: add more integration coverage, document JWT expectations.  
Retro outcomes/agreements: add env mocking in tests; run pytest locally before PR; keep JWT flow in docs.

**Sprint 3**

Roles: PO: Michail; SM: Vako; Devs: Sofiia, Oliver, Simonida, Denis  
Backlog snapshot: Book service generate/status endpoints (DEV\_MODE), blob helper placeholders, Azure jobs stubs, wiring with Auth, more pytest coverage.  
Review outcomes: Book generate/status reachable, DEV\_MODE flow returns story\_id; job stubs in place; coverage still low.   
Feedback: align tests with DEV\_MODE behavior, add integration tests for story flow.  
Retro outcomes/agreements: standardize service imports in tests; avoid hard-coded secrets; document DEV\_MODE vs Azure mode.

**Sprint 4**

Roles: PO: Vako; SM: Simonida; Devs: Sofiia, Oliver, Michail, Denis  
Backlog snapshot: Translation endpoints with Linguee proxy, vocabulary CRUD/stats, caching, tests for translation helper and endpoints, README API notes.  
Review outcomes: Translation/vocabulary endpoints OK; caching works; docs mention translation params.   
Feedback: fix import collisions in tests, add integration coverage across services.  
Retro outcomes/agreements: use importlib loading per service in tests; set default envs in conftest; keep cache clearing in fixtures.

**Sprint 5**

Roles: PO: Simonida; SM: Denis; Devs: Sofiia, Oliver, Michail, Vako  
Backlog snapshot: Integration suite (book DEV\_MODE flow, translation caching, user profile), stabilize pytest imports, add README testing commands, raise coverage.  
Review outcomes: Integration tests passing; README has pytest commands (full suite and no-gate option); coverage improved.   
Feedback: some unit tests still failing due to env/asyncpg mocks-carry into the next sprint.  
Retro outcomes/agreements: stub asyncpg globally; patch service mains explicitly; relax tests to match DEV\_MODE responses.

**Sprint 6**

Roles: PO: Denis; SM: Sofiia; Devs: Oliver, Michail, Vako, Simonida  
Backlog snapshot: Fix remaining test failures, align blob/job tests with current code, ensure auth/user/book verify\_token paths import correctly, reach passing suite.  
Review outcomes: 136/136 tests passing with coverage \~88%; import collisions resolved; blob/job tests aligned; auth verify-token test mocked user creation.   
Feedback: capture DoD and Scrum artifacts for submission (this doc).  
Retro outcomes/agreements: keep venv/bin/python \-m pytest \-v as pre-merge check; update docs when commands change; maintain DEV\_MODE notes; continue rotating roles next sprint.