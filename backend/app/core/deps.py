from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _resolve_token_from_request(request: Request, bearer_token: str | None) -> str | None:
    if bearer_token:
        return bearer_token
    return request.cookies.get(settings.auth_cookie_name)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    resolved_token = _resolve_token_from_request(request, token)
    if not resolved_token:
        raise credentials_exception
    try:
        payload = jwt.decode(resolved_token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        sub = payload.get("sub")
        if not sub:
            raise credentials_exception
        user_id = UUID(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id)
    if not user:
        raise credentials_exception
    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_oauth2_scheme),
) -> User | None:
    resolved_token = _resolve_token_from_request(request, token)
    if not resolved_token:
        return None
    try:
        return get_current_user(request=request, db=db, token=resolved_token)
    except HTTPException:
        return None


def is_admin_user(user: User) -> bool:
    return bool(getattr(user, "is_admin", False) or user.role == "admin")


def user_has_role(user: User, role: str) -> bool:
    if role == "admin":
        return is_admin_user(user)
    return user.role == role


def require_roles(*roles: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(user_has_role(current_user, role) for role in roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return checker
