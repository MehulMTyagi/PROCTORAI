import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.debounce import FaceEventDebouncer
from app.schemas import AnalyzeFrameRequest, AnalyzeFrameResponse, ModelInfo, utc_now
from app.vision import OpenCvFaceDetector

app = FastAPI(title="ProctorAI AI Engine", version="0.1.0")
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = OpenCvFaceDetector()
debouncer = FaceEventDebouncer()


def model_info() -> ModelInfo:
    info = detector.info
    return ModelInfo(
        name=info.name,
        version=info.version,
        detector=info.detector,
        cascade_path=info.cascade_path,
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "ProctorAI AI Engine",
        "version": "0.1.0",
        "model": model_info().model_dump(),
    }


@app.post("/analyze-frame", response_model=AnalyzeFrameResponse)
def analyze_frame(payload: AnalyzeFrameRequest) -> AnalyzeFrameResponse:
    try:
        face_count = (
            payload.observed_face_count
            if payload.observed_face_count is not None
            else detector.count_faces(payload.frame_data_url or "", payload.config.min_face_size_px)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    model = model_info()
    state, events = debouncer.update(
        session_id=payload.session_id,
        face_count=face_count,
        captured_at=payload.captured_at,
        config=payload.config,
        model=model,
    )
    return AnalyzeFrameResponse(
        session_id=payload.session_id,
        captured_at=payload.captured_at,
        processed_at=utc_now(),
        face_count=face_count,
        state=state,
        events=events,
        model=model,
    )
