import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.event import Event
from app.models.notification import Notification
from app.models.participant import EventParticipant
from app.models.sport import Sport
from app.models.user import User
from app.models.venue import Venue
from app.models.wallet import WalletAccount
from app.schemas.notification import NotificationOut
from app.schemas.user import (
    LeaderboardPlayerOut,
    UserEventSummary,
    UserOut,
    UserProfileGamesOut,
    UserProfileUpdate,
)
from app.services.player_rating_service import calculate_player_rating

router = APIRouter(prefix="/users")


def _build_user_event_summary(db: Session, event: Event) -> UserEventSummary:
    """Собирает краткую сводку события для разделов профиля пользователя."""
    current_players = db.scalar(
        select(func.count(EventParticipant.id)).where(
            EventParticipant.event_id == event.id,
            EventParticipant.status == "joined",
        )
    ) or 0
    sport = db.get(Sport, event.sport_id)
    venue = db.get(Venue, event.venue_id)
    return UserEventSummary(
        id=event.id,
        title=event.title,
        start_at=event.start_at,
        end_at=event.end_at,
        status=event.status,
        sport_name=sport.name if sport else None,
        venue_name=venue.name if venue else None,
        venue_city=venue.city if venue else None,
        current_players=current_players,
        required_players=event.required_players,
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Возвращает профиль текущего авторизованного пользователя."""
    return current_user


@router.get("/leaderboard", response_model=list[LeaderboardPlayerOut])
def leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Формирует таблицу лидеров игроков по рейтингу и активности."""
    _ = current_user
    results = db.execute(
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.nickname,
            User.photo_url,
            User.onboarding_score,
            func.count(EventParticipant.id).label("games_played"),
        )
        .outerjoin(
            EventParticipant,
            and_(
                EventParticipant.user_id == User.id,
                EventParticipant.status == "joined",
            ),
        )
        .where(User.role == "player")
        .group_by(
            User.id,
            User.first_name,
            User.last_name,
            User.nickname,
            User.photo_url,
            User.onboarding_score,
        )
        .limit(50)
    ).all()

    ranked = sorted(
        results,
        key=lambda row: (
            calculate_player_rating(row.onboarding_score, row.games_played),
            row.games_played,
            row.nickname or f"{row.first_name or ''} {row.last_name or ''}".strip() or str(row.id),
        ),
        reverse=True,
    )

    return [
        LeaderboardPlayerOut(
            id=row.id,
            first_name=row.first_name,
            last_name=row.last_name,
            nickname=row.nickname,
            photo_url=row.photo_url,
            games_played=row.games_played,
            player_rating=calculate_player_rating(row.onboarding_score, row.games_played),
            rank=index + 1,
        )
        for index, row in enumerate(ranked)
    ]


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновляет редактируемые поля профиля текущего пользователя."""
    if "nickname" in payload.model_fields_set:
        current_user.nickname = payload.nickname
    if payload.photo_url is not None:
        current_user.photo_url = payload.photo_url
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.favorite_sports is not None:
        current_user.favorite_sports = payload.favorite_sports
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/stats")
def my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает персональную статистику игрока и баланс кошелька."""
    games_played = db.scalar(
        select(func.count(EventParticipant.id)).where(
            EventParticipant.user_id == current_user.id,
            EventParticipant.status == "joined",
        )
    ) or 0

    account = db.scalar(select(WalletAccount).where(WalletAccount.user_id == current_user.id))
    balance = account.balance if account else 0
    player_rating = calculate_player_rating(current_user.onboarding_score, games_played)

    return {
        "games_played": games_played,
        "balance": balance,
        "onboarding_score": current_user.onboarding_score,
        "player_rating": player_rating,
        "onboarding_level_label": current_user.onboarding_level_label,
    }


@router.get("/me/games", response_model=UserProfileGamesOut)
def my_games(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает списки игр пользователя: созданные, завершенные и отмененные."""
    created_events = list(
        db.scalars(
            select(Event)
            .where(Event.created_by_user_id == current_user.id)
            .order_by(Event.start_at.desc())
            .limit(50)
        )
    )

    participant_event_ids = list(
        db.scalars(
            select(EventParticipant.event_id).where(
                EventParticipant.user_id == current_user.id,
                EventParticipant.status == "joined",
            )
        )
    )
    participant_events = []
    if participant_event_ids:
        participant_events = list(
            db.scalars(
                select(Event)
                .where(Event.id.in_(participant_event_ids))
                .order_by(Event.start_at.desc())
                .limit(100)
            )
        )

    created_ids = {event.id for event in created_events}
    completed_games = [
        _build_user_event_summary(db, event)
        for event in participant_events
        if event.status == "completed"
    ]
    cancelled_games = [
        _build_user_event_summary(db, event)
        for event in participant_events
        if event.status == "cancelled" or event.post_game_outcome == "refunded"
    ]
    created_games = [
        _build_user_event_summary(db, event)
        for event in created_events
    ]

    # Добавляем созданные пользователем завершенные/отмененные игры, даже если он явно не вступал в них.
    for event in created_events:
        if event.id in created_ids and event.status == "completed" and all(item.id != event.id for item in completed_games):
            completed_games.append(_build_user_event_summary(db, event))
        if (
            event.id in created_ids
            and (event.status == "cancelled" or event.post_game_outcome == "refunded")
            and all(item.id != event.id for item in cancelled_games)
        ):
            cancelled_games.append(_build_user_event_summary(db, event))

    return UserProfileGamesOut(
        created_games=created_games,
        completed_games=completed_games,
        cancelled_games=cancelled_games,
    )


@router.get("/me/notifications", response_model=list[NotificationOut])
def my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает последние уведомления текущего пользователя."""
    notifications = list(db.scalars(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ))
    return notifications


@router.post("/me/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Помечает одно уведомление пользователя как прочитанное."""
    notif = db.get(Notification, notification_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.commit()
    return {"ok": True}


@router.post("/me/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Помечает все непрочитанные уведомления пользователя как прочитанные."""
    notifications = list(db.scalars(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    ))
    for n in notifications:
        n.is_read = True
    db.commit()
    return {"ok": True}
