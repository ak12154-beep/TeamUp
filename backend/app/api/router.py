from fastapi import APIRouter

from app.api.routes import (
    ai,
    admin,
    auth,
    availability,
    events,
    sports,
    users,
    venues,
    wallet,
)

api_router = APIRouter()
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(sports.router, tags=["sports"])
api_router.include_router(venues.router, tags=["venues"])
api_router.include_router(availability.router, tags=["availability"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(wallet.router, tags=["wallet"])
api_router.include_router(admin.router, tags=["admin"])
