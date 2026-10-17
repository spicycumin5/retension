from collections.abc import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, returns aware UTC. Behaves the same on Postgres and SQLite."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to UTCDateTime")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


class Base(DeclarativeBase):
    pass


# Serverless instances come and go, so pooled connections would sit open on Neon until they time
# out; open one per request instead.
engine = create_async_engine(
    get_settings().database_url, **({"poolclass": NullPool} if get_settings().vercel else {})
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
