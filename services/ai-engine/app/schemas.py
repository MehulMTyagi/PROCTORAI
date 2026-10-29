from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class FaceMonitorConfig(BaseModel):
    absent_frame_threshold: int = Field(default=3, ge=1, le=30)
    multiple_frame_threshold: int = Field(default=2, ge=1, le=30)
    event_cooldown_seconds: int = Field(default=10, ge=0, le=300)
    min_face_size_px: int = Field(default=24, ge=10, le=400)


class ObjectMonitorConfig(BaseModel):
    min_confidence: float = Field(default=0.15, ge=0.01, le=1)
    max_detections: int = Field(default=20, ge=1, le=100)
    phone_like_classes: list[str] = Field(default_factory=lambda: ["cell phone", "remote"])


class LivenessConfig(BaseModel):
    min_single_face_ratio: float = Field(default=0.45, ge=0.1, le=1)
    min_turn_offset: float = Field(default=0.04, ge=0.01, le=0.4)
    min_samples_per_prompt: int = Field(default=6, ge=2, le=16)
    min_eye_open_count: int = Field(default=1, ge=0, le=4)
    min_motion_score: float = Field(default=0.035, ge=0.005, le=0.3)
    min_blink_motion_score: float = Field(default=0.025, ge=0.005, le=0.3)


class AnalyzeFrameRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    frame_data_url: str | None = Field(default=None, max_length=2_000_000)
    observed_face_count: int | None = Field(default=None, ge=0, le=10)
    captured_at: datetime = Field(default_factory=utc_now)
    config: FaceMonitorConfig = Field(default_factory=FaceMonitorConfig)

    @model_validator(mode="after")
    def require_frame_or_observation(self) -> "AnalyzeFrameRequest":
        if self.frame_data_url is None and self.observed_face_count is None:
            raise ValueError("Either frame_data_url or observed_face_count is required")
        return self


class ScratchClassifierResult(BaseModel):
    model: Literal["PhoneCropCNN-v1"]
    label: Literal["cell_phone", "other_object"]
    phone_score: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0.1, le=0.9)


class DetectedObject(BaseModel):
    class_name: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0, le=1)
    bbox: list[float] = Field(default_factory=list, max_length=4)
    phone_like: bool = False
    scratch_classifier: ScratchClassifierResult | None = None


class DetectObjectsRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    frame_data_url: str | None = Field(default=None, max_length=2_000_000)
    observed_objects: list[DetectedObject] | None = Field(default=None, max_length=100)
    captured_at: datetime = Field(default_factory=utc_now)
    config: ObjectMonitorConfig = Field(default_factory=ObjectMonitorConfig)

    @model_validator(mode="after")
    def require_frame_or_observation(self) -> "DetectObjectsRequest":
        if self.frame_data_url is None and self.observed_objects is None:
            raise ValueError("Either frame_data_url or observed_objects is required")
        return self


class ObservedLivenessSignals(BaseModel):
    face_counts: list[int] = Field(default_factory=list, max_length=16)
    eye_counts: list[int] = Field(default_factory=list, max_length=16)
    face_center_offsets: list[float] = Field(default_factory=list, max_length=16)
    motion_scores: list[float] = Field(default_factory=list, max_length=16)
    upper_motion_scores: list[float] = Field(default_factory=list, max_length=16)
    profile_left_seen: bool = False
    profile_right_seen: bool = False


class LivenessPromptSample(BaseModel):
    prompt: Literal["BLINK", "TURN_LEFT", "TURN_RIGHT"]
    frame_data_urls: list[str] = Field(default_factory=list, max_length=8)
    observed: ObservedLivenessSignals | None = None

    @model_validator(mode="after")
    def require_frames_or_observation(self) -> "LivenessPromptSample":
        if not self.frame_data_urls and self.observed is None:
            raise ValueError("Either frame_data_urls or observed liveness signals are required")
        if any(len(frame) > 2_000_000 for frame in self.frame_data_urls):
            raise ValueError("Each liveness frame must be at most 2 MB of encoded data")
        return self


class VerifyLivenessRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    samples: list[LivenessPromptSample] = Field(min_length=1, max_length=6)
    captured_at: datetime = Field(default_factory=utc_now)
    config: LivenessConfig = Field(default_factory=LivenessConfig)

    @model_validator(mode="after")
    def limit_total_encoded_frames(self) -> "VerifyLivenessRequest":
        total_chars = sum(len(frame) for sample in self.samples for frame in sample.frame_data_urls)
        if total_chars > 8_000_000:
            raise ValueError("Total liveness frame data must be at most 8 MB")
        return self


class ModelInfo(BaseModel):
    name: str
    version: str
    detector: str
    cascade_path: str | None = None
    model_path: str | None = None


class EventCandidate(BaseModel):
    event_type: Literal["FACE_ABSENT", "MULTIPLE_PERSONS"]
    severity: Literal["HIGH"]
    confidence: float = Field(ge=0, le=1)
    priority_score: int = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FaceMonitorState(BaseModel):
    consecutive_absent_frames: int
    consecutive_multiple_frames: int
    normal_frames: int
    samples_analyzed: int


class AnalyzeFrameResponse(BaseModel):
    session_id: str
    captured_at: datetime
    processed_at: datetime
    face_count: int
    state: FaceMonitorState
    events: list[EventCandidate]
    model: ModelInfo


class ObjectEventCandidate(BaseModel):
    event_type: Literal["PHONE_DETECTED"]
    severity: Literal["HIGH"]
    confidence: float = Field(ge=0, le=1)
    priority_score: int = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DetectObjectsResponse(BaseModel):
    session_id: str
    captured_at: datetime
    processed_at: datetime
    objects: list[DetectedObject]
    phone_like_objects: list[DetectedObject]
    events: list[ObjectEventCandidate]
    model: ModelInfo


class LivenessPromptResult(BaseModel):
    prompt: Literal["BLINK", "TURN_LEFT", "TURN_RIGHT"]
    passed: bool
    confidence: float = Field(ge=0, le=1)
    face_count_mode: int
    evidence: dict[str, Any] = Field(default_factory=dict)
    reason: str


class VerifyLivenessResponse(BaseModel):
    session_id: str
    captured_at: datetime
    processed_at: datetime
    passed: bool
    confidence: float = Field(ge=0, le=1)
    results: list[LivenessPromptResult]
    model: ModelInfo


class VerifyIdentityRequest(BaseModel):
    frame_data_url: str = Field(min_length=1, max_length=2_000_000)
    reference_data_url: str = Field(min_length=1, max_length=2_000_000)


class VerifyIdentityResponse(BaseModel):
    matched: bool
    reason: Literal[
        "match",
        "no_face",
        "multiple_faces",
        "reference_no_face",
        "reference_multiple_faces",
        "identity_mismatch",
    ]
    similarity: float | None = Field(default=None, ge=-1, le=1)
    threshold: float
    face_count: int
    detector: str
    recognizer: str
