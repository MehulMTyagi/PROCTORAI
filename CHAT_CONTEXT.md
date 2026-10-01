# ProctorAI Chat Context

Last updated: 2026-10-01

## Standing Instruction

Keep this file updated whenever project direction, milestone status, setup steps, verification results, running services, or important implementation decisions change.

Use this file as the quick handoff context for future Codex work in this repository.

## Project

ProctorAI is a BCA Semester V capstone project for an AI-native, privacy-aware remote assessment and interview integrity system.

Core architecture:

- Candidate desktop app: Tauri 2, React, TypeScript.
- Web portal: React, TypeScript, Vite, shared examiner/proctor role switch.
- Backend API: FastAPI, SQLAlchemy, Alembic. Reliable local mode uses SQLite; hosted/production mode can use PostgreSQL.
- AI sidecar: local-only FastAPI service using OpenCV.
- Evidence model: event-driven, privacy-aware evidence capture. Normal camera/audio should stay local unless an integrity event requires evidence.

Important source documents:

- `ProctorAI_Codex_Context.md`
- `ProctorAI_Capstone_Master_Spec.md`
- `PROJECT_COMPLETION_PLAN.md`

## Current Milestone Status

Completed:

- Week 1: repository skeleton, Docker/PostgreSQL, FastAPI foundation, migrations, core schema, auth, seed users, backend tests.
- Week 2: dummy integrity-event ingestion, WebSocket alerts, candidate shell, proctor event queue, Tauri scaffold.
- Week 3: examiner assessment setup, questions, assignments, rules, candidate attempt runner, answer save, submit, basic MCQ scoring.
- Week 4: consent gate, readiness checks, heartbeats, focus/fullscreen/heartbeat-gap events, retry queue, proctor high-priority visibility.
- Week 5: local AI sidecar, OpenCV face counting, debounced `FACE_ABSENT` and `MULTIPLE_PERSONS` candidates, candidate sidecar integration, face-event demos, proctor visibility.
- Week 6: protected evidence upload/download, SHA-256 verification, candidate rolling media buffer, pre/post clips, evidence status transitions, proctor playback.
- Week 7: duplicate-suppressed YOLO phone events, sidecar-verified randomized active liveness setup with motion fallback, `LIVENESS_FAILED` event path with proof/evidence.

Next:

- Week 8: proctor review workflow and examiner reporting.

## Local Services

Expected development URLs:

- API: `http://127.0.0.1:8010`
- AI engine: `http://127.0.0.1:8765`
- Web portal: `http://127.0.0.1:5173`
- Candidate runner: `http://127.0.0.1:5174`

Reliable local commands:

- Start everything: `npm run local:start`
- Stop everything: `npm run local:stop`
- Check health/login/assessment loading: `npm run local:check`
- Local SQLite DB: `services/api/data/proctorai-local.db`
- Runtime logs: `data/logs`

Docker/PostgreSQL:

- No longer required for local development.
- PostgreSQL service name, when available: `proctorai-postgres`

Seed users:

- `candidate@example.com / password123`
- `proctor@example.com / password123`
- `examiner@example.com / password123`

## Latest Stabilization Pass

2026-10-01 reliable local mode:

- User reported the current setup was unreliable with recurring service errors.
- Switched local development to a SQLite-first runner instead of relying on Docker/PostgreSQL availability.
- Added:
  - `scripts/start-local.ps1`
  - `scripts/stop-local.ps1`
  - `scripts/check-local.ps1`
  - root npm scripts `local:start`, `local:stop`, and `local:check`
- `npm run local:start` clears the known ports, migrates/seeds SQLite, launches API, AI sidecar, web portal, and candidate portal with fixed env vars, then runs smoke checks.
- Keep using ports:
  - API `8010`
  - AI `8765`
  - Web `5173`
  - Candidate `5174`

2026-10-01 local connection fix:

- Candidate showed "Unable to connect to your assessment service" while all local services were healthy.
- Root cause: web and candidate frontends defaulted `VITE_API_BASE_URL` to `http://127.0.0.1:8000`, but the active ProctorAI API runs on `http://127.0.0.1:8010` because port `8000` may be occupied by another local FastAPI app.
- Updated both frontend defaults and `.env.example` to use `http://127.0.0.1:8010`.
- Docker/PostgreSQL was unavailable, so the local API was restarted against SQLite:
  - `DATABASE_URL=sqlite+pysqlite:///C:/git/PROCTORAI/services/api/data/proctorai-local.db`
  - ran `python -m alembic upgrade head`
  - ran `python -m app.db.seed`
