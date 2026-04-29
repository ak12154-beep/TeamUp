from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.notification import Notification
from app.models.user import User
from app.models.wallet import WalletTransaction
from app.schemas.common import RequestModel
from app.schemas.wallet import WalletBalanceOut, WalletTransactionOut
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet")


class CreditRequestPayload(RequestModel):
    """Тело запроса на пополнение: желаемое число кредитов."""
    amount: int = Field(gt=0, le=100000)


@router.get("/me", response_model=WalletBalanceOut)
def wallet_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Возвращает текущий баланс кошелька пользователя."""
    account = WalletService.get_or_create_account(db, current_user.id)
    db.commit()
    return WalletBalanceOut(balance=account.balance)


@router.get("/transactions", response_model=list[WalletTransactionOut])
def get_transactions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Возвращает историю транзакций кошелька пользователя."""
    account = WalletService.get_account_for_user(db, current_user.id)
    transactions = db.scalars(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_account_id == account.id)
        .order_by(WalletTransaction.created_at.desc())
    ).all()
    return transactions


@router.post("/request-credits")
def request_credits(
    payload: CreditRequestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создает запрос на кредиты и уведомляет администраторов системы."""
    if current_user.role not in ("player",):
        raise HTTPException(status_code=403, detail="Only players can request credits")

    # Находим всех администраторов и отправляем им уведомления о запросе.
    admins = list(db.scalars(select(User).where(or_(User.is_admin.is_(True), User.role == "admin"))))
    for admin in admins:
        notification = Notification(
            user_id=admin.id,
            title="Credit Request",
            message=f"{current_user.email.split('@')[0]} requested {payload.amount} credits",
        )
        db.add(notification)

    db.commit()
    return {"ok": True, "message": f"Requested {payload.amount} credits. An admin will review your request."}
