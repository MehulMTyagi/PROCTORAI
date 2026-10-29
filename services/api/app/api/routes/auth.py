import hashlib
import hmac
import secrets
import smtplib
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import write_audit_log
from app.core.config import settings
from app.core.email import send_verification_code
from app.core.security import (
    consume_dummy_password_work,
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.db.session import get_db
from app.models.email_verification import EmailVerification
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import (
    ActivateAccountRequest,
    ActivationRequest,
    ActivationResponse,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth")
VERIFICATION_MINUTES = 15
VERIFICATION_MAX_ATTEMPTS = 5
VERIFICATION_RESEND_SECONDS = 60


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _code_digest(email: str, code: str) -> str:
    value = f"{email}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode("utf-8"), value, hashlib.sha256).hexdigest()


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _deliver_code(email: str, code: str) -> str | None:
    if not settings.smtp_host or not settings.smtp_from_email:
        if settings.app_env.lower() in {"development", "dev", "test"}:
            return code
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account verification email is unavailable. Contact the administrator.",
        )
    try:
        send_verification_code(email, code)
    except (OSError, RuntimeError, smtplib.SMTPException) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send the verification email. Please retry later.",
        ) from exc
    return None


def _issue_verification(db: Session, user: User) -> str | None:
    code = _new_code()
    now = datetime.now(UTC)
    record = db.scalar(
        select(EmailVerification).where(EmailVerification.user_id == user.id)
    )
    if record is None:
        record = EmailVerification(user_id=user.id)
        db.add(record)
    record.code_hash = _code_digest(user.email, code)
    record.sent_at = now
    record.expires_at = now + timedelta(minutes=VERIFICATION_MINUTES)
    record.attempts = 0
    return _deliver_code(user.email, code)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))

    password_valid = (
        verify_password(payload.password, user.password_hash)
        if user is not None
        else False
    )
    if user is None:
        consume_dummy_password_work(payload.password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    write_audit_log(
        db,
        request,
        actor_id=user.id,
        action="user_login_succeeded",
        target_type="user",
        target_id=user.id,
    )
    db.commit()

    access_token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/activation/request", response_model=ActivationResponse, status_code=202)
def request_account_activation(
    payload: ActivationRequest, db: Session = Depends(get_db)
) -> ActivationResponse:
    email = _normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    eligible = (
        user is not None
        and user.role == UserRole.CANDIDATE.value
        and user.roll_number is not None
        and not user.is_active
    )
    dev_code = None
    if eligible:
        record = db.scalar(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        if record is not None:
            sent_at = record.sent_at
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=UTC)
            if datetime.now(UTC) - sent_at < timedelta(seconds=VERIFICATION_RESEND_SECONDS):
                return ActivationResponse(
                    email=email,
                    message=(
                        "If this account is on the university roster, an activation code "
                        "will be sent."
                    ),
                )
        try:
            dev_code = _issue_verification(db, user)
            db.commit()
        except HTTPException:
            db.rollback()
            raise
    return ActivationResponse(
        email=email,
        message=(
            "If this account is on the university roster, an activation code will be sent."
        ),
        dev_verification_code=dev_code,
    )


@router.post("/activation/complete", response_model=TokenResponse)
def activate_candidate_account(
    payload: ActivateAccountRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = _normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    record = (
        db.scalar(select(EmailVerification).where(EmailVerification.user_id == user.id))
        if user is not None
        else None
    )
    if (
        user is None
        or user.role != UserRole.CANDIDATE.value
        or user.roll_number is None
        or user.is_active
        or record is None
    ):
        raise HTTPException(status_code=400, detail="Activation code is invalid or expired.")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if datetime.now(UTC) >= expires_at:
        raise HTTPException(status_code=400, detail="Activation code expired. Request a new code.")
    if record.attempts >= VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    record.attempts += 1
    if not hmac.compare_digest(record.code_hash, _code_digest(email, payload.code)):
        db.commit()
        raise HTTPException(status_code=400, detail="Activation code is invalid or expired.")

    user.password_hash = hash_password(payload.password)
    user.is_active = True
    db.delete(record)
    write_audit_log(
        db,
        request,
        actor_id=user.id,
        action="candidate_account_activated",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    return TokenResponse(
        access_token=create_access_token(subject=str(user.id), role=user.role),
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
