from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.assessment import Assessment
from app.models.enums import AssessmentStatus, UserRole
from app.models.user import User


def _token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_examiner_can_create_assessment_and_question(client: TestClient) -> None:
    token = _token(client, "examiner@example.com")

    assessment_response = client.post(
        "/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Week 3 Assessment",
            "description": "Assessment CRUD test",
            "duration_minutes": 45,
            "status": "DRAFT",
        },
    )

    assert assessment_response.status_code == 201
    assessment_id = assessment_response.json()["id"]

    question_response = client.post(
        f"/assessments/{assessment_id}/questions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "prompt": "Which data structure uses FIFO ordering?",
            "question_type": "MCQ",
            "options": [
                {"id": "stack", "label": "Stack"},
                {"id": "queue", "label": "Queue"},
            ],
            "correct_answer": "queue",
            "points": 5,
            "display_order": 1,
        },
    )

    assert question_response.status_code == 201
    assert question_response.json()["correct_answer"] == "queue"


def test_examiner_only_lists_owned_assessments(
    client: TestClient,
    db_session: Session,
) -> None:
    owner = db_session.scalar(select(User).where(User.email == "examiner@example.com"))
    other_examiner = User(
        email="other-examiner@example.com",
        full_name="Other Examiner",
        role=UserRole.EXAMINER.value,
        password_hash=hash_password("password123"),
    )
    assert owner is not None
    db_session.add(other_examiner)
    db_session.flush()
    db_session.add_all(
        [
            Assessment(
                title="Owned Assessment",
                status=AssessmentStatus.ACTIVE.value,
                created_by_id=owner.id,
            ),
            Assessment(
                title="Other Examiner Assessment",
                status=AssessmentStatus.ACTIVE.value,
                created_by_id=other_examiner.id,
            ),
        ]
    )
    db_session.commit()

    token = _token(client, "examiner@example.com")
    response = client.get("/assessments", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    titles = {assessment["title"] for assessment in response.json()}
    assert "Owned Assessment" in titles
    assert "Other Examiner Assessment" not in titles


def test_examiner_cannot_manage_another_examiner_assessment(
    client: TestClient,
    db_session: Session,
) -> None:
    other_examiner = User(
        email="other-owner@example.com",
        full_name="Other Owner",
        role=UserRole.EXAMINER.value,
        password_hash=hash_password("password123"),
    )
    db_session.add(other_examiner)
    db_session.flush()
    assessment = Assessment(
        title="Private Other Assessment",
        status=AssessmentStatus.ACTIVE.value,
        created_by_id=other_examiner.id,
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)
    candidate = db_session.scalar(select(User).where(User.email == "candidate@example.com"))
    assert candidate is not None

    token = _token(client, "examiner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    detail_response = client.get(f"/assessments/{assessment.id}", headers=headers)
    update_response = client.put(
        f"/assessments/{assessment.id}",
        headers=headers,
        json={"title": "Hijacked Assessment"},
    )
    question_response = client.post(
        f"/assessments/{assessment.id}/questions",
        headers=headers,
        json={"prompt": "Unauthorized question"},
    )
    assignment_response = client.post(
        f"/assessments/{assessment.id}/candidates",
        headers=headers,
        json={"user_id": str(candidate.id)},
    )
    rules_response = client.put(
        f"/assessments/{assessment.id}/rules",
        headers=headers,
        json={"rules": {"APP_FOCUS_LOST": {"enabled": True}}},
    )

    assert detail_response.status_code == 403
    assert update_response.status_code == 403
    assert question_response.status_code == 403
    assert assignment_response.status_code == 403
    assert rules_response.status_code == 403


def test_candidate_cannot_create_assessment(client: TestClient) -> None:
    token = _token(client, "candidate@example.com")

    response = client.post(
        "/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Forbidden Assessment"},
    )

    assert response.status_code == 403


def test_examiner_can_assign_candidate_and_proctor(
    client: TestClient,
    db_session: Session,
) -> None:
    token = _token(client, "examiner@example.com")
    users = {user.email: user for user in db_session.scalars(select(User)).all()}

    assessment_response = client.post(
        "/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Assignment Test"},
    )
    assessment_id = assessment_response.json()["id"]

    candidate_response = client.post(
        f"/assessments/{assessment_id}/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": str(users["candidate@example.com"].id)},
    )
    proctor_response = client.post(
        f"/assessments/{assessment_id}/proctors",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": str(users["proctor@example.com"].id)},
    )

    assert candidate_response.status_code == 204
    assert proctor_response.status_code == 204


def test_users_endpoint_filters_roles(client: TestClient) -> None:
    token = _token(client, "examiner@example.com")

    response = client.get("/users?role=CANDIDATE", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()[0]["role"] == "CANDIDATE"


def test_examiner_is_limited_to_assigned_student_groups(
    client: TestClient,
    db_session: Session,
) -> None:
    outside_candidate = User(
        email="outside@example.com",
        full_name="Outside Section Student",
        role=UserRole.CANDIDATE.value,
        password_hash=hash_password("password123"),
        roll_number="S24BCAU9001",
        program="BCA",
        admission_year=2024,
        section="B",
    )
    db_session.add(outside_candidate)
    db_session.commit()
    token = _token(client, "examiner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    listed = client.get("/users?role=CANDIDATE", headers=headers)
    assert listed.status_code == 200
    assert "outside@example.com" not in {person["email"] for person in listed.json()}

    assessment = client.post(
        "/assessments",
        headers=headers,
        json={"title": "Outside group test", "candidate_ids": [str(outside_candidate.id)]},
    )
    assert assessment.status_code == 403
