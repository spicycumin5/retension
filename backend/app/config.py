from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://recall:recall@localhost:5432/recall"
    secret: str = "dev-secret-change-me-dev-secret-change-me"
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
