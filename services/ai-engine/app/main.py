import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.debounce import FaceEventDebouncer
from app.face_identity import FaceIdentityVerifier
from app.schemas import (
    AnalyzeFrameRequest,
    AnalyzeFrameResponse,
    DetectedObject,
    DetectObjectsRequest,
    DetectObjectsResponse,
    LivenessPromptResult,
    ModelInfo,
    ObjectEventCandidate,
    VerifyIdentityRequest,
    VerifyIdentityResponse,
    VerifyLivenessRequest,
    VerifyLivenessResponse,
    utc_now,
)
from app.vision import (
    LivenessFrameSignals,
    OpenCvFaceDetector,
    OpenCvLivenessVerifier,
    YoloObjectDetector,
)

APP_ENV = os.getenv("APP_ENV", "development").lower()
app = FastAPI(
    title="ProctorAI AI Engine",
    version="0.1.0",
    docs_url=None if APP_ENV in {"production", "prod"} else "/docs",
    redoc_url=None if APP_ENV in {"production", "prod"} else "/redoc",
    openapi_url=None if APP_ENV in {"production", "prod"} else "/openapi.json",
)
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "AI_CORS_ORIGINS",
        "http://localhost:5174,http://127.0.0.1:5174,tauri://localhost,http://tauri.localhost",
    ).split(",")
    if origin.strip()
]
cors_origin_regex = os.getenv("AI_CORS_ORIGIN_REGEX")
trusted_hosts = [
    host.strip()
    for host in os.getenv(
        "AI_TRUSTED_HOSTS", "localhost,127.0.0.1,tauri.localhost,testserver"
    ).split(",")
    if host.strip()
]
if APP_ENV in {"production", "prod"} and (
    not cors_origins
    or any(
        not (
            origin.startswith("https://")
            or origin in {"tauri://localhost", "http://tauri.localhost"}
        )
        or "*" in origin
        for origin in cors_origins
    )
    or cors_origin_regex
    or not trusted_hosts
    or "*" in trusted_hosts
):
    raise RuntimeError(
        "Production AI service requires exact HTTPS AI_CORS_ORIGINS and AI_TRUSTED_HOSTS"
    )
IDENTITY_THRESHOLD = float(os.getenv("IDENTITY_SIMILARITY_THRESHOLD", "0.363"))
if not 0.1 <= IDENTITY_THRESHOLD <= 0.9:
    raise RuntimeError("IDENTITY_SIMILARITY_THRESHOLD must be between 0.1 and 0.9")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

detector = OpenCvFaceDetector()
object_detector = YoloObjectDetector()
liveness_verifier = OpenCvLivenessVerifier()
identity_verifier = FaceIdentityVerifier()
debouncer = FaceEventDebouncer()


def model_info() -> ModelInfo:
    info = detector.info
    return ModelInfo(
        name=info.name,
        version=info.version,
        detector=info.detector,
        cascade_path=None,
    )


def object_model_info() -> ModelInfo:
    info = object_detector.info
    return ModelInfo(
        name=info.name,
        version=info.version,
        detector=info.detector,
        model_path=None,
    )


def liveness_model_info() -> ModelInfo:
    info = liveness_verifier.info
    return ModelInfo(
        name=info.name,
        version=info.version,
        detector=info.detector,
        cascade_path=None,
        model_path=None,
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "ProctorAI AI Engine",
        "version": "0.1.0",
        "model": model_info().model_dump(),
        "object_model": object_model_info().model_dump(),
        "liveness_model": liveness_model_info().model_dump(),
    }


@app.post("/analyze-frame", response_model=AnalyzeFrameResponse)
def analyze_frame(payload: AnalyzeFrameRequest) -> AnalyzeFrameResponse:
    if APP_ENV in {"production", "prod"} and payload.observed_face_count is not None:
        raise HTTPException(status_code=400, detail="Observed test signals are disabled")
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
    if APP_ENV in {"production", "prod"} and payload.observed_objects is not None:
        raise HTTPException(status_code=400, detail="Observed test signals are disabled")
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
                    scratch_classifier=item.scratch_classifier,
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
        logging.getLogger(__name__).exception("YOLO object detection failed")
        raise HTTPException(
            status_code=503, detail="YOLO object detection is unavailable"
        ) from exc

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
                "scratch_classifier": (
                    phone_like_objects[0].scratch_classifier.model_dump()
                    if phone_like_objects[0].scratch_classifier
                    else None
                ),
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


