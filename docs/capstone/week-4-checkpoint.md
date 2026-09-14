# Week 4 Checkpoint

Date: 2026-09-07

## Completed

- Added candidate readiness workflow:
  - explicit consent gate before attempt start;
  - backend health check;
  - camera availability check;
  - microphone availability check;
  - AI sidecar health check placeholder;
  - fullscreen state check.
- Added session heartbeat persistence:
  - `POST /attempts/{attempt_id}/heartbeats`;
  - candidate ownership check;
  - submitted attempts reject new heartbeats;
  - readiness and sync metrics stored in `session_heartbeats`.
- Added app-integrity event behavior:
  - focus-loss event capture;
  - fullscreen-exit event capture;
  - heartbeat-gap event capture;
  - submitted attempts reject new integrity events.
- Added candidate retry behavior:
  - local queue for answer saves;
  - local queue for integrity events;
  - local queue for heartbeats;
  - network-outage demo toggle;
  - retry sync control;
  - submission blocked while local operations are queued.
- Updated proctor dashboard:
  - high-priority metric now counts priority score `8+` and high/critical severities;
  - Week 4 rule defaults include focus loss, fullscreen exit, heartbeat gap, camera disabled, and microphone disabled.
- Updated seed data:
  - canonical two-question development assessment is recreated on seed;
  - old dev draft answers are cleared on seed;
  - Week 4 proctoring rules are restored on seed.
- Added backend tests for heartbeat persistence, heartbeat authorization, post-submit heartbeat rejection, and post-submit event rejection.

## Verified

```text
Backend tests: 27 passed
Web portal build: passed
Candidate frontend build: passed
Tauri cargo check: passed
```

Browser smoke test:

```text
Candidate runner loaded on http://127.0.0.1:5174
Start Attempt stayed disabled before consent and readiness checks
Consent plus Run Checks unlocked Start Attempt
Attempt started and heartbeat status changed to Synced
Network outage simulation queued answer, event, and heartbeat operations
Retry sync cleared queued operations after network restoration
Heartbeat gap event was created after delayed heartbeat recovery
Candidate submitted the assessment and saw Score 5
Proctor dashboard showed HEARTBEAT_GAP and APP_FOCUS_LOST events
High Priority metric counted the HEARTBEAT_GAP event
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

- Camera and microphone checks use browser media-device discovery in the current runner.
- The AI sidecar check points at `http://127.0.0.1:8765/health`; it reports a warning until the Week 5 sidecar exists.
- Week 4 events are still log-only; video/audio evidence clips begin in the rolling-buffer milestone.
- The retry queue is in-memory for the current candidate session. Persistent local storage can be added before longer interruption demos.
- The token helper remains a local foundation and should be reviewed or replaced before production-style deployment.

## Next Step

Start Week 5 AI sidecar and face-monitoring workflow:

1. Add a local-only Python AI sidecar service with `/health`.
2. Connect candidate readiness to the sidecar health endpoint.
3. Implement CPU-friendly camera frame analysis.
4. Detect face absence and multiple-person states.
5. Add debounce thresholds before creating AI-derived events.
6. Include model/config metadata in AI-derived event payloads.
