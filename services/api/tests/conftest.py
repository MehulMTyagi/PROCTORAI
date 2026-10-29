from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.teaching_group import TeachingGroupAssignment
from app.models.user import User


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        session.add_all(
            [
                User(
                    email="candidate@example.com",
                    full_name="Dev Candidate",
                    role=UserRole.CANDIDATE.value,
                    password_hash=hash_password("password123"),
                    roll_number="S24BCAU9000",
                    program="BCA",
                    admission_year=2024,
                    section="A",
                ),
                User(
                    email="proctor@example.com",
                    full_name="Dev Proctor",
                    role=UserRole.PROCTOR.value,
                    password_hash=hash_password("password123"),
                ),
                User(
                    email="examiner@example.com",
                    full_name="Dev Examiner",
                    role=UserRole.EXAMINER.value,
                    password_hash=hash_password("password123"),
                ),
                User(
                    email="admin@example.com",
                    full_name="Dev Admin",
                    role=UserRole.ADMIN.value,
                    password_hash=hash_password("password123"),
                ),
            ]
        )
        session.flush()
        examiner = session.scalar(select(User).where(User.email == "examiner@example.com"))
        assert examiner is not None
        session.add(
            TeachingGroupAssignment(
                examiner_id=examiner.id,
                program="BCA",
                admission_year=2024,
                section="A",
            )
        )
        session.commit()
        yield session

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
