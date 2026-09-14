# Week 3 Checkpoint

Date: 2026-09-07

## Completed

- Added examiner assessment workflow:
  - `POST /assessments`;
  - `GET /assessments`;
  - `GET /assessments/{assessment_id}`;
  - `PUT /assessments/{assessment_id}`;
  - role-aware assessment visibility.
- Added question management:
  - `POST /assessments/{assessment_id}/questions`;
  - MCQ and short-answer schema support;
  - candidate-facing question responses hide correct answers.
- Added candidate and proctor assignment APIs:
  - `GET /users?role=...`;
  - `POST /assessments/{assessment_id}/candidates`;
  - `POST /assessments/{assessment_id}/proctors`.
- Added proctoring-rule editing:
  - `PUT /assessments/{assessment_id}/rules`;
  - JSON rule configuration preserved in the database.
- Added attempt workflow:
  - `POST /attempts/start`;
  - `GET /attempts/{attempt_id}`;
  - `POST /attempts/{attempt_id}/answers`;
  - `POST /attempts/{attempt_id}/submit`;
  - objective MCQ scoring on submission.
- Extended seed data with a two-question active assessment.
- Rebuilt the web portal as a role-aware examiner/proctor workspace.
- Rebuilt the candidate frontend as an assessment runner with assigned assessments, answer save, submit, score display, and retained dummy event trigger.
- Added backend tests for assessment authorization, assignment behavior, answer save, and submission scoring.

## Verified

```text
Backend tests: 23 passed
Web portal build: passed
Candidate frontend build: passed
Tauri cargo check: passed
```

Browser smoke test:

```text
Examiner portal loaded on http://127.0.0.1:5173
Candidate runner loaded on http://127.0.0.1:5174
Candidate started/resumed the seeded assessment
Candidate saved MCQ and short-answer responses
Candidate submitted and saw Score 5
Candidate emitted APP_FOCUS_LOST after submission
Proctor dashboard showed the event queue with the latest event
```

## Local URLs

```text
API:              http://127.0.0.1:8000
Web portal:       http://127.0.0.1:5173
Candidate runner: http://127.0.0.1:5174
```

## Development Users

```text
candidate@example.com / password123
proctor@example.com / password123
examiner@example.com / password123
```

## Notes

- MCQ answers are scored automatically when `selected_option` matches the stored correct answer.
- Short answers are stored but not auto-scored yet.
- Evidence is still log-only for dummy events. Clip creation starts in the rolling-buffer milestone.
- The candidate readiness checks are still placeholders and move into Week 4.
- The token helper remains a local foundation and should be reviewed or replaced before production-style deployment.

## Next Step

Start Week 4 candidate readiness and app-integrity workflow:

1. Add consent before monitoring.
2. Add camera, microphone, backend, and sidecar checks.
3. Add session heartbeat indicators.
4. Emit app-focus-lost and fullscreen-exit events from the candidate app.
5. Add local retry queue behavior for answers and events during temporary network failures.
6. Extend tests around readiness, retry, and authorization boundaries.