- Verified candidate login and assigned assessment loading through `http://127.0.0.1:8010`.
- Local live health checks passed for API `8010`, AI `8765`, web `5173`, and candidate `5174`.

2026-09-20 liveness reliability pass:

- Fixed false failures in the active liveness setup by adding frame-to-frame motion scoring to the AI sidecar verifier.
- Candidate preflight now captures ten frames over roughly three seconds per prompt so users have enough time to blink or turn slowly.
- Candidate liveness preview now explicitly reattaches the already-approved camera stream when the liveness step renders.
- `/verify-liveness` still prefers direct evidence from eye-state changes, face-center movement, and profile-face cues, but can pass real webcam variance with lower-confidence motion fallback when those detectors miss.
- Verification:
  - `python -m pytest services/ai-engine/tests -q` -> `10 passed`
  - `npm run build:candidate` -> passed
  - `python -m pytest services/api/tests -q` -> `35 passed`
  - `npm run build:web` -> passed
  - `cargo check` in `apps/candidate-desktop/src-tauri` -> passed
  - Restarted local AI sidecar on `http://127.0.0.1:8765`.
  - Live health checks passed for API `8010`, AI `8765`, web `5173`, and candidate `5174`.
  - Live `/verify-liveness` motion-fallback smoke returned `passed=true`.

2026-09-20 Week 7 completion:

- Hardened phone detection:
  - still uses local AI sidecar YOLO;
  - requires two consecutive phone-like samples;
  - suppresses repeat `PHONE_DETECTED` events while the phone remains active;
  - clears active phone state after three no-phone samples.
- Added active liveness setup:
  - new preflight `Liveness` step;
  - randomized blink / left / right prompts;
  - ten-frame, roughly three-second local burst capture for each prompt;
  - AI sidecar `/verify-liveness` validation;
  - one-face ratio, blink eye-state change, directional turn checks, and motion fallback for normal webcam variance;
  - start remains blocked until liveness passes.
- Added `LIVENESS_FAILED` event path with proof/evidence support through the Week 6 rolling clip pipeline.
- Updated seeded/default rules for `PHONE_DETECTED` and `LIVENESS_FAILED`.
- Verification:
  - `python -m pytest services/api/tests -q` -> `35 passed`
  - `python -m pytest services/ai-engine/tests -q` -> `10 passed`
  - `npm run build:candidate` -> passed
  - `npm run build:web` -> passed
  - `cargo check` in `apps/candidate-desktop/src-tauri` -> passed
  - `python -m pytest services/api/tests/test_seed.py services/api/tests/test_events.py -q` -> `14 passed`
  - Local demo seed refreshed with Week 7 rules.
  - Local live health checks passed for API `8010`, AI `8765`, web `5173`, and candidate `5174`.
  - Restarted the local AI sidecar and confirmed `/health` reports `opencv-active-liveness`.
  - Live `/verify-liveness` smoke returned `passed=true`.

2026-09-20 Week 6 completion:

- Implemented the rolling evidence pipeline:
  - candidate keeps a bounded local `MediaRecorder` buffer from the camera stream;
  - clip-worthy events create `PENDING` evidence first;
  - candidate waits for post-roll, builds a local WebM clip, hashes it with SHA-256, and uploads it;
  - API verifies the hash, stores the file under `evidence_dir`, persists metadata, and marks the event `READY`;
  - failed clip generation/upload marks the event `FAILED` with failure metadata.
- Added protected API routes:
  - `POST /attempts/{attempt_id}/events/{event_id}/evidence`;
  - `POST /attempts/{attempt_id}/events/{event_id}/evidence/failure`;
  - `GET /proctor/events/{event_id}/evidence/{evidence_id}`.
