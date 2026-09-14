# ProctorAI - Full Codex Handoff Context

> Copy this file into the repository root (or give its contents to Codex) before implementation. It captures the product decisions made during planning and should be treated as the current source of truth unless the project team explicitly changes it.

---

# 1. Mission

Build **ProctorAI**, a zero/near-zero-cost BCA capstone: an **AI-native multimodal proctoring and assessment-integrity monitoring system** for remote academic assessments, placement tests, and online interviews.

This is not a generic proctoring website and not a live-video surveillance product. The key engineering idea is:

> **Run AI primarily on the candidate's Windows laptop, continuously overwrite normal temporary camera/audio data, and upload only short evidence clips/logs when potential integrity events are detected. A human proctor reviews those events.**

---

# 2. University context

- Course: CBCA301 Capstone Project.
- Programme: BCA Semester V.
- Proposed TID: **T6 - AI-Native Computing**.
- University T6 meaning: **Systems designed around AI rather than conventional software.**
- Primary SDG: **SDG 4 - Quality Education**.
- Secondary optional SDG: **SDG 8 - Decent Work and Economic Growth**.
- Milestone 2 expects a working demonstrable MVP and strongly rewards modular technical design, documented testing, and quantitative/qualitative results.

Formal title:

**AI-Native Multimodal Proctoring and Assessment Integrity Monitoring System for Remote Assessments and Interviews**

Working name: **ProctorAI**.

---

# 3. Hard product decisions

Do NOT casually change these:

1. Candidate client is a **Windows desktop app**.
2. Proctor client is a **web portal**.
3. Examiner client is a **web portal**.
4. Mobile app was discussed and then explicitly **dropped**.
5. **No live webcam streaming** to proctor.
6. **No continuous cloud webcam recording** by default.
7. AI runs **locally/on-device** on candidate laptop wherever feasible.
8. Core project must require **no paid cloud GPU**.
9. Core project must require **no paid AI API/subscription**.
10. Use a local **rolling camera/audio buffer**.
11. When suspicious event occurs, retain **short evidence**, target default ~10 seconds: **5 seconds before + 5 seconds after**.
12. Long events can use adaptive evidence with a max duration (target 20-30 sec).
13. Normal footage is overwritten/discarded.
14. Logs are enough for app-focus/fullscreen/copy-paste/monitoring events.
15. **No system-wide keylogger.**
16. AI never automatically declares candidate guilty or fails them.
17. Proctor reviews each relevant event as **confirmed suspicious / false positive / inconclusive**.
18. Examiner sees final score and reviewed integrity report.
19. Deepfake detection is **stretch**, not MVP-critical.
20. Privacy/data minimisation/human oversight are technical requirements.
21. Assessment integrity rules must be configurable per assessment.
22. We prefer working core functionality over too many experimental features.

---

# 4. User roles

## Candidate
Uses Windows app to:
- login;
- view assigned assessment;
- read/accept monitoring consent;
- run camera/mic/system check;
- pass optional identity + liveness check;
- take assessment;
- have local AI monitoring running;
- submit assessment.

Candidate must NOT be able to see other candidates, proctor evidence review, hidden risk weights, or examiner controls.

## Proctor
Uses web portal to:
- login;
- see assigned assessment(s);
- receive event notifications (WebSocket), NOT live video;
- open candidate event;
- play short clip/listen to short audio/read event log;
- choose confirmed suspicious / false positive / inconclusive;
- add note;
- see candidate event history/priority.

## Examiner
Uses web portal to:
- create/edit assessment;
- add questions;
- set date/duration;
- assign candidates;
- assign proctors;
- configure proctoring rules;
- publish assessment;
- inspect submitted answers/scores;
- see reviewed integrity report/evidence.

Optional ADMIN role only if convenient.

---

# 5. Architecture

