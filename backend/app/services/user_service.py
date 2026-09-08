"""Business logic for user account administration."""

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.user import User


def list_users(session: Session) -> list[User]:
    return session.exec(select(User)).all()


def create_user(session: Session, login_name: str, password: str, role) -> User:
    existing = session.exec(select(User).where(User.login == login_name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cet identifiant est déjà utilisé")

    user = User(
        login=login_name,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user(
    session: Session, user_id: int, is_active: bool | None, role
) -> User:
    user = _get_user_or_404(session, user_id)
    if is_active is not None:
        user.is_active = is_active
    if role is not None:
        user.role = role
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def reset_password(session: Session, user_id: int, new_password: str) -> None:
    user = _get_user_or_404(session, user_id)
    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()


def delete_user(session: Session, user_id: int, admin: User) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status_code=400, detail="Impossible de supprimer son propre compte"
        )
    user = _get_user_or_404(session, user_id)
    session.delete(user)
    session.commit()


def _get_user_or_404(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user
