from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.seed import upsert_dev_assessment, upsert_dev_users
from app.models.assessment import Assessment
from app.models.question import Question
from app.models.session_health import SessionHeartbeat


def _token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _seed_assessment(db_session: Session) -> Assessment:
    upsert_dev_users(db_session)
    upsert_dev_assessment(db_session)
    assessment = db_session.scalar(select(Assessment).where(Assessment.title == "Week 2 Dummy Event Demo"))
    assert assessment is not None
    return assessment


def test_candidate_can_list_assigned_assessments(client: TestClient, db_session: Session) -> None:
    _seed_assessment(db_session)
    token = _token(client, "candidate@example.com")

    response = client.get("/assessments", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Week 2 Dummy Event Demo"


def test_candidate_can_start_save_and_submit_attempt(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment = _seed_assessment(db_session)
    question = db_session.scalar(
        select(Question).where(
            Question.assessment_id == assessment.id,
            Question.question_type == "MCQ",
        )
    )
    assert question is not None

    token = _token(client, "candidate@example.com")
    start_response = client.post(
        "/attempts/start",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": str(assessment.id)},
    )
    assert start_response.status_code == 201
    attempt_id = start_response.json()["attempt_id"]

    answer_response = client.post(
        f"/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": str(question.id), "selected_option": "queue"},
    )
    assert answer_response.status_code == 200

    submit_response = client.post(
        f"/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "SUBMITTED"
    assert submit_response.json()["score"] == 5
    assert submit_response.json()["total_points"] == 10


def test_candidate_can_record_session_heartbeat(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment = _seed_assessment(db_session)
    token = _token(client, "candidate@example.com")
    start_response = client.post(
        "/attempts/start",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": str(assessment.id)},
    )
    assert start_response.status_code == 201
    attempt_id = start_response.json()["attempt_id"]

    response = client.post(
        f"/attempts/{attempt_id}/heartbeats",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "status": "OK",
            "metrics": {
                "consent_accepted": True,
                "camera_available": True,
                "microphone_available": True,
                "ai_sidecar_reachable": False,
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["attempt_id"] == attempt_id
    assert payload["status"] == "OK"
    assert payload["metrics"]["consent_accepted"] is True

    heartbeat = db_session.get(SessionHeartbeat, UUID(payload["id"]))
    assert heartbeat is not None
    assert heartbeat.metrics["camera_available"] is True


def test_proctor_cannot_record_candidate_heartbeat(client: TestClient, db_session: Session) -> None:
    assessment = _seed_assessment(db_session)
    candidate_token = _token(client, "candidate@example.com")
    start_response = client.post(
        "/attempts/start",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"assessment_id": str(assessment.id)},
    )
    assert start_response.status_code == 201

    proctor_token = _token(client, "proctor@example.com")
    response = client.post(
        f"/attempts/{start_response.json()['attempt_id']}/heartbeats",
        headers={"Authorization": f"Bearer {proctor_token}"},
        json={"status": "OK", "metrics": {}},
    )

    assert response.status_code == 403


def test_submitted_attempt_rejects_new_heartbeat(client: TestClient, db_session: Session) -> None:
    assessment = _seed_assessment(db_session)
    question = db_session.scalar(
        select(Question).where(
            Question.assessment_id == assessment.id,
            Question.question_type == "MCQ",
        )
    )
    assert question is not None
    token = _token(client, "candidate@example.com")
    start_response = client.post(
        "/attempts/start",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": str(assessment.id)},
    )
    attempt_id = start_response.json()["attempt_id"]
    client.post(
        f"/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": str(question.id), "selected_option": "queue"},
    )
    submit_response = client.post(
        f"/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_response.status_code == 200

    heartbeat_response = client.post(
        f"/attempts/{attempt_id}/heartbeats",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "OK", "metrics": {}},
    )

    assert heartbeat_response.status_code == 409


def test_proctor_cannot_start_candidate_attempt(client: TestClient, db_session: Session) -> None:
    assessment = _seed_assessment(db_session)
    token = _token(client, "proctor@example.com")

    response = client.post(
        "/attempts/start",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_id": str(assessment.id)},
    )

    assert response.status_code == 403
