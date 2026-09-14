# ProctorAI - CBCA301 Capstone Master Project Specification

> **Proposed academic title:** **AI-Native Multimodal Proctoring and Assessment Integrity Monitoring System for Remote Assessments and Interviews**  
> **Working/product name:** **ProctorAI**  
> **Course:** CBCA301 - Capstone Project, BCA Semester V  
> **Recommended Technology ID (TID):** **T6 - AI-Native Computing**  
> **University definition of T6:** *Systems designed around AI rather than conventional software.*  
> **Primary SDG:** **SDG 4 - Quality Education**  
> **Secondary SDG:** **SDG 8 - Decent Work and Economic Growth**  
> **Core clients:** Candidate Windows desktop application + Proctor web portal + Examiner web portal  
> **Mobile application:** **Out of scope**  
> **Live webcam streaming to proctor:** **Out of scope**  
> **Continuous cloud recording:** **Out of scope**  
> **Evidence strategy:** Local AI + event-driven short evidence clips + human review  
> **Budget target:** **₹0 for development and university demonstration**

---

## 1. Why this document exists

This is the master specification for the ProctorAI capstone. It is written for three audiences:

1. **Capstone coordinator / guide / evaluation panel** - to understand the problem, technical depth, feasibility, SDG mapping, privacy safeguards, scope, limitations, milestones, and expected outcome.
2. **Project teammates** - to understand exactly what is being built, why each feature exists, how it should work, what technology is recommended, and what alternatives exist.
3. **Developers / Codex** - to provide sufficient technical context to begin implementing the project without re-deciding the architecture every time.

The project deliberately avoids expensive commercial AI APIs, cloud GPUs, continuous video upload, and unnecessary surveillance. The intended system is **AI-assisted, evidence-based, privacy-aware, and human-in-the-loop**.

---

# 2. Executive summary

Remote examinations, placement tests, certification tests, and online job interviews are convenient but create integrity challenges. A human proctor cannot efficiently watch many candidates continuously, and simple web-based controls such as tab-switch detection do not cover physical-world behavior such as another person entering the room, use of a mobile phone, candidate absence, still-image spoofing, or suspicious background speech.

**ProctorAI** is proposed as an **AI-native multimodal integrity monitoring system**. A Windows desktop application used by the candidate accesses the camera and microphone with explicit consent and performs most AI inference **locally on the candidate's computer**. It monitors permitted application/session events and uses computer vision, audio analysis, identity/liveness checks, and rule-based risk logic to identify potentially suspicious integrity events.

The system does **not** continuously upload the candidate's webcam feed and does **not** require a proctor to watch live video. Instead, the candidate application maintains a small temporary rolling buffer. When a suspicious event is detected, it creates a short evidence clip - normally about **10 seconds (5 seconds before and 5 seconds after the event)** - and uploads only the event metadata and evidence to the backend. The proctor receives the alert on a web dashboard and classifies it as **Confirmed Suspicious**, **False Positive**, or **Inconclusive**. The examiner later sees assessment results together with a reviewed integrity report.

The system assists human decision-making; it does **not automatically declare that a candidate cheated** or automatically fail a candidate.

---

# 3. Capstone alignment and approval rationale

## 3.1 Recommended Technology ID: T6 - AI-Native Computing

The university's technology-stack document defines:

- **T6 - AI-Native Computing:** *Systems designed around AI rather than conventional software.*

This is the best match because AI is not an optional add-on in ProctorAI. The core monitoring workflow is built around AI-driven interpretation of camera, audio, liveness, and behavioral signals.

### Why not T3 - Agentic AI?

T3 is defined by the university as AI systems that plan, reason, use tools, and autonomously execute tasks. ProctorAI does not need an autonomous agent to satisfy its core objective. It primarily performs multimodal perception, event detection, evidence fusion, and human-assisted review. T3 could become relevant in a future version with an autonomous investigation/proctor agent, but selecting T6 keeps the current proposal accurate and achievable.

### Related but not selected

T7 - AI + Edge Computing is conceptually related because much of the AI inference occurs near the data source (the candidate device). However, the project's defining idea is an AI-native integrity platform rather than an edge-computing research project, so **T6 remains the recommended primary TID**.

---

## 3.2 SDG alignment

### Primary: SDG 4 - Quality Education

Remote assessments are increasingly part of digital education. The project supports SDG 4 by attempting to improve the credibility, fairness, and reliability of remote assessments while reducing the requirement for constant manual surveillance.

**Suggested SDG rationale for submission:**

> The proposed system supports fair and reliable technology-enabled assessment by providing AI-assisted integrity monitoring, explainable evidence collection, and human review for remote examinations and academic evaluations. This contributes to the credibility and quality of digital education and assessment practices.

### Secondary: SDG 8 - Decent Work and Economic Growth

The same platform can support online recruitment assessments and interviews. Reliable remote hiring assessments can help organizations evaluate candidates in geographically distributed settings.

**Suggested secondary rationale:**

> The platform can also support trustworthy remote recruitment assessments and interviews, contributing to efficient and accessible digital hiring processes.

Use SDG 8 only if the proposal explicitly includes recruitment/interview use. SDG 4 alone is sufficient if the coordinator prefers a tighter academic scope.

---

# 4. Approval-ready project proposal

## 4.1 Proposed project title

**AI-Native Multimodal Proctoring and Assessment Integrity Monitoring System for Remote Assessments and Interviews**

Alternative shorter title:

**ProctorAI: AI-Native Multimodal Remote Proctoring and Integrity Monitoring System**

The first title is recommended for the university form because it describes the system directly rather than relying on a product name.

---

## 4.2 Problem statement

> Remote examinations, technical assessments, and online interviews are increasingly conducted through digital platforms, creating challenges in maintaining assessment integrity and verifying that candidates complete evaluations under permitted conditions. Continuous manual remote proctoring is difficult to scale and can require significant human attention and network/storage resources. Existing simple browser controls also cannot reliably observe physical-world indicators such as candidate absence, additional persons, prohibited objects, presentation attacks, or suspicious background speech. The proposed project aims to develop an AI-native multimodal proctoring and integrity monitoring system that performs primarily on-device analysis of visual, audio, and application/session signals, captures short evidence clips only when suspicious events are detected, and provides these events to authorised human proctors for review. The system will support human decision-making rather than automatically determining misconduct.

---

## 4.3 Problem significance / motivation

> Remote assessment systems must balance integrity, scalability, cost, privacy, and fairness. Continuous video monitoring is resource-intensive and may collect significantly more personal data than is necessary. At the same time, purely browser-based monitoring provides limited visibility into physical-world events. ProctorAI addresses this gap by combining local AI inference with event-driven evidence capture, allowing normal footage to be discarded while retaining short evidence segments only for potentially relevant events. This reduces bandwidth and storage requirements while providing human reviewers with explainable evidence instead of opaque automated accusations.

---

## 4.4 Target users / stakeholders

### Primary stakeholders

- **Candidates** - students, job applicants, trainees, or certification candidates taking an assessment/interview.
- **Proctors** - authorised reviewers responsible for reviewing integrity events during or after an active session.
- **Examiners** - faculty, recruiters, or assessment owners who create assessments, configure rules, inspect results, and make final decisions.

### Secondary stakeholders

- University/institution administrators.
- Placement/recruitment teams.
- Project guides and evaluators.
- IT/security administrators responsible for deployment and data retention.
- Accessibility/privacy stakeholders.

---

## 4.5 Brief proposed solution

> The proposed system consists of a Windows candidate application and a web-based portal for proctors and examiners. With explicit consent, the candidate application accesses the webcam and microphone and performs local AI analysis for face presence, multiple-person detection, prohibited-object detection, basic head-pose/gaze behavior, blink/liveness checks, presentation-attack indicators, and audio activity. It also monitors assessment-application events such as loss of focus, fullscreen exit, disabled monitoring components, and permitted copy/paste restrictions. Normal video/audio is not continuously uploaded. A temporary rolling buffer is maintained locally and, when an integrity event is detected, the application creates and securely uploads a short evidence clip together with event metadata. A proctor reviews the evidence and marks the event as confirmed suspicious, false positive, or inconclusive. Examiners use the web portal to create assessments, configure proctoring rules, review results, and inspect reviewed integrity reports.

---

## 4.6 Expected outcome

> A functional prototype demonstrating a complete remote assessment workflow with candidate, proctor, and examiner roles; local AI-based multimodal monitoring; event-driven evidence capture; secure event upload; human evidence review; assessment scoring; and final integrity reporting. The project will be evaluated using reproducible test scenarios and quantitative measures such as event-detection precision/recall where feasible, false-positive rate, detection latency, local CPU/RAM usage, evidence upload size, and review workflow correctness.

---

