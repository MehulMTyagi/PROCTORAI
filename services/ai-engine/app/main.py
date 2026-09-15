import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.debounce import FaceEventDebouncer
from app.schemas import (
    AnalyzeFrameRequest,
    AnalyzeFrameResponse,
    DetectObjectsRequest,
    DetectObjectsResponse,
    DetectedObject,
    ModelInfo,
    ObjectEventCandidate,
    utc_now,
)
from app.vision import OpenCvFaceDetector, YoloObjectDetector

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
object_detector = YoloObjectDetector()
debouncer = FaceEventDebouncer()


def model_info() -> ModelInfo:
    info = detector.info
    return ModelInfo(
        name=info.name,
        version=info.version,
        detector=info.detector,
        cascade_path=info.cascade_path,
    )


def object_model_info() -> ModelInfo:
    info = object_detector.info
    return ModelInfo(
        name=info.name,
        version=info.version,
        detector=info.detector,
        model_path=info.model_path,
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "ProctorAI AI Engine",
        "version": "0.1.0",
        "model": model_info().model_dump(),
        "object_model": object_model_info().model_dump(),
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


@app.post("/detect-objects", response_model=DetectObjectsResponse)
def detect_objects(payload: DetectObjectsRequest) -> DetectObjectsResponse:
    try:
        objects = (
            payload.observed_objects
            if payload.observed_objects is not None
            else [
                DetectedObject(
                    class_name=item.class_name,
                    confidence=item.confidence,
                    bbox=item.bbox,
                    phone_like=item.phone_like,
                )
                for item in object_detector.detect_objects(
                    payload.frame_data_url or "",
                    min_confidence=payload.config.min_confidence,
                    max_detections=payload.config.max_detections,
                    phone_like_classes=set(payload.config.phone_like_classes),
                )
            ]
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"YOLO object detection unavailable: {exc}") from exc

    phone_like_objects = [item for item in objects if item.phone_like]
    events = [
        ObjectEventCandidate(
            event_type="PHONE_DETECTED",
            severity="HIGH",
            confidence=phone_like_objects[0].confidence,
            priority_score=9,
            metadata={
                "object_type": phone_like_objects[0].class_name,
                "bbox": phone_like_objects[0].bbox,
                "detector": object_model_info().detector,
                "model": object_model_info().model_dump(),
            },
        )
    ] if phone_like_objects else []

    return DetectObjectsResponse(
        session_id=payload.session_id,
        captured_at=payload.captured_at,
        processed_at=utc_now(),
        objects=objects,
        phone_like_objects=phone_like_objects,
        events=events,
        model=object_model_info(),
    )
