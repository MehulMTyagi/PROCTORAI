from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed import DEV_ASSESSMENT_TITLE, DEV_USERS, upsert_dev_assessment, upsert_dev_users
from app.models.assessment import Assessment
from app.models.attempt import Attempt
from app.models.question import Question
from app.models.user import User


def test_seed_users_are_idempotent_and_hashed(db_session: Session) -> None:
    upsert_dev_users(db_session)
    upsert_dev_users(db_session)

    users = db_session.scalars(select(User).order_by(User.email)).all()
    seeded_emails = {user["email"] for user in DEV_USERS}
    matching_users = [user for user in users if user.email in seeded_emails]

    assert len(matching_users) == len(DEV_USERS)
    assert all(user.password_hash != "password123" for user in matching_users)
    assert all(user.password_hash.startswith("$argon2id$") for user in matching_users)


def test_seed_assessment_creates_vertical_slice_data(db_session: Session) -> None:
    upsert_dev_users(db_session)
    upsert_dev_assessment(db_session)
    upsert_dev_assessment(db_session)

    assessment = db_session.scalar(select(Assessment).where(Assessment.title == DEV_ASSESSMENT_TITLE))

    assert assessment is not None
    assert db_session.scalar(select(Attempt).where(Attempt.assessment_id == assessment.id)) is not None
    assert db_session.scalar(select(Question).where(Question.assessment_id == assessment.id)) is not None
