from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ActivationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ActivateAccountRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    code: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=12, max_length=128)


class ActivationResponse(BaseModel):
    email: str
    message: str
    dev_verification_code: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    roll_number: str | None = None
    program: str | None = None
    admission_year: int | None = None
    section: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
