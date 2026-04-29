import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.wallet import WalletAccount, WalletTransaction


class WalletService:
    @staticmethod
    def get_or_create_account(db: Session, user_id: uuid.UUID, for_update: bool = False) -> WalletAccount:
        dialect_name = db.get_bind().dialect.name
        if dialect_name == "postgresql":
            db.execute(
                insert(WalletAccount)
                .values(user_id=user_id, balance=0)
                .on_conflict_do_nothing(index_elements=[WalletAccount.user_id])
            )
        else:
            account = db.scalar(select(WalletAccount).where(WalletAccount.user_id == user_id))
            if not account:
                try:
                    with db.begin_nested():
                        db.add(WalletAccount(user_id=user_id, balance=0))
                        db.flush()
                except IntegrityError:
            # Аккаунт мог быть создан другой параллельной транзакцией.
                    pass

        query = select(WalletAccount).where(WalletAccount.user_id == user_id)
        if for_update:
            query = query.with_for_update()

        account = db.scalar(query)
        if account:
            return account

        # Защитная проверка: после ON CONFLICT DO NOTHING и повторного чтения аккаунт должен существовать.
        account = db.scalar(select(WalletAccount).where(WalletAccount.user_id == user_id))
        if account:
            return account
        raise HTTPException(status_code=500, detail="Failed to initialize wallet account")

    @staticmethod
    def get_account_for_user(db: Session, user_id: uuid.UUID, for_update: bool = False) -> WalletAccount:
        query = select(WalletAccount).where(WalletAccount.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        account = db.scalar(query)
        if not account:
            raise HTTPException(status_code=404, detail="Wallet account not found")
        return account

    @staticmethod
    def add_credits(
        db: Session,
        user_id: uuid.UUID,
        amount: int,
        tx_type: str,
        reason: str | None = None,
        event_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> WalletTransaction:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")

        account = WalletService.get_or_create_account(db, user_id, for_update=True)
        account.balance += amount

        tx = WalletTransaction(
            wallet_account_id=account.id,
            tx_type=tx_type,
            amount=amount,
            reason=reason,
            event_id=event_id,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        db.add(tx)
        db.flush()
        return tx

    @staticmethod
    def spend_credits(
        db: Session,
        user_id: uuid.UUID,
        amount: int,
        reason: str | None = None,
        event_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        tx_type: str = "spend",
    ) -> WalletTransaction:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")

        account = WalletService.get_account_for_user(db, user_id, for_update=True)
        if account.balance < amount:
            raise HTTPException(status_code=400, detail="Not enough credits")

        account.balance -= amount
        tx = WalletTransaction(
            wallet_account_id=account.id,
            tx_type=tx_type,
            amount=amount,
            reason=reason,
            event_id=event_id,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        db.add(tx)
        db.flush()
        return tx

    @staticmethod
    def credit(
        db: Session,
        user_id: uuid.UUID,
        amount: int,
        reason: str | None = None,
        event_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> WalletTransaction:
        """Add credits to a user's wallet (convenience wrapper for add_credits)."""
        return WalletService.add_credits(
            db, user_id, amount, tx_type="credit", reason=reason,
            event_id=event_id, idempotency_key=idempotency_key
        )
