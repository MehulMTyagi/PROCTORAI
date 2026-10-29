from fastapi import APIRouter

from app.api.routes import (
    assessments,
    attempts,
    auth,
    dev,
    events,
    health,
    identity,
    users,
    websockets,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(assessments.router, tags=["assessments"])
api_router.include_router(attempts.router, tags=["attempts"])
api_router.include_router(auth.router, tags=["auth"])
if settings.app_env.lower() not in {"production", "prod"}:
    api_router.include_router(dev.router, tags=["dev"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(identity.router, tags=["identity"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(websockets.router, tags=["websockets"])
