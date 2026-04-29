import logging
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import false, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.privacy import mask_email
from app.core.deps import get_current_user, get_db, get_optional_current_user, is_admin_user, require_roles
from app.models.event import Event
from app.models.participant import EventParticipant
from app.models.sport import Sport
from app.models.tournament_registration import TournamentRegistration
from app.models.user import User
from app.models.venue import Venue
from app.schemas.event import (
    EventCreate,
    EventJoinRequest,
    EventOut,
    EventRatingCreate,
    EventType,
    EventUpdate,
    ParticipantOut,
    TournamentRegistrationOut,
    TournamentTeamRegisterRequest,
)
from app.services.event_service import EventService
from app.services.post_game_service import PostGameService
from app.services.player_rating_service import calculate_player_rating
from app.services.pricing import calculate_pricing_breakdown
from app.services.tournament_service import TournamentService

router = APIRouter(prefix="/events")
logger = logging.getLogger(__name__)


def _serialize_tournament_registration_public(registration: TournamentRegistration) -> TournamentRegistrationOut:
    """Сериализует публичное представление турнирной регистрации без лишних персональных данных."""
    return TournamentRegistrationOut(
        id=registration.id,
        team_name=registration.team_name,
        team_slogan=registration.team_slogan,
        players_count=registration.players_count,
        status=registration.status,
        created_at=registration.created_at,
    )


def _enrich_event(db: Session, event: Event) -> dict:
    """Дополняет событие названиями спорта/площадки и текущим числом участников."""
    sport = db.get(Sport, event.sport_id)
    venue = db.get(Venue, event.venue_id)
    joined_count = db.scalar(
        select(func.count(EventParticipant.id)).where(
            EventParticipant.event_id == event.id,
            EventParticipant.status == "joined",
        )
    ) or 0
    registered_teams_count = len(event.tournament_registrations)
    registration_is_closed = TournamentService.is_registration_closed(event, registered_teams_count)
    if event.event_type == "tournament":
        pricing = {
            "rent_total": 0,
            "rent_share_per_player": 0,
            "platform_fee_per_player": 0,
            "admin_rent_total": 0,
            "admin_platform_fee_total": 0,
            "partner_rent_revenue": 0,
            "pricing_applied": False,
            "refund_required": False,
        }
    else:
        pricing = calculate_pricing_breakdown(
            hourly_rate=venue.hourly_rate if venue else 0,
            duration_hours=event.duration_hours,
            required_players=event.required_players,
            registered_players=joined_count,
        )

    # Дополняем участников маскированными email и расчетным рейтингом.
    participants = []
    for p in event.participants:
        u = db.get(User, p.user_id)
        games_played = 0
        if u:
            games_played = db.scalar(
                select(func.count(EventParticipant.id)).where(
                    EventParticipant.user_id == u.id,
                    EventParticipant.status == "joined",
                )
            ) or 0
        participants.append(ParticipantOut(
            id=p.id,
            user_id=p.user_id,
            team_id=p.team_id,
            status=p.status,
            first_name=u.first_name if u else None,
            last_name=u.last_name if u else None,
            nickname=u.nickname if u else None,
            user_email=mask_email(u.email) if u else None,
            user_rating=calculate_player_rating(u.onboarding_score, games_played) if u else None,
            onboarding_score=u.onboarding_score if u else None,
        ))
    tournament_registrations = [
        _serialize_tournament_registration_public(registration)
        for registration in event.tournament_registrations
    ]

    return EventOut(
        id=event.id,
        title=event.title,
        created_by_user_id=event.created_by_user_id,
        sport_id=event.sport_id,
        venue_id=event.venue_id,
        slot_id=event.slot_id,
        start_at=event.start_at,
        end_at=event.end_at,
        required_players=event.required_players,
        teams_count=event.teams_count,
        duration_hours=event.duration_hours,
        cost_credits_per_player=event.cost_credits_per_player,
        event_type=event.event_type,
        description=event.description,
        entry_fee_credits_team=event.entry_fee_credits_team,
        registration_deadline=event.registration_deadline,
        registration_closed=event.registration_closed,
        registration_is_closed=registration_is_closed,
        is_featured=event.is_featured,
        rent_total=pricing["rent_total"],
        rent_share_per_player=pricing["rent_share_per_player"],
        platform_fee_per_player=pricing["platform_fee_per_player"],
        admin_rent_total=pricing["admin_rent_total"],
        admin_platform_fee_total=pricing["admin_platform_fee_total"],
        partner_rent_revenue=pricing["partner_rent_revenue"],
        pricing_applied=pricing["pricing_applied"],
        refund_required=pricing["refund_required"],
        status=event.status,
        teams=[{"id": t.id, "team_number": t.team_number} for t in event.teams],
        participants=participants,
        sport_name=sport.name if sport else None,
        venue_name=venue.name if venue else None,
        venue_address=venue.address if venue else None,
        venue_city=venue.city if venue else None,
        current_players=joined_count,
        registered_teams_count=registered_teams_count,
        tournament_registrations=tournament_registrations,
        post_game_outcome=event.post_game_outcome,
    )


