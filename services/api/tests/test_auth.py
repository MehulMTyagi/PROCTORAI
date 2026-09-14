from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_roles
from app.models.enums import UserRole


def login(client: TestClient, email: str = "candidate@example.com") -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_returns_token_and_user(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "candidate@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["role"] == UserRole.CANDIDATE.value
    assert payload["user"]["email"] == "candidate@example.com"


def test_login_rejects_bad_password(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "candidate@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    token = login(client)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "candidate@example.com"


def test_role_dependency_allows_matching_role(client: TestClient) -> None:
    test_app = FastAPI()

    @test_app.get("/proctor-only")
    def proctor_only(_=Depends(require_roles(UserRole.PROCTOR))) -> dict[str, str]:
        return {"status": "allowed"}

    test_app.dependency_overrides.update(client.app.dependency_overrides)
    token = login(client, "proctor@example.com")

    with TestClient(test_app) as role_client:
        response = role_client.get(
            "/proctor-only",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200


def test_role_dependency_rejects_wrong_role(client: TestClient) -> None:
    test_app = FastAPI()

    @test_app.get("/proctor-only")
    def proctor_only(_=Depends(require_roles(UserRole.PROCTOR))) -> dict[str, str]:
        return {"status": "allowed"}

    test_app.dependency_overrides.update(client.app.dependency_overrides)
    token = login(client, "candidate@example.com")

    with TestClient(test_app) as role_client:
        response = role_client.get(
            "/proctor-only",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
