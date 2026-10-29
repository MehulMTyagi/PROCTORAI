import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.websocket_manager import websocket_manager
from app.core.audit import write_audit_log
from app.core.config import settings
from app.db.base_class import utc_now
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentProctor, ProctoringRule
from app.models.attempt import Attempt
from app.models.enums import AttemptStatus, EventStatus, EvidenceStatus, ReviewDecision, UserRole
from app.models.evidence import EvidenceFile
from app.models.integrity_event import IntegrityEvent
from app.models.review import EventReview
from app.models.user import User
from app.schemas.events import (
    EventReviewCreate,
    EvidenceFailureCreate,
    EvidenceFileResponse,
    IntegrityEventCreate,
    IntegrityEventResponse,
)

router = APIRouter()


def _get_authorized_candidate_attempt(
    attempt_id: UUID,
    current_user: User,
    db: Session,
) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if current_user.role != UserRole.CANDIDATE.value or attempt.candidate_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    if attempt.status == AttemptStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt is already submitted"
        )

    return attempt


def _ensure_event_belongs_to_attempt(
    event: IntegrityEvent | None, attempt: Attempt
) -> IntegrityEvent:
    if event is None or event.attempt_id != attempt.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_can_view_assessment_events(
    assessment: Assessment | None, current_user: User, db: Session
) -> None:
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if current_user.role == UserRole.PROCTOR.value:
        is_assigned = db.scalar(
            select(AssessmentProctor).where(
                AssessmentProctor.assessment_id == assessment.id,
                AssessmentProctor.proctor_id == current_user.id,
            )
        )
        if is_assigned is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
    elif current_user.role == UserRole.EXAMINER.value:
        if assessment.created_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
    elif current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _get_viewable_event(event_id: UUID, current_user: User, db: Session) -> IntegrityEvent:
    event = db.get(IntegrityEvent, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    attempt = db.get(Attempt, event.attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if current_user.role == UserRole.CANDIDATE.value:
        if attempt.candidate_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return event

    assessment = db.get(Assessment, attempt.assessment_id)
    _ensure_can_view_assessment_events(assessment, current_user, db)
    return event


def _event_assessment_id(event: IntegrityEvent, db: Session) -> UUID:
    attempt = db.get(Attempt, event.attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt.assessment_id


@router.post(
    "/attempts/{attempt_id}/events",
    response_model=IntegrityEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_integrity_event(
    attempt_id: UUID,
    payload: IntegrityEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrityEventResponse:
    attempt = _get_authorized_candidate_attempt(attempt_id, current_user, db)
    policy = db.scalar(
        select(ProctoringRule).where(ProctoringRule.assessment_id == attempt.assessment_id)
    )
    rule = policy.rules.get(payload.event_type, {}) if policy else {}
    if isinstance(rule, dict) and rule.get("enabled") is False:
        raise HTTPException(
            status_code=409, detail="This monitoring feature is disabled for the assessment"
        )

    received_at = utc_now()
    event_metadata = dict(payload.metadata)
    event_metadata["client_occurred_at"] = payload.occurred_at.isoformat()
    event = IntegrityEvent(
        attempt_id=attempt.id,
        event_type=payload.event_type,
        status=EventStatus.UNREVIEWED.value,
        severity=payload.severity,
        confidence=payload.confidence,
        priority_score=payload.priority_score,
        occurred_at=received_at,
        evidence_status=payload.evidence_status,
        payload=event_metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    response = IntegrityEventResponse.from_event(event, assessment_id=attempt.assessment_id)
    await websocket_manager.broadcast(str(attempt.assessment_id), response.model_dump(mode="json"))
    return response


@router.post(
    "/attempts/{attempt_id}/events/{event_id}/evidence",
    response_model=EvidenceFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_event_evidence(
    attempt_id: UUID,
    event_id: UUID,
    file: UploadFile = File(...),
    kind: str = Form(default="VIDEO"),
    sha256_hash: str | None = Form(default=None),
    duration_ms: int | None = Form(default=None),
    captured_start_at: datetime | None = Form(default=None),
    captured_end_at: datetime | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceFileResponse:
    attempt = _get_authorized_candidate_attempt(attempt_id, current_user, db)
    event = _ensure_event_belongs_to_attempt(db.get(IntegrityEvent, event_id), attempt)
    policy = db.scalar(
        select(ProctoringRule).where(ProctoringRule.assessment_id == attempt.assessment_id)
    )
    screen_rule = policy.rules.get("SCREEN_RECORDING", {}) if policy else {}
    if kind not in {"VIDEO", "SCREEN_RECORDING"}:
        raise HTTPException(status_code=400, detail="Unsupported evidence kind")
    if (
        kind == "SCREEN_RECORDING"
        and isinstance(screen_rule, dict)
        and screen_rule.get("enabled") is False
    ):
        raise HTTPException(
            status_code=409, detail="Screen recording is disabled for the assessment"
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Evidence file is required"
        )

    max_bytes = settings.max_evidence_mb * 1024 * 1024
    evidence_root = Path(settings.evidence_dir).resolve()
    storage_dir = evidence_root / str(attempt.id) / str(event.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"{attempt.id}/{event.id}/{uuid.uuid4().hex}.webm"
    storage_path = evidence_root / storage_key

    digest = hashlib.sha256()
    size_bytes = 0
    try:
        with storage_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    target.close()
                    storage_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Evidence exceeds {settings.max_evidence_mb} MB",
                    )
                digest.update(chunk)
                target.write(chunk)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    computed_hash = digest.hexdigest()
    if sha256_hash and sha256_hash.lower() != computed_hash:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Evidence hash mismatch"
        )

    if kind in {"VIDEO", "SCREEN_RECORDING"}:
        with storage_path.open("rb") as source:
            header = source.read(4)
        if header != b"\x1aE\xdf\xa3":
            storage_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Video evidence is not a complete WebM file. Please retry the capture.",
            )

    evidence_file = EvidenceFile(
        event_id=event.id,
        attempt_id=attempt.id,
        kind=kind,
        storage_key=storage_key,
        original_filename=Path(file.filename.replace("\\", "/")).name[:255],
        mime_type="video/webm",
        sha256_hash=computed_hash,
        size_bytes=size_bytes,
        duration_ms=duration_ms,
        captured_start_at=captured_start_at,
        captured_end_at=captured_end_at,
        retention_until=datetime.now(UTC) + timedelta(days=30),
    )
    event.evidence_status = EvidenceStatus.READY.value
    db.add(evidence_file)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    db.refresh(evidence_file)
    db.refresh(event)

    response = IntegrityEventResponse.from_event(event, assessment_id=attempt.assessment_id)
    await websocket_manager.broadcast(str(attempt.assessment_id), response.model_dump(mode="json"))
    return EvidenceFileResponse.from_file(evidence_file)


@router.post(
    "/attempts/{attempt_id}/events/{event_id}/evidence/failure",
    response_model=IntegrityEventResponse,
)
async def mark_event_evidence_failed(
    attempt_id: UUID,
    event_id: UUID,
    payload: EvidenceFailureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrityEventResponse:
    attempt = _get_authorized_candidate_attempt(attempt_id, current_user, db)
    event = _ensure_event_belongs_to_attempt(db.get(IntegrityEvent, event_id), attempt)
    event.evidence_status = EvidenceStatus.FAILED.value
    event.payload = {
        **(event.payload or {}),
        "evidence_failure": {
            "reason": payload.reason,
            "detail": payload.detail,
            "failed_at": datetime.now(UTC).isoformat(),
        },
    }
    db.commit()
    db.refresh(event)

    response = IntegrityEventResponse.from_event(event, assessment_id=attempt.assessment_id)
    await websocket_manager.broadcast(str(attempt.assessment_id), response.model_dump(mode="json"))
    return response


@router.get(
    "/proctor/assessments/{assessment_id}/events",
    response_model=list[IntegrityEventResponse],
)
def list_assessment_events(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IntegrityEventResponse]:
    assessment = db.get(Assessment, assessment_id)
    _ensure_can_view_assessment_events(assessment, current_user, db)

    events = db.scalars(
        select(IntegrityEvent)
        .join(Attempt, Attempt.id == IntegrityEvent.attempt_id)
        .where(Attempt.assessment_id == assessment_id)
        .order_by(IntegrityEvent.occurred_at.desc())
    ).all()

    return [
        IntegrityEventResponse.from_event(event, assessment_id=assessment_id) for event in events
    ]


@router.get("/proctor/events/{event_id}/evidence/{evidence_id}")
def download_event_evidence(
    event_id: UUID,
    evidence_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    event = _get_viewable_event(event_id, current_user, db)
    evidence_file = db.get(EvidenceFile, evidence_id)
    if evidence_file is None or evidence_file.event_id != event.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    evidence_root = Path(settings.evidence_dir).resolve()
    storage_path = (evidence_root / evidence_file.storage_key).resolve()
    if not storage_path.is_relative_to(evidence_root) or not storage_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file missing")

    write_audit_log(
        db,
        request,
        actor_id=current_user.id,
        action="evidence_downloaded",
        target_type="evidence_file",
        target_id=evidence_file.id,
        details={"event_id": str(event.id)},
    )
    db.commit()

    return FileResponse(
        storage_path,
        media_type=evidence_file.mime_type,
        filename=evidence_file.original_filename or storage_path.name,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/proctor/events/{event_id}/reviews",
    response_model=IntegrityEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def review_event(
    event_id: UUID,
    payload: EventReviewCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrityEventResponse:
    if current_user.role not in {
        UserRole.PROCTOR.value,
        UserRole.EXAMINER.value,
        UserRole.ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    event = _get_viewable_event(event_id, current_user, db)
    decision = payload.decision
    if decision not in {item.value for item in ReviewDecision}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported review decision"
        )

    review = EventReview(
        event_id=event.id,
        reviewer_id=current_user.id,
        decision=decision,
        note=payload.note,
    )
    if decision == ReviewDecision.CONFIRMED_SUSPICIOUS.value:
        event.status = EventStatus.CONFIRMED.value
    elif decision == ReviewDecision.FALSE_POSITIVE.value:
        event.status = EventStatus.FALSE_POSITIVE.value
    else:
        event.status = EventStatus.INCONCLUSIVE.value

    db.add(review)
    write_audit_log(
        db,
        request,
        actor_id=current_user.id,
        action="integrity_event_reviewed",
        target_type="integrity_event",
        target_id=event.id,
        details={"decision": decision},
    )
    db.commit()
    db.refresh(event)

    assessment_id = _event_assessment_id(event, db)
    response = IntegrityEventResponse.from_event(event, assessment_id=assessment_id)
    await websocket_manager.broadcast(str(assessment_id), response.model_dump(mode="json"))
    return response
