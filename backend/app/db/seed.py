from sqlalchemy import select
from datetime import date

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.sport import Sport
from app.models.user import User
from app.services.wallet_service import WalletService


SPORTS = ["football", "basketball", "volleyball"]
TEST_USERS = [
    {
        "email": "admin@teamup.com",
        "password": "admin123",
        "role": "player",
        "first_name": "TeamUp",
        "last_name": "Admin",
        "birth_date": date(1990, 1, 1),
        "email_verified": True,
        "is_admin": True,
    },
    {
        "email": "user.test@teamup.kg",
        "password": "User123!",
        "role": "player",
        "first_name": "Test",
        "last_name": "User",
        "birth_date": date(1998, 2, 2),
        "email_verified": True,
        "is_admin": False,
    },
    {
        "email": "partner.test@teamup.kg",
        "password": "Partner123!",
        "role": "partner",
        "first_name": "Test",
        "last_name": "Partner",
        "birth_date": date(1995, 1, 1),
        "email_verified": True,
        "is_admin": False,
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        for name in SPORTS:
            if not db.scalar(select(Sport).where(Sport.name == name)):
                db.add(Sport(name=name))

        # Seed для проверки работоспособности приложения при проверке:
        # создаем тестовые аккаунты admin, user и partner.
        for payload in TEST_USERS:
            user = db.scalar(select(User).where(User.email == payload["email"]))
            if not user:
                user = User(
                    email=payload["email"],
                    password_hash=hash_password(payload["password"]),
                    role=payload["role"],
                    first_name=payload["first_name"],
                    last_name=payload["last_name"],
                    birth_date=payload["birth_date"],
                    email_verified=payload["email_verified"],
                    is_admin=payload["is_admin"],
                )
                db.add(user)
                db.flush()
            else:
                user.first_name = payload["first_name"]
                user.last_name = payload["last_name"]
                user.birth_date = payload["birth_date"]
                user.email_verified = payload["email_verified"]
                user.is_admin = payload["is_admin"]
                user.role = payload["role"]

            user.password_hash = hash_password(payload["password"])
            db.add(user)
            WalletService.get_or_create_account(db, user.id)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
