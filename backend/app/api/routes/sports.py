from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.sport import Sport
from app.schemas.sport import SportOut

router = APIRouter(prefix="/sports")


@router.get("", response_model=list[SportOut])
def list_sports(db: Session = Depends(get_db)):
    return list(db.scalars(select(Sport).order_by(Sport.name.asc())))
