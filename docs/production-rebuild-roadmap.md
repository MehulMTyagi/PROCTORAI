# ProctorAI Production Rebuild Roadmap

Last updated: 2026-10-06

## Source Strategy

The two reference repositories are useful for architecture and feature inspiration, but not direct source copying. Neither local clone includes a root `LICENSE` file, so ProctorAI should rebuild equivalent behavior in its own code unless explicit permission or compatible licensing is confirmed.

Reference usage:

- `moodle-proctor`: use as the stronger production architecture reference.
- `AI-Interview-Cheating-Detection`: use as a lightweight UX/event-model reference.

## Target Architecture

Production ProctorAI should use a central durable backend as the connection hub:

```text
Candidate portal / desktop app
  -> authenticated API events, answers, heartbeats, evidence
  -> local or hosted AI analysis
  -> durable backend + PostgreSQL
  -> WebSocket/SSE proctor stream
  -> proctor dashboard review queue
```

The candidate and proctor portals should never depend on laptop tunnels for real use. Tunnels are acceptable only for demos.

## Inspired Patterns To Adopt

From `moodle-proctor`:

- Room/session model for live exams.
- Central backend for auth, attempts, rooms, violations/events, and monitoring state.
- PostgreSQL-backed persistence.
- WebSocket/SSE push channel for live proctor events.
- Optional WebRTC/mediasoup-style live stream for proctor viewing.
- FastAPI/WebSocket AI service that can analyze browser-streamed frames.
- Strictness presets and per-exam proctoring policy configuration.
- Teacher/proctor dashboard with alert review.

From `AI-Interview-Cheating-Detection`:

- Rolling risk score.
- 30-second signal timeline.
- Browser integrity events: focus/tab, clipboard, audio, screen/camera signals.
- CSV export.
- Compact proctor dashboard summary metrics.

## Current ProctorAI Position

Already aligned:

- Separate candidate and proctor portals.
- FastAPI backend with auth, assessments, attempts, answers, events, heartbeats, evidence, and WebSocket alerts.
- Local AI sidecar for face/phone/liveness.
- Event proof bundles and rolling evidence clips.
- Live proctor event queue with polling fallback.
- Risk score and browser-integrity events started on 2026-10-06.

Main production gaps:

- Local SQLite is for development only.
- Public Vercel portals previously depended on local tunnels.
- Evidence storage is local filesystem, not cloud object storage.
- WebSocket manager is in-memory, so it does not scale across multiple API instances.
- No durable proctor review decision workflow yet.
- No production secrets management, deployment observability, or audit export.
- AI sidecar availability depends on local machine for browser-only demos.

## Production Workstreams

### 1. Deployment Foundation

- Host API on a durable service.
- Use managed PostgreSQL.
- Use managed object storage for evidence files.
- Keep candidate and web portal as static deployments.
- Remove laptop tunnel dependency from all production env vars.
- Add deploy-time environment validation.

Acceptance:

- Candidate and proctor portals work from two different devices while this development machine is off.
- Health check, login, assessment load, event send, event receive, evidence upload, and evidence download pass against hosted services.

### 2. Realtime Reliability

- Keep WebSocket for live proctoring.
- Add SSE fallback for proctor event stream, inspired by Moodle-Proctor.
- Add Redis/Postgres pub-sub or an event bus so broadcasts work across multiple API workers.
- Keep polling as last-resort fallback.

Acceptance:

- Proctor receives candidate integrity events within 2 seconds in normal network conditions.
- Events still appear after WebSocket disconnect/reconnect.
- Running more than one API instance does not lose broadcasts.

### 3. Room And Session Model

- Add exam rooms with room codes.
- Track candidate room joins/leaves.
- Track session device, browser, IP, and heartbeat state.
- Support room-level live monitoring dashboard.

Acceptance:

- Examiner creates a room for an assessment.
- Candidate joins the room from assigned account/link.
- Proctor sees active candidates, current state, and event counts per candidate.

### 4. Proctor Review Workflow

- Persist decisions: unreviewed, reviewed-valid, reviewed-dismissed, escalated.
- Add notes, reviewer id, reviewer timestamp.
- Preserve original event metadata and evidence hashes.
- Add final attempt integrity report.

Acceptance:

- Proctor can review an event, attach a decision, and later export a report.
- Candidate score and integrity review are separate.

### 5. Evidence And Privacy

- Move evidence from local disk to object storage.
- Use signed URLs or authenticated proxy downloads.
- Add retention policy enforcement.
- Add evidence encryption-at-rest through provider settings.
- Add candidate consent and privacy copy per assessment.

Acceptance:

- Evidence remains inaccessible without an authorized proctor/examiner token.
- Expired evidence is cleaned or blocked according to retention policy.

### 6. AI And Proctoring Quality

- Keep YOLO for phone/object detection.
- Keep liveness checks, but add calibrated thresholds and human-review language.
- Add strictness profiles: lenient, moderate, strict.
- Add detector health telemetry.
- Add false-positive controls and confidence display.

Acceptance:

- Proctor sees detector name, confidence, threshold, and proof for every AI event.
- Candidate is not auto-failed solely by an AI signal.

### 7. Security

- Enforce strong production secrets.
- Restrict CORS to exact deployed origins.
- Add API rate limiting.
- Add audit logs for privileged actions.
- Add secure headers.
- Add input validation for all public routes.

Acceptance:

- Production app refuses to boot with default secrets.
- Auth, event creation, evidence access, and review actions are covered by role tests.

### 8. Testing And Verification

- Keep unit/integration tests for API and AI.
- Add Playwright cross-portal smoke tests.
- Add production-like hosted smoke script.
- Add evidence integrity tests.
- Add browser-permission failure tests.

Acceptance:

- One command verifies API, AI, web, candidate, event flow, evidence flow, and proctor live updates.

## Immediate Next Implementation Order

1. Add proctor review decisions and report export.
2. Add SSE fallback alongside WebSocket.
3. Add room/session model.
4. Replace local evidence storage with configurable object storage adapter.
5. Add production deployment env docs and hosted smoke scripts.
6. Add Redis/Postgres broadcast adapter for multi-instance realtime.

