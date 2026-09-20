# Week 7 Checkpoint

Date: 2026-09-20

## Completed

- Hardened phone detection behavior:
  - YOLO phone/object detection still runs through the local sidecar;
  - candidate requires two consecutive phone-like samples before sending `PHONE_DETECTED`;
  - duplicate phone spam is suppressed while the phone remains active;
  - the active phone state clears only after three no-phone samples.
- Added active liveness setup:
  - new preflight `Liveness` step between microphone and review;
  - randomized blink / left / right challenge order;
  - live local camera preview;
  - local frame capture for each prompt;
  - challenge passes only when captured frames change across prompts;
  - assessment start remains blocked until liveness passes.
- Added liveness event path:
  - `LIVENESS_FAILED` included in candidate monitoring controls;
  - failed liveness events use the same proof/evidence clip pipeline as other visual integrity events.
- Updated default proctoring rules:
  - `PHONE_DETECTED`;
  - `LIVENESS_FAILED`.
- Updated candidate consent copy to reflect event-driven short evidence clips.

## Verified

```text
Full backend tests: 35 passed
AI sidecar tests: 7 passed
Candidate frontend build: passed
Web portal build: passed
Tauri cargo check: passed
Seed + event backend tests: 14 passed
Local API/AI/web/candidate health checks: passed
Local demo seed refreshed with Week 7 rules
```

## Notes

- The active liveness challenge is an MVP browser implementation based on randomized prompts and changing local camera frames.
- It does not yet perform robust blink landmark detection or head-pose estimation.
- `LIVENESS_FAILED` events are review signals, not automatic misconduct verdicts.
- Evidence clips for `LIVENESS_FAILED` use the Week 6 rolling evidence pipeline.

## Next Step

Start Week 8 proctor review and examiner reporting:

1. Add stored review decisions for events.
2. Add proctor notes and review status filters.
3. Show event details with evidence playback and immutable event metadata.
4. Add examiner score/integrity summary report.
5. Add audit logging around review changes.
