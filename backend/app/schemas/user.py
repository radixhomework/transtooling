"""User request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.user import UserRole
from app.schemas.password import validate_password_strength


class UserCreateRequest(BaseModel):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    password: str
    role: UserRole = UserRole.user

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserResponse(BaseModel):
    id: int
    login: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
