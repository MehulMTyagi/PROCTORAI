from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentCandidate, AssessmentProctor, ProctoringRule
from app.models.attempt import Attempt
from app.models.enums import UserRole
from app.models.question import Question
from app.models.teaching_group import TeachingGroupAssignment
from app.models.user import User
from app.schemas.assessments import (
    AssessmentAssignments,
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


def _validate_assignees(
    db: Session,
    candidate_ids: list[UUID],
    proctor_ids: list[UUID],
    current_user: User,
) -> None:
    for ids, role in ((candidate_ids, UserRole.CANDIDATE), (proctor_ids, UserRole.PROCTOR)):
        if not ids:
            continue
        found = set(db.scalars(select(User.id).where(User.id.in_(ids), User.role == role.value)))
        if found != set(ids):
            raise HTTPException(
                status_code=400, detail=f"Select valid {role.value.lower()} accounts"
            )
    if candidate_ids and current_user.role == UserRole.EXAMINER.value:
        assignments = db.scalars(
            select(TeachingGroupAssignment).where(
                TeachingGroupAssignment.examiner_id == current_user.id
            )
        ).all()
        allowed_groups = {
            (item.program, item.admission_year, item.section) for item in assignments
        }
        students = db.scalars(
            select(User).where(
                User.id.in_(candidate_ids), User.role == UserRole.CANDIDATE.value
            )
        ).all()
        allowed_ids = {
            student.id
            for student in students
            if (student.program, student.admission_year, student.section) in allowed_groups
        }
        if allowed_ids != set(candidate_ids):
            raise HTTPException(
                status_code=403,
                detail="One or more candidates are outside your assigned teaching groups",
            )


def _detail(
    db: Session, assessment: Assessment, include_assignees: bool = False
) -> AssessmentDetailResponse:
    response = AssessmentDetailResponse.from_assessment(assessment)
    policy = db.scalar(select(ProctoringRule).where(ProctoringRule.assessment_id == assessment.id))
    response.rules = policy.rules if policy else {}
    if include_assignees:
        response.candidate_ids = list(
            db.scalars(
                select(AssessmentCandidate.candidate_id).where(
                    AssessmentCandidate.assessment_id == assessment.id
                )
            )
        )
        response.proctor_ids = list(
            db.scalars(
                select(AssessmentProctor.proctor_id).where(
                    AssessmentProctor.assessment_id == assessment.id
                )
            )
        )
    return response


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
    _validate_assignees(db, payload.candidate_ids, payload.proctor_ids, current_user)
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
    db.flush()
    db.add_all(
        [
            AssessmentCandidate(assessment_id=assessment.id, candidate_id=user_id)
            for user_id in set(payload.candidate_ids)
        ]
    )
    db.add_all(
        [
            AssessmentProctor(assessment_id=assessment.id, proctor_id=user_id)
            for user_id in set(payload.proctor_ids)
        ]
    )
    db.add(
        ProctoringRule(
            assessment_id=assessment.id, rules=payload.rules, config_version="assessment-v1"
        )
    )
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssessmentResponse]:
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

    assessments = list(db.scalars(statement).all())
    if current_user.role != UserRole.CANDIDATE.value or not assessments:
        return assessments

    statuses = dict(
        db.execute(
            select(Attempt.assessment_id, Attempt.status).where(
                Attempt.candidate_id == current_user.id,
                Attempt.assessment_id.in_([item.id for item in assessments]),
            )
        ).all()
    )
    return [
        AssessmentResponse.model_validate(assessment).model_copy(
            update={"attempt_status": statuses.get(assessment.id)}
        )
        for assessment in assessments
    ]


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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        response = _detail(db, assessment)
        response.questions = [
            QuestionResponse.candidate_view(question) for question in assessment.questions
        ]
        return response

    if current_user.role == UserRole.PROCTOR.value:
        assigned = db.get(AssessmentProctor, (assessment.id, current_user.id))
        if assigned is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
    elif current_user.role in {UserRole.EXAMINER.value, UserRole.ADMIN.value}:
        _ensure_examiner_owns_assessment(assessment, current_user)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    return _detail(
        db,
        assessment,
        include_assignees=current_user.role
        in {
            UserRole.EXAMINER.value,
            UserRole.ADMIN.value,
        },
    )


@router.put("/{assessment_id}/assignments", response_model=AssessmentDetailResponse)
def replace_assignments(
    assessment_id: UUID,
    payload: AssessmentAssignments,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AssessmentDetailResponse:
    assessment = _get_assessment(db, assessment_id)
    _ensure_examiner_owns_assessment(assessment, current_user)
    _validate_assignees(db, payload.candidate_ids, payload.proctor_ids, current_user)
    db.execute(
        delete(AssessmentCandidate).where(AssessmentCandidate.assessment_id == assessment_id)
    )
    db.execute(delete(AssessmentProctor).where(AssessmentProctor.assessment_id == assessment_id))
    db.add_all(
        [
            AssessmentCandidate(assessment_id=assessment_id, candidate_id=user_id)
            for user_id in set(payload.candidate_ids)
        ]
    )
    db.add_all(
        [
            AssessmentProctor(assessment_id=assessment_id, proctor_id=user_id)
            for user_id in set(payload.proctor_ids)
        ]
    )
    db.commit()
    return _detail(db, assessment, include_assignees=True)


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a candidate"
        )
    _validate_assignees(db, [user.id], [], current_user)
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
    return {
        "assessment_id": str(assessment_id),
        "config_version": rules.config_version,
        "rules": rules.rules,
    }
