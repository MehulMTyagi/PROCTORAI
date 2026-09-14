# ProctorAI Project Completion Plan

This plan is based on `ProctorAI_Codex_Context.md` and `ProctorAI_Capstone_Master_Spec.md`. The current repository contains the specification documents only, so implementation should begin with a narrow vertical slice and grow toward the Milestone 2 MVP.

## Scope Lock

Build ProctorAI as:

- a Windows candidate desktop app;
- a React web portal for proctor and examiner roles;
- a FastAPI/PostgreSQL backend;
- a local Python AI sidecar for candidate-device inference;
- an event-driven evidence system using short retained clips, not live streaming or continuous cloud recording.

Do not include mobile apps, paid AI APIs, paid cloud GPUs, system-wide keylogging, live webcam streaming, automatic cheating verdicts, or deepfake detection as an MVP dependency.

## Target MVP

The capstone MVP is complete when it can demonstrate:

- examiner creates an assessment, questions, candidates, proctors, and rules;
- candidate logs into the desktop app, consents, passes system check/liveness, takes the assessment, and submits;
- local monitoring creates potential integrity events for core cases;
- visual events can produce short evidence clips with pre/post context;
- backend persists attempts, answers, events, evidence metadata, reviews, and audit records;
- proctor receives event alerts, reviews evidence, and marks each event confirmed suspicious, false positive, or inconclusive;
- examiner sees scores and the reviewed integrity report;
- authorization tests prove users cannot access another role's data;
- performance, detection, storage, and review metrics are documented.

## Recommended Milestone Order

### Milestone 0: Repository Foundation

Deliverables:

- monorepo folders:
  - `apps/candidate-desktop`
  - `apps/web-portal`
  - `services/api`
  - `services/ai-engine`
  - `packages/shared-types`
  - `packages/rules`
  - `docs`
  - `tests`
  - `scripts`
- root `README.md`;
- `.env.example`;
- `docker-compose.yml` for PostgreSQL;
- `LICENSES.md`.

Exit criteria:

- repo has a runnable skeleton;
- setup instructions are clear enough for a teammate to start from a clean machine.

### Milestone 1: Backend and Database Core

Deliverables:

- FastAPI app with `/health`;
- SQLAlchemy database setup;
- Alembic migrations;
- UUID-based core tables:
  - users;
  - assessments;
  - questions;
  - assessment_candidates;
  - assessment_proctors;
  - proctoring_rules;
  - attempts;
  - answers;
  - integrity_events;
  - evidence_files;
  - event_reviews;
  - audit_logs;
- dev seed users for candidate, proctor, and examiner;
- password hashing;
- JWT auth;
- role and assignment checks.

Exit criteria:

- API starts locally on port `8000`;
- PostgreSQL starts locally;
- tests cover health, login, role permissions, and basic database persistence.

### Milestone 2: Dummy Realtime Event Vertical Slice

Deliverables:

- web portal with temporary login or dev role selector;
- proctor event queue page;
- candidate desktop shell with login placeholder and "Send Test Integrity Event" button;
- event ingestion endpoint;
- WebSocket endpoint for proctor assessment alerts;
- dummy event persisted to PostgreSQL and pushed to proctor UI.

Exit criteria:

- clicking the candidate dummy-event button creates one database event;
- assigned proctor sees it without page refresh;
- unauthorized role access returns `403`.

This milestone must be completed before integrating computer vision.

### Milestone 3: Assessment Workflow

Deliverables:

- examiner assessment list and create/edit screen;
- MCQ and short-answer question editor;
- candidate/proctor assignment;
- proctoring-rule configuration;
- candidate dashboard for assigned assessments;
- attempt start, answer save/autosave, submit;
- basic scoring for objective questions.

Exit criteria:

- E2E normal exam works:
  - examiner creates assessment;
  - candidate takes it;
  - candidate submits;
  - examiner sees score;
  - no unnecessary evidence is generated.

### Milestone 4: Candidate System Check and App Integrity Events

Deliverables:

