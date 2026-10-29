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
- `POST /auth/activation/request` (only for pre-provisioned student accounts)
- `POST /auth/activation/complete`
- `GET /auth/me`
- `GET /dev/bootstrap`
- `GET /users`
- `GET /users/teaching-groups`
- `POST /users/teaching-groups` (admin-only)
- `DELETE /users/teaching-groups/{assignment_id}` (admin-only)
- `POST /users/import-roster` (admin-only CSV import)
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

After running migrations, seed local development users (this command refuses to run when `APP_ENV=production`):

```powershell
python -m app.db.seed
```

All seeded users use the development password `password123`.

- `candidate@example.com`
- `proctor@example.com`
- `examiner@example.com`
- `admin@example.com`

All seeded users use the local-only development password `password123`; never seed or reuse these accounts in a deployed environment. The web portal requires credentials and verifies the account role. It no longer embeds demo passwords or calls the development bootstrap endpoint.

The current local slice supports examiner assessment setup, candidate exam taking, objective scoring, readiness/session heartbeat persistence, app-integrity event ingestion, AI-derived face events from the local sidecar, retry-friendly candidate workflows, and proctor WebSocket alerts.

## Admin-provisioned student accounts

Students cannot register themselves. An admin imports a UTF-8 CSV containing `roll_number,full_name,program,admission_year,section`; the API derives email as `<lowercase-roll-number>@<STUDENT_EMAIL_DOMAIN>`. Imports can contain up to 20,000 rows and 5 MB. Re-importing the same roster updates names and cohort fields without creating duplicate accounts. New accounts remain inactive and have no usable password until the student requests an activation code at their university mailbox and sets a password. First sign-in then takes the student through the existing one-time face enrollment. The activation request only works for a roster account and returns a generic response to avoid confirming account existence. In development without SMTP settings, a development-only code is returned; production requires configured SMTP.

Example CSV:

```csv
roll_number,full_name,program,admission_year,section
S24BCAU0044,Student Name,BCA,2024,A
```

Upload it to `POST /users/import-roster` as multipart field `file` with an admin bearer token. `/users` supports `program`, `admission_year`, and `section` query filters. An administrator assigns each examiner to one or more program/year/section groups through `/users/teaching-groups`; examiners only see and assign candidates from their groups. Review [production security and deployment](../../docs/production-security.md) before hosting any real student data.