- Extended proctor event responses with `evidence_files`.
- Proctor portal now fetches protected evidence with the bearer token and renders video playback plus clip metadata/hash preview.
- Added `python-multipart` to API dependencies.
- Added `docs/capstone/week-6-checkpoint.md`.
- Verification:
  - `python -m pytest services/api/tests -q` -> `35 passed`
  - `python -m pytest services/api/tests/test_events.py -q` -> `12 passed`
  - `python -m pytest services/ai-engine/tests -q` -> `7 passed`
  - `npm run build:web` -> passed
  - `npm run build:candidate` -> passed
  - `cargo check` in `apps/candidate-desktop/src-tauri` -> passed
  - Local live health checks passed for API `8010`, AI `8765`, web `5173`, and candidate `5174`.
  - Local evidence smoke created a `FACE_ABSENT` event, uploaded hashed evidence, and downloaded it as proctor.

2026-09-20 Week 5 close-out refresh:

- Confirmed Week 5 is complete with the current implementation:
  - local AI sidecar;
  - OpenCV face counting;
  - debounced `FACE_ABSENT` and `MULTIPLE_PERSONS`;
  - YOLO `PHONE_DETECTED` object detection;
  - candidate camera/microphone integrity events with review proof metadata;
  - proctor visibility for AI-derived and proof-backed events.
- Updated `docs/capstone/week-5-checkpoint.md` and README verification counts.
- Verification:
  - `python -m pytest services/api/tests -q` -> `32 passed`
  - `python -m pytest services/ai-engine/tests -q` -> `7 passed`
  - `npm run build:web` -> passed
  - `npm run build:candidate` -> passed
  - `cargo check` in `apps/candidate-desktop/src-tauri` -> passed
  - Local live checks passed for API `8010`, AI `8765`, web `5173`, and candidate `5174`.

2026-09-20 deployed portal connectivity repair:

- User reported both portals still disconnected:
  - Candidate showed `Unable to connect to your assessment service`.
  - Web/proctor portal showed `Failed to fetch`.
- Root cause was the backend data path, not the React bundles:
  - Local API `/health` can run without a database, but `/auth/login` hung when Docker/PostgreSQL was unavailable.
  - Docker Desktop UI processes were present, but the Docker engine / `dockerDesktopLinuxEngine` pipe was unavailable and the shell could not start `com.docker.service` without elevated Windows permissions.
- Restored the public demo by running the API against a seeded local SQLite DB:
  - Demo DB: `output/proctorai-demo-live.db`
  - Runtime `DATABASE_URL`: `sqlite+pysqlite:///C:/git/PROCTORAI/output/proctorai-demo-live.db`
  - API process: `http://127.0.0.1:8010`
  - AI/YOLO sidecar process: `http://127.0.0.1:8765`
- Replaced flaky LocalTunnel URLs with Cloudflare quick tunnels:
  - API: `https://covered-partial-raised-fifteen.trycloudflare.com`
  - AI sidecar: `https://settlement-issues-iso-observed.trycloudflare.com`
- Redeployed production Vercel aliases with those URLs:
  - Web/proctor portal: `https://web-portal-six-kappa.vercel.app`
  - Candidate portal: `https://candidate-desktop.vercel.app`
- Verification:
  - Public API health returned OK through the Cloudflare API tunnel.
  - Public AI health returned OK through the Cloudflare AI tunnel and reported `ultralytics-yolo`.
  - Browser-style CORS preflight passed for `https://candidate-desktop.vercel.app`.
  - Public API login and candidate assessment listing passed through the tunnel.
  - Public AI `/detect-objects` smoke returned a `PHONE_DETECTED` event candidate with `detector=ultralytics-yolo`.
  - Public candidate-to-proctor event smoke created a `PHONE_DETECTED` event through the API tunnel; proctor listing saw the same event with `evidence_status=READY` and `detector=ultralytics-yolo`.
- Important limitation: Cloudflare quick tunnels and the SQLite demo DB are still local-machine dependent. If this machine, the API/AI processes, or tunnel processes stop, the deployed portals will go offline again. Durable multi-device use still needs a hosted API and managed Postgres.

2026-09-15 YOLO phone detection migration:

- User requested YOLO after COCO-SSD browser detection was too weak for phone detection.
- Implemented local AI sidecar object detection with Ultralytics YOLO:
  - Added `YoloObjectDetector` in `services/ai-engine/app/vision.py`.
  - Added `POST /detect-objects` with `DetectObjectsRequest` / `DetectObjectsResponse`.
  - Default model path is `yolov8n.pt`; it can be overridden with `YOLO_MODEL_PATH`.
  - `PHONE_DETECTED` candidates are returned for phone-like classes (`cell phone`, `remote` by default).
