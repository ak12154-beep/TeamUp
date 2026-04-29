import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.routes.events import _enrich_event
from app.core.deps import get_db, require_roles
from app.core.security import hash_password
from app.models.email_verification import EmailVerificationCode
from app.models.event import Event
from app.models.participant import EventParticipant
from app.models.tournament_registration import TournamentRegistration
from app.models.user import User
from app.models.wallet import WalletTransaction, WalletAccount
from app.schemas.event import (
    EventOut,
    TournamentCreateRequest,
    TournamentRegistrationAdminOut,
    TournamentRegistrationAdminUpdate,
)
from app.schemas.user import AdminCreatePartnerRequest, AdminUserRoleUpdateRequest, UserOut
from app.services.email_verification_service import validate_verification_code
from app.schemas.wallet import (
    WalletBalanceOut,
    WalletGrantRevokeRequest,
    WalletGrantRequest,
    WalletTransactionOut,
)
from app.services.event_service import EventService
from app.services.player_rating_service import calculate_player_rating
from app.services.pricing import calculate_pricing_breakdown
from app.services.tournament_service import TournamentService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/admin")


def _serialize_tournament_registration_admin(
    registration: TournamentRegistration,
) -> TournamentRegistrationAdminOut:
    return TournamentRegistrationAdminOut(
        id=registration.id,
        team_name=registration.team_name,
        team_slogan=registration.team_slogan,
        captain_name=f"{registration.captain_first_name} {registration.captain_last_name}".strip(),
        captain_user_id=registration.captain_user_id,
        captain_phone=registration.captain_phone,
        players_count=registration.players_count,
        status=registration.status,
        payment_tx_id=registration.payment_tx_id,
        created_at=registration.created_at,
        members=[
            {
                "id": member.id,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "is_captain": member.is_captain,
            }
            for member in registration.members
        ],
    )


