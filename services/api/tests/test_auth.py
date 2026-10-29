from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import require_roles
from app.api.routes import auth as auth_routes
from app.models.enums import UserRole
from app.models.user import User


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


def test_admin_roster_import_creates_accounts_then_student_activates(client: TestClient, db_session, monkeypatch) -> None:
    monkeypatch.setattr(auth_routes.settings, "app_env", "development")
    monkeypatch.setattr(auth_routes.settings, "smtp_host", None)
    monkeypatch.setattr(auth_routes.settings, "smtp_from_email", None)
    admin_token = login(client, "admin@example.com")
    imported = client.post(
        "/users/import-roster",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("roster.csv", "roll_number,full_name,program,admission_year,section\nS24BCAU0044,New Student,BCA,2024,A\n", "text/csv")},
    )
    assert imported.status_code == 200
    assert imported.json()["created"] == 1
    assert imported.json()["rejected"] == 0
    email = "s24bcau0044@bennett.edu.in"
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.full_name == "New Student"
    assert user.role == UserRole.CANDIDATE.value
    assert user.is_active is False
    assert client.post("/auth/login", json={"email": email, "password": "anything-long-enough"}).status_code == 401

    requested = client.post("/auth/activation/request", json={"email": email})
    assert requested.status_code == 202
    code = requested.json()["dev_verification_code"]
    assert len(code) == 6
    activated = client.post(
        "/auth/activation/complete",
        json={"email": email, "code": code, "password": "a-long-test-password"},
    )
    assert activated.status_code == 200
    assert activated.json()["user"]["is_active"] is True
    assert activated.json()["user"]["role"] == UserRole.CANDIDATE.value
    assert activated.json()["user"]["roll_number"] == "S24BCAU0044"
    assert activated.json()["user"]["program"] == "BCA"
    assert activated.json()["user"]["admission_year"] == 2024
    assert activated.json()["user"]["section"] == "A"
    assert client.post("/auth/login", json={"email": email, "password": "a-long-test-password"}).status_code == 200


def test_roster_import_is_admin_only_and_repeatable(client: TestClient) -> None:
    csv_data = "roll_number,full_name,program,admission_year,section\nS24BCAU0045,Another Student,BCA,2024,B\n"
    response = client.post(
        "/users/import-roster",
        headers={"Authorization": f"Bearer {login(client)}"},
        files={"file": ("roster.csv", csv_data, "text/csv")},
    )
    assert response.status_code == 403
    headers = {"Authorization": f"Bearer {login(client, 'admin@example.com')}"}
    first = client.post("/users/import-roster", headers=headers, files={"file": ("roster.csv", csv_data, "text/csv")})
    second = client.post("/users/import-roster", headers=headers, files={"file": ("roster.csv", csv_data, "text/csv")})
    assert first.json()["created"] == 1
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 1


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
