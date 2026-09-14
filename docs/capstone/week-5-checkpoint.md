# Week 5 Checkpoint

Date: 2026-09-07

## Completed

- Added local AI sidecar service under `services/ai-engine`:
  - FastAPI app bound for localhost development;
  - CORS access for the candidate runner;
  - `GET /health`;
  - `POST /analyze-frame`.
- Added OpenCV face analysis:
  - Haar cascade frontal-face detector;
  - frame data URL decoding;
  - configurable minimum face size;
  - model metadata returned with each response.
- Added face-event debouncing:
  - `FACE_ABSENT` after three consecutive absent samples;
  - `MULTIPLE_PERSONS` after two consecutive multiple-face samples;
  - cooldown protection to avoid repeated alert spam;
  - normal single-face samples reset abnormal counters.
- Added deterministic test/demo override:
  - `observed_face_count` allows repeatable tests and browser demos without depending on a physical webcam scenario.
- Updated candidate runner:
  - sidecar readiness check now calls `http://127.0.0.1:8765/health`;
  - low-rate camera sampler sends local frames to the sidecar while monitoring is active;
  - face monitor status tile shows sidecar state;
  - face monitor panel shows model name, sample count, and latest face count;
  - demo controls create debounced absent-face and multiple-person samples;
  - AI-derived event candidates are uploaded to the backend as normal integrity events.
- Updated proctor/examiner portal:
  - default rule editor includes `FACE_ABSENT` and `MULTIPLE_PERSONS`;
  - high-priority metric counts the multiple-person face event.
- Updated development seed rules:
  - `FACE_ABSENT`;
  - `MULTIPLE_PERSONS`;
  - existing Week 4 app-integrity rules.

## Verified

```text
Backend tests: 27 passed
AI sidecar tests: 5 passed
Web portal build: passed
Candidate frontend build: passed
Tauri cargo check: passed
```

Browser smoke test:

```text
AI sidecar health returned OpenCV model metadata
Candidate readiness marked AI sidecar as Pass
Attempt started with heartbeat sync still active
Face Absent demo produced FACE_ABSENT after three samples
Multiple People demo produced MULTIPLE_PERSONS after two samples
Candidate uploaded AI-derived events to the backend
Proctor queue showed FACE_ABSENT and MULTIPLE_PERSONS
High Priority metric counted AI-derived high-priority events
```

## Local URLs

```text
API:              http://127.0.0.1:8000
AI engine:        http://127.0.0.1:8765
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

- Raw camera frames are sent only to the local sidecar, not to the backend.
- The current detector is CPU-friendly and zero-cost, but it is a classical Haar cascade and has known accuracy limits.
- AI event confidence and priority are review hints only. They are not misconduct verdicts.
- Evidence remains log-only in Week 5. Video clip generation begins in Week 6.
- The sidecar state is in-memory for local MVP sessions.

## Next Step

Start Week 6 rolling evidence pipeline:

1. Add a bounded local rolling media buffer.
2. Capture pre/post context around selected integrity events.
3. Generate short local evidence clips.
4. Compute SHA-256 hashes and media metadata.
5. Add evidence upload and protected retrieval endpoints.
6. Render evidence metadata and playback in the proctor portal.