```text
Candidate Windows App
  |
  +-- React/Tauri UI
  +-- local camera/mic
  +-- local Python AI sidecar
  +-- app-focus/fullscreen monitoring
  +-- rolling media buffer
  +-- event engine
  `-- evidence clip uploader
            |
            | HTTPS + JSON/files
            v
FastAPI Backend
  |
  +-- Auth/RBAC
  +-- Assessments/questions/attempts
  +-- Event ingestion
  +-- Evidence metadata/storage
  +-- Proctor review
  +-- Risk priority
  +-- WebSocket alerts
  `-- Reporting
            |
            +--> PostgreSQL
            +--> local evidence directory / MinIO optional
            |
            +--> Proctor Web (React)
            `--> Examiner Web (React)
```

No WebRTC live video is required.

---

# 6. Recommended monorepo

```text
proctorai/
  apps/
    candidate-desktop/
    web-portal/                 # proctor + examiner routes in one React app
  services/
    api/                        # FastAPI
    ai-engine/                  # Python local AI service
  packages/
    shared-types/
    ui/
    rules/
  models/
  docs/
  tests/
  scripts/
  docker-compose.yml
  .env.example
  README.md
  LICENSES.md
```

Prefer one `web-portal` project with RBAC routes over separate proctor/examiner repositories unless separation becomes necessary.

---

# 7. Recommended technologies

## Candidate desktop
Preferred: **Tauri 2 + React + TypeScript**.

AI: separate local **Python** sidecar/service.

Fallback if packaging becomes a blocker: **PySide6 + Python** single-process desktop app.

Do an early spike before committing too much work to Tauri/Python packaging.

## Backend
- Python 3.12+ as team environment permits.
- FastAPI.
- Pydantic.
- SQLAlchemy + Alembic.
- PostgreSQL.
- WebSockets.
- JWT/session auth.

## Web
- React + TypeScript.
- Use Vite or Next.js; prefer Vite if SSR is unnecessary.
- A component library can be added only if it speeds development and is free.

## AI/CV
- OpenCV.
- MediaPipe/landmark model for face landmarks, blink, head movement.
- ONNX Runtime for small local inference models.
- Small object detector for person/mobile phone. Select model based on CPU latency + licence.
- VAD/background speech later.

## Evidence
- OpenCV VideoWriter initially.
- FFmpeg if needed for better compression/encoding.
- SHA-256 hashes of final evidence files.

## Dev infrastructure
- PostgreSQL local or Docker Compose.
- Evidence local filesystem initially.
- MinIO optional for S3-style local object storage.
- No cloud is required for first working demo.

---

# 8. AI pipeline

Do not process every model at full 30 FPS. Use controlled sampling.

Example local frame pipeline:

```text
Camera 20-30 FPS
  |
  +--> preview UI (normal rate)
  |
  `--> AI sampler e.g. 3-8 FPS depending model
          |
          +--> face presence/count
          +--> landmarks/head pose/blink
          `--> object detector at lower rate e.g. 2-5 FPS
```

Actual rates must be benchmarked and configurable.

### Raw detection is NOT an event

Use an event debouncer/state machine:

```text
raw model outputs
   -> confidence threshold
   -> persistence / N-of-M frames
   -> min duration
   -> cooldown / merge
   -> integrity event
