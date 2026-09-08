"""View layer of the MVC structure: request/response DTOs (Pydantic models).

Re-exports every domain schema so controllers can keep a single import site:
``from app.schemas import UserCreateRequest``.
"""

from app.schemas.app_settings import (
    AppSettingsResponse,
    AppSettingsUpdateRequest,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.job import JobResponse
from app.schemas.translation import (
    TranslationJobCreateRequest,
    TranslationModelResponse,
    TranslationModelUpdateRequest,
)
from app.schemas.user import (
    AdminResetPasswordRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.schemas.whisper_model import (
    EnabledModelResponse,
    WhisperModelResponse,
    WhisperModelUpdateRequest,
)

__all__ = [
    "AppSettingsResponse",
    "AppSettingsUpdateRequest",
    "ChangePasswordRequest",
    "EnabledModelResponse",
    "JobResponse",
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    "TranslationJobCreateRequest",
    "TranslationModelResponse",
    "TranslationModelUpdateRequest",
    "AdminResetPasswordRequest",
    "UserCreateRequest",
    "UserResponse",
    "UserUpdateRequest",
    "WhisperModelResponse",
    "WhisperModelUpdateRequest",
]
