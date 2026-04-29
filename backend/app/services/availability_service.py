import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.availability import VenueSlot
from app.models.venue import Venue


class AvailabilityService:
    @staticmethod
    def assert_owner(db: Session, venue_id: uuid.UUID, partner_user_id: uuid.UUID) -> Venue:
        venue = db.get(Venue, venue_id)
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        if venue.partner_user_id != partner_user_id:
            raise HTTPException(status_code=403, detail="You do not own this venue")
        return venue

    @staticmethod
    def ensure_no_overlap(
        db: Session,
        venue_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
        exclude_slot_id: uuid.UUID | None = None,
    ) -> None:
        if end_at <= start_at:
            raise HTTPException(status_code=400, detail="end_at must be greater than start_at")

        conditions = [
            VenueSlot.venue_id == venue_id,
            VenueSlot.start_at < end_at,
            VenueSlot.end_at > start_at,
        ]
        if exclude_slot_id:
            conditions.append(VenueSlot.id != exclude_slot_id)

        overlap = db.scalar(select(VenueSlot).where(and_(*conditions)).limit(1))
        if overlap:
            raise HTTPException(status_code=400, detail="Slot overlaps with existing slot")

    @staticmethod
    def list_slots(db: Session, venue_id: uuid.UUID, from_dt: datetime, to_dt: datetime) -> list[VenueSlot]:
        return list(
            db.scalars(
                select(VenueSlot)
                .where(
                    VenueSlot.venue_id == venue_id,
                    VenueSlot.start_at < to_dt,
                    VenueSlot.end_at > from_dt,
                )
                .order_by(VenueSlot.start_at.asc())
            )
        )

    @staticmethod
    def update_slot_owner(db: Session, slot_id: uuid.UUID, partner_user_id: uuid.UUID) -> VenueSlot:
        slot = db.get(VenueSlot, slot_id)
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        venue = db.get(Venue, slot.venue_id)
        if not venue or venue.partner_user_id != partner_user_id:
            raise HTTPException(status_code=403, detail="You do not own this slot")
        return slot
