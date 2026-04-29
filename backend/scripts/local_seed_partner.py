from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.services.wallet_service import WalletService


def main() -> None:
    db = SessionLocal()
    try:
        email = "partner.test@teamup.kg"
        password = "Partner123!"
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                email=email,
                password_hash=hash_password(password),
                role="partner",
                first_name="Test",
                last_name="Partner",
                birth_date=date(1995, 1, 1),
                email_verified=True,
                is_admin=False,
            )
            db.add(user)
            db.flush()
            WalletService.get_or_create_account(db, user.id)

        user.password_hash = hash_password(password)
        user.role = "partner"
        user.email_verified = True
        db.add(user)
        db.commit()

        print(email)
        print(password)
    finally:
        db.close()


if __name__ == "__main__":
    main()