```

Example phone rule (initial placeholder only):

```text
confidence >= 0.70 in >=3 of last 5 object-detection samples
=> start PHONE_DETECTED incident
```

Tune using test data.

---

# 9. Core event types

Implement in this order:

## P0 / MVP
- FACE_ABSENT
- MULTIPLE_PERSONS
- PHONE_DETECTED
- LIVENESS_FAILED
- APP_FOCUS_LOST
- FULLSCREEN_EXIT
- CAMERA_DISABLED
- MICROPHONE_DISABLED
- AI_ENGINE_INTERRUPTED / HEARTBEAT_GAP

## P1
- GAZE_ANOMALY / persistent head-turn pattern
- BACKGROUND_SPEECH
- NETWORK_INTERRUPTION
- COPY_ATTEMPT / PASTE_ATTEMPT when assessment rule forbids it

## P2 / stretch
- POSSIBLE_PRESENTATION_ATTACK
- IDENTITY_MISMATCH (can move earlier if easy)
- AUDIO_ANOMALY
- DEEPFAKE_SIGNAL
- SPEAKER_DIARIZATION_SIGNAL

Use `DEEPFAKE_SIGNAL` only as an experimental risk signal if implemented, never as definitive proof.

---

# 10. Rolling evidence buffer

This is a flagship feature.

Target behavior:

```text
normal state:
  keep last 5 sec locally in bounded memory/buffer
  overwrite old content continuously

when event starts:
  freeze/prevent deletion of previous 5 sec
  record next 5 sec
  encode final ~10 sec clip
  calculate SHA-256
  send event metadata
  upload evidence
  clear normal temporary data after safe completion
