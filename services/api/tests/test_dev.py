from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.seed import upsert_dev_assessment, upsert_dev_users


def _token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_dev_bootstrap_returns_candidate_attempt(
    client: TestClient,
    db_session: Session,
) -> None:
    upsert_dev_users(db_session)
    upsert_dev_assessment(db_session)
    token = _token(client, "candidate@example.com")

    response = client.get("/dev/bootstrap", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["attempt_id"] is not None
    assert response.json()["assessment_title"] == "Week 2 Dummy Event Demo"


def test_dev_bootstrap_returns_proctor_assessment_without_attempt(
    client: TestClient,
    db_session: Session,
) -> None:
    upsert_dev_users(db_session)
    upsert_dev_assessment(db_session)
    token = _token(client, "proctor@example.com")

    response = client.get("/dev/bootstrap", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["attempt_id"] is None