@router.post("", response_model=EventOut)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("player")),
):
    """Создает новое событие и возвращает расширенное представление для клиента."""
    event = EventService.create_event(
        db=db,
        creator_user_id=current_user.id,
        sport_id=payload.sport_id,
        venue_id=payload.venue_id,
        slot_id=payload.slot_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        required_players=payload.required_players,
        teams_count=payload.teams_count,
        duration_hours=payload.duration_hours,
        auto_join_creator=payload.auto_join_creator,
    )
    db.commit()
    _notify_partner_on_event_created(db, event.id, current_user)
    db.commit()
    enriched_event = EventService.get_event_with_relations(db, event.id)
    return _enrich_event(db, enriched_event)


@router.get("", response_model=list[EventOut])
def list_events(
    city: str | None = Query(default=None, max_length=100),
    sport_id: uuid.UUID | None = None,
    status: Literal["active", "cancelled", "completed"] | None = None,
    event_type: EventType | None = None,
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Возвращает список событий с фильтрацией по параметрам запроса."""
    if from_dt and to_dt and to_dt < from_dt:
        raise HTTPException(status_code=400, detail="'to' must be greater than or equal to 'from'")
    query = select(Event).options(
        selectinload(Event.teams),
        selectinload(Event.participants),
        selectinload(Event.tournament_registrations).selectinload(TournamentRegistration.members),
    )

    if city:
        query = query.join(Venue, Venue.id == Event.venue_id).where(Venue.city.ilike(f"%{city}%"))
    if sport_id:
        query = query.where(Event.sport_id == sport_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    is_admin = bool(current_user and is_admin_user(current_user))
    if status:
        if status == "cancelled" and not is_admin:
            query = query.where(false())
        else:
            query = query.where(Event.status == status)
    elif not is_admin:
        query = query.where(Event.status != "cancelled")
    if from_dt:
        query = query.where(Event.start_at >= from_dt)
    if to_dt:
        query = query.where(Event.start_at <= to_dt)

    query = query.order_by(Event.start_at.asc()).limit(100)
    events = list(db.scalars(query))
    return [_enrich_event(db, e) for e in events]


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    event = EventService.get_event_with_relations(db, event_id)
    return _enrich_event(db, event)


@router.patch("/{event_id}", response_model=EventOut)
def update_event(
    event_id: uuid.UUID,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновляет событие: администратор может редактировать любое, создатель — только свое."""
    event = db.scalar(
        select(Event)
        .options(
            selectinload(Event.teams),
            selectinload(Event.participants),
            selectinload(Event.tournament_registrations).selectinload(TournamentRegistration.members),
        )
        .where(Event.id == event_id)
        .with_for_update()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not is_admin_user(current_user) and event.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this event")

    if payload.status is not None:
        previous_status = event.status
        event.status = payload.status
        if payload.status == "cancelled" and previous_status != "cancelled":
            logger.info(
                "Event cancelled by admin or owner",
                extra={
                    "event_id": str(event.id),
                    "actor_user_id": str(current_user.id),
                    "previous_status": previous_status,
                    "new_status": payload.status,
                },
            )
    if payload.required_players is not None:
        if event.event_type == "tournament":
            raise HTTPException(status_code=400, detail="Tournament player capacity is managed through team registrations")
        sport = db.get(Sport, event.sport_id)
        if sport:
            EventService.validate_required_players(sport.name, payload.required_players)
        joined_count = db.scalar(
            select(func.count(EventParticipant.id)).where(
                EventParticipant.event_id == event.id,
                EventParticipant.status == "joined",
            )
        ) or 0
        if payload.required_players < joined_count:
            raise HTTPException(
                status_code=400,
                detail="required_players cannot be less than joined players",
            )
        event.required_players = payload.required_players
    if payload.teams_count is not None:
        if event.event_type == "tournament" and payload.teams_count < len(event.tournament_registrations):
            raise HTTPException(status_code=400, detail="teams_count cannot be less than registered teams")
        event.teams_count = payload.teams_count
    if payload.registration_closed is not None:
        if event.event_type != "tournament":
            raise HTTPException(status_code=400, detail="Only tournaments support registration closing")
        event.registration_closed = payload.registration_closed

    db.commit()
    return _enrich_event(db, EventService.get_event_with_relations(db, event.id))


@router.post("/{event_id}/join", response_model=ParticipantOut)
def join_event(
    event_id: uuid.UUID,
    payload: EventJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("player")),
):
    participant = EventService.join_event(db, event_id, current_user.id, payload.team_number)
    db.commit()

    # Создаем уведомление для владельца площадки.
    _notify_partner_on_join(db, event_id, current_user)
    db.commit()

    u = db.get(User, participant.user_id)
    return ParticipantOut(
        id=participant.id,
        user_id=participant.user_id,
        team_id=participant.team_id,
        status=participant.status,
        first_name=u.first_name if u else None,
        last_name=u.last_name if u else None,
        nickname=u.nickname if u else None,
        user_email=u.email if u else None,
        user_rating=calculate_player_rating(u.onboarding_score, 0) if u else None,
        onboarding_score=u.onboarding_score if u else None,
    )


@router.post("/{event_id}/register-team", response_model=TournamentRegistrationOut)
def register_tournament_team(
    event_id: uuid.UUID,
    payload: TournamentTeamRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("player")),
):
    registration = TournamentService.register_team(db, event_id, current_user.id, payload)
    db.commit()
    refreshed_event = TournamentService.get_tournament_with_registrations(db, event_id)
    refreshed_registration = next(
        (item for item in refreshed_event.tournament_registrations if item.id == registration.id),
        None,
    )
    if not refreshed_registration:
        raise HTTPException(status_code=500, detail="Failed to load tournament registration")
    return _serialize_tournament_registration_public(refreshed_registration)