def _signals_from_observed(observed) -> list[LivenessFrameSignals]:
    sample_count = max(
        len(observed.face_counts),
        len(observed.eye_counts),
        len(observed.face_center_offsets),
        len(observed.motion_scores),
        len(observed.upper_motion_scores),
        1,
    )
    signals: list[LivenessFrameSignals] = []
    for index in range(sample_count):
        signals.append(
            LivenessFrameSignals(
                face_count=observed.face_counts[index] if index < len(observed.face_counts) else 1,
                eye_count=observed.eye_counts[index] if index < len(observed.eye_counts) else 0,
                face_center_offset=(
                    observed.face_center_offsets[index]
                    if index < len(observed.face_center_offsets)
                    else None
                ),
                profile_left_seen=observed.profile_left_seen,
                profile_right_seen=observed.profile_right_seen,
                motion_score=observed.motion_scores[index] if index < len(observed.motion_scores) else 0.0,
                upper_motion_score=(
                    observed.upper_motion_scores[index] if index < len(observed.upper_motion_scores) else 0.0
                ),
            )
        )
    return signals


def _mode(values: list[int]) -> int:
    if not values:
        return 0
    return max(set(values), key=values.count)


def _evaluate_liveness_prompt(prompt: str, signals: list[LivenessFrameSignals], config) -> LivenessPromptResult:
    face_counts = [signal.face_count for signal in signals]
    eye_counts = [signal.eye_count for signal in signals]
    offsets = [signal.face_center_offset for signal in signals if signal.face_center_offset is not None]
    motion_scores = [signal.motion_score for signal in signals]
    upper_motion_scores = [signal.upper_motion_score for signal in signals]
    single_face_ratio = sum(1 for count in face_counts if count == 1) / max(len(face_counts), 1)
    any_face_ratio = sum(1 for count in face_counts if count >= 1) / max(len(face_counts), 1)
    one_face_ok = single_face_ratio >= config.min_single_face_ratio
    enough_samples = len(signals) >= config.min_samples_per_prompt
    max_motion = max(motion_scores or [0.0])
    max_upper_motion = max(upper_motion_scores or [0.0])
    offset_span = (max(offsets) - min(offsets)) if len(offsets) > 1 else 0.0
    reasons: list[str] = []
    if not enough_samples:
        reasons.append("too_few_samples")
    if not one_face_ok:
        reasons.append("single_face_ratio_low")

    action_passed = False
    action_confidence = 0.0
    evidence = {
        "sample_count": len(signals),
        "single_face_ratio": round(single_face_ratio, 3),
        "any_face_ratio": round(any_face_ratio, 3),
        "eye_counts": eye_counts,
        "face_center_offsets": [round(value, 4) for value in offsets],
        "max_motion_score": round(max_motion, 4),
        "max_upper_motion_score": round(max_upper_motion, 4),
        "offset_span": round(offset_span, 4),
        "profile_left_seen": any(signal.profile_left_seen for signal in signals),
        "profile_right_seen": any(signal.profile_right_seen for signal in signals),
    }

    if prompt == "BLINK":
        has_open = max(eye_counts or [0]) >= config.min_eye_open_count
        has_closed = min(eye_counts or [0]) == 0
        motion_blink = max_upper_motion >= config.min_blink_motion_score and any_face_ratio >= config.min_single_face_ratio
        action_passed = (has_open and has_closed) or motion_blink
        action_confidence = (
            0.95 if has_open and has_closed else
            0.72 if motion_blink else
            0.35 if has_open or has_closed else
            0.1
        )
        evidence["motion_fallback_used"] = motion_blink and not (has_open and has_closed)
        if not action_passed:
            reasons.append("blink_not_observed")
    elif prompt == "TURN_LEFT":
        min_offset = min(offsets) if offsets else 0.0
        profile_seen = any(signal.profile_left_seen for signal in signals)
        directional_turn = min_offset <= -config.min_turn_offset or profile_seen
        motion_turn = (
            not directional_turn
            and any_face_ratio >= config.min_single_face_ratio
            and (offset_span >= config.min_turn_offset or max_motion >= config.min_motion_score)
        )
        action_passed = directional_turn or motion_turn
        action_confidence = min(
            0.95,
            max(
                abs(min_offset) / max(config.min_turn_offset, 0.01),
                1.0 if profile_seen else 0,
                0.72 if motion_turn else 0,
            ) * 0.75,
        )
        evidence["motion_fallback_used"] = motion_turn
        if not action_passed:
            reasons.append("left_turn_not_observed")
        evidence["min_offset"] = round(min_offset, 4)
    elif prompt == "TURN_RIGHT":
        max_offset = max(offsets) if offsets else 0.0
        profile_seen = any(signal.profile_right_seen for signal in signals)
        directional_turn = max_offset >= config.min_turn_offset or profile_seen
        motion_turn = (
            not directional_turn
            and any_face_ratio >= config.min_single_face_ratio
            and (offset_span >= config.min_turn_offset or max_motion >= config.min_motion_score)
        )
        action_passed = directional_turn or motion_turn
        action_confidence = min(
            0.95,
            max(
                abs(max_offset) / max(config.min_turn_offset, 0.01),
                1.0 if profile_seen else 0,
                0.72 if motion_turn else 0,
            ) * 0.75,
        )
        evidence["motion_fallback_used"] = motion_turn
        if not action_passed:
            reasons.append("right_turn_not_observed")
        evidence["max_offset"] = round(max_offset, 4)

    passed = enough_samples and one_face_ok and action_passed
    confidence = min(0.99, action_confidence * (0.9 if one_face_ok else 0.45))
    return LivenessPromptResult(
        prompt=prompt,
        passed=passed,
        confidence=round(confidence, 3),
        face_count_mode=_mode(face_counts),
        evidence=evidence,
        reason="passed" if passed else ",".join(reasons),
    )


