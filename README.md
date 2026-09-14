# ProctorAI
f
ProctorAI is a BCA Semester V capstone project for an AI-native multimodal proctoring and assessment-integrity monitoring system for remote assessments and interviews.

The system is designed around a privacy-aware workflow: the candidate app performs AI monitoring primarily on the candidate's Windows laptop, keeps normal camera/audio data in a bounded rolling buffer, and uploads only short evidence clips or logs when a potential integrity event is detected. A human proctor reviews each event. The system does not make automatic misconduct decisions.

## Scope

Core clients:

- Candidate Windows desktop application.
- Proctor web portal.
- Examiner web portal.

Core backend:

- FastAPI REST and WebSocket API.
- PostgreSQL database.
- Local filesystem evidence storage for MVP.
- Python AI sidecar for local computer vision/audio inference.

Out of scope for MVP:

- mobile application;
- live webcam streaming to proctors;
- continuous cloud webcam recording;
- paid AI APIs;
- paid cloud GPUs;
- system-wide keylogging;
- automatic cheating verdicts;
- deepfake detection as a required feature.

## Repository Layout

```text
PROCTORAI/
  apps/
    candidate-desktop/       # Tauri + React candidate app
    web-portal/              # React proctor + examiner portal
  services/
    api/                     # FastAPI backend
    ai-engine/               # Python local AI sidecar
  packages/
    shared-types/            # shared event/API types
    ui/                      # optional shared UI components
    rules/                   # shared event/risk rule definitions
  models/                    # model manifests only; large model files stay out of Git
  docs/
    architecture/
    api/
    testing/
    ethics-privacy/
    capstone/
  tests/
  scripts/
  ProctorAI_Codex_Context.md
  ProctorAI_Capstone_Master_Spec.md
  PROJECT_COMPLETION_PLAN.md
```

## Planned Stack

- Candidate desktop: Tauri 2, React, TypeScript, local Python sidecar.
- Web portal: React, TypeScript, Vite.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- Database: PostgreSQL.
- AI/CV: OpenCV, MediaPipe or equivalent landmarks, ONNX Runtime where useful.
- Evidence: OpenCV/FFmpeg clip generation, SHA-256 hashes, protected backend storage.

## First Vertical Slice

Before adding AI models, the first implementation goal is a dummy event path:

1. FastAPI `/health`.
2. PostgreSQL connection and migrations.
3. Seed users for candidate, proctor, and examiner.
4. Candidate desktop button: "Send Test Integrity Event".
5. Backend persists the event.
6. WebSocket pushes the event to the proctor portal.
7. Proctor event queue renders it.
8. Tests verify event ingestion and role permissions.

This proves the Candidate app -> API -> database -> WebSocket -> Proctor portal path before the project takes on AI complexity.

## Development Principles

- Use UUID identifiers.
- Store UTC timestamps in the database.
- Keep event types and rule configuration centralized.
- Treat AI risk score only as review priority.
- Store proctor review separately from AI event data.
- Enforce authorization server-side for every role and assignment.
- Never store plaintext passwords.
- Keep secrets in environment variables.
- Keep normal media local and temporary unless an event requires evidence.

## Key Documents

- `ProctorAI_Codex_Context.md`: current handoff/source-of-truth summary for implementation.
- `ProctorAI_Capstone_Master_Spec.md`: full academic and technical master specification.
- `PROJECT_COMPLETION_PLAN.md`: milestone plan for completing the MVP.

## Current Status

Task 1 is complete: the monorepo structure and root README have been created.

Task 2 is complete: Docker Compose PostgreSQL configuration, the FastAPI API foundation, `/health`, SQLAlchemy setup, Alembic setup, and minimal core database models have been created.

Week 1 is complete: monorepo skeleton, FastAPI/PostgreSQL foundation, auth/RBAC helpers, development seed users, initial migration, and foundational backend tests are in place.

Week 1 verification:

- Docker Desktop installed and running.
- PostgreSQL container `proctorai-postgres` is healthy.
- Alembic database revision is `202609070001 (head)`.
- Development users are seeded.
- Backend test suite passes with `8 passed`.

Week 2 is complete: dummy integrity-event ingestion, proctor WebSocket alerts, proctor event queue, candidate test-event shell, development bootstrap data, and Tauri candidate scaffold are in place.

Week 2 verification:

- Backend test suite passes with `16 passed`.
- Web portal production build passes.
- Candidate frontend production build passes.
- Candidate Tauri scaffold passes `cargo check`.
- Browser smoke test confirms the candidate button updates the proctor queue without page refresh.

Local development URLs:

- API: `http://127.0.0.1:8000`
- Proctor portal: `http://127.0.0.1:5173`
- Candidate shell: `http://127.0.0.1:5174`

Week 3 is complete: examiner assessment setup, question management, candidate/proctor assignments, rule editing, candidate assessment runner, attempt start/save/submit, and basic objective scoring are in place.

Week 3 verification:

