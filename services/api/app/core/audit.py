from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    request: Request,
    *,
    actor_id: UUID | None,
    action: str,
    target_type: str,
    target_id: UUID | None = None,
    details: dict | None = None,
) -> None:
    client = request.client
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            ip_address=client.host[:64] if client else None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
        )
    )