# 5. Product principles - decisions that should not casually change

These are the core decisions established during project planning.

1. **Candidate uses a Windows desktop application.**
2. **Proctor uses a web application.**
3. **Examiner uses a web application.**
4. **No mobile application in the current capstone.**
5. **No live webcam streaming to the proctor.**
6. **No continuous cloud video recording by default.**
7. **AI inference runs primarily on the candidate's laptop.**
8. **The project must work without a paid cloud GPU.**
9. **The project must not require paid AI APIs or subscriptions.**
10. **Suspicious events generate short evidence clips.**
11. **Default video evidence target: ~10 seconds, approximately 5 seconds before + 5 seconds after detection.**
12. **Long events may create adaptive clips with a reasonable maximum (e.g. 20-30 seconds).**
13. **Normal footage should be discarded rather than uploaded.**
14. **Tab/app-focus events that do not need camera evidence use logs rather than video.**
15. **No system-wide keylogger.**
16. **No automatic guilt/cheating verdict.** AI flags potentially suspicious events; humans review them.
17. **Deepfake detection is an advanced/experimental feature, not an MVP dependency.**
18. **Privacy/data minimisation is a technical requirement, not only documentation.**
19. **System behavior must be configurable per assessment.** A phone may be forbidden in one exam and permitted in an interview.
20. **The architecture must be modular enough to score well under the CBCA301 design rubric.**

---

# 6. High-level architecture

```text
                                PROCTORAI

                      +-----------------------+
                      |   FastAPI Backend     |
                      | REST + WebSocket API  |
                      +----------+------------+
                                 |
                 +---------------+---------------+
                 |                               |
        +--------v---------+              +------v-------+
        |   PostgreSQL     |              | Evidence     |
        | users, exams,    |              | Storage      |
        | events, reviews  |              | short clips  |
        +------------------+              +--------------+
                 ^                               ^
                 | HTTPS / WebSocket             |
                 |                               |
+----------------+------------------------------------------------------+
|                  CANDIDATE WINDOWS APPLICATION                        |
|                                                                       |
| Camera ----+                                                         |
| Microphone-+--> Local AI Engine --> Event Engine --> Rolling Buffer   |
| App state--+                              |               |            |
|                                             suspicious?  |            |
|                                                  | YES    |            |
|                                                  v        |            |
|                                      Create evidence clip+metadata     |
+--------------------------------------------------+--------------------+
                                                   |
                                                   | secure upload
                                                   v
                                  +----------------+----------------+
                                  |                                 |
                         +--------v---------+              +--------v---------+
                         | Proctor Website  |              | Examiner Website |
                         | alerts/evidence  |              | setup/results    |
                         | human review     |              | final reports    |
                         +------------------+              +------------------+
```

### Why this architecture?

- Local inference avoids continuous cloud GPU cost.
- Event upload drastically reduces bandwidth/storage compared with continuous recording.
- Desktop candidate app provides more controlled assessment behavior than a normal browser.
- Web portals allow proctors/examiners to work without installing software.
- A shared backend/database keeps role data consistent.
- Human review reduces the risk of automated false accusations.

---

# 7. Suggested repository architecture