- Candidate portal now sends camera snapshots to the local AI sidecar `/detect-objects` endpoint instead of loading TensorFlow.js/COCO-SSD in the browser.
- Removed TensorFlow.js and COCO-SSD dependencies from the candidate package.
- Restarted the local AI sidecar on `http://127.0.0.1:8765`; YOLO warmed up successfully and reported model version `8.4.30`.
- Current public tunnels:
  - API: `https://wicked-mayfly-44.loca.lt`
  - AI sidecar: `https://gentle-deer-46.loca.lt`
- Verification:
  - `python -m pytest services/ai-engine/tests -q` -> `7 passed`
  - `python -m pytest services/api/tests/test_events.py -q` -> `9 passed`
  - `npm run build:candidate` -> passed
  - `npm run build:web` -> passed
  - Public AI tunnel smoke: `POST https://tricky-moose-59.loca.lt/detect-objects` returned a `PHONE_DETECTED` candidate with `detector=ultralytics-yolo`.
  - Public API smoke: created a `PHONE_DETECTED` integrity event and proctor listing returned `evidence_status=READY` with `detector=ultralytics-yolo`.
  - Redeployed candidate production alias: `https://candidate-desktop.vercel.app`.

2026-09-15 local monitoring availability fix:

- User reported the candidate System page still showed: "Local monitoring is unavailable. Start the monitoring service and retry."
- Checks showed the local YOLO sidecar was healthy, but public LocalTunnel URLs had changed/expired and CORS was too narrow for generated Vercel deployment URLs.
- Fix:
  - Added `allow_origin_regex` support to the API CORS middleware, defaulting to `https://.*\.vercel\.app`.
  - Added `CORS_ORIGIN_REGEX` support to the AI sidecar CORS middleware, defaulting to `https://.*\.vercel\.app`.
  - Increased candidate sidecar health-check timeout from 8 seconds to 20 seconds and surfaced the actual health-check error in the System page detail.
  - Restarted local API on `http://127.0.0.1:8010` and AI sidecar on `http://127.0.0.1:8765`.
  - Started fresh LocalTunnel URLs:
    - API: `https://wicked-mayfly-44.loca.lt`
    - AI sidecar: `https://gentle-deer-46.loca.lt`
  - Redeployed both production aliases against the fresh tunnels:
    - Web portal: `https://web-portal-six-kappa.vercel.app`
    - Candidate portal: `https://candidate-desktop.vercel.app`
- Verification:
  - `python -m pytest services/ai-engine/tests -q` -> `7 passed`
  - `python -m pytest services/api/tests/test_events.py -q` -> `9 passed`
  - `npm run build:candidate` -> passed
  - `npm run build:web` -> passed
  - Public API health returned OK through `https://wicked-mayfly-44.loca.lt`.
  - Public AI/YOLO health returned OK through `https://gentle-deer-46.loca.lt`.
  - Browser-style CORS preflight passed for both `https://candidate-desktop.vercel.app` and the generated Vercel deployment origin.

2026-09-14 real-time camera/microphone integrity events:

- Candidate monitoring now emits additional integrity events during the active attempt, before submission:
  - `CAMERA_DISABLED` when the camera stream cannot start, is muted, or ends/disconnects.
  - `MICROPHONE_DISABLED` when the microphone stream cannot start, is muted, or ends/disconnects.
  - `BACKGROUND_SPEECH` when the browser microphone monitor detects sustained audio/noise above threshold.
  - `AI_ENGINE_INTERRUPTED` when sidecar frame analysis fails during monitoring.
  - `PHONE_DETECTED` when the YOLO object detector finds a phone-like object in the camera frame.