@router.post("/{event_id}/leave", response_model=ParticipantOut)
def leave_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("player")),
):
    participant = EventService.leave_event(db, event_id, current_user.id)
    db.commit()
    u = db.get(User, participant.user_id)
    return ParticipantOut(
        id=participant.id,
        user_id=participant.user_id,
        team_id=participant.team_id,
        status=participant.status,
        first_name=u.first_name if u else None,
        last_name=u.last_name if u else None,
        nickname=u.nickname if u else None,
        user_email=u.email if u else None,
        user_rating=calculate_player_rating(u.onboarding_score, 0) if u else None,
        onboarding_score=u.onboarding_score if u else None,
    )


@router.post("/{event_id}/ratings")
def submit_event_rating(
    event_id: uuid.UUID,
    payload: EventRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("player")),
):
    rating = PostGameService.submit_rating(db, event_id, current_user.id, payload.rating)
    db.commit()
    return {
        "ok": True,
        "event_id": str(rating.event_id),
        "user_id": str(rating.user_id),
        "rating": rating.rating,
    }


def _notify_partner_on_join(db: Session, event_id: uuid.UUID, player: User):
    """Уведомляет владельца площадки, когда игрок присоединяется к матчу на его площадке."""
    from app.models.notification import Notification

    event = db.get(Event, event_id)
    if not event:
        return
    venue = db.get(Venue, event.venue_id)
    if not venue:
        return
    sport = db.get(Sport, event.sport_id)

    notification = Notification(
        user_id=venue.partner_user_id,
        title="New Booking",
        message=f"{player.email.split('@')[0]} joined {sport.name if sport else 'a game'} at {venue.name} on {event.start_at.strftime('%b %d at %H:%M')}",
    )
    db.add(notification)


def _notify_partner_on_event_created(db: Session, event_id: uuid.UUID, player: User):
    from app.models.notification import Notification

    event = db.get(Event, event_id)
    if not event:
        return
    venue = db.get(Venue, event.venue_id)
    if not venue:
        return
    sport = db.get(Sport, event.sport_id)

    notification = Notification(
        user_id=venue.partner_user_id,
        title="Game Created",
        message=(
            f"{player.email.split('@')[0]} created "
            f"{sport.name if sport else 'a game'} at {venue.name} for "
            f"{event.start_at.strftime('%b %d, %H:%M')} - {event.end_at.strftime('%H:%M')}. "
            "Please update your calendar and mark this time as booked."
        ),
    )
    db.add(notification)
