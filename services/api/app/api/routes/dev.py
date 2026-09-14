from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.seed import DEV_ASSESSMENT_TITLE
from app.db.session import get_db
from app.models.assessment import Assessment
from app.models.attempt import Attempt
from app.models.user import User
from app.schemas.dev import DevBootstrapResponse

router = APIRouter(prefix="/dev")


@router.get("/bootstrap", response_model=DevBootstrapResponse)
def dev_bootstrap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DevBootstrapResponse:
    assessment = db.scalar(select(Assessment).where(Assessment.title == DEV_ASSESSMENT_TITLE))
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development assessment not found. Run python -m app.db.seed.",
        )

    attempt = db.scalar(
        select(Attempt).where(
            Attempt.assessment_id == assessment.id,
            Attempt.candidate_id == current_user.id,
        )
    )

    return DevBootstrapResponse(
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        attempt_id=attempt.id if attempt is not None else None,
        role=current_user.role,
    )
