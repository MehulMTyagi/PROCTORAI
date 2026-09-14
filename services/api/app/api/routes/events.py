from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.websocket_manager import websocket_manager
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentProctor
from app.models.attempt import Attempt
from app.models.enums import AttemptStatus, EventStatus, EvidenceStatus, UserRole
from app.models.integrity_event import IntegrityEvent
from app.models.user import User
from app.schemas.events import IntegrityEventCreate, IntegrityEventResponse

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if attempt.status == AttemptStatus.SUBMITTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt is already submitted")

    return attempt


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

    event = IntegrityEvent(
        attempt_id=attempt.id,
        event_type=payload.event_type,
        status=EventStatus.UNREVIEWED.value,
        severity=payload.severity,
        confidence=payload.confidence,
        priority_score=payload.priority_score,
        occurred_at=payload.occurred_at,
        evidence_status=payload.evidence_status,
        payload=payload.metadata,
    )
    db.add(event)
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
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if current_user.role == UserRole.PROCTOR.value:
        is_assigned = db.scalar(
            select(AssessmentProctor).where(
                AssessmentProctor.assessment_id == assessment_id,
                AssessmentProctor.proctor_id == current_user.id,
            )
        )
        if is_assigned is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    elif current_user.role == UserRole.EXAMINER.value:
        if assessment.created_by_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    elif current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    events = db.scalars(
        select(IntegrityEvent)
        .join(Attempt, Attempt.id == IntegrityEvent.attempt_id)
        .where(Attempt.assessment_id == assessment_id)
        .order_by(IntegrityEvent.occurred_at.desc())
    ).all()

    return [IntegrityEventResponse.from_event(event, assessment_id=assessment_id) for event in events]
