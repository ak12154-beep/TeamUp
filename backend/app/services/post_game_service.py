import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.event import Event
from app.models.event_rating import EventRating
from app.models.notification import Notification
from app.models.participant import EventParticipant
from app.models.venue import Venue
from app.models.wallet import WalletAccount, WalletTransaction
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)

class PostGameService:
    @staticmethod
    def process_upcoming_event_reminders(db: Session, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        reminder_cutoff = now + timedelta(hours=1)
        events = list(
            db.scalars(
                select(Event)
                .where(
                    Event.status == "active",
                    Event.start_at > now,
                    Event.start_at <= reminder_cutoff,
                )
                .order_by(Event.start_at.asc())
            )
        )

        sent = 0
        for event in events:
            sent += PostGameService._send_single_event_reminder(db, event)
        return sent

    @staticmethod
    def process_due_events(db: Session, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        events = list(
            db.scalars(
                select(Event)
                .where(
                    Event.end_at <= now,
                    Event.post_game_processed_at.is_(None),
                )
                .order_by(Event.end_at.asc())
                .with_for_update(skip_locked=True)
            )
        )

        processed = 0
        for event in events:
            PostGameService._process_single_event(db, event, now)
            processed += 1
        return processed

    @staticmethod
    def _send_single_event_reminder(db: Session, event: Event) -> int:
        venue = db.get(Venue, event.venue_id)
        joined_participants = list(
            db.scalars(
                select(EventParticipant).where(
                    EventParticipant.event_id == event.id,
                    EventParticipant.status == "joined",
                )
            )
        )

        recipients: list[tuple[uuid.UUID, str, str, str]] = [
            (
                participant.user_id,
                "Game Starts Soon",
                f"Your game '{event.title}' starts in less than one hour.",
                f"event-starting-soon:{event.id}:{participant.user_id}",
            )
            for participant in joined_participants
        ]

        if venue:
            recipients.append(
                (
                    venue.partner_user_id,
                    "Upcoming Game Reminder",
                    f"The game '{event.title}' at {venue.name} starts in less than one hour.",
                    f"event-starting-soon:{event.id}:partner:{venue.partner_user_id}",
                )
            )

        created = 0
        for user_id, title, message, idempotency_key in recipients:
            existing = db.scalar(select(Notification.id).where(Notification.idempotency_key == idempotency_key))
            if existing:
                continue
            db.add(
                Notification(
                    user_id=user_id,
                    event_id=event.id,
                    title=title,
                    message=message,
                    notification_type="event_starting_soon",
                    idempotency_key=idempotency_key,
                )
            )
            created += 1
        if created:
            db.flush()
        return created

    @staticmethod
    def _process_single_event(db: Session, event: Event, now: datetime) -> None:
        joined_participants = list(
            db.scalars(
                select(EventParticipant)
                .where(
                    EventParticipant.event_id == event.id,
                    EventParticipant.status == "joined",
                )
                .order_by(EventParticipant.user_id.asc())
            )
        )

        if len(joined_participants) >= event.required_players:
            for participant in joined_participants:
                notification = Notification(
                    user_id=participant.user_id,
                    event_id=event.id,
                    title="Rate Game",
                    message=f"Please rate how the game '{event.title}' went from 1 to 5.",
                    notification_type="event_rating_request",
                    action_payload=[
                        {
                            "kind": "rate_event",
                            "event_id": str(event.id),
                            "value": value,
                            "label": str(value),
                        }
                        for value in range(1, 6)
                    ],
                    idempotency_key=f"event-rating-request:{event.id}:{participant.user_id}",
                )
                db.add(notification)
                logger.info(
                    "Sent post-game rating request",
                    extra={"event_id": str(event.id), "user_id": str(participant.user_id)},
                )
            event.post_game_outcome = "ratings_requested"
        else:
            refunded_users: list[str] = []
            for participant in joined_participants:
                spent_tx = db.scalar(
                    select(WalletTransaction)
                    .join(WalletAccount, WalletAccount.id == WalletTransaction.wallet_account_id)
                    .where(
                        WalletTransaction.event_id == event.id,
                        WalletTransaction.tx_type == "spend",
                        WalletAccount.user_id == participant.user_id,
                    )
                )
                existing_refund = db.scalar(
                    select(WalletTransaction.id).where(
                        WalletTransaction.event_id == event.id,
                        WalletTransaction.tx_type == "refund",
                        WalletTransaction.idempotency_key == f"event-refund:{event.id}:{participant.user_id}",
                    )
                )
                if spent_tx and not existing_refund:
                    WalletService.add_credits(
                        db,
                        user_id=participant.user_id,
                        amount=event.cost_credits_per_player,
                        tx_type="refund",
                        reason=f"Automatic refund for event {event.id}: not enough participants",
                        event_id=event.id,
                        idempotency_key=f"event-refund:{event.id}:{participant.user_id}",
                    )
                    refunded_users.append(str(participant.user_id))
                    logger.info(
                        "Issued automatic event refund",
                        extra={"event_id": str(event.id), "user_id": str(participant.user_id)},
                    )

                db.add(
                    Notification(
                        user_id=participant.user_id,
                        event_id=event.id,
                        title="Credits Refunded",
                        message=(
                            f"We refunded {event.cost_credits_per_player} credits for '{event.title}' "
                            f"because fewer than {event.required_players} players joined."
                        ),
                        notification_type="event_refund",
                        idempotency_key=f"event-refund-notification:{event.id}:{participant.user_id}",
                    )
                )
                logger.info(
                    "Sent refund notification",
                    extra={"event_id": str(event.id), "user_id": str(participant.user_id)},
                )
            event.post_game_outcome = "refunded"
            logger.info(
                "Completed automatic refund flow",
                extra={"event_id": str(event.id), "refunded_users": refunded_users},
            )

        event.post_game_processed_at = now
        if event.status == "active":
            event.status = "completed"
        db.flush()

    @staticmethod
    def submit_rating(db: Session, event_id: uuid.UUID, user_id: uuid.UUID, rating: int) -> EventRating:
        event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.post_game_outcome != "ratings_requested":
            raise HTTPException(status_code=400, detail="Ratings are not available for this event")

        participant = db.scalar(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.user_id == user_id,
                EventParticipant.status == "joined",
            )
        )
        if not participant:
            raise HTTPException(status_code=403, detail="Only participants can rate this event")

        existing = db.scalar(
            select(EventRating).where(
                EventRating.event_id == event_id,
                EventRating.user_id == user_id,
            )
        )
        if existing:
            existing.rating = rating
            db.flush()
            logger.info(
                "Updated event rating",
                extra={"event_id": str(event_id), "user_id": str(user_id), "rating": rating},
            )
            return existing

        new_rating = EventRating(event_id=event_id, user_id=user_id, rating=rating)
        db.add(new_rating)
        db.flush()
        logger.info(
            "Created event rating",
            extra={"event_id": str(event_id), "user_id": str(user_id), "rating": rating},
        )
        return new_rating


class PostGameScheduler:
    def __init__(self, poll_seconds: int = 60):
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="teamup-post-game-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            db = SessionLocal()
            try:
                reminders_sent = PostGameService.process_upcoming_event_reminders(db)
                processed = PostGameService.process_due_events(db)
                if processed or reminders_sent:
                    db.commit()
                else:
                    db.rollback()
            except Exception:
                db.rollback()
                logger.exception("Post-game scheduler iteration failed")
            finally:
                db.close()
            self._stop.wait(self.poll_seconds)


def build_scheduler() -> PostGameScheduler | None:
    poll_seconds = getattr(settings, "post_game_poll_seconds", 60)
    scheduler_enabled = getattr(settings, "post_game_scheduler_enabled", True)
    if not scheduler_enabled:
        return None
    return PostGameScheduler(poll_seconds=int(poll_seconds))
