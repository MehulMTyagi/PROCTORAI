# Assessment participants and proctoring configuration

Assessment creation now includes candidate selection, proctor selection, and monitoring features before **Create & add questions**. Candidate and proctor lists support multiple selections, search, Select all, and Clear. Nothing is assigned automatically. An assessment with no candidates is inaccessible to candidate accounts until someone is assigned.

After creation, use **People** to add or remove participants and **Monitoring policy** to change enabled features. Saved selections reload from the API rather than resetting to a template.

## Available features

- Face monitoring: missing faces and multiple people.
- Phone detection and student identity verification.
- Microphone availability and sustained background audio signals.
- Event-based screen recording.
- Fullscreen requirement and exit signals.
- Tab/application focus changes.
- Clipboard restrictions and restricted shortcuts.
- Additional screen-capture request detection.
- Extra-display checks and heartbeat-gap monitoring.

Student identity verification is always required: the candidate checks their face against the university photo linked to their signed-in email during setup, then the local AI sidecar repeats the comparison every 60 seconds during the assessment. Two consecutive mismatches create an event for proctor review; the software does not decide misconduct. Camera and local AI access are required for identity verification. Phone detection also requires camera access. Disabled optional camera/audio/screen features do not request their device permissions or run the corresponding analysis. Basic assessment connectivity, consent, answer saving, and session health remain available.

The university admin creates student accounts from a roster CSV with roll number, name, program, admission year, and section. The API derives the university email from the roll number. Students cannot register new accounts: they request a code at their university mailbox for an account already present on the roster, then set a password to activate it. After first sign-in, they capture one JPEG photo in the app. The local AI sidecar requires exactly one visible face before saving; the API allows one enrollment per account and rejects candidate attempts to replace it. This locks the account to that capture but does not establish that the person captured is the real-world student; mailbox verification links activation to the university email, and an institution or proctor check is needed for stronger identity assurance.

The admin-only `POST /users/import-roster` endpoint accepts UTF-8 CSV files with `roll_number,full_name,program,admission_year,section` columns. The same roster can be safely re-imported to refresh names and cohort fields. `/users` supports filters for program, admission year, and section so examiners can choose the students in the groups they teach.

Admins can also import university photos using a CSV manifest with `email,photo_path` columns and JPEG/PNG files beside the CSV or in its subfolders. Run `python -m app.db.import_identity_references path/to/students.csv` from `services/api` after database migrations. It links photos to existing candidate accounts by exact normalized email. This initial import format remains available as an alternative while the university's actual roster/export format is unknown.

Identity images are stored as separate files under `IDENTITY_REFERENCE_DIR`; the database stores only the candidate link, file key, and hash. The current local-folder storage is suitable for the capstone/demo. For 10,000 students, plan roughly 1–3 GB if each 640×480 JPEG averages 100–300 KB (the API caps enrollment uploads at 1 MB, or 10 GB worst case before backups). A deployed system should use private object storage with backups and access controls, while keeping the file key and hash in the database.

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
- Enabling only phone detection restored the camera setup requirement while leaving screen, microphone, devices, and fullscreen requirements off. Continuation remained blocked until camera and identity checks passed.
- Creation, participant editing, and policy editing passed axe WCAG 2 A/AA scans at 390 and 1440 pixels with no detected violations or horizontal overflow.

Local screenshots and browser scripts are in ignored `output/playwright/`, including `assignment-creation-390.png`, `assignment-creation-1440.png`, and `assignment-minimal-setup.png`. The verification assessment was closed afterward; its submitted attempt remains as test data.