```text
proctorai/
|
|-- apps/
|   |-- candidate-desktop/       # Tauri + React candidate shell
|   |-- proctor-web/             # React/Next.js web portal
|   `-- examiner-web/            # Can share same web app with RBAC routes
|
|-- services/
|   |-- api/                     # FastAPI backend
|   `-- ai-engine/               # Python local AI service / sidecar
|
|-- packages/
|   |-- shared-types/            # shared event/API types
|   |-- ui/                      # optional shared React components
|   `-- rules/                   # event/risk rule definitions
|
|-- models/                      # model manifests, NOT huge model files in Git
|-- docs/
|   |-- architecture/
|   |-- api/
|   |-- testing/
|   |-- ethics-privacy/
|   `-- capstone/
|
|-- scripts/
|-- tests/
|-- docker-compose.yml           # backend + PostgreSQL for development
|-- .env.example
|-- README.md
`-- LICENSES.md
```

### Simpler fallback architecture

If Tauri + Rust + Python sidecar becomes too difficult, replace the candidate app with **PySide6 + Python**. That reduces engineering complexity because OpenCV/MediaPipe/ONNX and the desktop UI can run in the same Python process. The trade-off is less UI-code reuse with the web portal.

---

# 8. Technology stack - recommended choices, reasons, costs, and alternatives

## 8.1 Candidate desktop shell

### Recommended: Tauri 2 + React/TypeScript

**Purpose:** Windows desktop application shell, exam UI, application lifecycle, local filesystem/IPC, fullscreen handling, packaging.

**Why:**
- Modern native desktop shell with a web frontend.
- Lets the team reuse React knowledge/components.
- Tauri itself is MIT/Apache-2.0 licensed.
- Uses WebView2 on Windows rather than bundling a full browser engine.
- Works well with a local Python AI sidecar.

**Cost:** ₹0.

**How:**
- React/TypeScript renders candidate UI.
- Tauri commands/plugins expose required desktop capabilities.
- Python AI process runs locally and communicates by localhost/IPC/stdin-stdout.
- Tauri manages assessment mode, evidence files, and backend upload.

**Alternative 1: PySide6 + Python**
- Lower implementation risk.
- AI libraries integrate directly.
- Good fallback if Rust/Tauri packaging consumes too much time.

**Alternative 2: Electron + React**
- Very mature ecosystem and easier Node integration.
- Heavier memory footprint because Chromium is bundled.

**Decision rule:** Start with Tauri if the team can handle JS/TypeScript plus basic Rust configuration. Keep PySide6 as the contingency plan.

---

## 8.2 Web portal

### Recommended: React + TypeScript (optionally Next.js)

**Purpose:** Proctor and Examiner interfaces.

**Why:**
- Strong ecosystem.
- Easy WebSocket/realtime UI.
- Can share TypeScript types with Tauri UI.
- No paid service required.

**Cost:** ₹0.

**Alternative:** Vue/Svelte. Use only if the team already knows them better.

**Recommendation:** A single web codebase with RBAC routes is enough:

```text
/proctor/*
/examiner/*
/admin/* (optional)
```

Do not build two completely separate web projects unless needed.

---

## 8.3 Backend API

### Recommended: Python + FastAPI

**Purpose:** Authentication, RBAC, assessment data, event ingestion, evidence metadata, proctor reviews, results, WebSocket notifications, reports.

**Why:**
- Same language as AI code.
- Excellent API validation via Pydantic.
- Supports OAuth2/JWT patterns and WebSockets.
- Easy to run locally.

**Cost:** ₹0.

**Alternative:** Node.js/NestJS. Good if the team is much stronger in TypeScript, but Python simplifies sharing code/knowledge with AI work.

---

## 8.4 Database

### Recommended: PostgreSQL

**Purpose:** Durable structured storage for users, assessments, attempts, events, reviews, scores, rules, and audit logs.

**Why:**
- Open source and free.
- Relational structure is appropriate for assessments and role relationships.
- Transactions and constraints are useful for integrity/audit records.

**Cost:** ₹0 locally.

**Alternative:** SQLite for very early prototype, then PostgreSQL before Milestone 2.

**Optional hosted alternative:** A free managed PostgreSQL tier may be used for demonstration, but the capstone should not depend on a paid cloud plan.

---

## 8.5 ORM and migrations

### Recommended: SQLAlchemy + Alembic

**Purpose:** Python database models, queries, schema migration history.

**Cost:** ₹0.

**Alternative:** SQLModel for simpler FastAPI integration.

---

## 8.6 Computer vision foundation

### Recommended: OpenCV

**Purpose:** Camera frames, image preprocessing, drawing overlays, frame conversion, video encoding helpers, geometry.

**Why:** Mature, fast, widely used, open source. OpenCV 4.5+ is Apache-2.0 licensed.

**Cost:** ₹0.

**Alternative:** Pillow for simple image operations, but not as suitable as the main real-time CV layer.

---

## 8.7 Facial landmarks / blink / head pose

### Recommended: MediaPipe Face Landmarker / Face Mesh-style landmarks

**Purpose:** Face landmarks, eye geometry, blink heuristics, head pose inputs, basic liveness challenge signals.

**Why:** Lightweight and suitable for local CPU inference.

**Cost:** ₹0.

**Alternative:** OpenCV DNN face landmarks or another permissively licensed landmark model.

---

## 8.8 General local model inference

### Recommended: ONNX Runtime

**Purpose:** Run exported object detection / anti-spoof / classification models locally.

**Why:**
- Cross-platform.
- Supports CPU inference.
- Can take advantage of available hardware acceleration without requiring a cloud GPU.
- Appropriate for Windows on-device inference.

**Cost:** ₹0.

**Alternative:** PyTorch directly. Easier during experimentation, but packaged desktop inference can be larger/heavier.

**Recommended workflow:** Train/experiment in PyTorch if required -> export to ONNX -> ship inference model with candidate app.

---

## 8.9 Object detection

### Recommended for MVP

Use a **small, locally runnable pretrained object detector** exported to ONNX. Required classes should at minimum include:

- person
- cell phone

Optional classes:

- book
- laptop/tablet (depending assessment rules)

**Why not lock the project to one model brand now?** Model licences and packaging conditions differ. The engineering requirement is a small detector with a licence acceptable for the project.

**Possible options:**
- MobileNet-SSD / SSD-family model.
- EfficientDet-Lite-family model.
- A YOLO-family model if its current licence is reviewed and acceptable for the intended distribution.

**Decision criteria:** CPU latency, model size, accuracy on phone/person classes, licence, easy ONNX export.

---

## 8.10 Audio analysis

### Recommended MVP components

- Local microphone capture.
- Voice Activity Detection (VAD).
- Sustained background-speech/anomalous-audio detection using simple features/thresholds.

**Possible technology:** Silero VAD or WebRTC VAD, subject to licence/dependency review.

**Important:** MVP should detect **speech activity / possible additional speech**, not claim reliable speaker identity.

**Alternative advanced feature:** speaker diarization. More computationally expensive and not necessary for approval.

---

## 8.11 Short evidence video encoding

### Recommended: FFmpeg or platform/native encoding

**Purpose:** Convert rolling camera frames into compact MP4/WebM evidence clips.

**How:**
- Keep a ring buffer of compressed or lightweight frames.
- When an event occurs, preserve pre-event frames.
- Continue collecting post-event frames.
- Encode a compact evidence clip.

**Alternative:** OpenCV `VideoWriter` for a simpler first implementation.

**MVP recommendation:** Start with OpenCV/video writer; optimise with FFmpeg only if needed.

---

## 8.12 Realtime alerts

### Recommended: WebSockets via FastAPI

**Purpose:** Notify the proctor dashboard immediately when a candidate uploads a new event.

**Data sent:** JSON event metadata, not a live webcam stream.

Example:

```json
{
  "type": "PHONE_DETECTED",
  "attempt_id": "ATT-001",
  "timestamp": "2026-10-10T10:24:51+05:30",
  "confidence": 0.91,
  "severity": "HIGH",
  "evidence_status": "UPLOADING"
}
```

**Alternative:** Server-Sent Events (SSE) if alerts only need server-to-browser communication.

---

## 8.13 Authentication

### Recommended

- Email/student ID + password for prototype.
- Password hashing using a modern library.
- Short-lived access token + refresh/session mechanism.
- RBAC enforced by backend, not only hidden UI buttons.

Roles:

```text
CANDIDATE
PROCTOR
EXAMINER
ADMIN (optional)
```

**Alternative:** University SSO/OAuth integration is future scope because it depends on institutional access/configuration.

---

## 8.14 Evidence storage

### MVP: Local backend filesystem + metadata in PostgreSQL

This keeps cost at ₹0.

Directory idea:

```text
data/evidence/<assessment_id>/<attempt_id>/<event_id>.mp4
```

Production-style alternative: S3-compatible object storage/MinIO.

**Recommended development option:** MinIO locally if the team wants to demonstrate object-storage architecture without paying for cloud storage.

---

# 9. Why no cloud GPU is needed

A webcam can generate 20-30 frames every second. Sending all of those frames from every candidate to a server and running face/object/liveness models centrally would create three problems:

1. Significant continuous network traffic.
2. High server compute requirements, potentially requiring paid GPU infrastructure.
3. Much greater privacy exposure because normal footage leaves the candidate device.

Instead, ProctorAI performs lightweight inference on the candidate computer.

```text
Candidate webcam
      |
      v
Candidate desktop app
      |
      v
LOCAL AI
 |    |    |    |
face phone person pose
      |
      v
Event generated only when necessary
      |
      v
Small JSON + short evidence clip -> backend
```

### Example normal processing

```text
face_count = 1
phone = false
candidate_present = true
head_pose = normal
```

No evidence upload is necessary.

### Example suspicious event

```text
type = PHONE_DETECTED
confidence = 0.91
time = 10:24:51
```

Only then is evidence retained and uploaded.

### Candidate hardware requirement

The MVP should target normal modern student laptops without a dedicated GPU. The exact minimum specification must be established experimentally. A reasonable initial target for testing is:

- Windows 10/11
- 8 GB RAM
- integrated webcam/microphone
- modern x64 Intel/AMD processor

Do not promise these as verified minimums until benchmarks are complete.

---

# 10. Evidence-driven recording design

## 10.1 Core principle

**Do not continuously upload normal webcam/audio footage.**

The candidate app keeps a short rolling buffer locally. If no event occurs, old frames are discarded.

### Example rolling timeline

```text
10:24:46 | 10:24:47 | 10:24:48 | 10:24:49 | 10:24:50 | 10:24:51
                                                                  ^
                                                         phone detected
```

At detection:

1. Freeze/preserve previous ~5 seconds.
2. Record next ~5 seconds.
3. Encode ~10-second clip.
4. Attach event metadata.
5. Upload to backend.
6. Securely remove expired temporary buffer data.

---

## 10.2 Adaptive duration

Some events last longer than one frame.

Example: second person remains visible for 14 seconds.

Clip can be:

```text
5 sec before + actual event + 5 sec after
```

Use a maximum cap such as 20-30 seconds to avoid unbounded files.

---

## 10.3 Which events need which evidence?

| Event | Default evidence | Why |
|---|---|---|
| Mobile phone detected | 10-sec video clip | Context matters; single frame may be misleading |
| Multiple people detected | 10-20 sec clip | Shows whether person merely passed behind candidate |
| Candidate absent | Short clip | Shows duration/context |
| Identity mismatch | Screenshot + short clip | Human can compare session context |
| Liveness challenge failure | Short clip | Shows challenge response |
| Possible still-image/presentation attack | Clip | Temporal behavior is important |
| Repeated head/gaze anomaly | Clip only after threshold | Avoid retaining every normal glance |
| Possible background speaker | Short audio clip | Human can decide whether it is relevant |
| App loses focus | Event log | Visual evidence usually unnecessary |
| Fullscreen exit | Event log | OS/app event is sufficient |
| Copy/paste attempt in restricted field | Event log | Application event is sufficient |
| Camera disabled | Event log | Device-state evidence |
| Microphone disabled | Event log | Device-state evidence |
| Monitoring engine stopped | Event log + heartbeat gap | System integrity signal |

---

# 11. Functional modules

The system intentionally has more than five meaningful modules, aligning well with the CBCA301 technical-design rubric.

## Module 1 - Authentication and Role-Based Access Control

### Features
- Login/logout.
- Candidate, Proctor, Examiner permissions.
- Optional Admin role.
- Session/token management.
- Password hashing.
- Audit trail for sensitive actions.

### Why
Prevents candidates from seeing proctor/examiner features and ensures evidence is available only to authorised users.

### Implementation
FastAPI dependencies enforce roles server-side. Frontend route guards are convenience only; backend remains authoritative.

### Alternatives
University SSO can replace local auth later.

---

## Module 2 - Assessment and Question Management

### Examiner features
- Create/edit/archive assessment.
- Title, description, date/time, duration.
- Assessment type: academic exam / placement test / interview.
- Add question sections.
- MCQ and short-answer support for MVP.
- Configure scoring.
- Add/select candidates.
- Assign proctor(s).
- Configure proctoring rules.

### Why
Makes ProctorAI a complete demonstrable assessment platform rather than only a camera detector demo.

### Alternatives
Integrate with an external LMS in future. Not needed for MVP.

---

## Module 3 - Candidate System Check and Consent

Before a monitored attempt starts:

- display monitoring/privacy notice;
- obtain explicit consent;
- check camera;
- check microphone;
- test local AI engine;
- verify sufficient application permissions;
- check backend connectivity;
- verify candidate identity/liveness if configured.

### Why
Prevents an exam from starting when monitoring components are unavailable and makes consent visible/auditable.

### Important
Provide a clear accommodation/manual-review pathway in project documentation. AI monitoring should not silently penalise candidates for disability, camera quality, network interruptions, or environmental conditions.

---

## Module 4 - Identity Verification

### Goal
Establish that the person beginning the assessment reasonably matches the enrolled candidate image/profile.

### MVP approach
- Capture enrollment/reference photo using consented test data.
- Capture live face image.
- Generate face embeddings using an appropriate local model.
- Compare similarity against a configurable threshold.
- Store only necessary result/embedding according to retention policy.

### Why
A proctored assessment needs basic identity assurance.

### Alternatives
- Manual proctor identity check.
- University identity provider integration.
- Skip biometric matching for initial MVP and use active liveness only if model integration becomes too large.

### Safety/ethics
Face matching can make mistakes. Identity mismatch should trigger **manual review**, not automatic exclusion.

---

## Module 5 - Liveness and Presentation-Attack Checks

### MVP active liveness
Random challenge examples:
- blink twice;
- turn head left;
- turn head right;
- look toward camera.

Use facial landmarks to verify that requested movement occurred within a time window.

### Passive signals
- repeated identical/frozen frames;
- no natural landmark movement for extended period;
- inconsistent motion during challenge.

### Why
Makes holding a still photograph in front of the camera harder.

### Alternatives
Dedicated anti-spoof neural model.

### Important scope decision
Advanced photo/video/deepfake anti-spoofing is a **stretch goal**. Active liveness is the MVP.

---

## Module 6 - Face Presence and Multiple-Person Monitoring

### Features
- zero faces / candidate absent;
- exactly one face = expected state;
- multiple faces = event candidate;
- debounce thresholds to avoid single-frame false alarms.

### Example rule

```text
if face_count == 0 continuously for > 5 s:
    raise FACE_ABSENT

if face_count >= 2 for > 1.5 s:
    raise MULTIPLE_PERSONS
```

Thresholds must be tuned through testing rather than assumed final.

### Why
High-value, understandable integrity signals.

---

## Module 7 - Object Detection

### MVP prohibited object
- mobile phone.

### Optional
- book;
- second laptop/tablet;
- other configurable classes.

### How
- Sample webcam frames at a controlled rate rather than every 30 FPS.
- Run a small ONNX object detector locally.
- Apply confidence threshold + persistence window.
- Trigger clip only after persistence criteria.

### Example

```text
phone confidence >= 0.70
for 3 of last 5 sampled frames
=> PHONE_DETECTED event
```

### Why
Reduces false alerts from a single misclassified frame.

### Alternative
Server-side detector - rejected for MVP due cost/bandwidth/privacy.

---

## Module 8 - Head Pose / Gaze Behavior

### MVP
Use facial landmarks to estimate approximate head orientation:
- forward;
- left/right;
- up/down.

### Rule philosophy
A normal glance is not suspicious. Only persistent/repeated patterns may create a low/medium evidence event.

Example:

```text
Looking down for 1 second -> ignore
Looking away repeatedly for configured duration -> low/medium event
```

### Why
Adds behavioral context.

### Limitation
Gaze estimation is affected by camera position, glasses, face angle, disability, reading style, and environment. It should **never be a standalone high-severity cheating indicator**.

---

## Module 9 - Blink Detection

### Approach
Use eye landmarks and an eye-closure ratio/geometry threshold to estimate blink events.

### Primary use
- active liveness challenge;
- temporal human-presence signal.

### Do not use
"Candidate did not blink enough" must **not** be treated as evidence of cheating.

---

## Module 10 - Audio Activity / Background Speech

### MVP
- microphone availability;
- voice activity periods;
- unusually sustained speech outside expected candidate behavior;
- configurable event creation.

### Evidence
Short audio segment around the trigger.

### Why
Can identify situations requiring human review, such as possible prompting from another person.

### Limitations
TV, family, traffic, roommates, accessibility tools, or noise can trigger audio events. Human review is mandatory.

### Stretch goal
Speaker diarization / multiple-speaker estimation.

---

## Module 11 - Candidate Application Integrity Monitoring

Because the candidate uses a desktop app rather than a normal website, the project should monitor **the assessment application's state**, not secretly monitor every action on the entire computer.

### MVP signals
- application loses focus;
- application minimised;
- fullscreen exited when required;
- copy/paste attempt within restricted assessment fields;
- candidate attempts to close monitoring;
- camera/microphone disabled;
- AI sidecar stops responding;
- backend heartbeat interrupted.

### Explicitly excluded
- system-wide keylogging;
- secretly capturing passwords/messages from other apps;
- unrestricted surveillance of unrelated files/processes.

### Why
This gives useful integrity signals without creating malware-like behavior.

---

## Module 12 - Rolling Buffer and Evidence Capture

### Responsibilities
- maintain pre-event video/audio buffer;
- receive event trigger;
- collect post-event context;
- encode evidence;
- generate checksum/hash;
- upload;
- clear expired normal buffer.

### Evidence metadata

```text
event_id
attempt_id
candidate_id
event_type
started_at
detected_at
ended_at
model_name/model_version
confidence
severity
clip_path
clip_sha256
client_timestamp
server_received_at
```

### Why hash evidence?
A SHA-256 checksum allows the project to demonstrate basic tamper-evidence: the system can verify that a stored clip has not changed since ingestion.

---

## Module 13 - Event Engine / Debouncing

AI models operate frame-by-frame, but users need meaningful events.

The Event Engine converts noisy detections into stable events using:
- confidence threshold;
- minimum duration;
- N-of-M frame persistence;
- cooldown window;
- event start/end state;
- duplicate suppression.

Example:

```text
Raw detections:
phone, no-phone, phone, phone, phone, no-phone

Event engine:
One PHONE_DETECTED incident, not four separate alerts.
```

---

## Module 14 - Risk / Evidence Fusion Engine

### Goal
Prioritise events for proctor review without pretending the score proves misconduct.

Example initial configurable weights (to be validated, not treated as scientific truth):

| Event | Example base weight |
|---|---:|
| App focus loss | 5 |
| Fullscreen exit | 5 |
| Repeated gaze anomaly | 5 |
| Candidate absent | 10 |
| Background speech | 10 |
| Mobile phone | 20 |
| Multiple persons | 25 |
| Liveness failure | 30 |
| Identity mismatch | 35 |
| Monitoring/tamper interruption | 20 |

### Suggested risk bands

```text
0-20   Low
21-50  Moderate
51-75  High
76-100 Critical Review Priority
```

These bands are **queue-prioritisation aids**, not guilt levels.

### Better design
Keep two concepts separate:

1. **AI Review Priority Score** - automated.
2. **Human Reviewed Status** - based on proctor decisions.

---

## Module 15 - Proctor Alert and Evidence Review Portal

### Dashboard
- current assigned assessments;
- candidate count;
- event count;
- unresolved events;
- priority queue;
- filters by severity/type/candidate;
- realtime alerts via WebSocket.

### Event review screen

```text
Candidate: C028
Event: Mobile phone detected
Time: 10:24:51
Model confidence: 0.91
AI review priority: High

[Play evidence clip]

Decision:
( ) Confirm suspicious event
( ) False positive
( ) Inconclusive

Notes: _____________________
[Save review]
```

### Why
Human oversight is central to the project's fairness and explainability.

---

## Module 16 - Examiner Portal

### Features
- create assessment;
- configure duration/window;
- add questions;
- configure integrity rules;
- add candidates;
- assign proctors;
- start/publish assessment;
- view submissions and scores;
- view reviewed integrity summary;
- inspect confirmed/inconclusive evidence;
- export/generate final report.

### Rule configuration examples

Academic exam:

```text
phone_detection = HIGH
multiple_persons = HIGH
app_focus_loss = MEDIUM
background_speech = MEDIUM
```

Remote interview:

```text
phone_detection = LOW/OFF
multiple_persons = HIGH
app_focus_loss = LOW
background_speech = HIGH
```

This avoids assuming the same behavior is forbidden in every assessment.

---

## Module 17 - Reporting

### Candidate assessment report
- attempt metadata;
- marks/score;
- start/end time;
- monitoring health;
- number of detected events;
- proctor-reviewed event counts;
- evidence links for authorised users;
- final integrity status such as "No significant reviewed events" or "Examiner review required".

### Do not output
"Cheater = true".

---

## Module 18 - Audit Logging

Track sensitive administrative actions:
- assessment created/updated;
- proctor assignment;
- evidence viewed;
- review changed;
- report generated;
- retention/deletion action.

This gives useful security and project-management depth.

---

# 12. Candidate workflow

```text
Install/open ProctorAI Candidate
        |
        v
Login
        |
        v
Select scheduled assessment
        |
        v
Read monitoring + privacy notice
        |
        v
Give consent
        |
        v
System check
(camera, mic, AI engine, network)
        |
        v
Identity verification (if enabled)
        |
        v
Active liveness challenge
        |
        v
Enter assessment mode
        |
        +--> Question answering
        |
        +--> Local AI monitoring
        |
        +--> Local rolling buffer
        |
        +--> Integrity event -> evidence clip -> upload
        |
        v
Submit assessment
        |
        v
Local temporary monitoring buffer cleaned
```

---

# 13. Proctor workflow

```text
Web login
   |
   v
Assigned active assessment
   |
   v
Event queue
   |
   +--> High priority first
   |
   v
Open event
   |
   v
Review short clip/log/audio
   |
   v
Confirm / False Positive / Inconclusive
   |
   v
Add optional note
   |
   v
Event becomes reviewed
```

The proctor is reviewing **exceptions**, not watching continuous video.

---

# 14. Examiner workflow

```text
Web login
   |
   v
Create assessment
   |
   +--> Questions
   +--> Duration
   +--> Candidates
   +--> Proctors
   +--> Integrity rules
   |
   v
Publish/schedule
   |
   v
Assessment occurs
   |
   v
Review submissions/scores
   |
   v
Review proctor-confirmed/inconclusive events
   |
   v
Generate final assessment + integrity report
```

---

# 15. Suggested database model

## users

```text
id UUID PK
email UNIQUE
student_or_employee_id nullable
name
password_hash
role ENUM(candidate, proctor, examiner, admin)
is_active
created_at
```

## assessments

```text
id UUID PK
title
description
assessment_type
created_by -> users.id
start_at
end_at
duration_minutes
status
created_at
```

## questions

```text
id UUID PK
assessment_id FK
question_type
prompt
options JSONB nullable
correct_answer JSONB nullable
marks
position
```

## assessment_candidates

```text
assessment_id FK
candidate_id FK
status
```

## assessment_proctors

```text
assessment_id FK
proctor_id FK
```

## proctoring_rules

```text
id UUID PK
assessment_id FK
event_type
enabled
severity
confidence_threshold nullable
min_duration_ms nullable
config JSONB
```

## attempts

```text
id UUID PK
assessment_id FK
candidate_id FK
started_at
submitted_at
score
monitoring_status
ai_priority_score
review_status
```

## answers

```text
id UUID PK
attempt_id FK
question_id FK
answer JSONB
marks_awarded
saved_at
```

## integrity_events

```text
id UUID PK
attempt_id FK
event_type
started_at
detected_at
ended_at
confidence nullable
severity
model_name nullable
model_version nullable
client_metadata JSONB
server_received_at
status
```

## evidence_files

```text
id UUID PK
event_id FK
media_type
storage_path
sha256
size_bytes
duration_ms nullable
created_at
retention_until
```

## event_reviews

```text
id UUID PK
event_id FK
proctor_id FK
decision ENUM(confirmed, false_positive, inconclusive)
notes
reviewed_at
```

## session_heartbeats

For the prototype, these can be sampled/aggregated rather than stored every few seconds forever.

```text
attempt_id
client_time
server_time
camera_ok
mic_ok
ai_engine_ok
app_focused
```

## audit_logs

```text
id UUID PK
actor_id
operation
entity_type
entity_id
metadata JSONB
created_at
```

---

# 16. Suggested API surface

## Authentication

```text
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

## Examiner

```text
POST   /assessments
GET    /assessments
GET    /assessments/{id}
PATCH  /assessments/{id}
POST   /assessments/{id}/questions
POST   /assessments/{id}/candidates
POST   /assessments/{id}/proctors
PUT    /assessments/{id}/rules
POST   /assessments/{id}/publish
GET    /assessments/{id}/results
GET    /attempts/{id}/integrity-report
```

## Candidate

```text
GET  /candidate/assessments
POST /attempts/start
POST /attempts/{id}/heartbeat
POST /attempts/{id}/answers
POST /attempts/{id}/events
POST /attempts/{id}/events/{event_id}/evidence
POST /attempts/{id}/submit
```

## Proctor

```text
GET  /proctor/assessments
GET  /assessments/{id}/events
GET  /events/{id}
POST /events/{id}/review
GET  /events/{id}/evidence
```

## Realtime

```text
WS /ws/proctor/assessments/{assessment_id}
```

Messages:
- NEW_EVENT
- EVIDENCE_READY
- CANDIDATE_MONITORING_INTERRUPTED
- CANDIDATE_SUBMITTED

---

# 17. Event taxonomy

Recommended initial enum:

```text
FACE_ABSENT
MULTIPLE_PERSONS
PHONE_DETECTED
GAZE_ANOMALY
LIVENESS_FAILED
POSSIBLE_PRESENTATION_ATTACK
IDENTITY_MISMATCH
BACKGROUND_SPEECH
AUDIO_ANOMALY
APP_FOCUS_LOST
FULLSCREEN_EXIT
COPY_ATTEMPT
PASTE_ATTEMPT
CAMERA_DISABLED
MICROPHONE_DISABLED
AI_ENGINE_INTERRUPTED
HEARTBEAT_GAP
NETWORK_INTERRUPTION
```

Do not implement all events on day one. The enum can exist while the MVP activates only a subset.

---

# 18. MVP definition - what must work by Milestone 2

A strong but achievable MVP should demonstrate the entire workflow with a limited set of robust detectors.

## Required MVP features

### Candidate Windows application
- Login.
- Assessment list.
- Consent screen.
- Camera/mic/system check.
- Start assessment.
- MCQ/short-answer assessment UI.
- Face presence/absence.
- Multiple-person detection.
- Mobile-phone detection.
- Basic active liveness/blink/head-turn challenge.
- Application focus/fullscreen monitoring.
- Local rolling buffer.
- Short evidence clip generation.
- Event metadata upload.
- Answer autosave.
- Submit assessment.

### Backend
- Authentication + RBAC.
- Assessments/questions/attempts.
- Event ingestion.
- Evidence upload.
- PostgreSQL persistence.
- WebSocket proctor notifications.
- Basic risk priority calculation.

### Proctor web
- Login.
- Assigned assessment.
- Realtime event queue.
- Event details.
- Play evidence clip.
- Confirm / false positive / inconclusive.
- Notes.

### Examiner web
- Login.
- Create assessment.
- Create basic questions.
- Assign candidate/proctor.
- Configure core rules.
- See candidate score.
- See reviewed integrity events/report.

## MVP AI set

**Must-have:**
1. Face absent.
2. Multiple persons/faces.
3. Phone detection.
4. Active liveness.
5. App focus/fullscreen event.

**Should-have:**
6. Head pose / repeated gaze anomaly.
7. Basic voice activity/background speech.

**Stretch:**
8. Passive anti-spoofing.
9. Deepfake detection.
10. Speaker diarization.
11. Virtual-camera detection.

---

# 19. Features intentionally excluded from MVP

## 19.1 Live streaming

**Excluded.** The proctor receives event evidence only.

Why:
- bandwidth;
- storage/streaming complexity;
- privacy;
- distracts from the AI/event-driven innovation;
- not required to demonstrate the system.

Alternative future implementation: WebRTC live stream for an individually escalated candidate.

---

## 19.2 Continuous cloud recording

**Excluded by default.**

Why:
- expensive storage;
- excessive data collection;
- harder retention/security requirements.

Alternative: local recording under institution policy or event-only evidence clips.

---

## 19.3 System-wide keylogger

**Explicitly excluded.**

Why:
- unnecessary for the project goal;
- privacy/security risk;
- resembles malicious surveillance;
- application-focus and in-app input policy is sufficient.

Use app-level copy/paste/focus monitoring instead.

---

## 19.4 Automatic cheating verdict

**Explicitly excluded.**

Why:
- AI detections are probabilistic;
- innocent behavior can resemble suspicious behavior;
- fairness and due process require human review.

Use "Potential integrity event" and "Review priority", not "Cheater".

---

# 20. Deepfake/still-image detection - realistic scope

The original idea included deepfake detection, still-image detection, blink checks, and liveness. These should be separated:

### MVP: active liveness
- blink/head-turn challenge.
- frozen-frame detection.

### Intermediate: presentation-attack detection
- photo/replay/spoof classifier if a reliable open model is found.

### Stretch: deepfake detection
Deepfake detection is a difficult research problem and may have domain-shift/false-positive issues. Include it only if the core MVP is complete.

### Approval wording

Do not promise "100% deepfake detection." Say:

> Advanced presentation-attack/deepfake analysis will be explored as an extended feature and will provide an additional risk signal rather than a standalone misconduct decision.

---

# 21. Privacy, ethics, and responsible AI

This section is essential because camera, microphone, facial analysis, and assessment decisions are sensitive.

## 21.1 Consent

Before monitoring begins, candidate must see a clear notice describing:
- camera access;
- microphone access;
- local AI analysis;
- application/session monitoring;
- what evidence may be retained;
- who can review it;
- approximate retention policy.

Record consent timestamp/version.

---

## 21.2 Data minimisation

Design principle:

> Analyse locally; upload only what is needed for review.

Normal footage should be discarded. Only event clips/logs are retained.

---

## 21.3 Human-in-the-loop

- AI detects/flags.
- Proctor reviews evidence.
- Examiner/institution makes final decision.
- False positives can be dismissed.
- AI score alone should never automatically fail a candidate.

---

## 21.4 Retention

Prototype policy example:
- temporary ring buffer: seconds only, automatically overwritten;
- unreviewed evidence: retained until assessment review;
- final evidence: deleted after a configurable demonstration retention period;
- deletion is logged.

Actual institutional deployment would require a formally approved retention policy.

---

## 21.5 Access control

- Candidate cannot access other candidates' evidence.
- Proctor can access only assigned assessments.
- Examiner can access owned/authorised assessments.
- Evidence endpoints must check authorization server-side.

---

## 21.6 Fairness and accessibility limitations

Potential issues:
- poor lighting;
- low-quality webcams;
- glasses/face coverings;
- disability or involuntary movement;
- neurodivergent behavior;
- environmental background noise;
- unstable internet;
- different skin tones or face geometries affecting model performance.

Mitigation:
- calibrate/test;
- use persistence thresholds;
- treat weak behavioral signals as low severity;
- allow human dismissal;
- include accommodations/manual review path;
- never infer emotions, honesty, personality, or mental state.

---

# 22. Security design

## Candidate -> backend
- HTTPS/TLS in deployed environment.
- Auth token scoped to current user/attempt.
- Server checks attempt ownership.
- Evidence hash recorded.
- File-size/type validation.
- Rate limits for event/evidence endpoints.

## Passwords
- Strong password hashing; never plaintext.

## Evidence
- Random/non-guessable IDs.
- Authorization required for playback.
- Avoid public evidence URLs.
- SHA-256 checksum.

## Session health
Candidate app sends periodic heartbeat:

```json
{
  "attempt_id": "...",
  "camera_ok": true,
  "mic_ok": true,
  "ai_engine_ok": true,
  "app_focused": true,
  "client_time": "..."
}
```

Missing heartbeat beyond threshold can generate `HEARTBEAT_GAP`.

## Important limitation
Local inference can theoretically be tampered with by a sophisticated attacker. The prototype can demonstrate signed builds, heartbeat, event ordering, server validation, and hashes, but does not claim enterprise-grade anti-tamper protection.

---

# 23. Offline/network-failure strategy

The assessment should not immediately fail if Wi-Fi drops.

Candidate app can:
1. keep answering locally;
2. queue answers/events/evidence securely;
3. mark network interruption;
4. retry uploads when connection returns;
5. preserve timestamps and event sequence.

MVP can implement a simple persistent local queue.

Why this matters: internet failure should not be misclassified as cheating.

---

# 24. Risk engine philosophy

Risk scoring is for **prioritisation**, not adjudication.

A useful formula for prototype:

```text
event_score = base_weight(event_type)
              * confidence_factor
              * persistence_factor
```

Candidate AI priority score can be capped at 100.

Repeated identical events should use diminishing contribution or cooldown to avoid one noisy detector creating hundreds of points.

Example:

```text
First PHONE_DETECTED event: full weight
Second within 30 seconds: merge into same incident
Later independent event: new incident
```

Human-reviewed results should be reported separately.

---

# 25. Testing and validation plan

The CBCA301 rubric strongly rewards documented test cases, validation, reproducible results, and quantitative/qualitative interpretation.

## 25.1 Unit tests

- RBAC permissions.
- Risk score calculations.
- event debouncing.
- evidence filename/hash creation.
- assessment scoring.
- API validation.

## 25.2 Integration tests

- candidate event -> backend -> WebSocket -> proctor UI.
- evidence upload -> playback.
- proctor review -> examiner report.
- candidate submission -> scoring.

## 25.3 AI validation scenarios

Create a consented/synthetic test matrix:

### Face absence
- normal seated candidate;
- candidate leaves frame 2 s;
- candidate leaves frame 10 s.

### Multiple persons
- one person;
- second person passes briefly;
- two people remain visible.

### Phone
- no phone;
- phone held clearly;
- phone partially visible;
- similarly shaped harmless object.

### Liveness
- live person passes challenge;
- printed face photo;
- still image displayed on another screen if feasible.

### Head pose
- natural short glance;
- repeated prolonged turn.

### Audio
- silence;
- candidate speaking;
- external background speech;
- fan/traffic/music.

---

## 25.4 Metrics

### Detection quality
When ground-truth scenarios are available:
- true positives;
- false positives;
- false negatives;
- precision;
- recall;
- F1 score.

### System performance
- average local inference latency;
- FPS/sample rate;
- CPU usage;
- RAM usage;
- evidence clip size;
- event-to-proctor notification latency;
- upload time;
- backend response time.

### Storage comparison
Demonstrate the benefit of event-only evidence:

```text
Continuous 60-minute recording size
vs
Total evidence size for N detected events
```

This can be one of the strongest quantitative results in the report.

---

# 26. Success criteria

The project can be considered successful if the final prototype demonstrates:

1. Three distinct roles with correct permissions.
2. Examiner can configure and publish an assessment.
3. Candidate can complete it in the Windows application.
4. At least three visual integrity detectors work locally.
5. Active liveness works in a controlled demo.
6. Application-focus/fullscreen event works.
7. Event engine avoids obvious one-frame alert spam.
8. A suspicious visual event automatically generates a short evidence clip.
9. The evidence reaches the server without live streaming.
10. Proctor receives a realtime event notification.
11. Proctor can play evidence and review it.
12. Examiner can see score + reviewed integrity report.
13. Core AI works on a normal laptop without paid cloud GPU/API.
14. Testing report contains measurable accuracy/performance results and limitations.

---

# 27. Feasibility

## 27.1 Technical feasibility

Feasible because:
- camera/mic capture is standard;
- OpenCV/MediaPipe/ONNX can run locally;
- event detection can sample frames rather than process every frame;
- short evidence clips are technically simpler than live streaming;
- FastAPI/PostgreSQL/React are established technologies;
- no requirement to train a giant model from scratch.

Main technical risks:
- Tauri/Python sidecar packaging;
- object-detection CPU performance;
- false positives;
- liveness robustness;
- video ring-buffer implementation.

Mitigations are defined below.

---

## 27.2 Economic feasibility

Target development cost: **₹0**.

Required paid products: **none**.

Use:
- local PostgreSQL;
- local FastAPI;
- open-source CV/AI libraries;
- local model inference;
- Git/GitHub free usage;
- university/team hardware.

Avoid:
- paid OpenAI/Gemini API dependency;
- AWS/Azure computer-vision APIs;
- paid cloud GPU;
- commercial deepfake API;
- mandatory custom domain;
- continuous cloud video storage.

If an online demo is desired, use only a free-tier service or run the server on a team laptop/LAN. The project should remain fully demonstrable locally if free-tier policies change.

---

## 27.3 Operational feasibility

- Candidate installs one Windows application.
- Proctor/examiner need only a browser.
- Event evidence is easier for a proctor to review than dozens of live feeds.
- Assessment-specific rules avoid one-size-fits-all proctoring.

---

## 27.4 Ethical/legal feasibility

The project handles camera/microphone/biometric-like information, so consent, minimisation, access control, retention, explainability, and human review are mandatory parts of the design.

The capstone prototype should use team members or other explicitly consenting volunteers for testing. Do not scrape or retain real applicant/student biometric data without approval.

---

# 28. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Object model too slow on CPU | High | Small model, lower input resolution, frame sampling, ONNX |
| Many false phone detections | High | confidence+persistence thresholds; dataset tests; human review |
| Tauri + Python sidecar packaging difficult | High | early spike; fallback to PySide6 |
| Deepfake detector unreliable | Medium | stretch only; not MVP dependency |
| Poor lighting affects face model | Medium | pre-exam system check/calibration; warnings |
| Background noise causes false alerts | Medium | low/medium severity; duration threshold; human review |
| Network drops during exam | High | local queue/autosave and retry |
| Evidence storage grows | Medium | short clips; retention/deletion; compression |
| Privacy concern | High | local processing, explicit consent, minimal evidence |
| Candidate tampers with client | Medium/High | heartbeat, server checks, hashes, signed build discussion; document limitation |
| Team runs out of time | High | freeze MVP; defer deepfake/speaker diarization/advanced anti-tamper |
| Model licence problem | Medium | maintain LICENSES.md; choose permissive model or comply with licence |

---

# 29. Alternatives considered

## Cloud AI processing
**Rejected for MVP.** More expensive, bandwidth-heavy, and privacy-heavy.

## Live proctor video wall
**Rejected.** Proctor reviews event evidence instead.

## Continuous video recording
**Rejected by default.** Event-driven clips are the chosen innovation.

## Pure web candidate client
**Rejected as primary.** Desktop client gives stronger control of assessment application state and local AI packaging.

## Mobile candidate app
**Removed from scope.** Avoids OS restrictions and unnecessary workload.

## Full speaker recognition
**Deferred.** VAD/background speech is sufficient for MVP.

## Deepfake as core feature
**Deferred.** Too risky to make approval/demo depend on it.

## System-wide keylogger
**Rejected.** Unnecessary and privacy-invasive.

---

# 30. Proposed team split (4-person example)

The framework allows a maximum of four according to the updated email/course tables; one sentence in the framework document says three, so the latest programme-office instruction should be treated as authoritative and clarified if needed.

## Member 1 - Candidate desktop + evidence pipeline
- Tauri shell.
- camera/mic integration.
- rolling buffer.
- evidence encoder/upload.
- app focus/fullscreen monitoring.

## Member 2 - AI/computer vision
- face presence.
- multiple persons.
- landmarks/blink/head pose.
- phone object detection.
- liveness.
- performance benchmarking.

## Member 3 - Backend/database/security
- FastAPI.
- PostgreSQL.
- auth/RBAC.
- event/evidence APIs.
- WebSocket.
- audit/report backend.

## Member 4 - Web portals + testing/reporting
- proctor UI.
- examiner UI.
- assessment/question workflow.
- test-case harness.
- metrics dashboards/report generation.

### If team has 3 members
Combine Member 4 duties into Members 1/3.

### If team has 2 members
Reduce scope: one web portal with role-based screens, only 3 core AI detectors, no audio stretch features.

---

# 31. Work breakdown and implementation phases

## Phase 0 - Repository and architecture spike
**Goal:** prove the risky pieces before building features.

- monorepo setup;
- FastAPI health endpoint;
- PostgreSQL docker-compose;
- React web login shell;
- Tauri candidate shell;
- Python AI sidecar starts/stops;
- camera frame reaches AI sidecar;
- one dummy event reaches backend;
- WebSocket alert appears on web page.

**Exit criterion:** end-to-end dummy event works.

---

## Phase 1 - Core assessment platform

- database schema/migrations;
- auth/RBAC;
- examiner creates assessment/questions;
- candidate sees assessment;
- attempt start/save/submit;
- basic scoring;
- proctor assignment.

---

## Phase 2 - Core local monitoring

- camera capture;
- face present/absent;
- multiple persons;
- app focus/fullscreen;
- monitoring heartbeat;
- raw event engine.

---

## Phase 3 - Evidence pipeline

- ring buffer;
- 5 s pre-event buffer;
- 5 s post-event capture;
- MP4/WebM output;
- event metadata;
- SHA-256;
- upload;
- evidence playback.

This is one of the project's key demonstration milestones.

---

## Phase 4 - Object detection + liveness

- phone detector;
- confidence/persistence tuning;
- blink/head-turn liveness;
- basic head pose.

---

## Phase 5 - Proctor workflow

- realtime queue;
- severity filters;
- event page;
- clip playback;
- review decision;
- notes;
- candidate summary.

---

## Phase 6 - Examiner reporting

- scores;
- reviewed event summary;
- rule configuration;
- integrity report;
- report export/print-friendly view.

---

## Phase 7 - Audio + stretch AI

Only after core is stable:
- VAD/background speech;
- passive spoof model;
- deepfake experiment;
- advanced analytics.

---

## Phase 8 - Testing, documentation, demo hardening

- reproduce test scenarios;
- benchmark CPU/RAM;
- measure detection quality;
- calculate storage savings;
- create screenshots;
- architecture/UML/DFD;
- update risk register;
- prepare live demo dataset/script.

---

# 32. CBCA301 milestone mapping

## Milestone 0 - approval
Submit:
- project title;
- problem statement;
- significance;
- stakeholders;
- T6;
- SDG 4 (+ SDG 8 if desired);
- brief proposed solution;
- expected outcome;
- team consent evidence.

## Milestone 1 - 30 marks
Prepare:
- literature/existing solutions review;
- gap analysis;
- stakeholder requirements;
- functional/non-functional requirements;
- architecture proposal;
- technology justification;
- technical/economic/operational/ethical feasibility;
- risk/mitigation table;
- scope/exclusions/limitations;
- WBS and schedule;
- success metrics.

## Milestone 2 - 30 marks
Demonstrate:
- >5 coherent modules;
- architecture/UML/DFD;
- database;
- working candidate app;
- working backend;
- proctor/examiner web;
- local AI detections;
- short evidence clip creation;
- human review flow;
- documented tests;
- quantitative performance/accuracy results;
- remaining-work statement.

## Final
- 20-30 page mini-report;
- 10-15 minute presentation;
- live demonstration;
- viva;
- each member able to explain their owned module and overall architecture.

---

# 33. Functional requirements

## Candidate
- FR-C01: Candidate shall authenticate.
- FR-C02: Candidate shall view assigned assessments.
- FR-C03: System shall display consent/privacy information before monitored attempt.
- FR-C04: System shall verify camera/microphone/AI-engine readiness.
- FR-C05: Candidate shall start assessment only within valid rules/window.
- FR-C06: Candidate shall answer and save questions.
- FR-C07: Local engine shall monitor enabled integrity signals.
- FR-C08: System shall create events using persistence/debounce rules.
- FR-C09: System shall maintain rolling pre-event buffer.
- FR-C10: System shall generate evidence clip for configured visual events.
- FR-C11: System shall upload event/evidence securely.
- FR-C12: Candidate shall submit assessment.
- FR-C13: Temporary normal footage shall be discarded according to policy.

## Proctor
- FR-P01: Proctor shall see only assigned assessments.
- FR-P02: Proctor shall receive new-event notifications.
- FR-P03: Proctor shall filter/sort event queue.
- FR-P04: Proctor shall inspect metadata/evidence.
- FR-P05: Proctor shall mark event confirmed/false-positive/inconclusive.
- FR-P06: Proctor shall add notes.

## Examiner
- FR-E01: Examiner shall create/edit assessment.
- FR-E02: Examiner shall add questions/scoring.
- FR-E03: Examiner shall configure integrity rules.
- FR-E04: Examiner shall assign candidates/proctors.
- FR-E05: Examiner shall view scores/submissions.
- FR-E06: Examiner shall view reviewed integrity report.
- FR-E07: Examiner shall access authorised evidence when needed.

---

# 34. Non-functional requirements

- **NFR-01 Privacy:** Normal footage should not leave device by default.
- **NFR-02 Cost:** Core system must run without paid API or cloud GPU.
- **NFR-03 Performance:** Candidate UI should remain responsive while AI runs.
- **NFR-04 Reliability:** Answers should autosave and tolerate temporary network loss.
- **NFR-05 Security:** Passwords hashed, authorization server-side, evidence protected.
- **NFR-06 Explainability:** Each alert must show event type/time/evidence, not only a score.
- **NFR-07 Human oversight:** No automated misconduct final decision.
- **NFR-08 Auditability:** Sensitive review/admin actions logged.
- **NFR-09 Modularity:** Detection modules independently enabled/configured.
- **NFR-10 Maintainability:** Shared event schemas and documented APIs.
- **NFR-11 Testability:** Each core detector has reproducible scenarios.
- **NFR-12 Accessibility:** Accommodations/manual handling documented for users for whom automated signals are unsuitable.

---

# 35. Proposed novelty / engineering contribution

The project should not claim that face/object detection itself is novel. The stronger engineering contribution is the **combination and architecture**:

1. **On-device multimodal AI** rather than mandatory cloud inference.
2. **Event-driven short evidence clips** rather than continuous upload.
3. **Temporary rolling buffer** that preserves pre-event context while discarding normal footage.
4. **Assessment-specific configurable integrity rules.**
5. **Multimodal event fusion and review prioritisation.**
6. **Human-in-the-loop evidence review.**
7. **Separation of Candidate desktop, Proctor review portal, and Examiner assessment portal.**
8. **Privacy/cost/scalability treated as architecture requirements.**

This is the part to emphasize during approval and viva.

---

# 36. Demo scenario for final presentation

A strong 8-10 minute demo can be scripted:

1. Examiner logs in and creates "Programming Placement Test".
2. Examiner enables phone, multiple-person, face-absence, liveness, focus-loss rules.
3. Examiner assigns Candidate A and Proctor P.
4. Candidate launches desktop app.
5. System check passes.
6. Candidate completes liveness challenge.
7. Assessment starts.
8. Candidate answers one question normally - no evidence uploaded.
9. Candidate intentionally holds phone in frame.
10. Local model detects persistent phone.
11. Rolling buffer saves 5 sec before + 5 sec after.
12. Backend receives event and clip.
13. Proctor website immediately shows high-priority alert.
14. Proctor plays clip and marks "Confirmed suspicious event".
15. Candidate triggers app focus loss; proctor receives log-only event.
16. Candidate submits.
17. Examiner opens final result and sees academic score + reviewed integrity events.
18. Show storage/performance metrics comparing event-only evidence with continuous recording.

This demonstrates the full architecture without relying on deepfake detection.

---

# 37. Coordinator questions and recommended answers

## "Is this just another proctoring website?"
No. The candidate monitoring is a Windows application performing local multimodal AI inference. The main engineering focus is event-driven evidence generation and human-reviewed integrity analytics, not a generic CRUD website.

## "Why does it need AI?"
Face/person/object/liveness/head-pose/audio signals require machine perception. Without these modules, the physical-world monitoring objective is not achievable.

## "Why T6?"
The core product architecture is built around AI inference and AI-derived events, matching T6's "systems designed around AI" description.

## "Will it spy on everything on the computer?"
No. The prototype monitors its own assessment application's focus/fullscreen state and enabled camera/microphone signals. It explicitly excludes system-wide keylogging and unrestricted surveillance.

## "Does AI decide who cheated?"
No. AI creates potential integrity events and review priority. A human proctor reviews evidence; the examiner/institution remains responsible for decisions.

## "Will you record the full exam?"
Not by default. Local normal footage is overwritten. Only short evidence segments around detected events are uploaded.

## "Do you need paid AI/cloud GPU?"
No. Models run primarily on the candidate laptop using local inference libraries. Backend and database can run locally for demonstration.

## "Is deepfake detection achievable?"
Basic active liveness is core. Advanced deepfake/presentation-attack detection is a stretch goal and will not be represented as infallible.

## "How will you evaluate it?"
Controlled test scenarios, detection metrics, false-positive analysis, inference latency, CPU/RAM measurements, evidence sizes, notification latency, and end-to-end functional tests.

---

# 38. Zero-cost development plan

## Required software - no subscription required

- Git.
- GitHub free repository or university Git service.
- VS Code.
- Node.js.
- Rust/Tauri toolchain.
- Python.
- FastAPI.
- PostgreSQL.
- React/TypeScript.
- OpenCV.
- MediaPipe/local landmark model.
- ONNX Runtime.
- FFmpeg/OpenCV encoding.
- Docker Desktop alternative if licensing/environment is a concern: PostgreSQL can run directly; Docker is not mandatory.

## Avoid paid dependencies

- OpenAI API.
- Gemini paid API dependency.
- AWS Rekognition.
- Azure Face.
- paid cloud GPU.
- paid deepfake service.
- paid object storage.
- custom domain.
- App Store/Play Store distribution.

## Demo deployment

Safest zero-cost path:
- backend + database on teammate laptop;
- candidate app on Windows laptop;
- proctor/examiner website served on LAN/local machine;
- test users on same network.

Optional free hosting is a convenience, not a project dependency.

---

# 39. Licensing checklist

Before final submission/distribution:

- keep `LICENSES.md`;
- record every third-party library/model;
- record source URL/version/licence;
- avoid redistributing a model whose licence is incompatible with the app;
- do not assume that "open weights" means unrestricted use;
- document datasets and consent.

Known examples from official sources at planning time:
- Tauri: MIT or Apache-2.0.
- OpenCV 4.5+: Apache-2.0.
- PostgreSQL: permissive PostgreSQL licence and free for academic use.

Model-specific licences must be checked when a concrete object detector/face model is selected.

---

# 40. Documentation / diagrams to create for Milestone 1 and 2

1. System context diagram.
2. Three-role use-case diagram.
3. Candidate attempt sequence diagram.
4. Integrity-event sequence diagram.
5. Evidence rolling-buffer flowchart.
6. Component/module diagram.
7. Deployment diagram.
8. ER diagram/database schema.
9. State diagram for an integrity event: raw -> detected -> evidence_ready -> reviewed.
10. DFD Level 0/1 if requested.
11. Risk matrix.
12. WBS/Gantt/timeline.
13. Test matrix.
14. AI evaluation table.
15. Privacy data-flow diagram.

---

# 41. Key states

## Assessment

```text
DRAFT -> PUBLISHED -> ACTIVE -> CLOSED -> ARCHIVED
```

## Attempt

```text
NOT_STARTED -> SYSTEM_CHECK -> IN_PROGRESS -> SUBMITTED
                              -> INTERRUPTED (recoverable)
```

## Integrity event

```text
DETECTED
   |
   v
EVIDENCE_PENDING
   |
   v
EVIDENCE_READY
   |
   v
UNREVIEWED
   |
   +--> CONFIRMED
   +--> FALSE_POSITIVE
   `--> INCONCLUSIVE
```

---

# 42. Important terminology

Use these terms consistently:

- **Potential integrity event** - preferred over "cheating detection".
- **AI confidence** - model confidence for a detection, not probability of cheating.
- **AI review priority** - automated prioritisation score.
- **Proctor review decision** - confirmed / false positive / inconclusive.
- **Evidence clip** - short retained media segment linked to event.
- **Local/on-device inference** - AI runs on candidate device.
- **Rolling buffer** - temporary bounded media history.
- **Presentation attack** - attempt to fool biometric/liveness process using photo/replay/etc.
- **Human-in-the-loop** - human reviews AI output before consequential decision.

Avoid:
- "100% cheat proof";
- "AI knows the candidate cheated";
- "emotion detection";
- "lie detection";
- "keylogger";
- "records everything".

---

# 43. Final recommended approval text - compact version

### Project Title
**AI-Native Multimodal Proctoring and Assessment Integrity Monitoring System for Remote Assessments and Interviews**

### Technology ID
**T6 - AI-Native Computing**

### Primary SDG
**SDG 4 - Quality Education**

### Secondary SDG
**SDG 8 - Decent Work and Economic Growth**

### Problem Statement
Remote examinations and online recruitment assessments face integrity challenges that are difficult to address using either continuous manual supervision or simple browser-based monitoring. Continuous video proctoring can also create high bandwidth, storage, and privacy costs. The project aims to develop an AI-native system that analyses camera, microphone, and assessment-application signals locally on the candidate's Windows device, detects potential integrity events, and stores only short evidence segments associated with those events for authorised human review.

### Proposed Solution
A Windows candidate application will perform local computer-vision/audio monitoring and maintain a temporary rolling buffer. Events such as candidate absence, multiple persons, phone detection, liveness failure, selected behavioral anomalies, application focus loss, or monitoring interruption will generate timestamped event records. Visual/audio events will retain short evidence clips, normally approximately five seconds before and five seconds after detection. A FastAPI/PostgreSQL backend will securely ingest events and notify a web-based proctor dashboard. Proctors will review evidence and classify events; examiners will create assessments, configure rules, view results, and inspect final reviewed integrity reports. The system will not require live video streaming or paid cloud AI and will not automatically determine misconduct.

### Expected Outcome
A working three-role prototype that demonstrates local multimodal AI monitoring, event-driven evidence collection, human review, assessment workflow, integrity reporting, and quantitative validation while remaining feasible on normal student hardware and zero/near-zero development budget.

---

# 44. Reference technologies / official documentation used during planning

These links are for the team to verify installation, capabilities, and licences. Always re-check model-specific licences before final distribution.

- Tauri prerequisites: https://tauri.app/start/prerequisites/
- Tauri architecture/licence: https://tauri.app/concept/architecture/
- OpenCV licence: https://opencv.org/license/
- ONNX Runtime docs: https://onnxruntime.ai/docs/
- ONNX Runtime Windows: https://onnxruntime.ai/docs/get-started/with-windows.html
- FastAPI security: https://fastapi.tiangolo.com/tutorial/security/
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- PostgreSQL: https://www.postgresql.org/about/

---

# 45. Final scope lock

Unless the capstone coordinator requests a change, the recommended project scope is:

```text
PROJECT
ProctorAI

TID
T6 - AI-Native Computing

PRIMARY CLIENT
Windows Candidate Desktop Application

WEB CLIENTS
Proctor + Examiner

MOBILE
NO

LIVE VIDEO TO PROCTOR
NO

CONTINUOUS CLOUD RECORDING
NO

CORE EVIDENCE MODEL
Short event-driven clips
~5 sec before + ~5 sec after

AI LOCATION
Primarily candidate device

PAID CLOUD GPU/API
NO

CORE AI
Face presence
Multiple persons
Phone detection
Active liveness
Head pose (basic)
App/session integrity events

SHOULD HAVE
Basic background speech/VAD

STRETCH
Passive spoof detection
Deepfake detection
Speaker diarization
Advanced anti-tamper

FINAL MISCONDUCT DECISION
Human, not AI
```

This scope is technically substantial, demonstrable, ethically more defensible than continuous surveillance, affordable for a student group, and aligned with the CBCA301 requirements for a meaningful, feasible, modular, testable capstone project.
