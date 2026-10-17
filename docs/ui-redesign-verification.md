# Multipage UI redesign — 17 October 2026

The examiner, proctor, and candidate clients now use a consistent responsive interface: Inter typography, navy navigation, blue actions, readable status colors, keyboard focus styles, loading and empty states, and reduced-motion support. Navigation uses hash routes, so direct links and browser Back/Forward work on the existing Vite servers without server rewrite configuration.

## Pages

| Workspace | Pages |
| --- | --- |
| Examiner | Overview, searchable assessments, new assessment, assessment details, question builder, people assignments, monitoring policy, help |
| Proctor | Overview, live event monitoring, evidence review with notes/history, reports and CSV export, help |
| Candidate | Dashboard, searchable assessments, preparation/help, eight separate setup steps, exam runner, submission receipt |

Examiner/proctor entry: `http://127.0.0.1:5173/#/examiner/overview` and `#/proctor/monitoring`. Candidate entry: `http://127.0.0.1:5174/#/dashboard`.

The pages use the API and actual assessment/event data. The proctor interface does not invent live webcam feeds or candidate attendance counts. The existing development-only exam diagnostics are excluded from production builds. The subsequent [assessment configuration update](assessment-configuration.md) adds saved candidate/proctor selections and policies during creation, plus setup/monitoring behavior driven by enabled features. Setup now shows only the enabled requirements, up to eight steps.

## Verification performed

- Both production frontend builds pass. Both TypeScript projects also pass `--noUnusedLocals --noUnusedParameters`.
- Tested 12 examiner/proctor routes on desktop. The responsive sweep covered seven admin routes and four candidate routes at 390, 768, and 1440 pixels: 33 route/viewport combinations, no page-level horizontal overflow, no JavaScript page exceptions, and no detected axe WCAG 2 A/AA violations after corrections. This is an automated scan, not a formal accessibility certification.
- Tested mobile navigation opening/closing, keyboard focus containment, Escape restoring the menu trigger, and browser Back/Forward. Closed mobile navigation is inert; opening it makes the background inert.
- Created assessments through the actual forms (`201`), added editable MCQ options/correct answer (`201`), and saved assessment details (`200`).
- Candidate consent, denied screen/camera permissions, an extra display signal, and fullscreen gating block continuation. Previous navigation preserves completed checks; jumping ahead by URL redirects to the first incomplete step.
- Started/resumed a real attempt, saved answer B through the API, generated a real clipboard event, uploaded screen evidence (`201`), played it in the proctor interface, and saved a false-positive decision plus note (`201`). The playable uploaded clip had finite duration 13.549 seconds and no media error.
- Submission confirmation can be cancelled. Final submission returned score **5/5**, and the receipt displayed the saved answer.
- Verified submitting immediately after a new event waits for its evidence upload: response order was **evidence 201 → submit 200**. This prevents closing an attempt before its pending media is stored.
- Exported an actual CSV report; checked its header and event rows. Tested a search with no matches, a simulated `503` assessment response, and successful reconnect.
- Updated the existing transitive `source-map-js` dependency to its patched release; `npm audit` reports zero vulnerabilities.

Browser media devices and the liveness verification response were simulated for repeatable UI testing. Assessment, attempt, answer, event, evidence, review, and submission requests used the real local API/database. These checks do not measure AI accuracy or verify native camera permission dialogs. The two assessments created for verification were closed afterward, retaining their test evidence and results.

## Reliability fixes found during UI testing

1. SQLite timestamps without an offset represent UTC. The clients now parse those correctly, fixing an exam that appeared expired immediately in the Asia/Calcutta timezone. Regression check: `node --experimental-strip-types scripts/check-ui-time.mjs`.
2. Arbitrary slices of a long WebM recording can lose the initialization header. The candidate now records bounded, staggered complete segments, retains each segment's header, and finalizes duration metadata. Only segments selected by an event are uploaded. After warmup, clips include 5–10 seconds before the signal and at least 5 seconds after it; early signals include the available lead-in. Media timestamps reflect actual recording boundaries.
3. Submission drains pending event and evidence work before closing the attempt. New signals are paused during final submission.
4. Evidence selection remains stable when new live events arrive. Older invalid saved clips show a playback error and retain their download link.

Recorder regression check, with the candidate server running and a Playwright CLI session open on port 5174:

```powershell
npx --yes --package @playwright/cli playwright-cli -s=candidateui run-code --filename=scripts/browser/check-evidence-recorder.js
```

It records beyond a segment rotation, then verifies a decodable clip, finite duration, and pre/post coverage. The measured run produced a playable 11.518-second clip with 6,514 ms pre-roll and 5,004 ms post-roll.

## Review artifacts

Local screenshots and browser scripts are under ignored `output/playwright/`, including `final-admin-examiner-overview-1440.png`, `final-candidate-dashboard-1440.png`, their 390-pixel variants, `question-builder-desktop.png`, `proctor-evidence-review-desktop.png`, and `final-submission-desktop.png`.

## Deployment boundary

This work improves the UI and verified local workflows. Existing seed-account auto-login/role switching remains development infrastructure. Production identity/session management, native Tauri/device testing, security review, and deployment configuration remain separate project work. No deployment was performed and the experimental scratch-trained model was not changed.
