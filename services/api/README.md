# ProctorAI API

FastAPI backend for authentication, assessments, attempts, integrity events, evidence metadata, proctor review, and reporting.

## Local Setup

From the repository root:

```powershell
docker compose up -d postgres
```

From `services/api`:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## Current API Surface

- `GET /health`
- `POST /auth/login`
- `GET /auth/me`
- `GET /dev/bootstrap`
- `GET /users`
- `POST /assessments`
- `GET /assessments`
- `GET /assessments/{assessment_id}`
- `PUT /assessments/{assessment_id}`
- `POST /assessments/{assessment_id}/questions`
- `POST /assessments/{assessment_id}/candidates`
- `POST /assessments/{assessment_id}/proctors`
- `PUT /assessments/{assessment_id}/rules`
- `POST /attempts/start`
- `GET /attempts/{attempt_id}`
- `POST /attempts/{attempt_id}/answers`
- `POST /attempts/{attempt_id}/heartbeats`
- `POST /attempts/{attempt_id}/submit`
- `POST /attempts/{attempt_id}/events`
- `GET /proctor/assessments/{assessment_id}/events`
- `WS /ws/proctor/assessments/{assessment_id}`

The initial schema includes users, assessments, questions, candidate/proctor assignments, proctoring rules, attempts, answers, integrity events, evidence metadata, proctor reviews, session heartbeats, and audit logs.

## Development Users

After running migrations, seed local development users:

```powershell
python -m app.db.seed
```

All seeded users use the development password `password123`.

- `candidate@example.com`
- `proctor@example.com`
- `examiner@example.com`

The current local slice supports examiner assessment setup, candidate exam taking, objective scoring, readiness/session heartbeat persistence, app-integrity event ingestion, AI-derived face events from the local sidecar, retry-friendly candidate workflows, and proctor WebSocket alerts.
