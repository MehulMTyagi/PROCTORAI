from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.assessment import Assessment, AssessmentProctor
from app.models.attempt import Attempt
from app.models.enums import AssessmentStatus, AttemptStatus, UserRole
from app.models.integrity_event import IntegrityEvent
from app.models.user import User


def _token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_attempt(db_session: Session) -> tuple[Assessment, Attempt]:
    examiner = db_session.scalar(select(User).where(User.email == "examiner@example.com"))
    candidate = db_session.scalar(select(User).where(User.email == "candidate@example.com"))
    proctor = db_session.scalar(select(User).where(User.email == "proctor@example.com"))

    assert examiner is not None
    assert candidate is not None
    assert proctor is not None

    assessment = Assessment(
        title="Dummy Event Test",
        status=AssessmentStatus.ACTIVE.value,
        duration_minutes=60,
        created_by_id=examiner.id,
    )
    db_session.add(assessment)
    db_session.flush()

    attempt = Attempt(
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        status=AttemptStatus.IN_PROGRESS.value,
    )
    db_session.add_all(
        [
            AssessmentProctor(assessment_id=assessment.id, proctor_id=proctor.id),
            attempt,
        ]
    )
    db_session.commit()
    db_session.refresh(assessment)
    db_session.refresh(attempt)
    return assessment, attempt


def test_candidate_can_create_dummy_integrity_event(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, attempt = _create_attempt(db_session)
    token = _token(client, "candidate@example.com")

    response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "APP_FOCUS_LOST",
            "severity": "MEDIUM",
            "confidence": 0.9,
            "priority_score": 5,
            "occurred_at": datetime.now(UTC).isoformat(),
            "metadata": {"source": "week2-test"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["assessment_id"] == str(assessment.id)
    assert payload["attempt_id"] == str(attempt.id)
    assert payload["event_type"] == "APP_FOCUS_LOST"
    assert payload["status"] == "UNREVIEWED"

    event_count = db_session.scalar(select(IntegrityEvent).where(IntegrityEvent.id == UUID(payload["id"])))
    assert event_count is not None


def test_submitted_attempt_rejects_new_integrity_event(
    client: TestClient,
    db_session: Session,
) -> None:
    _, attempt = _create_attempt(db_session)
    attempt.status = AttemptStatus.SUBMITTED.value
    db_session.commit()
    token = _token(client, "candidate@example.com")

    response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "APP_FOCUS_LOST",
            "severity": "MEDIUM",
            "metadata": {"source": "after-submit-test"},
        },
    )

    assert response.status_code == 409


def test_proctor_can_list_assigned_assessment_events(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, attempt = _create_attempt(db_session)
    event = IntegrityEvent(
        attempt_id=attempt.id,
        event_type="APP_FOCUS_LOST",
        status="UNREVIEWED",
        severity="MEDIUM",
        priority_score=5,
        payload={"source": "seeded-test"},
    )
    db_session.add(event)
    db_session.commit()

    token = _token(client, "proctor@example.com")
    response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["event_type"] == "APP_FOCUS_LOST"


def test_non_candidate_cannot_create_attempt_event(
    client: TestClient,
    db_session: Session,
) -> None:
    _, attempt = _create_attempt(db_session)
    token = _token(client, "proctor@example.com")

    response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_type": "APP_FOCUS_LOST", "metadata": {}},
    )

    assert response.status_code == 403


def test_candidate_cannot_list_proctor_events(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, _ = _create_attempt(db_session)
    token = _token(client, "candidate@example.com")

    response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_examiner_cannot_list_another_examiner_assessment_events(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = db_session.scalar(select(User).where(User.email == "candidate@example.com"))
    assert candidate is not None
    other_examiner = User(
        email="events-owner@example.com",
        full_name="Events Owner",
        role=UserRole.EXAMINER.value,
        password_hash=hash_password("password123"),
    )
    db_session.add(other_examiner)
    db_session.flush()
    assessment = Assessment(
        title="Other Examiner Event Queue",
        status=AssessmentStatus.ACTIVE.value,
        duration_minutes=60,
        created_by_id=other_examiner.id,
    )
    db_session.add(assessment)
    db_session.flush()
    attempt = Attempt(
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        status=AttemptStatus.IN_PROGRESS.value,
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.refresh(assessment)

    token = _token(client, "examiner@example.com")
    response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_role_enum_values_are_used_for_seeded_users(db_session: Session) -> None:
    roles = set(db_session.scalars(select(User.role)).all())

    assert UserRole.CANDIDATE.value in roles
    assert UserRole.PROCTOR.value in roles
    assert UserRole.EXAMINER.value in roles
