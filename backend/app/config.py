from functools import lru_cache
from typing import Literal

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

    email_backend: Literal["console", "resend"] = "console"
    email_from: str = "Recall <reminders@example.com>"
    resend_api_key: str = ""

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, url: str) -> str:
        # Hosts like Render hand out postgres:// URLs; SQLAlchemy async needs the driver named.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url

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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
