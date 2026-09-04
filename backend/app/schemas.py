from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.user import UserRole
from app.models.job import JobStatus
from app.models.whisper_model import ModelStatus

MIN_PASSWORD_LENGTH = 8


def _validate_password_strength(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères"
        )
    if not any(c.isdigit() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre")
    if not any(c.isalpha() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins une lettre")
    return password


# --- Auth ---

class LoginRequest(BaseModel):
    login: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


# --- Utilisateurs ---

class UserCreateRequest(BaseModel):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    password: str
    role: UserRole = UserRole.user

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserResponse(BaseModel):
    id: int
    login: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Jobs de transcription ---

class JobResponse(BaseModel):
    id: int
    user_id: int
    filename_original: str
    model_used: str
    language: str
    status: JobStatus
    error_message: Optional[str] = None
    progress: Optional[int] = None
    audio_duration_seconds: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Modèles Whisper ---

class WhisperModelResponse(BaseModel):
    id: int
    name: str
    status: ModelStatus
    is_enabled: bool
    is_default: bool
    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None
    error_message: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WhisperModelUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class EnabledModelResponse(BaseModel):
    """Modèle proposé aux utilisateurs (sélecteur d'upload) : téléchargé et activé."""

    name: str
    is_default: bool

    class Config:
        from_attributes = True


# --- Paramètres applicatifs ---

class AppSettingsResponse(BaseModel):
    max_file_size_mb: int
    max_duration_min: float
    max_text_length_chars: int
    preview_truncate_chars: int
    max_archive_size_mb: int
    max_archive_files_count: int
    max_archive_uncompressed_mb: int
    translatable_extensions: str


class AppSettingsUpdateRequest(BaseModel):
    max_file_size_mb: Optional[int] = None
    max_duration_min: Optional[float] = None
    max_text_length_chars: Optional[int] = None
    preview_truncate_chars: Optional[int] = None
    max_archive_size_mb: Optional[int] = None
    max_archive_files_count: Optional[int] = None
    max_archive_uncompressed_mb: Optional[int] = None
    translatable_extensions: Optional[str] = None


# --- Traduction ---

class TranslationJobCreateRequest(BaseModel):
    direction: str  # "fr-en" | "en-fr"
    text: str = Field(min_length=1)


class TranslationModelResponse(BaseModel):
    id: int
    direction: str
    status: str
    is_enabled: bool
    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None
    error_message: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TranslationModelUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