- consent screen before monitoring;
- camera/mic availability check;
- AI sidecar heartbeat check;
- candidate assessment status indicators;
- app focus lost event;
- fullscreen exit event if rule requires fullscreen;
- camera disabled, microphone disabled, AI heartbeat gap events;
- local retry queue for temporary network failure.

Exit criteria:

- log-only events reach backend/proctor without video evidence;
- network outage queues events/answers and retries when backend returns.

### Milestone 5: AI Sidecar and Face Monitoring

Deliverables:

- local Python AI sidecar bound to local-only communication;
- OpenCV camera frame path from candidate app to sidecar;
- face presence/count detector;
- event debouncer/state machine;
- FACE_ABSENT event;
- MULTIPLE_PERSONS event;
- model/version/config metadata on AI-derived events.

Exit criteria:

- one bad frame does not create an event;
- persistence thresholds create stable events;
- proctor sees face-absence and multiple-person alerts.

### Milestone 6: Rolling Evidence Pipeline

Deliverables:

- bounded local rolling media buffer;
- default 5-second pre-roll and 5-second post-roll;
- adaptive max duration for long events;
- local clip generation;
- SHA-256 hashing;
- evidence upload endpoint;
- protected evidence download/playback;
- local cleanup of normal temporary footage;
- evidence failure states.

Exit criteria:

- manual trigger can produce a roughly 10-second clip;
- proctor can play uploaded evidence;
- evidence metadata includes event ID, attempt ID, timestamps, hash, MIME type, size, and duration;
- normal footage is not uploaded.

### Milestone 7: Phone Detection and Liveness

Deliverables:

- compact CPU-friendly object detector via ONNX Runtime or another zero-cost local option;
- PHONE_DETECTED event with confidence and persistence rules;
- active liveness challenge:
  - blink;
  - turn left/right;
  - randomized challenge order;
- LIVENESS_FAILED event;
- basic head-pose/gaze anomaly only if stable enough.

Exit criteria:

- phone scenario produces one merged event, not repeated spam;
- liveness passes for a cooperative live user;
- static image/replay fails basic challenge-response behavior.

### Milestone 8: Proctor Review and Examiner Reporting

Deliverables:

- proctor event filters by assessment, candidate, type, status, and priority;
- event details page;
- media player for video/audio evidence;
- log-only event rendering;
- review decisions:
  - confirmed suspicious;
  - false positive;
  - inconclusive;
- proctor notes;
- audit logging for review changes;
- examiner results page;
- candidate integrity report;
- printable/exportable report view if time permits.

Exit criteria:

- proctor review is stored separately from immutable AI event data;
- examiner report updates after review;
- UI wording avoids "cheater detected" or AI-verdict language.

### Milestone 9: Testing, Metrics, and Demo Hardening

Deliverables:

- unit tests for backend services, rules, risk scoring, and event debouncing;
- integration tests for auth, attempts, events, evidence, and reviews;
- E2E tests for the eight required scenarios:
  - normal exam;
  - phone event;
  - multiple persons;
  - face absence;
  - focus loss;
  - liveness;
  - network interruption;
  - authorization;
- AI validation scenario CSV;
- benchmark scripts for inference latency, CPU, RAM, evidence size, encode duration, upload duration, and alert latency;
- screenshots and final demo script;
- architecture diagrams, ER diagram, sequence diagrams, risk matrix, and privacy data-flow diagram.

Exit criteria:

- final report can include measured results and limitations;
- demo can run locally without paid services;
- known false positives/false negatives are documented honestly.

## Suggested Build Order by Week

### Week 1

- Create monorepo skeleton.
- Build FastAPI/PostgreSQL foundation.
- Add auth, seed users, and minimal database migrations.
- Include evidence metadata, event review, heartbeat, and audit-log tables in the initial backend foundation.

### Week 2

- Build web portal shell.
- Build candidate desktop shell.
- Complete dummy event API and WebSocket vertical slice.
- Add development bootstrap data and verify candidate button -> API -> database -> WebSocket -> proctor queue.

### Week 3

- Implement assessment CRUD, question editor, assignments, attempts, answer save, and submit.

