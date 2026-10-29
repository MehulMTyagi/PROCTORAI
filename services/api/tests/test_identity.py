from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.identity import settings
from app.models.identity_reference import IdentityReference
from app.models.user import User


def candidate_token(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "candidate@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_candidate_can_fetch_only_their_linked_identity_reference(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    image = b"\xff\xd8\xffuniversity-photo"
    (tmp_path / "candidate.jpg").write_bytes(image)
    candidate = db_session.query(User).filter_by(email="candidate@example.com").one()
    db_session.add(
        IdentityReference(
            user_id=candidate.id,
            relative_path="candidate.jpg",
            sha256_hash="a" * 64,
            source="university_import",
        )
    )
    db_session.commit()
    monkeypatch.setattr(settings, "identity_reference_dir", str(tmp_path))

    response = client.get(
        "/identity/reference",
        headers={"Authorization": f"Bearer {candidate_token(client)}"},
    )

    assert response.status_code == 200
    assert response.content == image
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store, private"


def test_identity_reference_requires_candidate_account(client: TestClient) -> None:
    token_response = client.post(
        "/auth/login",
        json={"email": "proctor@example.com", "password": "password123"},
    )
    assert token_response.status_code == 200

    response = client.get(
        "/identity/reference",
        headers={"Authorization": f"Bearer {token_response.json()['access_token']}"},
    )

    assert response.status_code == 403


def test_candidate_without_university_reference_gets_not_found(client: TestClient) -> None:
    response = client.get(
        "/identity/reference",
        headers={"Authorization": f"Bearer {candidate_token(client)}"},
    )

    assert response.status_code == 404


def test_candidate_can_enroll_once_and_cannot_replace_photo(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "identity_reference_dir", str(tmp_path))
    headers = {"Authorization": f"Bearer {candidate_token(client)}"}
    photo = b"\xff\xd8\xfffirst-camera-photo"

    enrolled = client.post(
        "/identity/reference",
        headers=headers,
        files={"image": ("identity.jpg", photo, "image/jpeg")},
    )
    replacement = client.post(
        "/identity/reference",
        headers=headers,
        files={"image": ("identity.jpg", b"\xff\xd8\xffdifferent-photo", "image/jpeg")},
    )

    assert enrolled.status_code == 201
    assert replacement.status_code == 409
    candidate = db_session.query(User).filter_by(email="candidate@example.com").one()
    reference = db_session.query(IdentityReference).filter_by(user_id=candidate.id).one()
    assert (tmp_path / reference.relative_path).read_bytes() == photo


def test_identity_enrollment_rejects_non_images(client: TestClient) -> None:
    response = client.post(
        "/identity/reference",
        headers={"Authorization": f"Bearer {candidate_token(client)}"},
        files={"image": ("identity.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 415
