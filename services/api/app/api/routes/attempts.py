from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentCandidate
from app.models.attempt import Answer, Attempt
from app.models.enums import AttemptStatus, EvidenceStatus, QuestionType, UserRole
from app.models.integrity_event import IntegrityEvent
from app.models.question import Question
from app.models.session_health import SessionHeartbeat
from app.models.user import User
from app.schemas.attempts import (
    AnswerResponse,
    AnswerSaveRequest,
    AttemptDetailResponse,
    AttemptStartRequest,
    AttemptStartResponse,
    SessionHeartbeatCreate,
    SessionHeartbeatResponse,
    SubmitResponse,
)

router = APIRouter(prefix="/attempts")


def _get_candidate_attempt(db: Session, attempt_id: UUID, current_user: User) -> Attempt:
    attempt = db.scalar(
        select(Attempt)
        .options(selectinload(Attempt.answers))
        .where(Attempt.id == attempt_id)
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    if current_user.role != UserRole.CANDIDATE.value or attempt.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return attempt


@router.post("/start", response_model=AttemptStartResponse, status_code=status.HTTP_201_CREATED)
def start_attempt(
    payload: AttemptStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptStartResponse:
    if current_user.role != UserRole.CANDIDATE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    assessment = db.get(Assessment, payload.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if db.get(AssessmentCandidate, (payload.assessment_id, current_user.id)) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate is not assigned")

    attempt = db.scalar(
        select(Attempt).where(
            Attempt.assessment_id == payload.assessment_id,
            Attempt.candidate_id == current_user.id,
        )
    )
    if attempt is None:
        attempt = Attempt(
            assessment_id=payload.assessment_id,
            candidate_id=current_user.id,
            status=AttemptStatus.IN_PROGRESS.value,
            started_at=datetime.now(UTC),
        )
        db.add(attempt)
    elif attempt.status == AttemptStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment has already been submitted",
        )
    else:
        attempt.status = AttemptStatus.IN_PROGRESS.value
        if attempt.started_at is None:
            attempt.started_at = datetime.now(UTC)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        attempt = db.scalar(
            select(Attempt).where(
                Attempt.assessment_id == payload.assessment_id,
                Attempt.candidate_id == current_user.id,
            )
        )
        if attempt is None:
            raise error
        if attempt.status == AttemptStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This assessment has already been submitted",
            ) from error
    db.refresh(attempt)
    return AttemptStartResponse(
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        status=attempt.status,
    )


@router.get("/{attempt_id}", response_model=AttemptDetailResponse)
def get_attempt(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptDetailResponse:
    return AttemptDetailResponse.from_attempt(_get_candidate_attempt(db, attempt_id, current_user))


@router.post("/{attempt_id}/answers", response_model=AnswerResponse)
def save_answer(
    attempt_id: UUID,
    payload: AnswerSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Answer:
    attempt = _get_candidate_attempt(db, attempt_id, current_user)
    if attempt.status == AttemptStatus.SUBMITTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt is already submitted")

    question = db.get(Question, payload.question_id)
    if question is None or question.assessment_id != attempt.assessment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question does not belong to attempt")

    answer = db.scalar(
        select(Answer).where(
            Answer.attempt_id == attempt.id,
            Answer.question_id == payload.question_id,
        )
    )
    if answer is None:
        answer = Answer(attempt_id=attempt.id, question_id=payload.question_id)
        db.add(answer)

    answer.answer_text = payload.answer_text
    answer.selected_option = payload.selected_option
    db.commit()
    db.refresh(answer)
    return answer


@router.post("/{attempt_id}/heartbeats", response_model=SessionHeartbeatResponse, status_code=status.HTTP_201_CREATED)
def create_session_heartbeat(
    attempt_id: UUID,
    payload: SessionHeartbeatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionHeartbeatResponse:
    attempt = _get_candidate_attempt(db, attempt_id, current_user)
    if attempt.status == AttemptStatus.SUBMITTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt is already submitted")

    heartbeat = SessionHeartbeat(
        attempt_id=attempt.id,
        client_sent_at=payload.client_sent_at,
        status=payload.status,
        metrics=payload.metrics,
    )
    db.add(heartbeat)
    db.commit()
    db.refresh(heartbeat)
    return SessionHeartbeatResponse.from_heartbeat(heartbeat)


@router.post("/{attempt_id}/submit", response_model=SubmitResponse)
def submit_attempt(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmitResponse:
    attempt = _get_candidate_attempt(db, attempt_id, current_user)

    questions = db.scalars(
        select(Question)
        .where(Question.assessment_id == attempt.assessment_id)
        .order_by(Question.display_order)
    ).all()
    answers_by_question = {answer.question_id: answer for answer in attempt.answers}
    score = 0
    total_points = sum(question.points for question in questions)

    for question in questions:
        answer = answers_by_question.get(question.id)
        if answer is None:
            continue
        if (
            question.question_type == QuestionType.MCQ.value
            and question.correct_answer is not None
            and answer.selected_option == question.correct_answer
        ):
            answer.score_awarded = question.points
        elif question.question_type == QuestionType.MCQ.value:
            answer.score_awarded = 0

        if answer.score_awarded is not None:
            score += answer.score_awarded

    attempt.status = AttemptStatus.SUBMITTED.value
    attempt.submitted_at = datetime.now(UTC)
    attempt.score = score
    for event in db.scalars(
        select(IntegrityEvent).where(
            IntegrityEvent.attempt_id == attempt.id,
            IntegrityEvent.evidence_status == EvidenceStatus.PENDING.value,
        )
    ):
        event.evidence_status = EvidenceStatus.FAILED.value
        event.payload = {
            **(event.payload or {}),
            "evidence_failure": {
                "reason": "evidence_not_saved_before_submission",
                "detail": "The evidence clip was not saved before the assessment was submitted.",
                "failed_at": datetime.now(UTC).isoformat(),
            },
        }
    db.commit()
    db.refresh(attempt)

    return SubmitResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        score=score,
        total_points=total_points,
        answers=[AnswerResponse.model_validate(answer) for answer in attempt.answers],
    )