@router.post("/tournaments", response_model=EventOut, status_code=201)
def admin_create_tournament(
    payload: TournamentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    event = TournamentService.create_tournament(db, current_user.id, payload)
    db.commit()
    return _enrich_event(db, EventService.get_event_with_relations(db, event.id))


@router.get("/tournaments/{event_id}/registrations", response_model=list[TournamentRegistrationAdminOut])
def admin_list_tournament_registrations(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    event = db.scalar(
        select(Event)
        .options(
            selectinload(Event.tournament_registrations).selectinload(TournamentRegistration.members),
        )
        .where(Event.id == event_id)
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.event_type != "tournament":
        raise HTTPException(status_code=400, detail="Only tournaments have team registrations")

    registrations = sorted(
        event.tournament_registrations,
        key=lambda item: item.created_at,
    )
    return [_serialize_tournament_registration_admin(item) for item in registrations]


@router.patch("/tournaments/{event_id}/registrations/{registration_id}", response_model=TournamentRegistrationAdminOut)
def admin_update_tournament_registration(
    event_id: uuid.UUID,
    registration_id: uuid.UUID,
    payload: TournamentRegistrationAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    registration = TournamentService.update_registration(db, event_id, registration_id, payload)
    db.commit()
    return _serialize_tournament_registration_admin(registration)


@router.delete("/tournaments/{event_id}/registrations/{registration_id}", status_code=204)
def admin_delete_tournament_registration(
    event_id: uuid.UUID,
    registration_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    TournamentService.delete_registration(db, event_id, registration_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/partners", response_model=UserOut, status_code=201)
def admin_create_partner(
    payload: AdminCreatePartnerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")

    code_entry = db.scalar(select(EmailVerificationCode).where(EmailVerificationCode.email == email))
    validate_verification_code(email, payload.verification_code, code_entry)

    partner = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        birth_date=payload.birth_date,
        email=email,
        email_verified=True,
        password_hash=hash_password(payload.password),
        role="partner",
        is_admin=False,
    )
    db.add(partner)
    db.flush()
    if code_entry:
        db.delete(code_entry)
    db.commit()
    db.refresh(partner)
    return partner


@router.get("/users", response_model=list[UserOut])
def admin_list_users(
    role: Literal["player", "partner", "admin"] | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    query = select(User)
    if role:
        query = query.where(User.role == role)
    query = query.order_by(User.email.asc())
    return list(db.scalars(query))


@router.get("/users/with-balance")
def admin_list_users_with_balance(
    role: Literal["player", "partner", "admin"] | None = None,
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """List users with wallet balance and game stats."""
    _ = current_user
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    query = query.order_by(User.email.asc())
    users = list(db.scalars(query))

    result = []
    for u in users:
        # Получаем баланс
        account = db.scalar(select(WalletAccount).where(WalletAccount.user_id == u.id))
        balance = account.balance if account else 0

        # Получаем количество сыгранных матчей
        games_played = db.scalar(
            select(func.count(EventParticipant.id)).where(
                EventParticipant.user_id == u.id,
                EventParticipant.status == "joined",
            )
        ) or 0

        result.append({
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "is_admin": u.is_admin,
            "photo_url": u.photo_url,
            "bio": u.bio,
            "balance": balance,
            "games_played": games_played,
            "onboarding_score": u.onboarding_score,
            "player_rating": calculate_player_rating(u.onboarding_score, games_played),
        })

    return result


@router.patch("/users/{user_id}/admin", response_model=UserOut)
def admin_set_user_admin_role(
    user_id: uuid.UUID,
    payload: AdminUserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.role != "player":
        raise HTTPException(status_code=400, detail="Admin rights can only be assigned to player accounts")
    if target_user.id == current_user.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin rights")

    target_user.is_admin = payload.is_admin
    db.commit()
    db.refresh(target_user)
    return target_user


@router.get("/wallet/transactions")
def admin_list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Get all grant/refund transactions for admin view with user info"""
    _ = current_user
    transactions = db.execute(
        select(WalletTransaction, User.email)
        .join(WalletAccount, WalletTransaction.wallet_account_id == WalletAccount.id)
        .join(User, WalletAccount.user_id == User.id)
        .where(WalletTransaction.tx_type.in_(["grant", "refund", "spend", "grant_reversal", "admin_debit"]))
        .order_by(WalletTransaction.created_at.desc())
        .limit(100)
    ).all()

    def is_grant_revoked(transaction_id: uuid.UUID) -> bool:
        return bool(
            db.scalar(
                select(WalletTransaction.id).where(
                    WalletTransaction.idempotency_key == f"grant-reversal:{transaction_id}"
                )
            )
        )

    return [
        {
            "id": str(tx.id),
            "user_email": email,
            "amount": tx.amount,
            "tx_type": tx.tx_type,
            "reason": tx.reason,
            "created_at": tx.created_at.isoformat(),
            "can_revoke": tx.tx_type == "grant" and not is_grant_revoked(tx.id),
            "is_revoked": tx.tx_type == "grant" and is_grant_revoked(tx.id),
        }
        for tx, email in transactions
    ]


@router.post("/wallet/grant", response_model=WalletBalanceOut)
def admin_wallet_grant(
    payload: WalletGrantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    # Ищем пользователя по email
    target_user = db.query(User).filter(User.email == payload.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with email {payload.email} not found")
    
    WalletService.add_credits(
        db,
        user_id=target_user.id,
        amount=payload.amount,
        tx_type="grant",
        reason=payload.reason,
        idempotency_key=f"grant:{target_user.id}:{uuid.uuid4()}",
    )
    account = WalletService.get_account_for_user(db, target_user.id)
    db.commit()
    return WalletBalanceOut(balance=account.balance)


@router.post("/wallet/debit", response_model=WalletBalanceOut)
def admin_wallet_debit(
    payload: WalletGrantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    target_user = db.query(User).filter(User.email == payload.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with email {payload.email} not found")

    WalletService.spend_credits(
        db,
        user_id=target_user.id,
        amount=payload.amount,
        reason=payload.reason or "Admin credit adjustment",
        idempotency_key=f"admin-debit:{target_user.id}:{uuid.uuid4()}",
        tx_type="admin_debit",
    )
    account = WalletService.get_account_for_user(db, target_user.id)
    db.commit()
    return WalletBalanceOut(balance=account.balance)


@router.post("/wallet/grant/{transaction_id}/revoke", response_model=WalletBalanceOut)
def admin_wallet_revoke_grant(
    transaction_id: uuid.UUID,
    payload: WalletGrantRevokeRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    original_tx = db.execute(
        select(WalletTransaction, WalletAccount.user_id)
        .join(WalletAccount, WalletTransaction.wallet_account_id == WalletAccount.id)
        .where(WalletTransaction.id == transaction_id)
    ).first()
    if not original_tx:
        raise HTTPException(status_code=404, detail="Grant transaction not found")

    tx, user_id = original_tx
    if tx.tx_type != "grant":
        raise HTTPException(status_code=400, detail="Only grant transactions can be revoked")

    reversal_key = f"grant-reversal:{tx.id}"
    existing_reversal = db.scalar(
        select(WalletTransaction.id).where(WalletTransaction.idempotency_key == reversal_key)
    )
    if existing_reversal:
        raise HTTPException(status_code=400, detail="This grant has already been revoked")

    reason = payload.reason if payload else None
    if reason:
        reversal_reason = f"Grant reversal: {reason}"
    elif tx.reason:
        reversal_reason = f"Grant reversal: {tx.reason}"
    else:
        reversal_reason = "Grant reversal"

    WalletService.spend_credits(
        db,
        user_id=user_id,
        amount=tx.amount,
        reason=reversal_reason,
        idempotency_key=reversal_key,
        tx_type="grant_reversal",
    )
    account = WalletService.get_account_for_user(db, user_id)
    db.commit()
    return WalletBalanceOut(balance=account.balance)

@router.get("/stats/player/{user_id}")
def player_stats(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Get detailed stats for a player."""
    _ = current_user
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    games_played = db.scalar(
        select(func.count(EventParticipant.id)).where(
            EventParticipant.user_id == user_id,
            EventParticipant.status == "joined",
        )
    ) or 0

    # Получаем баланс кошелька
    account = db.scalar(select(WalletAccount).where(WalletAccount.user_id == user_id))
    balance = account.balance if account else 0

    return {
        "user_id": str(user_id),
        "email": user.email,
        "games_played": games_played,
        "balance": balance,
        "onboarding_score": user.onboarding_score,
        "player_rating": calculate_player_rating(user.onboarding_score, games_played),
    }


@router.get("/stats/partner")
def partner_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("partner")),
):
    """Get real stats for current partner: revenue, bookings, venue performance."""
    from app.models.venue import Venue
    from app.models.availability import VenueSlot

    # Получаем площадки партнера
    venues = list(db.scalars(select(Venue).where(Venue.partner_user_id == current_user.id)))
    venue_ids = [v.id for v in venues]

    if not venue_ids:
        return {
            "total_bookings": 0,
            "total_revenue": 0,
            "revenue_today": 0,
            "revenue_week": 0,
            "revenue_month": 0,
            "upcoming_games": 0,
            "venues_count": 0,
            "recent_bookings": [],
        }

    # Общее число событий на площадках партнера
    total_events = db.scalar(
        select(func.count(Event.id)).where(Event.venue_id.in_(venue_ids))
    ) or 0

    events_at_venues = list(db.scalars(
        select(Event).where(Event.venue_id.in_(venue_ids))
    ))

    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=start_of_today.weekday())
    start_of_month = start_of_today.replace(day=1)

    total_revenue = 0
    revenue_today = 0
    revenue_week = 0
    revenue_month = 0
    for event in events_at_venues:
        venue = next((item for item in venues if item.id == event.venue_id), None)
        joined = db.scalar(
            select(func.count(EventParticipant.id)).where(
                EventParticipant.event_id == event.id,
                EventParticipant.status == "joined",
            )
        ) or 0
        pricing = calculate_pricing_breakdown(
            hourly_rate=venue.hourly_rate if venue else 0,
            duration_hours=event.duration_hours,
            required_players=event.required_players,
            registered_players=joined,
        )
        revenue = int(pricing["partner_rent_revenue"])
        total_revenue += revenue
        if event.start_at >= start_of_month:
            revenue_month += revenue
        if event.start_at >= start_of_week:
            revenue_week += revenue
        if event.start_at >= start_of_today:
            revenue_today += revenue

    # Ближайшие игры
    upcoming = db.scalar(
        select(func.count(Event.id)).where(
            Event.venue_id.in_(venue_ids),
            Event.start_at > now,
            Event.status == "active",
        )
    ) or 0

    # Последние бронирования (10 последних событий)
    recent_events = list(db.scalars(
        select(Event)
        .where(Event.venue_id.in_(venue_ids))
        .order_by(Event.start_at.desc())
        .limit(10)
    ))

    recent_bookings = []
    from app.models.sport import Sport
    for e in recent_events:
        sport = db.get(Sport, e.sport_id)
        venue = db.get(Venue, e.venue_id)
        joined = db.scalar(
            select(func.count(EventParticipant.id)).where(
                EventParticipant.event_id == e.id,
                EventParticipant.status == "joined",
            )
        ) or 0
        pricing = calculate_pricing_breakdown(
            hourly_rate=venue.hourly_rate if venue else 0,
            duration_hours=e.duration_hours,
            required_players=e.required_players,
            registered_players=joined,
        )
        recent_bookings.append({
            "event_id": str(e.id),
            "title": e.title,
            "sport_name": sport.name if sport else "",
            "venue_name": venue.name if venue else "",
            "start_at": e.start_at.isoformat(),
            "players_joined": joined,
            "required_players": e.required_players,
            "revenue": pricing["partner_rent_revenue"],
            "pricing_applied": pricing["pricing_applied"],
            "status": e.status,
        })

    return {
        "total_bookings": total_events,
        "total_revenue": total_revenue,
        "revenue_today": revenue_today,
        "revenue_week": revenue_week,
        "revenue_month": revenue_month,
        "upcoming_games": upcoming,
        "venues_count": len(venues),
        "recent_bookings": recent_bookings,
    }