- Backend test suite passes with `23 passed`.
- Web portal production build passes.
- Candidate frontend production build passes.
- Candidate Tauri scaffold passes `cargo check`.
- Browser smoke test confirms the candidate can start an assigned assessment, save answers, submit, see the objective score, and still emit an integrity event visible in the proctor queue.

Week 4 is complete: candidate consent, readiness checks, session heartbeats, app-focus/fullscreen/heartbeat-gap integrity events, local retry queue behavior, and proctor high-priority event visibility are in place.

Week 4 verification:

- Backend test suite passes with `27 passed`.
- Web portal production build passes.
- Candidate frontend production build passes.
- Candidate Tauri scaffold passes `cargo check`.
- Browser smoke test confirms preflight gating, heartbeat sync, offline answer/event queueing, retry sync recovery, submission, and proctor visibility for high-priority events.

Week 5 is complete: the local AI sidecar, OpenCV face counting, debounced `FACE_ABSENT` and `MULTIPLE_PERSONS` event candidates, candidate sidecar readiness, low-rate frame sampling, deterministic face-event demos, live camera/microphone integrity events, and proctor visibility for AI-derived events are in place.

Week 5 verification:

- Backend test suite passes with `27 passed`.
- AI sidecar test suite passes with `5 passed`.
- Web portal production build passes.
- Candidate frontend production build passes.
- Candidate Tauri scaffold passes `cargo check`.
- Browser smoke test confirms sidecar readiness, candidate face-event demos, backend event persistence, and proctor queue visibility for `FACE_ABSENT` and `MULTIPLE_PERSONS`.
- Focused regression confirms proof-backed `CAMERA_DISABLED`, `MICROPHONE_DISABLED`, `BACKGROUND_SPEECH`, `PHONE_DETECTED`, and `AI_ENGINE_INTERRUPTED` event paths are supported by the same live candidate-to-proctor event flow.

Local AI sidecar URL:

- AI engine: `http://127.0.0.1:8765`

## Candidate Setup Pages

The candidate portal now uses a multi-page setup flow before an assessment can start:

1. Assessment: choose an assigned assessment.
2. Consent: accept the monitoring and privacy notice.
3. System: verify the backend API and local AI sidecar are reachable.
4. Camera: grant camera permission and confirm a live local preview.
5. Microphone: grant microphone permission and confirm a live input.
6. Review: confirm all requirements, enter fullscreen, and start the assessment.
7. Exam: answer questions while heartbeats, focus/fullscreen events, retry sync, and local face monitoring run.
8. Submission: view submitted answers and the objective score receipt.

Setup pages use hash routes under the candidate runner, for example `http://127.0.0.1:5174/#/assessments`. Direct navigation cannot skip incomplete requirements, and active attempts are kept on the exam route so answers are not discarded by changing the URL.

The requirement checks are candidate-side readiness gates. The backend still remains the source of truth for authentication, assignments, attempts, answers, and submitted scores.

## Proctor Evidence Review

Candidate integrity signals are sent to the proctor queue automatically during an active attempt. Current automatic signals include fullscreen exits, focus loss, heartbeat gaps, face absence, multiple-person detections, camera disabled/device-loss events, microphone disabled/device-loss events, sustained background audio/noise signals, and AI sidecar interruption events.

Each new event includes review proof in the event metadata and is marked `READY` when proof is attached. Camera-based signals include a local snapshot, hash, timestamp, model/sample details, and session state. Browser/session signals include fullscreen and visibility context, and use the current camera sampler frame when one is available. The proctor dashboard renders this proof beside each event for human review.

`PHONE_DETECTED` is wired through the live integrity-event and proof path with a candidate-side demo control. Automatic phone/object recognition remains a model-integration task; the current browser microphone background-voice/noise detection is an audio-level heuristic, not speech transcription or speaker identification.

This proof path is intended for the live MVP demo. The next production hardening step is the Week 6 evidence-file pipeline with protected media storage, short clip generation, playback controls, retention, and cleanup.

## Public Demo Deployment

Current Vercel demo URLs:

- Examiner/proctor portal: `https://web-portal-six-kappa.vercel.app`
- Candidate portal: `https://candidate-desktop.vercel.app`

These deployments are currently wired to temporary LocalTunnel URLs for the local ProctorAI API and AI sidecar:

- API tunnel: `https://wicked-duck-66.loca.lt`
- AI sidecar tunnel: `https://tricky-moose-59.loca.lt`

The public demo works across devices while the local API, AI sidecar, and tunnel sessions remain running on this development machine. For a permanent deployment, replace the tunnel setup with a hosted backend and cloud PostgreSQL database, then redeploy both portals with `VITE_API_BASE_URL` and `VITE_AI_ENGINE_URL` pointing to durable HTTPS services.

Next task: build the Week 6 rolling evidence pipeline with bounded local media buffering, clip generation, hashing, upload metadata, protected playback, and cleanup behavior.
