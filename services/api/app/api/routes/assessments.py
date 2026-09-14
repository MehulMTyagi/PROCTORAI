from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentCandidate, AssessmentProctor, ProctoringRule
from app.models.enums import UserRole
from app.models.question import Question
from app.models.user import User
from app.schemas.assessments import (
    AssessmentCreate,
    AssessmentDetailResponse,
    AssessmentResponse,
    AssessmentUpdate,
    AssignmentRequest,
    QuestionCreate,
    QuestionResponse,
    RuleUpdate,
)

router = APIRouter(prefix="/assessments")


def _get_assessment(db: Session, assessment_id: UUID) -> Assessment:
    assessment = db.scalar(
        select(Assessment)
        .options(selectinload(Assessment.questions))
        .where(Assessment.id == assessment_id)
    )
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment


def _ensure_examiner_owns_assessment(assessment: Assessment, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN.value:
        return
    if current_user.role == UserRole.EXAMINER.value and assessment.created_by_id == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: AssessmentCreate,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Assessment:
    assessment = Assessment(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        start_at=payload.start_at,
        end_at=payload.end_at,
        duration_minutes=payload.duration_minutes,
        created_by_id=current_user.id,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Assessment]:
    if current_user.role == UserRole.ADMIN.value:
        statement = select(Assessment).order_by(Assessment.created_at.desc())
    elif current_user.role == UserRole.EXAMINER.value:
        statement = (
            select(Assessment)
            .where(Assessment.created_by_id == current_user.id)
            .order_by(Assessment.created_at.desc())
        )
    elif current_user.role == UserRole.PROCTOR.value:
        statement = (
            select(Assessment)
            .join(AssessmentProctor, AssessmentProctor.assessment_id == Assessment.id)
            .where(AssessmentProctor.proctor_id == current_user.id)
            .order_by(Assessment.created_at.desc())
        )
    else:
        statement = (
            select(Assessment)
            .join(AssessmentCandidate, AssessmentCandidate.assessment_id == Assessment.id)
            .where(AssessmentCandidate.candidate_id == current_user.id)
            .order_by(Assessment.created_at.desc())
        )

    return list(db.scalars(statement).all())


@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentDetailResponse:
    assessment = _get_assessment(db, assessment_id)

    if current_user.role == UserRole.CANDIDATE.value:
        assigned = db.get(AssessmentCandidate, (assessment.id, current_user.id))
        if assigned is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        response = AssessmentDetailResponse.from_assessment(assessment)
        response.questions = [QuestionResponse.candidate_view(question) for question in assessment.questions]
        return response

    if current_user.role == UserRole.PROCTOR.value:
        assigned = db.get(AssessmentProctor, (assessment.id, current_user.id))
        if assigned is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    elif current_user.role in {UserRole.EXAMINER.value, UserRole.ADMIN.value}:
        _ensure_examiner_owns_assessment(assessment, current_user)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return AssessmentDetailResponse.from_assessment(assessment)


@router.put("/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    assessment_id: UUID,
    payload: AssessmentUpdate,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Assessment:
    assessment = _get_assessment(db, assessment_id)
    _ensure_examiner_owns_assessment(assessment, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, field, value)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.post(
    "/{assessment_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    assessment_id: UUID,
    payload: QuestionCreate,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Question:
    assessment = _get_assessment(db, assessment_id)
    _ensure_examiner_owns_assessment(assessment, current_user)
    question = Question(assessment_id=assessment_id, **payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.post("/{assessment_id}/candidates", status_code=status.HTTP_204_NO_CONTENT)
def assign_candidate(
    assessment_id: UUID,
    payload: AssignmentRequest,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> None:
    assessment = _get_assessment(db, assessment_id)
    _ensure_examiner_owns_assessment(assessment, current_user)
    user = db.get(User, payload.user_id)
    if user is None or user.role != UserRole.CANDIDATE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a candidate")
    if db.get(AssessmentCandidate, (assessment_id, payload.user_id)) is None:
        db.add(AssessmentCandidate(assessment_id=assessment_id, candidate_id=payload.user_id))
        db.commit()


@router.post("/{assessment_id}/proctors", status_code=status.HTTP_204_NO_CONTENT)
def assign_proctor(
    assessment_id: UUID,
    payload: AssignmentRequest,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> None:
    assessment = _get_assessment(db, assessment_id)
    _ensure_examiner_owns_assessment(assessment, current_user)
    user = db.get(User, payload.user_id)
    if user is None or user.role != UserRole.PROCTOR.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a proctor")
    if db.get(AssessmentProctor, (assessment_id, payload.user_id)) is None:
        db.add(AssessmentProctor(assessment_id=assessment_id, proctor_id=payload.user_id))
        db.commit()


@router.put("/{assessment_id}/rules", response_model=dict)
def update_rules(
    assessment_id: UUID,
    payload: RuleUpdate,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    assessment = _get_assessment(db, assessment_id)
    _ensure_examiner_owns_assessment(assessment, current_user)
    rules = db.scalar(select(ProctoringRule).where(ProctoringRule.assessment_id == assessment_id))
    if rules is None:
        rules = ProctoringRule(assessment_id=assessment_id)
        db.add(rules)

    rules.rules = payload.rules
    rules.config_version = payload.config_version
    db.commit()
    return {"assessment_id": str(assessment_id), "config_version": rules.config_version, "rules": rules.rules}
