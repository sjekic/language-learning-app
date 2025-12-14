Definition of Done (DoD)

1. Code

Compiles and builds locally; lints pass; typed where applicable; no TODOs left in touched files. I follow the existing style and don't leave dead/debug code. New deps are justified and added to the right config.

2. Tests

Unit and integration added or updated; venv/bin/python \-m pytest \-v passes (or \--cov-fail-under=0 if gate temporarily waived); frontend tests run if UI changed; coverage stays ≥ configured threshold or justified note. We document any skipped tests and why. Integration tests should cover the real flows we touched.

3. Security and Secrets

We don't have any hardcoded secrets; .env values mocked in tests; auth headers validated where required. If we add tokens/keys, they live in env files and are explained in README. Sensitive logs are avoided.

4. API/Contracts

Endpoints are validated with FastAPI schemas; request/response examples updated if changed; backward compatibility considered. If I break a contract, I call it out and provide migration guidance. Error responses use consistent status codes and messages.

5. Data

Migrations and schema changes captured; seed/dev data updated if needed; no breaking DB ops without rollback plan. We check for nullability/index changes and document any data backfill steps. Local/dev DB still starts cleanly.

6. CI/Automation

Pipeline scripts updated if build/test commands changed; Docker/dev scripts still run (docker-compose up works). Any new script has a one-liner on how to run it. CI variables/env expectations are noted.

7. UX/UI

Responsive check for affected pages; key flows manually smoke-tested in browser; accessibility basics (labels/ARIA) kept. We verify the UI in at least desktop \+ mobile breakpoints. Animations or visual changes don't block usability.

8. Documentation

README/testing instructions reflect new commands or services; API docs (FastAPI docs/README snippets) updated when endpoints change. If we add flags/env vars, we list them. Screenshots/GIFs are updated when the UI meaningfully changes.

9. Deployment

All env vars/config documented; feature works in DEV\_MODE and notes for cloud/Azure paths if relevant. If the feature needs cloud resources, we state the prerequisites. Startup scripts still succeed without hidden steps.

10. Review

MR/PR includes summary, test commands run, and known limitations; no open critical bugs on the story. We note any follow-up tickets. The branch is ready to merge to main without surprise breakage.