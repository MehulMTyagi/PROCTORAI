# Week 6 Checkpoint

Date: 2026-09-20

## Completed

- Added protected evidence upload to the API:
  - `POST /attempts/{attempt_id}/events/{event_id}/evidence`;
  - multipart media upload;
  - candidate/attempt ownership checks;
  - max upload size enforcement using `max_evidence_mb`;
  - server-side SHA-256 verification;
  - local filesystem storage under `evidence_dir`.
- Added evidence failure handling:
  - `POST /attempts/{attempt_id}/events/{event_id}/evidence/failure`;
  - failed evidence status is persisted and visible to proctors.
- Added protected evidence playback route:
  - `GET /proctor/events/{event_id}/evidence/{evidence_id}`;
  - candidate, assigned proctor, owning examiner, and admin authorization checks.
- Extended event responses with `evidence_files` metadata:
  - evidence ID;
  - event ID;
  - attempt ID;
  - kind;
  - MIME type;
  - size;
  - duration;
  - captured start/end timestamps;
  - retention timestamp;
  - SHA-256 hash;
  - protected download URL.
- Added candidate-side rolling evidence capture:
  - bounded `MediaRecorder` buffer from the local camera stream;
  - default 5-second pre-roll and 5-second post-roll;
  - local WebM clip creation;
  - browser-side SHA-256 hashing before upload;
  - evidence status transitions from `PENDING` to `READY` or `FAILED`.
- Added proctor evidence playback:
  - protected fetch with bearer token;
  - in-page video playback;
  - clip metadata and hash preview.

## Verified

```text
Full backend tests: 35 passed
Backend event/evidence tests: 12 passed
AI sidecar tests: 7 passed
Candidate frontend build: passed
Web portal build: passed
Tauri cargo check: passed
Local API/AI/web/candidate health checks: passed
```

Additional backend coverage:

```text
Candidate can upload a hashed evidence clip
Hash mismatch rejects upload and stores no evidence
Proctor can download assigned event evidence
Candidate can mark evidence upload failed
Unauthorized event/evidence access remains blocked by role and assignment checks
Live local smoke created a FACE_ABSENT event, uploaded hashed evidence, and downloaded it as proctor
```

## Local URLs

```text
API:              http://127.0.0.1:8010
AI engine:        http://127.0.0.1:8765
Web portal:       http://127.0.0.1:5173
Candidate runner: http://127.0.0.1:5174
```

## Notes

- Normal rolling media chunks stay in the browser and are discarded unless an integrity event requires evidence.
- Uploaded evidence is local filesystem storage for the MVP, not cloud object storage.
- Protected playback uses API authorization rather than public media URLs.
- Clip generation depends on browser `MediaRecorder` support.
- Week 6 evidence is functional for local/demo use; production hardening should add durable object storage, retention jobs, encryption-at-rest configuration, and larger E2E browser coverage.

## Next Step

Start Week 7 phone detection and liveness hardening:

1. Tune phone detection persistence and duplicate-event merging.
2. Add active liveness challenge prompts.
3. Record `LIVENESS_FAILED` events with proof metadata.
4. Add scenario-based validation for normal user, phone, face absence, multiple persons, and liveness failure.