- Background voice/noise detection is currently a Web Audio RMS-level heuristic for MVP review, not speaker identification or transcription.
- Phone detection now uses the local YOLO sidecar path. It sends the event immediately with the current camera proof frame, score, bounding box, and detector metadata.
- Proctor rules JSON now includes `BACKGROUND_SPEECH`, `PHONE_DETECTED`, and `AI_ENGINE_INTERRUPTED`.
- Proctor dashboard shows `polling` as a healthy fallback state when WebSocket is unavailable but the 5-second event poll is still loading events.
- Examiner-created assessments are now automatically assigned to the default seeded candidate and proctor, and the proctor dashboard includes an assessment queue selector so events from newly created tests are visible.
- Verification:
  - `python -m pytest services/api/tests/test_events.py -q` -> `9 passed`
  - `npm run build:candidate` -> passed
  - `npm run build:web` -> passed
  - Redeployed production Vercel aliases:
    - Web portal: `https://web-portal-six-kappa.vercel.app`
    - Candidate portal: `https://candidate-desktop.vercel.app`
  - Live public API smoke through `https://wicked-duck-66.loca.lt` created a `PHONE_DETECTED` event and the proctor event listing returned `evidence_status=READY` with `detector=coco_ssd_lite_mobilenet_v2`.

2026-09-14 phone detection sensitivity fix:

- Superseded on 2026-09-15 by the YOLO sidecar implementation above.
- Candidate phone detection was hardened after live testing showed phones were not being detected reliably.
- Changes:
  - lowered COCO-SSD object detection threshold from `0.35` to `0.18`;
  - scans every 2 seconds instead of every 4 seconds;
  - treats `remote` as phone-like because COCO-SSD often misclassifies phones as remotes;
  - requires 2 consecutive phone-like samples before sending `PHONE_DETECTED` to reduce accidental false positives;
  - shows top detector labels/scores in the candidate object monitor for debugging.
- Verification:
  - `npm run build:candidate` -> passed
  - `python -m pytest services/api/tests/test_events.py -q` -> `9 passed`
  - Restarted API LocalTunnel on `https://wicked-duck-66.loca.lt` after it returned `503`.
  - Redeployed the candidate production alias: `https://candidate-desktop.vercel.app`.

2026-09-14 proctoring visibility regression fix:

- User reported that "all the proctoring is gone" after the phone-detection iteration.
- Root causes found:
  - The public API LocalTunnel was again returning `503`, which breaks deployed portal authentication, assessment loading, heartbeats, and event delivery.
  - Candidate camera/object monitoring was coupled to `sidecarReady`, so if the face sidecar was pending or flaky the camera stream and browser phone detector could fail to start.
- Fix:
  - Restarted the API LocalTunnel; LocalTunnel could not reclaim `https://wicked-duck-66.loca.lt`, so the then-current API tunnel became `https://friendly-owl-32.loca.lt`.
  - Candidate camera stream now starts whenever an attempt is active and browser media APIs are available; face analysis still requires the sidecar, but camera-disabled events and object/phone detection no longer depend on `sidecarReady`.
  - Candidate status grid now shows the real face/camera monitor state instead of forcing `Pending` whenever the sidecar is unavailable.
- Verification:
  - `npm run build:candidate` -> passed
  - `python -m pytest services/api/tests/test_events.py -q` -> `9 passed`
  - API tunnel health check returned `{"status":"ok","service":"ProctorAI API","version":"0.1.0"}` for `https://friendly-owl-32.loca.lt`.
  - Redeployed both production aliases against the new API tunnel:
    - Web portal: `https://web-portal-six-kappa.vercel.app`
    - Candidate portal: `https://candidate-desktop.vercel.app`
  - Public API smoke through `https://friendly-owl-32.loca.lt` created an `APP_FOCUS_LOST` event and the proctor event listing returned `evidence_status=READY`.

2026-09-14 automatic integrity proof for proctor review:

- Candidate automatic integrity events now attach a proof bundle in event metadata and set `evidence_status` to `READY`.
- Proof bundle includes:
  - proof kind (`CAMERA_SNAPSHOT` when a frame is available, otherwise `SESSION_LOG`);
  - capture timestamp;
  - fullscreen/page visibility state;
  - viewport size;
  - camera snapshot data URL when available;
  - SHA-256 hash of the attached snapshot data URL;
  - a proctor-facing review note.
