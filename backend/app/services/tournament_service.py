import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.availability import VenueSlot
from app.models.event import Event
from app.models.sport import Sport
from app.models.tournament_registration import TournamentRegistration
from app.models.tournament_registration_member import TournamentRegistrationMember
from app.models.user import User
from app.models.venue import Venue
from app.models.venue_sport import VenueSport
from app.schemas.event import (
    TournamentCreateRequest,
    TournamentRegistrationAdminUpdate,
    TournamentTeamRegisterRequest,
)
from app.services.event_service import EventService
from app.services.wallet_service import WalletService


class TournamentService:
    @staticmethod
    def is_registration_closed(
        event: Event,
        registered_teams_count: int,
        *,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or datetime.now(timezone.utc)
        if event.event_type != "tournament":
            return False
        if event.status != "active":
            return True
        if event.registration_closed:
            return True
        if event.registration_deadline and current_time >= event.registration_deadline:
            return True
        return registered_teams_count >= event.teams_count

    @staticmethod
    def create_tournament(
        db: Session,
        creator_user_id: uuid.UUID,
        payload: TournamentCreateRequest,
    ) -> Event:
        venue = db.scalar(select(Venue).where(Venue.id == payload.venue_id).with_for_update())
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        sport = db.get(Sport, payload.sport_id)
        if not sport:
            raise HTTPException(status_code=404, detail="Sport not found")

        sport_link = db.scalar(
            select(VenueSport).where(
                VenueSport.venue_id == payload.venue_id,
                VenueSport.sport_id == payload.sport_id,
            )
        )
        if not sport_link:
            raise HTTPException(status_code=400, detail="Venue does not support selected sport")

        chosen_slot = None
        start_at = payload.start_at
        end_at = payload.end_at
        slot_id = payload.slot_id
        if payload.slot_id:
            chosen_slot = db.scalar(select(VenueSlot).where(VenueSlot.id == payload.slot_id).with_for_update())
            if not chosen_slot or chosen_slot.venue_id != payload.venue_id:
                raise HTTPException(status_code=400, detail="Invalid slot_id for venue")
            if chosen_slot.status != "open":
                raise HTTPException(status_code=400, detail="Slot is not open")
            if start_at and end_at:
                if start_at < chosen_slot.start_at or end_at > chosen_slot.end_at:
                    raise HTTPException(status_code=400, detail="Event time must be within slot bounds")
            else:
                start_at = chosen_slot.start_at
                end_at = chosen_slot.end_at

        if not start_at or not end_at:
            raise HTTPException(status_code=400, detail="start_at and end_at are required")
        if end_at <= start_at:
            raise HTTPException(status_code=400, detail="end_at must be greater than start_at")
        if payload.registration_deadline >= start_at:
            raise HTTPException(status_code=400, detail="registration_deadline must be before start_at")

        duration_seconds = (end_at - start_at).total_seconds()
        if duration_seconds % 3600 != 0:
            raise HTTPException(status_code=400, detail="Event duration must be a whole number of hours")
        duration_hours = int(duration_seconds // 3600)

        overlap = db.scalar(
            select(Event).where(
                Event.venue_id == payload.venue_id,
                Event.status == "active",
                Event.start_at < end_at,
                Event.end_at > start_at,
            )
        )
        if overlap:
            raise HTTPException(status_code=400, detail="Venue already has active event in this time")

        if chosen_slot:
            chosen_slot = EventService._reserve_slot_for_event(db, chosen_slot, start_at, end_at)
            slot_id = chosen_slot.id

        event = Event(
            title=payload.title,
            created_by_user_id=creator_user_id,
            sport_id=payload.sport_id,
            venue_id=payload.venue_id,
            slot_id=slot_id,
            start_at=start_at,
            end_at=end_at,
            required_players=payload.teams_count,
            teams_count=payload.teams_count,
            duration_hours=duration_hours,
            cost_credits_per_player=0,
            event_type="tournament",
            description=payload.description,
            entry_fee_credits_team=payload.entry_fee_credits_team,
            registration_deadline=payload.registration_deadline,
            registration_closed=False,
            is_featured=payload.is_featured,
            status="active",
        )
        db.add(event)
        db.flush()
        return event

    @staticmethod
    def get_tournament_with_registrations(db: Session, event_id: uuid.UUID) -> Event:
        event = db.scalar(
            select(Event)
            .options(
                selectinload(Event.tournament_registrations).selectinload(TournamentRegistration.members),
            )
            .where(Event.id == event_id)
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    def register_team(
        db: Session,
        event_id: uuid.UUID,
        captain_user_id: uuid.UUID,
        payload: TournamentTeamRegisterRequest,
    ) -> TournamentRegistration:
        event = db.scalar(
            select(Event)
            .options(
                selectinload(Event.tournament_registrations).selectinload(TournamentRegistration.members),
            )
            .where(Event.id == event_id)
            .with_for_update()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.event_type != "tournament":
            raise HTTPException(status_code=400, detail="Only tournaments support team registration")

        captain = db.get(User, captain_user_id)
        if not captain:
            raise HTTPException(status_code=404, detail="User not found")

        registered_teams_count = len(event.tournament_registrations)
        if TournamentService.is_registration_closed(event, registered_teams_count):
            raise HTTPException(status_code=400, detail="Tournament registration is closed")

        existing = db.scalar(
            select(TournamentRegistration).where(
                TournamentRegistration.event_id == event_id,
                TournamentRegistration.captain_user_id == captain_user_id,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="You have already registered a team for this tournament")

        fee = event.entry_fee_credits_team or 0
        if fee <= 0:
            raise HTTPException(status_code=400, detail="Tournament entry fee is not configured")

        payment_tx = WalletService.spend_credits(
            db,
            user_id=captain_user_id,
            amount=fee,
            reason=f"Tournament registration: {event.title}",
            event_id=event.id,
            idempotency_key=f"tournament-registration:{event.id}:{captain_user_id}:{uuid.uuid4()}",
        )

        registration = TournamentRegistration(
            event_id=event.id,
            captain_user_id=captain_user_id,
            team_name=payload.team_name,
            team_slogan=payload.team_slogan,
            captain_first_name=payload.captain_first_name,
            captain_last_name=payload.captain_last_name,
            captain_phone=payload.captain_phone,
            players_count=payload.players_count,
            status="paid",
            payment_tx_id=payment_tx.id,
        )
        db.add(registration)
        db.flush()

        members = [
            TournamentRegistrationMember(
                registration_id=registration.id,
                first_name=member.first_name,
                last_name=member.last_name,
                is_captain=member.is_captain,
            )
            for member in payload.members
        ]
        db.add_all(members)
        db.flush()
        db.refresh(registration)
        return registration

    @staticmethod
    def delete_registration(
        db: Session,
        event_id: uuid.UUID,
        registration_id: uuid.UUID,
    ) -> None:
        event = db.scalar(
            select(Event)
            .where(Event.id == event_id)
            .with_for_update()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.event_type != "tournament":
            raise HTTPException(status_code=400, detail="Only tournaments have team registrations")

        registration = db.scalar(
            select(TournamentRegistration)
            .options(selectinload(TournamentRegistration.members))
            .where(
                TournamentRegistration.id == registration_id,
                TournamentRegistration.event_id == event_id,
            )
            .with_for_update()
        )
        if not registration:
            raise HTTPException(status_code=404, detail="Registration not found")

        if registration.payment_tx_id:
            WalletService.add_credits(
                db,
                user_id=registration.captain_user_id,
                amount=event.entry_fee_credits_team or 0,
                tx_type="refund",
                reason=f"Tournament registration removed: {event.title}",
                event_id=event.id,
                idempotency_key=f"tournament-registration-refund:{registration.id}",
            )

        db.delete(registration)

    @staticmethod
    def update_registration(
        db: Session,
        event_id: uuid.UUID,
        registration_id: uuid.UUID,
        payload: TournamentRegistrationAdminUpdate,
    ) -> TournamentRegistration:
        event = db.scalar(
            select(Event)
            .where(Event.id == event_id)
            .with_for_update()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.event_type != "tournament":
            raise HTTPException(status_code=400, detail="Only tournaments have team registrations")

        registration = db.scalar(
            select(TournamentRegistration)
            .options(selectinload(TournamentRegistration.members))
            .where(
                TournamentRegistration.id == registration_id,
                TournamentRegistration.event_id == event_id,
            )
            .with_for_update()
        )
        if not registration:
            raise HTTPException(status_code=404, detail="Registration not found")

        registration.team_slogan = payload.team_slogan
        db.flush()
        return registration