Status: complete.

Completed additions:

- role-aware examiner/proctor portal;
- examiner assessment create/list/detail flow;
- MCQ question creation;
- candidate and proctor assignment actions;
- JSON proctoring-rule editing;
- candidate assigned-assessment list;
- attempt start/resume;
- MCQ and short-answer answer save;
- submit flow with objective-question scoring;
- browser smoke path for normal candidate submission;
- proctor event queue regression check.

### Week 4

- Add consent, system check, heartbeat, app focus/fullscreen events, and local retry queue.

Status: complete.

Completed additions:

- candidate consent gate before attempt start;
- camera, microphone, backend, fullscreen, and AI-sidecar readiness checks;
- persisted session heartbeat endpoint;
- heartbeat-gap detection and event creation;
- app focus lost and fullscreen exit event capture;
- local retry queue for answers, events, and heartbeats;
- network-outage demo toggle and retry sync control;
- proctor high-priority metrics aligned with Week 4 event scores.

### Week 5

- Integrate AI sidecar.
- Implement face absence and multiple-person detection with debouncing.

Status: complete.

Completed additions:

- local-only FastAPI AI sidecar under `services/ai-engine`;
- OpenCV Haar cascade face counting;
- `/health` and `/analyze-frame` sidecar endpoints;
- deterministic `observed_face_count` path for tests and demos;
- debounced `FACE_ABSENT` and `MULTIPLE_PERSONS` event candidates;
- candidate sidecar health integration;
- candidate low-rate camera frame sampler;
- candidate face-event demo controls;
- AI model/config metadata in backend event payloads;
- proctor queue visibility for AI-derived face events.

### Week 6

- Implement rolling buffer, evidence encoding, evidence upload, evidence playback, and hashing.

### Week 7

- Add phone detection and active liveness.
- Tune thresholds using controlled scenarios.

### Week 8

- Complete proctor review workflow and examiner reports.
- Add audit logging and role/assignment hardening.

### Week 9

- Run E2E tests.
- Collect metrics.
- Prepare diagrams, screenshots, demo data, and capstone report content.

## Team Split

For four members:

- Member 1: candidate desktop, system check, focus/fullscreen events, rolling buffer, evidence upload.
- Member 2: AI sidecar, face/person detection, phone detection, liveness, benchmarking.
- Member 3: backend, database, auth/RBAC, event/evidence APIs, WebSocket, audit logging.
- Member 4: web portal, proctor review UI, examiner workflow, reports, E2E testing, documentation.

For three members:

- combine web portal/reporting with backend and candidate work;
- keep AI as a focused ownership area.

For two members:

- freeze stretch scope;
- prioritize dummy events, face absence, multiple persons, phone detection, focus loss, evidence clips, and review/reporting.

## Risk Controls

- Prove Tauri plus Python sidecar early; switch to PySide6 only if packaging blocks progress.
- Keep AI sampling low and configurable instead of running every model at camera FPS.
- Centralize event types, rules, thresholds, and risk weights.
- Treat risk score only as review priority, never cheating probability.
- Keep evidence storage behind an abstraction so local filesystem can later become MinIO/S3.
- Keep large model files out of Git.
- Maintain `LICENSES.md` as soon as models/libraries are selected.
- Do not add deepfake detection until the MVP is demonstrably stable.

## Definition of Done

A feature is done only when:

- it works in the relevant app or service;
- its data model/API contract is implemented;
- role/assignment authorization is enforced;
- evidence is generated when required and skipped when not required;
- failures are visible rather than silently ignored;
- tests cover normal and unauthorized behavior;
- limitations are documented.

## Immediate Next Task

Start Week 6 rolling evidence work:

1. Add a bounded local rolling media buffer in the candidate app.
2. Capture pre/post context around selected integrity events.
3. Generate short local clips for evidence-required visual events.
4. Compute SHA-256 hashes and clip metadata.
5. Add backend evidence upload and protected retrieval endpoints.
6. Render evidence metadata and playback affordances in the proctor portal.
7. Add cleanup behavior for normal temporary media that does not become evidence.
