import re
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

PASSWORD_MIN_LENGTH = 8

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__type="ID",
)


def hash_password(password: str) -> str:
    """Создает хэш пароля с использованием настроенного PasswordContext."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля и его хэша."""
    return pwd_context.verify(plain_password, hashed_password)


def password_needs_rehash(hashed_password: str) -> bool:
    """Определяет, нужно ли обновить хэш пароля по текущим правилам."""
    return pwd_context.needs_update(hashed_password)


def validate_password_strength(password: str) -> str:
    """Валидирует базовую сложность пароля."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include at least one digit")
    return password


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Формирует JWT access-token с временными claim-полями."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_min)
    )
    issued_at = datetime.now(timezone.utc)
    to_encode = {
        "exp": expire,
        "iat": issued_at,
        "nbf": issued_at,
        "sub": str(subject),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_alg)
