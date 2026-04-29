import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.models.email_verification import EmailVerificationCode
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
    TokenResponse,
)
from app.services.email_service import EmailService
from app.services.email_verification_service import (
    generate_numeric_code,
    hash_verification_code,
    validate_verification_code,
)
from app.services.login_rate_limiter import login_rate_limiter, verification_code_rate_limiter
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/auth")

INITIAL_CREDITS = 0
logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """Извлекает IP клиента с учетом прокси-заголовка X-Forwarded-For."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.client.host if request.client else "unknown"


@router.post("/send-code")
def send_verification_code(
    payload: SendVerificationCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Отправляет код верификации email с защитой от частых повторных запросов."""
    verification_code_rate_limiter.hit(_get_client_ip(request))
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")

    now = datetime.now(UTC)
    existing = db.scalar(select(EmailVerificationCode).where(EmailVerificationCode.email == email))

    if existing and existing.last_sent_at + timedelta(seconds=settings.verification_resend_sec) > now:
        seconds_left = int((existing.last_sent_at + timedelta(seconds=settings.verification_resend_sec) - now).total_seconds())
        retry_after = max(1, seconds_left)
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {retry_after}s before requesting a new code",
            headers={"Retry-After": str(retry_after)},
        )

    code = generate_numeric_code(settings.verification_code_length)
    code_hash = hash_verification_code(email, code)
    expires_at = now + timedelta(minutes=settings.verification_code_ttl_min)

    if existing:
        existing.code_hash = code_hash
        existing.expires_at = expires_at
        existing.last_sent_at = now
    else:
        db.add(
            EmailVerificationCode(
                email=email,
                code_hash=code_hash,
                expires_at=expires_at,
                last_sent_at=now,
            )
        )

    try:
        EmailService.send_verification_code(email, code)
    except Exception as exc:
        db.rollback()
        logger.warning("auth.send_code.failed email=%s reason=%s", email, exc)
        raise HTTPException(
            status_code=503,
            detail="Could not send verification email right now. Please try again later.",
        )

    db.commit()
    return {"detail": "Verification code sent"}


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Регистрирует нового пользователя и устанавливает auth-cookie с access-токеном."""
    if payload.role and payload.role.lower() != "player":
        raise HTTPException(status_code=400, detail="Public registration is only available for players")

    role = "player"

    email = payload.email.lower()
    exists = db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    code_entry = db.scalar(select(EmailVerificationCode).where(EmailVerificationCode.email == email))
    validate_verification_code(email, payload.verification_code, code_entry)

    user = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        birth_date=payload.birth_date,
        email=email,
        email_verified=True,
        password_hash=hash_password(payload.password),
        role=role,
        is_admin=False,
        onboarding_score=0,
    )
    db.add(user)
    db.flush()

    # Кошелек создается только для игроков; новый аккаунт стартует с нулевым балансом.
    if role == "player":
        WalletService.get_or_create_account(db, user.id)
        if INITIAL_CREDITS > 0:
            WalletService.credit(db, user.id, INITIAL_CREDITS, "Welcome bonus")

    db.delete(code_entry)
    db.commit()

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenResponse()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Проверяет учетные данные пользователя и выдает cookie-сессию."""
    email = payload.email.lower()
    client_ip = _get_client_ip(request)
    login_rate_limiter.check(email=email, ip_address=client_ip)

    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        login_rate_limiter.record_failure(email=email, ip_address=client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not verified")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()

    login_rate_limiter.reset(email=email, ip_address=client_ip)

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenResponse()


@router.post("/logout", status_code=204)
def logout(response: Response):
    """Завершает сессию пользователя удалением auth-cookie."""
    response.delete_cookie(
        key=settings.auth_cookie_name,
        domain=settings.auth_cookie_domain,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return None


def _set_auth_cookie(response: Response, token: str) -> None:
    """Устанавливает HttpOnly-cookie для авторизованной сессии."""
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_expire_min * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        path="/",
    )
