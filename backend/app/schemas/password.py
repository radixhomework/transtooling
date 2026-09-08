"""Shared password validation used by every request schema accepting a password."""

from pydantic import BaseModel, field_validator

MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères"
        )
    if not any(c.isdigit() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre")
    if not any(c.isalpha() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins une lettre")
    return password
