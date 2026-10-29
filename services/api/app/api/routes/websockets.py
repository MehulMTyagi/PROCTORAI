from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.api.websocket_manager import websocket_manager
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.assessment import Assessment, AssessmentProctor
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()


@router.websocket("/ws/proctor/assessments/{assessment_id}")
async def proctor_assessment_events(websocket: WebSocket, assessment_id: UUID) -> None:
    origin = websocket.headers.get("origin")
    if origin not in settings.cors_origins:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    token = next(
        (
            protocol.removeprefix("auth.")
            for protocol in websocket.scope.get("subprotocols", [])
            if protocol.startswith("auth.")
        ),
        None,
    )
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assessment = db.get(Assessment, assessment_id)
        if user is None or not user.is_active or assessment is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        is_allowed = user.role == UserRole.ADMIN.value or (
            user.role == UserRole.EXAMINER.value and assessment.created_by_id == user.id
        )
        if user.role == UserRole.PROCTOR.value:
            is_allowed = (
                db.scalar(
                    select(AssessmentProctor).where(
                        AssessmentProctor.assessment_id == assessment_id,
                        AssessmentProctor.proctor_id == user.id,
                    )
                )
                is not None
            )

        if not is_allowed:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket_manager.connect(str(assessment_id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(str(assessment_id), websocket)
