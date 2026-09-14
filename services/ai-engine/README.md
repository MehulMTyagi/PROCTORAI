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

`POST /analyze-frame` accepts a low-resolution frame data URL from the candidate app or an `observed_face_count` test/demo override. It returns the current face count, debounced monitoring state, and event candidates such as `FACE_ABSENT` and `MULTIPLE_PERSONS`.

The sidecar is intended to bind only to `127.0.0.1`. Raw camera frames stay on the candidate device and are sent only to this local process, not to the backend.

## Verification

```powershell
python -m pytest
```

Current tests cover health reporting, absent-face debounce, multiple-person debounce, normal-face reset behavior, and blank-frame decoding.
