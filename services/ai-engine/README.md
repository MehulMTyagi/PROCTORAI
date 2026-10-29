# ProctorAI AI Engine

Local-only FastAPI sidecar for candidate-device monitoring.

## Local Setup

From `services/ai-engine`:

```powershell
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

## Current API Surface

- `GET /health`
- `POST /analyze-frame`
- `POST /detect-objects`
- `POST /verify-liveness`
- `POST /verify-identity`

`POST /analyze-frame` accepts a low-resolution frame data URL from the candidate app or an `observed_face_count` test/demo override. It returns the current face count, debounced monitoring state, and event candidates such as `FACE_ABSENT` and `MULTIPLE_PERSONS`.

`POST /detect-objects` accepts a low-resolution frame data URL from the candidate app or an `observed_objects` test/demo override. It runs the Ultralytics YOLO object detector (`yolov8n.pt` by default) and returns detections plus `PHONE_DETECTED` event candidates for phone-like classes. For each phone-like YOLO box, the scratch-trained `PhoneCropCNN-v1` classifies that crop as `cell_phone` or `other_object`; its label and raw score are attached to the event for the proctor as a second opinion. The CNN never suppresses a YOLO event or makes a misconduct decision. The score is not calibrated probability, and current held-out precision is modest. The checkpoint is bundled under `app/model_artifacts/phone-classifier/` and checksum-verified on first use. Set `YOLO_MODEL_PATH` to use a different full-frame detector.

`POST /verify-liveness` accepts randomized prompt samples for `BLINK`, `TURN_LEFT`, and `TURN_RIGHT`. Each prompt can include a short burst of frame data URLs from the candidate app or deterministic observed signals for tests. The sidecar verifies one-face presence, blink eye-state change, directional turn evidence, and frame-to-frame motion using OpenCV face, eye, and profile cascades plus motion scoring. Motion fallback keeps real webcam checks usable when Haar eye/profile detection misses an otherwise valid live movement.

`POST /verify-identity` compares exactly one face in a live frame with exactly one face in the signed-in candidate's university reference photo. It uses OpenCV Zoo's pretrained YuNet detector and SFace recognizer; their model files and license notices are in `models/face-identity/`. The default cosine threshold (`0.363`) follows the OpenCV Zoo example and must be calibrated against the university's real camera and photo data before high-stakes use. A mismatch is a review signal, not an automatic misconduct decision.

The sidecar is intended to bind only to `127.0.0.1`. Live camera frames are sent to this local process, not to the backend. The API serves the signed-in candidate's reference image with private, no-store caching; the candidate app holds it in memory for comparisons. Only a mismatch snapshot and review metadata are sent to the backend as an integrity event.

## Verification

```powershell
python -m pytest
```

Current tests cover health reporting, absent-face debounce, multiple-person debounce, normal-face reset behavior, blank-frame decoding, YOLO object-event response shaping, identity matching outcomes, liveness pass/fail verification, and liveness motion fallback.