```

For event lasting longer:

```text
pre_roll 5 sec + event_duration + post_roll 5 sec
max clip duration 20-30 sec
```

Need a cooldown/merge strategy so one phone held for 30 seconds does not create 50 clips.

Potential event lifecycle:

```text
DETECTED
EVIDENCE_CAPTURING
EVIDENCE_ENCODING
EVIDENCE_UPLOADING
EVIDENCE_READY
UNREVIEWED
CONFIRMED | FALSE_POSITIVE | INCONCLUSIVE
```

---

# 11. Evidence requirements by event

- PHONE_DETECTED -> video clip.
- MULTIPLE_PERSONS -> video clip.
- FACE_ABSENT -> video clip if duration threshold reached.
- LIVENESS_FAILED -> video clip.
- POSSIBLE_PRESENTATION_ATTACK -> video clip.
- IDENTITY_MISMATCH -> screenshot + optional clip.
- GAZE_ANOMALY -> clip only after persistent/repeated threshold.
- BACKGROUND_SPEECH -> audio clip.
- APP_FOCUS_LOST -> log only.
- FULLSCREEN_EXIT -> log only.
- COPY/PASTE -> log only.
- CAMERA/MIC disabled -> log only.
- heartbeat/tamper interruption -> log only.

Every evidence file should have:
- event UUID;
- attempt UUID;
- timestamps;
- hash;
- MIME type;
- size;
- duration when applicable.

---

# 12. Local AI features and implementation notes

## Face presence/count
Start here. Must be stable and fast.

Goal:
```text
0 face/person -> absent after threshold
1 -> normal
>=2 -> multiple-person event after persistence
```

Do not alert from a single bad frame.

## Blink
Use facial landmarks/eye geometry.
Use for active liveness, NOT as "no blink = cheating".

## Head pose
Estimate coarse left/right/up/down/forward.
Natural glances should not generate alerts.
Only persistent/repeated behavior gets low/medium event.

## Phone detection
Use compact object detector exported to ONNX.
Object classes minimum: person + cell phone.
Benchmark on normal laptop CPU.

## Liveness
MVP = active challenge:
- blink twice;
- turn left/right;
- randomized sequence.
Validate landmark movement within time window.

## Still image/replay
MVP supportive checks:
- frozen/repeated frames;
- failed active liveness.
Dedicated anti-spoof model only after core works.

## Deepfake
Do not block MVP on this. If implemented, make it experimental and show accuracy limitations.

## Audio
Start with VAD/background speech duration, not speech transcription or identity.
Do not upload normal audio continuously.

---

# 13. Assessment application integrity

We are NOT building malware/spyware.

Allowed/desired prototype monitoring:
- candidate app focus lost;
- candidate app minimised;
- fullscreen exited if required;
- copy/paste inside the assessment UI if rules disable it;
- monitoring component disabled;
- camera/mic disabled;
- AI sidecar dead/unresponsive;
- heartbeat missing.

Explicit non-goals:
- global keylogger;
- capturing passwords typed elsewhere;
- reading unrelated files;
- secretly recording other applications;
- emotion/lie detection.

---

# 14. Risk scoring

Risk score is only for proctor queue priority.

Store configuration in DB/rules, not hard-coded everywhere.

Initial placeholder base weights:

```text
APP_FOCUS_LOST          5
FULLSCREEN_EXIT         5
GAZE_ANOMALY            5
FACE_ABSENT            10
BACKGROUND_SPEECH      10
PHONE_DETECTED         20
MULTIPLE_PERSONS       25
AI_ENGINE_INTERRUPTED  20
LIVENESS_FAILED        30
IDENTITY_MISMATCH      35
```

Priority bands:

```text
0-20 Low
21-50 Moderate
51-75 High
76-100 Critical review priority
```

Never call these "probability of cheating".

Need duplicate suppression/diminishing returns.

Keep human review separate:

```text
AI priority = automated
human review = confirmed / false positive / inconclusive
final decision = examiner/institution
```

---

# 15. Database entities

Implement with UUIDs.

Core:
- User
- Assessment
- Question
- AssessmentCandidate
- AssessmentProctor
- ProctoringRule
- Attempt
- Answer
- IntegrityEvent
- EvidenceFile
- EventReview
- AuditLog

Optional:
- IdentityEnrollment
- ConsentRecord
- HeartbeatSummary

See `ProctorAI_Capstone_Master_Spec.md` for suggested fields.

---

# 16. API implementation order

## First
```text
GET /health
POST /auth/login
GET /auth/me
```

## Assessment
```text
POST /assessments
GET /assessments
POST /assessments/{id}/questions
POST /assessments/{id}/candidates
POST /assessments/{id}/proctors
PUT /assessments/{id}/rules
```

## Attempt
```text
POST /attempts/start
POST /attempts/{id}/answers
POST /attempts/{id}/heartbeat
POST /attempts/{id}/submit
```

## Event/evidence
```text
POST /attempts/{id}/events
POST /attempts/{id}/events/{event_id}/evidence
GET  /events/{id}
GET  /events/{id}/evidence
POST /events/{id}/review
```

## Proctor realtime
```text
WS /ws/proctor/assessments/{assessment_id}
```

Every endpoint must enforce role + ownership/assignment.

---

# 17. Security invariants

- Never store plaintext passwords.
- Candidate cannot choose arbitrary candidate_id in request and access another attempt.
- Evidence download route must check authorization.
- Validate file content type/size.
- Evidence filename/path generated server-side.
- Record server receive time as well as client event time.
- Hash evidence.
- Do not expose direct public filesystem paths.
- Keep secrets in `.env`, never Git.
- Add `.env.example` with fake values.
- Use CORS narrowly in deployed environment.
- Audit proctor review changes.

---

# 18. Privacy invariants

- Consent must happen before monitoring begins.
- Normal rolling media must be bounded and overwritten.
- Do not upload media for "normal" state.
- Do not retain raw camera feed by default.
- Event evidence must have retention metadata.
- Provide deletion logic/script by final project if feasible.
- Do not infer emotion, honesty, intelligence, disability, or personality.
- Human review required for consequential use.

---

# 19. UI requirements

## Candidate
Screens:
1. Login.
2. Dashboard/upcoming assessments.
3. Assessment details.
4. Privacy/consent.
5. System check.
6. Identity/liveness (if enabled).
7. Assessment runner.
8. Submission success.
9. Network/interruption state.

During assessment show simple status:
- Camera active.
- Mic active.
- Monitoring active.
- Network status.

Do NOT show secret risk score/thresholds.

## Proctor
Screens:
1. Login.
2. Assigned assessments.
3. Active/recent assessment event dashboard.
4. Event queue.
5. Event review with media player.
6. Candidate event history.

## Examiner
Screens:
1. Login.
2. Assessment list.
3. Create/edit assessment.
4. Question editor.
5. Candidate/proctor assignment.
6. Proctoring-rule configuration.
7. Results.
8. Candidate integrity report.

---

# 20. MVP acceptance tests

Codex/developers should target these end-to-end tests.

### E2E-01 Normal exam
Examiner creates assessment -> candidate takes it normally -> submits -> score visible -> no evidence clips generated unnecessarily.

### E2E-02 Phone event
Candidate shows phone -> local detector persists -> one incident created -> ~10 sec clip includes pre-event context -> backend stores event -> proctor WebSocket alert -> proctor plays clip -> confirms/dismisses -> examiner report updates.

### E2E-03 Multiple persons
Second person stays in frame -> clip/event -> proctor review.

### E2E-04 Face absence
Candidate leaves for threshold -> clip/event.

### E2E-05 Focus loss
Candidate app loses focus -> log event only -> no video required.

### E2E-06 Liveness
Candidate performs blink/head-turn challenge -> passes. A static image should fail at least challenge-response behavior.

### E2E-07 Network interruption
Backend unavailable temporarily -> answer/event queued locally -> upload resumes when network returns.

### E2E-08 Authorization
Candidate tries to access proctor endpoint -> 403. Proctor not assigned to assessment -> 403.

---

# 21. Performance targets (initial, not guaranteed)

Treat as engineering targets to benchmark, not final claims:

- Candidate UI remains usable during inference.
- Face/landmark pipeline near-real-time on normal CPU.
- Object detection can run at lower sampling rate (2-5 FPS is acceptable if event latency remains reasonable).
- Event alert reaches proctor within a few seconds after evidence metadata is created when network is healthy.
- Evidence clips are compressed and small enough for free/local storage.

Record actual results for report.

---

# 22. Metrics to collect from day one

Create lightweight telemetry locally/for test builds:

- model inference ms per frame;
- sampling FPS;
- CPU percentage;
- RAM usage;
- event detection latency;
- evidence encode duration;
- evidence file bytes;
- upload duration;
- false positives/false negatives from test labels;
- proctor review decision counts.

Do not collect unrelated personal telemetry.

---

# 23. Development strategy for Codex

## Do not attempt everything in one generation.

Use vertical slices.

### Slice A - end-to-end dummy event
Goal: Tauri -> API -> PostgreSQL -> WebSocket -> React Proctor.

1. Scaffold repo.
2. Backend `/health`.
3. PostgreSQL connection/migration.
4. Seed 3 users (candidate/proctor/examiner) with dev passwords.
5. Candidate app button "Send test event".
6. `POST /events`.
7. WebSocket pushes event to proctor.
8. Proctor page renders it.

Do this before AI.

### Slice B - webcam + face absent
1. Candidate camera preview.
2. Python sidecar receives sampled frames.
3. face presence detector.
4. event debouncer.
5. real FACE_ABSENT event reaches proctor.

### Slice C - rolling buffer
1. buffer last 5 seconds.
2. manual trigger generates 10-second clip.
3. upload.
4. proctor playback.
5. then connect to AI events.

### Slice D - assessment engine
Build examiner -> candidate -> submit -> result.

### Slice E - phone + multiple persons + liveness
Add one by one with tests.

This order reduces integration risk.

---

# 24. Suggested first Git milestones

```text
v0.1 repository + backend + DB
v0.2 auth/RBAC + seeded roles
v0.3 examiner basic assessment CRUD
v0.4 candidate assessment runner
v0.5 proctor dummy realtime event queue
v0.6 camera + face presence
v0.7 rolling evidence clips
v0.8 phone/multiple-person detector
v0.9 liveness + application focus monitoring
v0.10 review workflow + integrity report
v0.11 testing/metrics/hardening
v1.0 capstone MVP
```

---

# 25. Testing data policy

Use:
- team members;
- explicitly consenting volunteers;
- synthetic/mock assessment records;
- public model-evaluation data only where licence permits.

Do not use real university exam recordings or applicant data without authorization.

Store ground truth for controlled tests, e.g.:

```csv
scenario_id,event_expected,start_sec,end_sec,notes
S01,NONE,0,60,normal candidate
S02,PHONE_DETECTED,15,25,phone clearly visible
S03,MULTIPLE_PERSONS,20,32,second person enters
```

This enables precision/recall/latency calculations.

---

# 26. Failure behavior

AI/model failures should be explicit.

Examples:
- model cannot load -> candidate system check fails; do not silently continue.
- camera dies mid-session -> CAMERA_DISABLED event.
- AI sidecar crashes -> AI_ENGINE_INTERRUPTED event.
- upload fails -> queue and retry.
- evidence encode fails -> event remains with `evidence_status=FAILED`; proctor sees failure instead of fake evidence.
- clock differences -> store client timestamp + server receive time.

---

# 27. Model/version traceability

Every AI-derived event should ideally record:

```text
model_name
model_version
threshold_config_version
client_app_version
```

This makes tests reproducible and improves viva/report quality.

Do not hard-code thresholds in 20 files. Centralise configs.

---

# 28. Future scope, not current requirements

- Deepfake classifier.
- Advanced face anti-spoof model.
- Speaker diarization.
- Virtual-camera detection.
- Institution SSO.
- LMS integration.
- Browser-only candidate mode.
- Mac/Linux candidate builds.
- optional escalated live WebRTC stream.
- continuous recording under explicit institution policy.
- cloud autoscaling.
- analytics across many examinations.
- automated question generation (not needed).
- agentic proctor/investigation assistant (could map to T3 in future).

---

# 29. Things Codex must NOT implement without explicit request

- mobile app;
- system-wide keylogger;
- spyware-like global input capture;
- covert recording;
- emotion detection;
- lie detection;
- automatic fail/ban decision based on AI;
- paid API dependency;
- cloud GPU dependency;
- continuous video upload;
- live proctor streaming;
- facial or audio data collection beyond the stated monitoring/evidence workflow;
- deepfake module before core MVP is stable.

---

# 30. Coding conventions

- TypeScript strict mode.
- Python type hints.
- Pydantic request/response schemas.
- UUID primary identifiers.
- UTC timestamps in database; render local time in UI.
- Structured logging.
- Secrets only via environment/config.
- No giant `main.py`; modular routers/services.
- AI detector interface abstraction.
- Central event-type enum and rules.
- Add tests alongside modules.
- Keep large AI models out of Git; use download/setup script or Git LFS only if team intentionally chooses it.
- Add comments for non-obvious logic, not every line.

Suggested AI interface:

```python
class Detector(Protocol):
    name: str
    version: str
    def process(self, frame, timestamp) -> list[RawDetection]: ...