- AI face events (`FACE_ABSENT`, `MULTIPLE_PERSONS`) include face count, sidecar model info, sample count, and the frame that triggered the AI analysis when available.
- Browser/session events (`FULLSCREEN_EXIT`, `APP_FOCUS_LOST`, `HEARTBEAT_GAP`) include proof context and use a camera snapshot when the sampler has a current frame.
- Proctor portal now watches the selected assigned assessment instead of always watching the seeded dev assessment.
- Proctor portal keeps a 5-second polling fallback so events still arrive even when the WebSocket badge is offline or LocalTunnel is unreliable.
- Proctor event queue now renders a proof review block with snapshot image, proof type, review note, capture time, fullscreen/page state, and SHA-256 preview.
- Regression and verification:
  - `python -m pytest services/api/tests/test_events.py -q` -> `8 passed`
  - `npm run build:candidate` -> passed
  - `npm run build:web` -> passed
  - Redeployed production Vercel aliases.
  - Live API smoke created a `FACE_ABSENT` event with `evidence_status=READY`; proctor listing returned `proof.kind=CAMERA_SNAPSHOT`.
  - Live Playwright smoke confirmed the deployed proctor UI renders `FACE ABSENT`, `CAMERA SNAPSHOT`, and the proof review note.
- This is reviewable proof embedded in event metadata for the public demo. The larger Week 6 protected evidence-file pipeline with durable media storage, clip hashing, playback authorization, retention, and cleanup remains the next hardening step.

2026-09-14 Vercel/tunnel demo:

- Closed the unrelated IP-SAKTI FastAPI process that was occupying local port `8000`; `8000` was then free.
- Vercel account is authenticated as `mehulmtyagi`.
- Deployed the examiner/proctor web portal to Vercel:
  - `https://web-portal-six-kappa.vercel.app`
  - Deployment URL: `https://web-portal-drpyk5iqf-mehul-tyagis-projects.vercel.app`
- Deployed the candidate portal to Vercel:
  - `https://candidate-desktop.vercel.app`
  - Deployment URL: `https://candidate-desktop-7bupdkdpw-mehul-tyagis-projects.vercel.app`
- The deployed portals are currently wired to temporary public LocalTunnel URLs:
  - ProctorAI API tunnel: `https://wicked-mayfly-44.loca.lt`
  - AI sidecar tunnel: `https://gentle-deer-46.loca.lt`
- Local services backing those tunnels must stay running on this machine:
  - API: `http://127.0.0.1:8010`
  - AI sidecar: `http://127.0.0.1:8765`
- Added `.vercelignore` files so Vercel does not upload local `node_modules`, `dist`, or Tauri/Rust build output.
- Updated the AI sidecar CORS setup to read `CORS_ORIGINS` from the environment.
- Restarted the local API and AI services with demo CORS so Vercel-hosted browsers can call them.
- Public API smoke through the tunnel passed:
  - examiner login;
  - active assessment creation;
  - MCQ creation;
  - candidate assignment;
  - candidate assessment listing;
  - attempt start;
  - answer save;
  - submit with score `5 / 5`.
- Important limitation: this is a working public demo path, not a durable cloud backend. If the local machine, local API/AI processes, or LocalTunnel sessions stop, the deployed portals will stop sharing data. A permanent multi-device deployment still needs a hosted backend plus cloud Postgres, or equivalent managed storage.

2026-09-14 tunnel recovery and candidate system-check fix:

- Previous API tunnel `https://social-melons-camp.loca.lt` started returning `503`, while the local API on `http://127.0.0.1:8010` was still healthy.
- Started fresh LocalTunnel sessions:
  - API: `https://wicked-duck-66.loca.lt`
  - AI sidecar: `https://tricky-moose-59.loca.lt`
- Redeployed production Vercel aliases with the fresh tunnel URLs:
  - `https://web-portal-six-kappa.vercel.app`
  - `https://candidate-desktop.vercel.app`
- Candidate System requirements initially still failed Local monitoring because the AI sidecar health check timeout was only `1200ms`; tunnel requests often take `2-3s`.
- Increased the candidate AI sidecar health timeout to `8000ms`.
- Rebuilt and redeployed candidate production alias.
- Live Playwright browser smoke passed:
  - web portal loaded without `Failed to fetch`;
  - created an assessment;
  - added MCQ;
  - assigned `Dev Candidate`;
  - proctor page loaded without `Failed to fetch`;
  - candidate portal found the assessment;
  - candidate System requirements passed both Assessment connection and Local monitoring.
- Reason the portals go offline often: the current deployment still depends on free LocalTunnel sessions from this laptop. Tunnels can drop, URLs can change, and latency can spike. A stable multi-device setup requires hosting `services/api` on a durable backend and using cloud Postgres instead of tunneling the local machine.

2026-09-14 Vercel portal connection bug fix:

