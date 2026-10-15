from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-secret-change-me-dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://recall:recall@localhost:5432/recall"
    secret: str = DEV_SECRET
    # Public URL of the app; used for links in emails.
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    # Built frontend to serve from the API process (production). Empty = don't serve.
    static_dir: str = ""

    email_backend: Literal["console", "resend", "smtp", "brevo"] = "console"
    email_from: str = "Retension <reminders@example.com>"
    resend_api_key: str = ""
    brevo_api_key: str = ""
    # SMTP defaults suit Gmail with an app password.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, url: str) -> str:
        # Hosts like Render hand out postgres:// URLs; SQLAlchemy async needs the driver named.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                url = "postgresql+asyncpg://" + url[len(prefix):]
        if url.startswith("postgresql+asyncpg://"):
            url = _asyncpg_query(url)
        return url

    @field_validator("smtp_password")
    @classmethod
    def _strip_spaces(cls, password: str) -> str:
        # Gmail displays app passwords in groups of four ("abcd efgh ..."); spaces aren't part of them.
        return "".join(password.split())

    @field_validator("frontend_url")
    @classmethod
    def _no_trailing_slash(cls, url: str) -> str:
        return url.rstrip("/")

    @model_validator(mode="after")
    def _production_guards(self):
        if not self.is_dev:
            if self.secret == DEV_SECRET or len(self.secret) < 32:
                raise ValueError("SECRET must be set to a random string of 32+ characters outside dev")
            if self.email_backend == "resend" and not self.resend_api_key:
                raise ValueError("RESEND_API_KEY is required when EMAIL_BACKEND=resend")
            if self.email_backend == "brevo" and not self.brevo_api_key:
                raise ValueError("BREVO_API_KEY is required when EMAIL_BACKEND=brevo")
            if self.email_backend == "smtp" and not (self.smtp_username and self.smtp_password):
                raise ValueError("SMTP_USERNAME and SMTP_PASSWORD are required when EMAIL_BACKEND=smtp")
        return self


def _asyncpg_query(url: str) -> str:
    """Hosted Postgres URLs (Neon, Supabase) carry libpq options asyncpg doesn't accept.

    sslmode=require becomes asyncpg's ssl=require; channel_binding has no asyncpg equivalent.
    """
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query):
        if key == "sslmode":
            query.append(("ssl", value))
        elif key != "channel_binding":
            query.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))


@lru_cache
def get_settings() -> Settings:
    return Settings()