```

Event engine should consume generic `RawDetection` rather than model-specific objects.

---

# 31. Suggested local dev ports

```text
FastAPI:        8000
Web portal:     5173
PostgreSQL:     5432
AI sidecar:     IPC preferred; localhost 8765 if HTTP/WebSocket is easier
MinIO optional: 9000/9001
```

Avoid exposing AI sidecar externally; bind to loopback only if networking is used.

---

# 32. Environment variables

Example `.env.example`:

```text
DATABASE_URL=postgresql+psycopg://proctorai:proctorai@localhost:5432/proctorai
JWT_SECRET=CHANGE_ME
JWT_ACCESS_MINUTES=30
EVIDENCE_DIR=./data/evidence
CORS_ORIGINS=http://localhost:5173
MAX_EVIDENCE_MB=25
WS_HEARTBEAT_SECONDS=10
```

Never put real secrets in the repo.

---

# 33. Evidence storage interface

Create abstraction early:

```text
EvidenceStorage
  save(...)
  open(...)
  delete(...)
  exists(...)
```

Implementation 1: local filesystem.
Future: MinIO/S3.

This prevents cloud-specific code from infecting domain logic.

---

# 34. Proctoring rule interface

Rules need per-assessment configuration:

```json
{
  "PHONE_DETECTED": {
    "enabled": true,
    "severity": "HIGH",
    "min_confidence": 0.70,
    "min_persistence_ms": 1000
  },
  "APP_FOCUS_LOST": {
    "enabled": true,
    "severity": "MEDIUM",
    "min_persistence_ms": 500
  }
}
```

Candidate app downloads signed/configured rules at attempt start. Server remains source of truth.

---

# 35. Human review data model

Do not overwrite AI event when proctor reviews it.

Keep:

```text
AI event data = immutable-ish observation
Proctor review = separate record
```

This preserves auditability and lets us measure false-positive rate later.

---

# 36. UI wording

Preferred:
- "Potential integrity event"
- "Review required"
- "AI confidence"
- "Review priority"
- "Confirmed suspicious event"
- "False positive"
- "Inconclusive"

Avoid:
- "Cheater detected"
- "Cheating probability"
- "Dishonest candidate"
- "AI verdict"

---

# 37. Definition of Done for core feature

A feature is not done because model returns output in a notebook.

For an event feature to be DONE:

1. Detector works in candidate app.
2. Threshold/persistence logic exists.
3. Event schema populated.
4. Evidence generated if required.
5. Backend ingests it.
6. Database persists it.
7. Proctor sees it.
8. Review decision saves.
9. Relevant tests exist.
10. Known limitations documented.

---

# 38. First implementation task for Codex

When starting from an empty repository, build only the **vertical-slice foundation** first.

### Task 1
Create monorepo directories and README.

### Task 2
Create Docker Compose PostgreSQL + FastAPI API with:
- `/health`;
- SQLAlchemy/Alembic;
- User/Assessment/Attempt/IntegrityEvent minimal tables.

### Task 3
Create React web portal with temporary role switch/dev login and an event queue page.

### Task 4
Create Tauri candidate shell with:
- basic login placeholder;
- camera preview placeholder;
- button "Send Test Integrity Event".

### Task 5
POST dummy event to backend, persist it, and push over WebSocket to web portal.

### Task 6
Add automated tests for event endpoint and role permissions.

**Stop there and verify the entire path before integrating any AI model.**

---

# 39. One-paragraph project reminder for future Codex sessions

> ProctorAI is a BCA capstone using T6 AI-Native Computing. The candidate takes an assessment in a Windows desktop app. Camera/microphone AI runs mainly on the candidate device, not on a paid cloud GPU. The app keeps a temporary rolling media buffer and normally discards footage. When an integrity event such as phone detection, multiple persons, face absence, liveness failure, or application focus loss occurs, it sends event metadata and, where relevant, a short evidence clip (normally 5 seconds before + 5 seconds after) to a FastAPI/PostgreSQL backend. There is no live webcam stream and no continuous cloud recording. A React web portal provides Proctor and Examiner roles. Proctors review evidence and mark it confirmed suspicious, false positive, or inconclusive; examiners create assessments and review final results/integrity reports. There is no mobile app, no system-wide keylogger, no automatic cheating verdict, and no required paid AI/API/cloud GPU. Deepfake detection is stretch only. Prioritize a working modular MVP, privacy/data minimisation, human oversight, documented testing, and measurable performance.

---

# 40. Source-of-truth hierarchy

If instructions conflict, use this order:

1. Explicit latest project-team decision.
2. This `ProctorAI_Codex_Context.md`.
3. `ProctorAI_Capstone_Master_Spec.md`.
4. Existing code/README.
5. Older brainstorming notes.

When making a major architecture change, update both Markdown documents so later sessions do not revert to old assumptions.
