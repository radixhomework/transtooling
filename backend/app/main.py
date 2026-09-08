from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.controllers import app_settings, auth, jobs, translation, users, whisper_models
from app.core.config import settings
from app.core.database import engine, init_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services.app_settings_service import ensure_app_settings

app = FastAPI(title="Transcription Audio FR - API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(whisper_models.router)
app.include_router(whisper_models.public_router)
app.include_router(app_settings.router)
app.include_router(translation.router)
app.include_router(translation.admin_models_router)


@app.on_event("startup")
def on_startup():
    init_db()
    _ensure_admin_account()
    ensure_app_settings()


def _ensure_admin_account() -> None:
    """Creates the initial administrator account defined in .env, if it does not exist yet."""
    # ADMIN_LOGIN is the expected variable; ADMIN_EMAIL is still read as a
    # legacy fallback for installations predating the login-based accounts.
    admin_login = settings.admin_login or settings.admin_email or "admin"
    with Session(engine) as session:
        existing_admin = session.exec(
            select(User).where(User.login == admin_login)
        ).first()
        if existing_admin:
            return

        admin = User(
            login=admin_login,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.admin,
            is_active=True,
        )
        session.add(admin)
        session.commit()


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok"}
