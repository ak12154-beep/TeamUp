from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent
ENV_FILES = (
    str(BASE_DIR / ".env"),
    str(PROJECT_DIR / ".env"),
)


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    return normalized.startswith("<") and normalized.endswith(">")


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str | None = None
    database_scheme: str = Field(
        default="postgresql+psycopg",
        validation_alias=AliasChoices("DATABASE_SCHEME", "DB_SCHEME"),
    )
    database_host: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_HOST", "DB_HOST", "POSTGRES_HOST", "PGHOST"),
    )
    database_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("DATABASE_PORT", "DB_PORT", "POSTGRES_PORT", "PGPORT"),
    )
    database_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_NAME", "DB_NAME", "POSTGRES_DB", "PGDATABASE"),
    )
    database_user: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_USER", "DB_USER", "POSTGRES_USER", "PGUSER"),
    )
    database_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_PASSWORD", "DB_PASSWORD", "POSTGRES_PASSWORD", "PGPASSWORD"),
    )
    database_sslmode: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_SSLMODE", "DB_SSLMODE", "PGSSLMODE"),
    )
    jwt_secret: str
    primary_admin_email: str
    jwt_alg: str = "HS256"
    access_token_expire_min: int = 60
    cors_origins: str = "https://teamup-kg.com,https://www.teamup-kg.com"
    auth_cookie_name: str = "teamup_session"
    auth_cookie_secure: bool = True
    auth_cookie_samesite: str = "lax"
    auth_cookie_domain: str | None = None
    local_db_fallback_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-nano"
    app_base_url: str = "https://teamup-kg.com"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    verification_code_ttl_min: int = 10
    verification_resend_sec: int = 60
    verification_code_length: int = 6
    post_game_scheduler_enabled: bool = True
    post_game_poll_seconds: int = 60

    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    @model_validator(mode="after")
    def build_database_url(self):
        component_values = {
            "DATABASE_HOST": self.database_host,
            "DATABASE_NAME": self.database_name,
            "DATABASE_USER": self.database_user,
            "DATABASE_PASSWORD": self.database_password,
        }

        if self.database_url and not _is_placeholder(self.database_url):
            try:
                parsed = make_url(self.database_url)
            except ArgumentError as exc:
                raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from exc
            if _is_placeholder(parsed.host):
                raise ValueError("DATABASE_URL host still contains a placeholder value")
            return self

        provided_components = [name for name, value in component_values.items() if value]
        if provided_components:
            missing_components = [name for name, value in component_values.items() if not value]
            if missing_components:
                missing_list = ", ".join(missing_components)
                raise ValueError(
                    f"Set DATABASE_URL or provide all of DATABASE_HOST, DATABASE_NAME, DATABASE_USER, "
                    f"and DATABASE_PASSWORD. Missing: {missing_list}"
                )
            placeholder_components = [name for name, value in component_values.items() if _is_placeholder(value)]
            if placeholder_components:
                placeholder_list = ", ".join(placeholder_components)
                raise ValueError(f"Database settings still contain placeholder values: {placeholder_list}")

            query = {"sslmode": self.database_sslmode} if self.database_sslmode else {}
            self.database_url = URL.create(
                self.database_scheme,
                username=self.database_user,
                password=self.database_password,
                host=self.database_host,
                port=self.database_port,
                database=self.database_name,
                query=query,
            ).render_as_string(hide_password=False)
            return self

        raise ValueError(
            "DATABASE_URL must be set, or provide DATABASE_HOST, DATABASE_NAME, DATABASE_USER, and DATABASE_PASSWORD"
        )

    @model_validator(mode="after")
    def normalize_database_url_for_local_dev(self):
        # Резервный режим включается только явно и работает только при локальном запуске (вне Docker).
        # Это сохраняет поведение продакшена и стейджинга неизменным по умолчанию.
        if not self.local_db_fallback_enabled:
            return self
        if _running_in_docker():
            return self

        try:
            parsed = make_url(self.database_url)
        except ArgumentError:
            return self

        if parsed.host == "db":
            # Локальный docker-compose публикует Postgres на localhost:5434.
            target_port = parsed.port if parsed.port and parsed.port != 5432 else 5434
            self.database_url = parsed.set(host="localhost", port=target_port).render_as_string(
                hide_password=False
            )
        return self

    @model_validator(mode="after")
    def validate_sensitive_defaults(self):
        insecure_defaults = {
            "dev_secret_change_later",
            "teamup-prod-secret-change-this-immediately-2026",
        }
        if self.environment.lower() in {"production", "staging"}:
            if self.jwt_secret in insecure_defaults or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be unique and at least 32 characters in non-development environments")
        return self

    @model_validator(mode="after")
    def normalize_primary_admin_email(self):
        self.primary_admin_email = self.primary_admin_email.strip().lower()
        if not self.primary_admin_email:
            raise ValueError("PRIMARY_ADMIN_EMAIL must be set")
        return self


settings = Settings()
