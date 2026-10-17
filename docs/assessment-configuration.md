# Assessment participants and proctoring configuration

Assessment creation now includes candidate selection, proctor selection, and monitoring features before **Create & add questions**. Candidate and proctor lists support multiple selections, search, Select all, and Clear. Nothing is assigned automatically. An assessment with no candidates is inaccessible to candidate accounts until someone is assigned.

After creation, use **People** to add or remove participants and **Monitoring policy** to change enabled features. Saved selections reload from the API rather than resetting to a template.

## Available features

- Face monitoring: missing faces and multiple people.
- Phone detection and liveness verification.
- Microphone availability and sustained background audio signals.
- Event-based screen recording.
- Fullscreen requirement and exit signals.
- Tab/application focus changes.
- Clipboard restrictions and restricted shortcuts.
- Additional screen-capture request detection.
- Extra-display checks and heartbeat-gap monitoring.

Phone detection and liveness require camera access even with face monitoring disabled. Camera availability and AI interruption signals follow the camera-based features. Disabled camera/audio/screen features do not request those device permissions or run the corresponding analysis. Setup omits checks that are not required. Basic assessment connectivity, consent, answer saving, and session health remain available.

## API behavior

`POST /assessments` accepts `candidate_ids`, `proctor_ids`, and `rules` alongside the existing assessment fields. The API validates account roles before creating anything, then saves the assessment, assignments, and policy in one database transaction.

`GET /assessments/{id}` returns saved `rules`. Authorized examiners/admins also receive `candidate_ids` and `proctor_ids`; participant lists are not disclosed to candidates or proctors. Candidate/proctor list and detail access remains limited to their assigned assessments.

`PUT /assessments/{id}/assignments` replaces both assignment lists. Only the owning examiner or an admin can change them. Existing single-person assignment endpoints remain compatible. `PUT /assessments/{id}/rules` continues to save the policy.

The candidate honors individual rule `enabled` flags. Disabled signals are also rejected by API event ingestion, and screen-evidence uploads are rejected when screen recording is disabled. Missing keys retain the previous enabled behavior for legacy assessments. No database schema migration was needed.

## Verification — 17 October 2026

- API suite: **41 passed**, including four configuration tests for selected-only access, persistence, role validation without partial creation, participant replacement, policy edit authorization, disabled events, and disabled screen uploads.
- Both production frontend builds pass, as do unused-symbol TypeScript checks.
- `node --experimental-strip-types scripts/check-proctoring-policy.mjs` verifies disabled checks, camera/AI dependencies, and legacy defaults.
- Real browser/API verification created an assessment with explicit participant selections and all 12 feature controls off, then reloaded its People and Monitoring policy pages. Assignment removal/addition and policy changes persisted across reloads.
- With monitoring disabled, candidate setup contained only Consent, System connection, and Final review. There were **zero media/device requests, zero AI-sidecar requests, zero integrity events**, clipboard actions were allowed, and the saved answer submitted with **5/5**. Device access was instrumented to fail if requested; this was not an AI-accuracy test.
- Enabling only phone detection restored the camera setup requirement while leaving screen, microphone, devices, liveness, and fullscreen requirements off. Continuation remained blocked until the camera check passed.
- Creation, participant editing, and policy editing passed axe WCAG 2 A/AA scans at 390 and 1440 pixels with no detected violations or horizontal overflow.

Local screenshots and browser scripts are in ignored `output/playwright/`, including `assignment-creation-390.png`, `assignment-creation-1440.png`, and `assignment-minimal-setup.png`. The verification assessment was closed afterward; its submitted attempt remains as test data.