- Fixed deployed portals receiving LocalTunnel's browser warning HTML (`Tunnel website ahead`) instead of API JSON.
- Added the `bypass-tunnel-reminder: 1` header to:
  - web portal API fetches;
  - candidate portal API fetches;
  - candidate portal AI sidecar health and frame-analysis fetches.
- Verified browser CORS preflight accepts the new custom header through both tunnels.
- Rebuilt locally:
  - `npm run build:web` -> passed
  - `npm run build:candidate` -> passed
- Redeployed both production Vercel domains:
  - web portal alias updated: `https://web-portal-six-kappa.vercel.app`
  - candidate portal alias updated: `https://candidate-desktop.vercel.app`
- Live browser smoke with Playwright passed on the deployed domains:
  - web portal loaded without LocalTunnel HTML;
  - created a unique assessment;
  - added an MCQ;
  - assigned `Dev Candidate`;
  - candidate portal loaded the same assessment title from the shared tunneled backend.

2026-09-14 assignment/create-access verification:

- Targeted API regression tests passed for assessment creation, question creation, candidate/proctor assignment, candidate assessment listing, attempt start, answer save, heartbeat rules, and submit:
  - `python -m pytest services/api/tests/test_assessments.py services/api/tests/test_attempts.py -q` -> `12 passed`
- Live API smoke passed against a disposable ProctorAI API on `http://127.0.0.1:8010` using a timestamped SQLite database:
  - examiner login succeeded;
  - examiner created an active assessment;
  - examiner added an MCQ;
  - examiner assigned `candidate@example.com`;
  - candidate list included the new assessment;
  - candidate detail returned the question;
  - candidate started an attempt;
  - candidate saved the selected option;
  - candidate submitted with score `5 / 5`.
- Local demo services currently started for this verification:
  - ProctorAI API: `http://127.0.0.1:8010`
  - AI sidecar: `http://127.0.0.1:8765`
  - Web portal pointed at API 8010: `http://127.0.0.1:5175`
  - Candidate portal pointed at API 8010 and AI 8765: `http://127.0.0.1:5176/#/assessments`
- Port `8000` is currently occupied by a different local FastAPI app whose OpenAPI paths are `/ask` and `/patent-check`. The default frontend ports `5173` and `5174` may therefore fail backend actions unless ProctorAI API is actually running on `8000` or the frontends are started with `VITE_API_BASE_URL=http://127.0.0.1:8010`.

2026-09-14 multi-page candidate setup:

- Reworked the candidate portal into a routed preflight journey:
  - `#/assessments` assessment selection.
  - `#/consent` monitoring/privacy notice.
  - `#/system` backend API and local AI sidecar checks.
  - `#/camera` real camera permission check with live local preview.
  - `#/microphone` real microphone permission check with input meter.
  - `#/review` final readiness review, fullscreen, and start.
  - `#/exam` active assessment.
  - `#/submitted` submitted-answer receipt.
- Direct URL changes cannot bypass incomplete setup requirements. Active attempts force the route back to the exam/submitted screen so answer state is not discarded.
- Start now revalidates fullscreen, backend health, and sidecar health immediately before creating an attempt.
- Consent acceptance time and consent version are included in candidate heartbeat metrics for audit context.
- Camera and microphone checks use live `getUserMedia` streams, invalidate on permission revoke/device disconnect, and stop tracks when consent is revoked or setup is left.
- The preflight gate is a candidate-side readiness gate only; backend authorization and attempt state remain the source of truth.
- Browser verification covered desktop, mobile, landscape, denied permissions, service failures, retry recovery, route clamping, fullscreen gating, stale health revalidation, answer save, submit, and reload behavior using Playwright with mocked API/AI responses and fake media devices.
- Candidate frontend build passed after the new flow.
- Real API/Postgres and AI sidecar are currently offline in this shell because Docker Desktop did not expose the `dockerDesktopLinuxEngine` pipe after launch.

2026-09-13 candidate run:

- Candidate runner dev server started with `npm --workspace @proctorai/candidate-desktop run dev`.
- Candidate runner URL `http://127.0.0.1:5174` returned HTTP 200.
- Login, attempt loading, event sync, and AI sidecar checks still require the API/Postgres stack and AI engine to be running.

2026-09-12 web run:

