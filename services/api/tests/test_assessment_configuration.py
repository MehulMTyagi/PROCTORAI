from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.assessment import Assessment
from app.models.user import User


def headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_persists_selected_people_and_policy_and_limits_access(
    client: TestClient,
    db_session: Session,
) -> None:
    users = {user.role: user for user in db_session.scalars(select(User))}
    for role in ("CANDIDATE", "PROCTOR"):
        db_session.add(
            User(
                email=f"other-{role.lower()}@example.com",
                full_name=f"Other {role}",
                role=role,
                password_hash=hash_password("password123"),
            )
        )
    db_session.commit()
    examiner = headers(client, "examiner@example.com")
    rules = {"PHONE_DETECTED": {"enabled": False}, "FULLSCREEN_EXIT": {"enabled": True}}
    response = client.post(
        "/assessments",
        headers=examiner,
        json={
            "title": "Selected people assessment",
            "status": "ACTIVE",
            "candidate_ids": [str(users["CANDIDATE"].id)],
            "proctor_ids": [str(users["PROCTOR"].id)],
            "rules": rules,
        },
    )
    assert response.status_code == 201
    assessment_id = response.json()["id"]
    detail = client.get(f"/assessments/{assessment_id}", headers=examiner).json()
    assert detail["candidate_ids"] == [str(users["CANDIDATE"].id)]
    assert detail["proctor_ids"] == [str(users["PROCTOR"].id)]
    assert detail["rules"] == rules
    for email in ("candidate@example.com", "proctor@example.com"):
        account = headers(client, email)
        assert assessment_id in {
            item["id"] for item in client.get("/assessments", headers=account).json()
        }
        response = client.get(f"/assessments/{assessment_id}", headers=account)
        assert response.status_code == 200
        assert response.json()["rules"] == rules
        assert response.json()["candidate_ids"] == []  # Do not disclose other participants.
    for email in ("other-candidate@example.com", "other-proctor@example.com"):
        account = headers(client, email)
        assert assessment_id not in {
            item["id"] for item in client.get("/assessments", headers=account).json()
        }
        assert client.get(f"/assessments/{assessment_id}", headers=account).status_code == 403

    # Replacing selections removes access as well as adding it.
    other_candidate = db_session.scalar(
        select(User).where(User.email == "other-candidate@example.com")
    )
    replacement = {"candidate_ids": [str(other_candidate.id)], "proctor_ids": []}
    assert (
        client.put(
            f"/assessments/{assessment_id}/assignments", headers=examiner, json=replacement
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/assessments/{assessment_id}", headers=headers(client, "candidate@example.com")
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/assessments/{assessment_id}", headers=headers(client, "proctor@example.com")
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/assessments/{assessment_id}", headers=headers(client, "other-candidate@example.com")
        ).status_code
        == 200
    )


@pytest.mark.parametrize("invalid", ["missing", "wrong-role"])
def test_invalid_selection_does_not_leave_partial_assessment(
    client: TestClient,
    db_session: Session,
    invalid: str,
) -> None:
    examiner = headers(client, "examiner@example.com")
    proctor = db_session.scalar(select(User).where(User.role == "PROCTOR"))
    before = db_session.scalar(select(func.count()).select_from(Assessment))
    response = client.post(
        "/assessments",
        headers=examiner,
        json={
            "title": "Invalid assignment",
            "candidate_ids": [str(uuid4() if invalid == "missing" else proctor.id)],
            "proctor_ids": [str(proctor.id)],
        },
    )
    assert response.status_code == 400
    assert db_session.scalar(select(func.count()).select_from(Assessment)) == before


def test_disabled_monitoring_is_rejected_and_policy_cannot_be_changed_by_candidate(
    client: TestClient,
    db_session: Session,
) -> None:
    examiner = headers(client, "examiner@example.com")
    candidate = db_session.scalar(select(User).where(User.role == "CANDIDATE"))
    response = client.post(
        "/assessments",
        headers=examiner,
        json={
            "title": "Policy enforcement",
            "status": "ACTIVE",
            "candidate_ids": [str(candidate.id)],
            "rules": {"PHONE_DETECTED": {"enabled": False}, "SCREEN_RECORDING": {"enabled": False}},
        },
    )
    assessment_id = response.json()["id"]
    account = headers(client, "candidate@example.com")
    attempt = client.post(
        "/attempts/start", headers=account, json={"assessment_id": assessment_id}
    ).json()["attempt_id"]
    event = {
        "event_type": "PHONE_DETECTED",
        "severity": "HIGH",
        "confidence": 1,
        "priority_score": 8,
        "metadata": {},
    }
    assert (
        client.post(f"/attempts/{attempt}/events", headers=account, json=event).status_code == 409
    )
    event["event_type"] = "CLIPBOARD_COPY"
    response = client.post(f"/attempts/{attempt}/events", headers=account, json=event)
    assert response.status_code == 201
    event_id = response.json()["id"]
    assert (
        client.post(
            f"/attempts/{attempt}/events/{event_id}/evidence",
            headers=account,
            data={"kind": "SCREEN_RECORDING"},
            files={"file": ("test.webm", b"test", "video/webm")},
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/assessments/{assessment_id}/rules", headers=account, json={"rules": {}}
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/assessments/{assessment_id}/assignments", headers=account, json={"candidate_ids": []}
        ).status_code
        == 403
    )
