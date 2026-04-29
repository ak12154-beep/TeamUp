from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User


def sync_primary_admin_access() -> None:
    db = SessionLocal()
    try:
        admin_user = db.scalar(select(User).where(User.email == settings.primary_admin_email))
        if not admin_user:
            return

        changed = False
        if admin_user.role == "admin":
            admin_user.role = "player"
            changed = True
        if not admin_user.is_admin:
            admin_user.is_admin = True
            changed = True

        if changed:
            db.commit()
    finally:
        db.close()