- Web portal dev server started with `npm --workspace @proctorai/web-portal run dev`.
- Web portal URL `http://127.0.0.1:5173` returned HTTP 200.
- Backend-powered portal data still requires the API/Postgres stack to be running.

2026-09-12:

- Fixed examiner ownership authorization for assessment listing, assessment detail, assessment update, question creation, candidate/proctor assignment, rule updates, and examiner event queue access.
- Added regression tests proving examiners cannot list/manage another examiner's assessments or inspect another examiner's event queue.
- Fixed candidate retry behavior so non-retriable API errors surface as errors instead of being queued forever.
- Fixed candidate retry status so failed queue flushes no longer leave the app claiming it is ready.
- Updated candidate answer sync to merge saved answer responses back into attempt state.
- Improved portal assignment/create/question/rule actions with in-flight disabling and visible success/error feedback.
- Verification after fixes:
  - API tests: `python -m pytest` in `services/api` -> `30 passed`
  - AI sidecar tests: `python -m pytest` in `services/ai-engine` -> `5 passed`
  - Web portal build: `npm run build:web` -> passed
  - Candidate frontend build: `npm run build:candidate` -> passed
  - Tauri scaffold: `cargo check` in `apps/candidate-desktop/src-tauri` -> passed
- Live Postgres-backed smoke could not be rerun in this shell because Docker Desktop's Windows service `com.docker.service` is stopped and Windows refused `Start-Service` without elevated permissions.

## Verification Baseline

Most recent full Week 5 live verification, rerun after the interrupted Week 5 close-out on 2026-09-10:

- API tests: `python -m pytest` in `services/api` -> `27 passed` at that time; latest suite is `30 passed`
- AI sidecar tests: `python -m pytest` in `services/ai-engine` -> `5 passed`
- Web portal build: `npm run build:web` -> passed
- Candidate frontend build: `npm run build:candidate` -> passed
- Tauri scaffold: `cargo check` in `apps/candidate-desktop/src-tauri` -> passed
- API health: `http://127.0.0.1:8000/health` -> ok
- AI engine health: `http://127.0.0.1:8765/health` -> ok
- Web portal dev URL: `http://127.0.0.1:5173` -> HTTP 200
- Candidate runner dev URL: `http://127.0.0.1:5174` -> HTTP 200

Browser smoke covered:

- Candidate readiness sees the AI sidecar as reachable.
- Candidate starts an attempt after consent and checks.
- Face Absent demo creates `FACE_ABSENT` after three samples.
- Multiple People demo creates `MULTIPLE_PERSONS` after two samples.
- Proctor queue shows both AI-derived events and counts high-priority events.

## Implementation Notes

- The repo has no initial commit yet, so `git status --short` reports the whole tree as untracked.
- Use `rg`/`rg --files` for searches.
- Use `apply_patch` for manual file edits.
- Do not revert user changes unless explicitly requested.
- Keep UI operational and dashboard-like, not marketing-style.
- Use Lucide icons for controls.
- Keep evidence/risk wording as review support, not automatic misconduct verdicts.
- The current token helper is a local foundation and should be reviewed or replaced before production-style deployment.
- The AI sidecar uses OpenCV Haar cascade detection, which is CPU-friendly and zero-cost but has known accuracy limits.
- Week 5 evidence is still log-only; media clips start in Week 6.
- When starting frontend dev servers from the repo root, prefer direct workspace commands:
  - `npm --workspace @proctorai/web-portal run dev`
  - `npm --workspace @proctorai/candidate-desktop run dev`
  Passing `--host` through the root script can add an extra positional argument and make Vite return 404 at `/`.

## Files Added Or Heavily Updated So Far

- `README.md`
- `PROJECT_COMPLETION_PLAN.md`
- `docs/capstone/week-1-checkpoint.md`
- `docs/capstone/week-2-checkpoint.md`
- `docs/capstone/week-3-checkpoint.md`
- `docs/capstone/week-4-checkpoint.md`
- `docs/capstone/week-5-checkpoint.md`
- `services/api`
- `services/ai-engine`
- `apps/web-portal`
- `apps/candidate-desktop`

## Update Checklist

When continuing this project, update this file if any of these change:

- milestone completion status;
- next task;
- local setup commands or service ports;
- test/build verification counts;
- seed users or demo data;
- major implementation decisions;
- known risks or limitations.
