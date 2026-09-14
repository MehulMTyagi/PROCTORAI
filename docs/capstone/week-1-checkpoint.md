# Week 1 Checkpoint

Date: 2026-09-07

## Completed

- Initialized the repository on the `main` branch.
- Created the monorepo directory structure for desktop, web, backend, AI engine, shared packages, docs, tests, and scripts.
- Added root project documentation and implementation plan.
- Added Docker Compose configuration for local PostgreSQL.
- Installed and verified Docker Desktop locally.
- Started the `proctorai-postgres` container.
- Created the FastAPI backend foundation.
- Added `/health`, `/auth/login`, and `/auth/me`.
- Added SQLAlchemy database setup.
- Added Alembic migration setup.
- Created initial database migration with foundational tables:
  - users;
  - assessments;
  - questions;
  - assessment candidates;
  - assessment proctors;
  - proctoring rules;
  - attempts;
  - answers;
  - integrity events;
  - evidence files;
  - event reviews;
  - session heartbeats;
  - audit logs.
- Added password hashing and token helpers.
- Added role guard dependency helpers.
- Added seed script for development users.
- Applied the initial migration to local PostgreSQL.
- Seeded development users.
- Added backend tests for health, auth, role checks, schema registration, and seed behavior.

## Verified

```text
Docker CLI: 29.7.2
Docker Compose: v5.5.0
PostgreSQL container: healthy
Alembic revision: 202609070001 (head)
Backend tests: 8 passed
```

Development users:

```text
candidate@example.com / password123
proctor@example.com / password123
examiner@example.com / password123
```

## Remaining Risk

- Docker may require a fresh terminal after installation so the `docker` command is available on PATH.
- The current token helper is a lightweight local implementation. Before production-style deployment, replace it with a vetted JWT/security library or add a fuller security review.
- The API has auth and schema foundations only. Assessment CRUD, event ingestion, WebSocket alerts, evidence upload, and web/desktop clients are Week 2+ work.

## Next Step

Build the Week 2 dummy event vertical slice:

1. Create a dev assessment and attempt seed path.
2. Add `POST /attempts/{id}/events`.
3. Persist a dummy potential integrity event.
4. Add proctor WebSocket connection by assessment.
5. Broadcast the dummy event to assigned proctors.
6. Scaffold the web portal event queue.
7. Scaffold the candidate desktop shell with a "Send Test Integrity Event" button.