@app.post("/verify-liveness", response_model=VerifyLivenessResponse)
def verify_liveness(payload: VerifyLivenessRequest) -> VerifyLivenessResponse:
    if APP_ENV in {"production", "prod"} and any(
        sample.observed is not None for sample in payload.samples
    ):
        raise HTTPException(status_code=400, detail="Observed test signals are disabled")
    results: list[LivenessPromptResult] = []
    try:
        for sample in payload.samples:
            signals = (
                _signals_from_observed(sample.observed)
                if sample.observed is not None
                else liveness_verifier.analyze_frames(sample.frame_data_urls)
            )
            results.append(_evaluate_liveness_prompt(sample.prompt, signals, payload.config))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    required_prompts = {"BLINK", "TURN_LEFT", "TURN_RIGHT"}
    seen_prompts = {result.prompt for result in results}
    passed = required_prompts.issubset(seen_prompts) and all(result.passed for result in results)
    confidence = round(sum(result.confidence for result in results) / max(len(results), 1), 3)
    return VerifyLivenessResponse(
        session_id=payload.session_id,
        captured_at=payload.captured_at,
        processed_at=utc_now(),
        passed=passed,
        confidence=confidence if passed else min(confidence, 0.49),
        results=results,
        model=liveness_model_info(),
    )


@app.post("/verify-identity", response_model=VerifyIdentityResponse)
def verify_identity(payload: VerifyIdentityRequest) -> VerifyIdentityResponse:
    try:
        result = identity_verifier.verify(
            payload.frame_data_url,
            payload.reference_data_url,
            IDENTITY_THRESHOLD,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return VerifyIdentityResponse(**result)
