import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.models.sport import Sport
from app.models.user import User
from app.models.venue import Venue
from app.models.venue_sport import VenueSport
from app.schemas.venue import VenueCreate, VenueOut, VenueUpdate

router = APIRouter()


def _validate_and_dedup_sport_ids(db: Session, sport_ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Проверяет существование sport_ids и убирает дубликаты с сохранением порядка."""
    deduped = list(dict.fromkeys(sport_ids))
    if not deduped:
        return deduped

    existing = set(db.scalars(select(Sport.id).where(Sport.id.in_(deduped))))
    missing = [sid for sid in deduped if sid not in existing]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sport_ids: {', '.join(str(sid) for sid in missing)}",
        )
    return deduped


def to_venue_out(db: Session, venue: Venue) -> VenueOut:
    """Преобразует модель площадки в DTO ответа API с привязанными sport_ids."""
    sport_ids = list(
        db.scalars(select(VenueSport.sport_id).where(VenueSport.venue_id == venue.id).order_by(VenueSport.sport_id))
    )
    partner = db.get(User, venue.partner_user_id)
    return VenueOut(
        id=venue.id,
        partner_user_id=venue.partner_user_id,
        partner_email=partner.email if partner else None,
        name=venue.name,
        city=venue.city,
        address=venue.address,
        hourly_rate=venue.hourly_rate,
        timezone=venue.timezone,
        sport_ids=sport_ids,
    )


@router.post("/partner/venues", response_model=VenueOut)
def create_venue(
    payload: VenueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("partner")),
):
    """Создает площадку партнера и привязывает к ней выбранные виды спорта."""
    venue = Venue(
        partner_user_id=current_user.id,
        name=payload.name,
        city=payload.city,
        address=payload.address,
        hourly_rate=payload.hourly_rate,
        timezone=payload.timezone,
    )
    db.add(venue)
    db.flush()

    if payload.sport_ids:
        sport_ids = _validate_and_dedup_sport_ids(db, payload.sport_ids)
        db.add_all([VenueSport(venue_id=venue.id, sport_id=sid) for sid in sport_ids])

    db.commit()
    db.refresh(venue)
    return to_venue_out(db, venue)


@router.get("/venues", response_model=list[VenueOut])
def list_venues(db: Session = Depends(get_db)):
    """Возвращает список всех площадок для публичного просмотра."""
    venues = list(db.scalars(select(Venue).order_by(Venue.city.asc(), Venue.name.asc())))
    return [to_venue_out(db, v) for v in venues]


@router.get("/venues/{venue_id}", response_model=VenueOut)
def get_venue(venue_id: uuid.UUID, db: Session = Depends(get_db)):
    """Возвращает детальную информацию о площадке по идентификатору."""
    venue = db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return to_venue_out(db, venue)


@router.patch("/partner/venues/{venue_id}", response_model=VenueOut)
def update_venue(
    venue_id: uuid.UUID,
    payload: VenueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("partner")),
):
    """Обновляет данные площадки партнера и ее спортивные специализации."""
    venue = db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    if venue.partner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this venue")

    for field in ["name", "city", "address", "hourly_rate", "timezone"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(venue, field, value)

    if payload.sport_ids is not None:
        sport_ids = _validate_and_dedup_sport_ids(db, payload.sport_ids)
        db.execute(delete(VenueSport).where(VenueSport.venue_id == venue_id))
        db.add_all([VenueSport(venue_id=venue.id, sport_id=sid) for sid in sport_ids])

    db.commit()
    db.refresh(venue)
    return to_venue_out(db, venue)
