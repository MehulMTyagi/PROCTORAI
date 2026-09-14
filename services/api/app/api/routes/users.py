from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.assessments import UserSummary

router = APIRouter(prefix="/users")


@router.get("", response_model=list[UserSummary])
def list_users(
    role: str | None = None,
    _: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserSummary]:
    statement = select(User).order_by(User.full_name)
    if role is not None:
        statement = statement.where(User.role == role.upper())

    return [UserSummary.model_validate(user) for user in db.scalars(statement).all()]
