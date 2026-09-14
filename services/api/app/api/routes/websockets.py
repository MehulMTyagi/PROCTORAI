from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.api.websocket_manager import websocket_manager
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.assessment import AssessmentProctor
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()


@router.websocket("/ws/proctor/assessments/{assessment_id}")
async def proctor_assessment_events(websocket: WebSocket, assessment_id: UUID) -> None:
    token = websocket.query_params.get("token")
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
        if user is None or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        is_allowed = user.role in {UserRole.EXAMINER.value, UserRole.ADMIN.value}
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
