# Week 2 Checkpoint

Date: 2026-09-07

## Completed

- Added dummy integrity-event ingestion:
  - `POST /attempts/{attempt_id}/events`
  - candidate ownership check;
  - event persistence;
  - `UNREVIEWED` event status;
  - log-only dummy event support.
- Added proctor event listing:
  - `GET /proctor/assessments/{assessment_id}/events`
  - proctor assignment check;
  - candidate access blocked.
- Added proctor realtime alerts:
  - `WS /ws/proctor/assessments/{assessment_id}`
  - token-based WebSocket authorization;
  - assignment checks for proctors;
  - broadcast on event creation.
- Added `/dev/bootstrap` so local apps can discover seeded development assessment/attempt IDs.
- Extended seed data:
  - one active development assessment;
  - one candidate assignment;
  - one proctor assignment;
  - one in-progress candidate attempt;
  - baseline proctoring rule config.
- Added backend tests for dummy event ingestion, proctor listing, authorization, and dev bootstrap.
- Created React web portal scaffold:
  - proctor login using dev account;
  - event queue dashboard;
  - WebSocket live status;
  - realtime event list updates.
- Created candidate frontend shell:
  - candidate login using dev account;
  - dev assessment display;
  - monitoring status tiles;
  - "Send Test Integrity Event" button;
  - last-event status.
- Added Tauri 2 scaffold for the candidate app:
  - `src-tauri/Cargo.toml`;
  - `tauri.conf.json`;
  - Rust entrypoints;
  - Windows icon asset.
- Installed and verified Rust/Cargo.

## Verified

```text
Backend tests: 16 passed
Web portal build: passed
Candidate frontend build: passed
Tauri cargo check: passed
PostgreSQL container: healthy
```

Live smoke test:

```text
Candidate login -> dev bootstrap -> POST dummy event -> DB persistence -> proctor event list
```

Realtime smoke test:

```text
Proctor WebSocket connected -> candidate POSTed dummy event -> WebSocket received APP_FOCUS_LOST
```

Browser smoke test:

```text
Proctor portal loaded on http://127.0.0.1:5173
Candidate shell loaded on http://127.0.0.1:5174
Candidate button click increased the proctor event queue without page refresh
```

## Local URLs

```text
API:             http://127.0.0.1:8000
Proctor portal:  http://127.0.0.1:5173
Candidate shell: http://127.0.0.1:5174
```

## Development Users

```text
candidate@example.com / password123
proctor@example.com / password123
examiner@example.com / password123
```

## Notes

- The candidate app has a real Tauri scaffold and passes `cargo check`.
- Current candidate camera/system-check UI is still placeholder-only.
- Dummy events are intentionally log-only. Evidence clips begin in the rolling-buffer milestone.
- The token helper is still a local foundation and should be reviewed/replaced before any production-style deployment.

## Next Step

Start Week 3 assessment workflow:

1. Examiner assessment list.
2. Create/edit assessment.
3. Add MCQ/short-answer questions.
4. Assign candidates and proctors.
5. Candidate assessment list.
6. Attempt start, answer save, and submit.
7. Basic objective scoring.
