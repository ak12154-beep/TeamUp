import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.availability import VenueSlot
from app.models.event import Event
from app.models.participant import EventParticipant
from app.models.sport import Sport
from app.models.team import Team
from app.models.tournament_registration import TournamentRegistration
from app.models.user import User
from app.models.venue import Venue
from app.models.venue_sport import VenueSport
from app.services.pricing import calculate_cost_per_player
from app.services.wallet_service import WalletService

REQUIRED_PLAYERS_RULES = {
    "football": {10, 15, 20},
    "basketball": {10, 15, 20},
    "volleyball": {12, 18, 24},
}


class EventService:
    @staticmethod
    def _get_sport_rule_key(sport_name: str) -> str | None:
        """Нормализует название спорта к ключу набора бизнес-правил."""
        normalized = sport_name.lower()
        if "football" in normalized or "soccer" in normalized:
            return "football"
        if "basketball" in normalized:
            return "basketball"
        if "volleyball" in normalized:
            return "volleyball"
        return None

    @staticmethod
    def _resolve_team_id(db: Session, event_id: uuid.UUID, team_number: int | None) -> uuid.UUID | None:
        """Определяет команду участника: явный выбор или авто-распределение."""
        teams = list(
            db.scalars(
                select(Team)
                .where(Team.event_id == event_id)
                .order_by(Team.team_number.asc())
            )
        )
        if not teams:
            return None

        if team_number is not None:
            team = next((item for item in teams if item.team_number == team_number), None)
            if not team:
                raise HTTPException(status_code=400, detail="Invalid team_number")
            return team.id

        team_counts = {
            team.id: db.scalar(
                select(func.count(EventParticipant.id)).where(
                    EventParticipant.event_id == event_id,
                    EventParticipant.team_id == team.id,
                    EventParticipant.status == "joined",
                )
            ) or 0
            for team in teams
        }
        smallest_team = min(teams, key=lambda team: (team_counts[team.id], team.team_number))
        return smallest_team.id

    @staticmethod
    def _reserve_slot_for_event(
        db: Session,
        slot: VenueSlot,
        start_at: datetime,
        end_at: datetime,
    ) -> VenueSlot:
        """Резервирует слот и при необходимости создает свободные интервалы до/после матча."""
        if start_at < slot.start_at or end_at > slot.end_at:
            raise HTTPException(status_code=400, detail="Event time must be within slot bounds")
        if slot.status != "open":
            raise HTTPException(status_code=400, detail="Slot is not open")

        original_start = slot.start_at
        original_end = slot.end_at
        original_note = slot.note

        slot.start_at = start_at
        slot.end_at = end_at
        slot.status = "booked"

        if start_at > original_start:
            db.add(
                VenueSlot(
                    venue_id=slot.venue_id,
                    start_at=original_start,
                    end_at=start_at,
                    status="open",
                    note=original_note,
                )
            )

        if end_at < original_end:
            db.add(
                VenueSlot(
                    venue_id=slot.venue_id,
                    start_at=end_at,
                    end_at=original_end,
                    status="open",
                    note=original_note,
                )
            )

        db.flush()
        return slot

    @staticmethod
    def _is_adult_on(birth_date: date, on_date: date) -> bool:
        """Проверяет, является ли пользователь совершеннолетним на дату события."""
        years = on_date.year - birth_date.year
        if (on_date.month, on_date.day) < (birth_date.month, birth_date.day):
            years -= 1
        return years >= 18

    @staticmethod
    def validate_required_players(sport_name: str, required_players: int) -> None:
        """Проверяет допустимое количество игроков для выбранного вида спорта."""
        sport_key = EventService._get_sport_rule_key(sport_name)
        allowed = REQUIRED_PLAYERS_RULES.get(sport_key) if sport_key else None
        if allowed and required_players not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"required_players for {sport_name} must be one of {sorted(allowed)}",
            )

    @staticmethod
    def validate_team_size_mapping(sport_name: str, teams_count: int, required_players: int) -> None:
        """Проверяет согласованность числа команд и required_players по правилам спорта."""
        sport_key = EventService._get_sport_rule_key(sport_name)
        if not sport_key:
            return

        allowed = sorted(REQUIRED_PLAYERS_RULES[sport_key])
        index = teams_count - 2
        if index < 0 or index >= len(allowed):
            raise HTTPException(status_code=400, detail="Invalid teams_count for selected sport")

        expected_players = allowed[index]
        if required_players != expected_players:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"required_players for {sport_name} with {teams_count} teams "
                    f"must be {expected_players}"
                ),
            )

    @staticmethod
    def create_event(
        db: Session,
        creator_user_id: uuid.UUID,
        sport_id: uuid.UUID,
        venue_id: uuid.UUID,
        slot_id: uuid.UUID | None,
        start_at: datetime | None,
        end_at: datetime | None,
        required_players: int,
        teams_count: int,
        duration_hours: int,
        auto_join_creator: bool = True,
    ) -> Event:
        """Создает событие, валидирует ограничения и резервирует слот площадки."""
        venue = db.scalar(select(Venue).where(Venue.id == venue_id).with_for_update())
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        sport = db.get(Sport, sport_id)
        if not sport:
            raise HTTPException(status_code=404, detail="Sport not found")

        sport_link = db.scalar(
            select(VenueSport).where(VenueSport.venue_id == venue_id, VenueSport.sport_id == sport_id)
        )
        if not sport_link:
            raise HTTPException(status_code=400, detail="Venue does not support selected sport")

        EventService.validate_required_players(sport.name, required_players)
        EventService.validate_team_size_mapping(sport.name, teams_count, required_players)

        chosen_slot = None
        if slot_id:
            chosen_slot = db.scalar(select(VenueSlot).where(VenueSlot.id == slot_id).with_for_update())
            if not chosen_slot or chosen_slot.venue_id != venue_id:
                raise HTTPException(status_code=400, detail="Invalid slot_id for venue")
            if chosen_slot.status != "open":
                raise HTTPException(status_code=400, detail="Slot is not open")
            
            # Если время начала и окончания переданы явно, проверяем, что интервал лежит внутри выбранного слота.
            if start_at and end_at:
                if start_at < chosen_slot.start_at or end_at > chosen_slot.end_at:
                    raise HTTPException(status_code=400, detail="Event time must be within slot bounds")
            else:
                # Если интервал не передан, используем весь слот целиком.
                start_at = chosen_slot.start_at
                end_at = chosen_slot.end_at

        if not start_at or not end_at:
            raise HTTPException(status_code=400, detail="start_at and end_at are required")

        if end_at <= start_at:
            raise HTTPException(status_code=400, detail="end_at must be greater than start_at")

        duration_seconds = (end_at - start_at).total_seconds()
        if duration_seconds % 3600 != 0:
            raise HTTPException(status_code=400, detail="Event duration must be a whole number of hours")

        actual_hours = int(duration_seconds // 3600)
        if actual_hours != duration_hours:
            raise HTTPException(status_code=400, detail="duration_hours must match slot duration")

        overlap = db.scalar(
            select(Event).where(
                Event.venue_id == venue_id,
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

        cost = calculate_cost_per_player(venue.hourly_rate, duration_hours, required_players)
        title = f"{sport.name.capitalize()} @ {venue.name}"
        event = Event(
            title=title,
            created_by_user_id=creator_user_id,
            sport_id=sport_id,
            venue_id=venue_id,
            slot_id=slot_id,
            start_at=start_at,
            end_at=end_at,
            required_players=required_players,
            teams_count=teams_count,
            duration_hours=duration_hours,
            cost_credits_per_player=cost,
            event_type="pickup",
            status="active",
        )
        db.add(event)
        db.flush()

        teams = [Team(event_id=event.id, team_number=i) for i in range(1, teams_count + 1)]
        db.add_all(teams)
        db.flush()

        if auto_join_creator:
            EventService.join_event(
                db=db,
                event_id=event.id,
                user_id=creator_user_id,
                team_number=None,
            )

        return event

    @staticmethod
    def get_event_with_relations(db: Session, event_id: uuid.UUID) -> Event:
        """Возвращает событие с основными связанными сущностями."""
        event = db.scalar(
            select(Event)
            .options(
                selectinload(Event.teams),
                selectinload(Event.participants),
                selectinload(Event.tournament_registrations).selectinload(TournamentRegistration.members),
            )
            .where(Event.id == event_id)
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    def get_event_for_update(db: Session, event_id: uuid.UUID) -> Event:
        """Возвращает событие с блокировкой строки для конкурентно-безопасных изменений."""
        event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    def join_event(db: Session, event_id: uuid.UUID, user_id: uuid.UUID, team_number: int | None) -> EventParticipant:
        """Добавляет пользователя в матч с проверками статуса, лимитов и списанием средств."""
        event = EventService.get_event_for_update(db, event_id)
        if event.event_type == "tournament":
            raise HTTPException(status_code=400, detail="Tournament events require team registration")
        if event.status != "active":
            raise HTTPException(status_code=400, detail="Event is not active")
        now = datetime.now(timezone.utc)
        if event.start_at <= now:
            raise HTTPException(status_code=400, detail="Cannot join after event start")

        joining_user = db.get(User, user_id)
        if not joining_user:
            raise HTTPException(status_code=404, detail="User not found")
        event_day = event.start_at.date()
        joining_user_is_adult = EventService._is_adult_on(joining_user.birth_date, event_day)

        creator = db.get(User, event.created_by_user_id)
        if creator:
            creator_is_adult = EventService._is_adult_on(creator.birth_date, event_day)
            if creator_is_adult != joining_user_is_adult:
                raise HTTPException(
                    status_code=400,
                    detail="Age group mismatch: adults can only play with adults, minors only with minors",
                )

        joined_birth_dates = db.scalars(
            select(User.birth_date)
            .join(EventParticipant, EventParticipant.user_id == User.id)
            .where(
                EventParticipant.event_id == event_id,
                EventParticipant.status == "joined",
            )
        ).all()
        for birth_date in joined_birth_dates:
            participant_is_adult = EventService._is_adult_on(birth_date, event_day)
            if participant_is_adult != joining_user_is_adult:
                raise HTTPException(
                    status_code=400,
                    detail="Age group mismatch: adults can only play with adults, minors only with minors",
                )

        joined_count = db.scalar(
            select(func.count(EventParticipant.id)).where(
                EventParticipant.event_id == event_id,
                EventParticipant.status == "joined",
            )
        )
        if joined_count >= event.required_players:
            raise HTTPException(status_code=400, detail="Event is full")

        participant = db.scalar(
            select(EventParticipant)
            .where(EventParticipant.event_id == event_id, EventParticipant.user_id == user_id)
            .with_for_update()
        )
        if participant and participant.status == "joined":
            return participant

        team_id = EventService._resolve_team_id(db, event_id, team_number)

        WalletService.spend_credits(
            db,
            user_id=user_id,
            amount=event.cost_credits_per_player,
            reason=f"Join event {event.id}",
            event_id=event.id,
            idempotency_key=f"spend:{event.id}:{user_id}:{uuid.uuid4()}",
        )

        if participant:
            participant.status = "joined"
            participant.team_id = team_id
            db.flush()
            return participant

        participant = EventParticipant(
            event_id=event_id,
            user_id=user_id,
            team_id=team_id,
            status="joined",
        )
        db.add(participant)
        db.flush()
        return participant

    @staticmethod
    def leave_event(db: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> EventParticipant:
        """Обрабатывает попытку выхода из события согласно текущим ограничениям сервиса."""
        event = EventService.get_event_for_update(db, event_id)
        if event.event_type == "tournament":
            raise HTTPException(status_code=400, detail="Tournament teams are managed by admin")
        raise HTTPException(status_code=403, detail="Leaving an event is not allowed after joining")
