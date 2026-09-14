from uuid import UUID

from pydantic import BaseModel


class DevBootstrapResponse(BaseModel):
    assessment_id: UUID
    assessment_title: str
    attempt_id: UUID | None
    role: str
