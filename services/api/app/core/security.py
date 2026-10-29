import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.core.config import settings

HASH_NAME = "sha256"
ARGON2 = PasswordHasher(
    time_cost=2,
    memory_cost=19_456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)
UNUSABLE_PASSWORD_HASH = ARGON2.hash(secrets.token_urlsafe(64))


def hash_password(password: str) -> str:
    return ARGON2.hash(password)


def consume_dummy_password_work(password: str) -> None:
    try:
        ARGON2.verify(UNUSABLE_PASSWORD_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        pass


def _verify_legacy_pbkdf2(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, expected_b64 = password_hash.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(expected_b64.encode("ascii"))
        digest = hashlib.pbkdf2_hmac(
            HASH_NAME,
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    if not password_hash.startswith("$argon2id$"):
        return True
    try:
        return ARGON2.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("$argon2id$"):
        try:
            return ARGON2.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    if password_hash.startswith("pbkdf2_sha256$"):
        return _verify_legacy_pbkdf2(password, password_hash)
    return False


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + (
        expires_delta or timedelta(minutes=settings.jwt_access_minutes)
    )
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256", headers={"typ": "JWT"})


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "iat", "exp", "iss", "aud", "jti"]},
        )
        if not isinstance(payload.get("jti"), str) or not payload["jti"]:
            raise credentials_error
        return payload
    except InvalidTokenError:
        raise credentials_error from None
