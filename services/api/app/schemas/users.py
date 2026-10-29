from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeachingGroupCreate(BaseModel):
    examiner_id: UUID
    program: str = Field(min_length=1, max_length=100)
    admission_year: int = Field(ge=2000, le=2100)
    section: str = Field(min_length=1, max_length=100)

    @field_validator("program", "section")
    @classmethod
    def normalize_group_text(cls, value: str) -> str:
        return " ".join(value.split())


class TeachingGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    examiner_id: UUID
    program: str
    admission_year: int
    section: str
