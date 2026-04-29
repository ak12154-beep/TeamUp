import hashlib
import secrets
import string
from datetime import UTC, datetime

from fastapi import HTTPException

from app.core.config import settings
from app.models.email_verification import EmailVerificationCode


def hash_verification_code(email: str, code: str) -> str:
    payload = f"{settings.jwt_secret}:{email}:{code}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_numeric_code(length: int | None = None) -> str:
    alphabet = string.digits
    code_length = length or settings.verification_code_length
    return "".join(secrets.choice(alphabet) for _ in range(code_length))


def validate_verification_code(email: str, submitted_code: str, code_entry: EmailVerificationCode | None) -> None:
    if not code_entry:
        raise HTTPException(status_code=400, detail="Verification code was not requested")

    now = datetime.now(UTC)
    if code_entry.expires_at < now:
        raise HTTPException(status_code=400, detail="Verification code expired. Request a new code")

    submitted_hash = hash_verification_code(email, submitted_code)
    if submitted_hash != code_entry.code_hash:
        raise HTTPException(status_code=400, detail="Invalid verification code")
