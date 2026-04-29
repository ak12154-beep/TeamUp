import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.models.availability import VenueSlot
from app.models.event import Event
from app.models.user import User
from app.schemas.availability import SlotCreate, SlotOut, SlotUpdate
from app.services.availability_service import AvailabilityService

router = APIRouter()


@router.get("/venues/{venue_id}/slots", response_model=list[SlotOut])
def list_slots(
    venue_id: uuid.UUID,
    from_dt: datetime = Query(alias="from"),
    to_dt: datetime = Query(alias="to"),
    db: Session = Depends(get_db),
):
    if to_dt <= from_dt:
        raise HTTPException(status_code=400, detail="'to' must be greater than 'from'")
    return AvailabilityService.list_slots(db, venue_id, from_dt, to_dt)


@router.post("/partner/venues/{venue_id}/slots", response_model=SlotOut)
def create_slot(
    venue_id: uuid.UUID,
    payload: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("partner")),
):
    AvailabilityService.assert_owner(db, venue_id, current_user.id)
    AvailabilityService.ensure_no_overlap(db, venue_id, payload.start_at, payload.end_at)

    slot = VenueSlot(
        venue_id=venue_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=payload.status,
        note=payload.note,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.patch("/partner/slots/{slot_id}", response_model=SlotOut)
def update_slot(
    slot_id: uuid.UUID,
    payload: SlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("partner")),
):
    slot = AvailabilityService.update_slot_owner(db, slot_id, current_user.id)

    new_start = payload.start_at or slot.start_at
    new_end = payload.end_at or slot.end_at
    AvailabilityService.ensure_no_overlap(db, slot.venue_id, new_start, new_end, exclude_slot_id=slot.id)

    if payload.start_at is not None:
        slot.start_at = payload.start_at
    if payload.end_at is not None:
        slot.end_at = payload.end_at
    if payload.status is not None:
        slot.status = payload.status
    if payload.note is not None:
        slot.note = payload.note

    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/partner/slots/{slot_id}")
def delete_slot(
    slot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("partner")),
):
    slot = AvailabilityService.update_slot_owner(db, slot_id, current_user.id)
    linked_event_id = db.scalar(
        select(Event.id).where(Event.slot_id == slot.id).limit(1)
    )
    if linked_event_id:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete slot linked to an event",
        )
    db.delete(slot)
    db.commit()
    return {"ok": True}
