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


class AnalyzeFrameRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    frame_data_url: str | None = None
    observed_face_count: int | None = Field(default=None, ge=0, le=10)
    captured_at: datetime = Field(default_factory=utc_now)
    config: FaceMonitorConfig = Field(default_factory=FaceMonitorConfig)

    @model_validator(mode="after")
    def require_frame_or_observation(self) -> "AnalyzeFrameRequest":
        if self.frame_data_url is None and self.observed_face_count is None:
            raise ValueError("Either frame_data_url or observed_face_count is required")
        return self


class ModelInfo(BaseModel):
    name: str
    version: str
    detector: str
    cascade_path: str | None = None


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
