from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.router import api_router
from app.core.config import settings
from app.core.db_errors import map_integrity_error
from app.services.admin_access_service import sync_primary_admin_access
from app.services.post_game_service import build_scheduler

app = FastAPI(title="TeamUp API", version="0.1.0")

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.state.post_game_scheduler = None


@app.exception_handler(IntegrityError)
def handle_integrity_error(_: Request, exc: IntegrityError):
    """Преобразует ошибки целостности БД в клиентский HTTP-ответ."""
    status_code, detail = map_integrity_error(exc)
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.exception_handler(OperationalError)
def handle_operational_error(_: Request, __: OperationalError):
    """Возвращает 503, если база данных недоступна."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Database is unavailable. Check DATABASE_URL and database reachability."},
    )


@app.get("/")
def health() -> dict[str, str]:
    """Проверка доступности API."""
    return {"status": "ok"}


@app.on_event("startup")
def startup_scheduler() -> None:
    """Инициализирует сервисы при старте приложения."""
    sync_primary_admin_access()
    scheduler = build_scheduler()
    app.state.post_game_scheduler = scheduler
    if scheduler:
        scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler() -> None:
    """Корректно останавливает фоновые задачи при завершении приложения."""
    scheduler = getattr(app.state, "post_game_scheduler", None)
    if scheduler:
        scheduler.stop()
