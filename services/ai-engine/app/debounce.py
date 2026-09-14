from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.schemas import EventCandidate, FaceMonitorConfig, FaceMonitorState, ModelInfo


@dataclass
class SessionFaceState:
    consecutive_absent_frames: int = 0
    consecutive_multiple_frames: int = 0
    normal_frames: int = 0
    samples_analyzed: int = 0
    last_event_at: dict[str, datetime] = field(default_factory=dict)


class FaceEventDebouncer:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionFaceState] = {}

    def reset(self) -> None:
        self._sessions.clear()

    def update(
        self,
        session_id: str,
        face_count: int,
        captured_at: datetime,
        config: FaceMonitorConfig,
        model: ModelInfo,
    ) -> tuple[FaceMonitorState, list[EventCandidate]]:
        state = self._sessions.setdefault(session_id, SessionFaceState())
        state.samples_analyzed += 1

        if face_count == 0:
            state.consecutive_absent_frames += 1
            state.consecutive_multiple_frames = 0
        elif face_count > 1:
            state.consecutive_multiple_frames += 1
            state.consecutive_absent_frames = 0
        else:
            state.normal_frames += 1
            state.consecutive_absent_frames = 0
            state.consecutive_multiple_frames = 0

        events: list[EventCandidate] = []
        if state.consecutive_absent_frames >= config.absent_frame_threshold:
            event = self._event_if_allowed(
                state,
                "FACE_ABSENT",
                captured_at,
                config,
                confidence=0.82,
                priority_score=7,
                metadata={
                    "face_count": face_count,
                    "consecutive_frames": state.consecutive_absent_frames,
                    "threshold": config.absent_frame_threshold,
                    "model": model.model_dump(),
                },
            )
            if event is not None:
                events.append(event)

        if state.consecutive_multiple_frames >= config.multiple_frame_threshold:
            event = self._event_if_allowed(
                state,
                "MULTIPLE_PERSONS",
                captured_at,
                config,
                confidence=0.86,
                priority_score=9,
                metadata={
                    "face_count": face_count,
                    "consecutive_frames": state.consecutive_multiple_frames,
                    "threshold": config.multiple_frame_threshold,
                    "model": model.model_dump(),
                },
            )
            if event is not None:
                events.append(event)

        return (
            FaceMonitorState(
                consecutive_absent_frames=state.consecutive_absent_frames,
                consecutive_multiple_frames=state.consecutive_multiple_frames,
                normal_frames=state.normal_frames,
                samples_analyzed=state.samples_analyzed,
            ),
            events,
        )

    def _event_if_allowed(
        self,
        state: SessionFaceState,
        event_type: str,
        captured_at: datetime,
        config: FaceMonitorConfig,
        confidence: float,
        priority_score: int,
        metadata: dict[str, Any],
    ) -> EventCandidate | None:
        previous = state.last_event_at.get(event_type)
        cooldown = timedelta(seconds=config.event_cooldown_seconds)
        if previous is not None and captured_at - previous < cooldown:
            return None

        state.last_event_at[event_type] = captured_at
        return EventCandidate(
            event_type=event_type,  # type: ignore[arg-type]
            severity="HIGH",
            confidence=confidence,
            priority_score=priority_score,
            metadata=metadata,
        )
