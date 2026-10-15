import re
import uuid
from datetime import timedelta
from zoneinfo import available_timezones

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import email, scheduling
from app.config import get_settings
from app.db import get_session
from app.models import Card, User

settings = get_settings()
_TIMEZONES = available_timezones()


def _check_tz(value: str | None) -> str | None:
    if value is not None and value not in _TIMEZONES:
        raise ValueError("unknown timezone")
    return value


_LC_USERNAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _check_lc_username(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None  # blank clears it
    if not _LC_USERNAME.match(value):
        raise ValueError("LeetCode usernames use letters, numbers, - and _ only")
    return value


class UserRead(schemas.BaseUser[uuid.UUID]):
    timezone: str
    digest_hour: int
    daily_review_cap: int
    digest_enabled: bool
    leetcode_username: str | None
    max_interval_days: int


class UserCreate(schemas.BaseUserCreate):
    timezone: str = "UTC"
    _tz = field_validator("timezone")(_check_tz)


class UserUpdate(schemas.BaseUserUpdate):
    timezone: str | None = None
    digest_hour: int | None = Field(default=None, ge=0, le=23)
    daily_review_cap: int | None = Field(default=None, ge=1, le=50)
    digest_enabled: bool | None = None
    leetcode_username: str | None = None
    max_interval_days: int | None = Field(
        default=None, ge=scheduling.MIN_MAX_INTERVAL_DAYS, le=scheduling.NO_MAX_INTERVAL_DAYS
    )
    _tz = field_validator("timezone")(_check_tz)
    _lc = field_validator("leetcode_username")(_check_lc_username)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.secret
    verification_token_secret = settings.secret

    async def validate_password(self, password: str, user) -> None:
        from fastapi_users.exceptions import InvalidPasswordException

        if len(password) < 8:
            raise InvalidPasswordException("Password must be at least 8 characters")

    async def on_after_update(self, user: User, update_dict: dict, request: Request | None = None) -> None:
        if "max_interval_days" in update_dict:
            await clamp_due_dates(self.user_db.session, user)

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        await self.request_verify(user, request)

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None) -> None:
        link = f"{settings.frontend_url}/verify?token={token}"
        await email.send(
            user.email,
            "Verify your Retension account",
            f"Welcome to Retension! Confirm your email address:\n\n{link}\n",
        )

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None) -> None:
        link = f"{settings.frontend_url}/reset-password?token={token}"
        await email.send(
            user.email,
            "Reset your Retension password",
            f"Someone asked to reset your Retension password. If it was you:\n\n{link}\n\n"
            "If not, you can ignore this email.",
        )


async def clamp_due_dates(session: AsyncSession, user: User) -> int:
    """Pull in reviews scheduled further out than the user's maximum interval allows."""
    cards = (
        await session.scalars(
            select(Card).where(Card.user_id == user.id, Card.last_review.is_not(None))
        )
    ).unique().all()
    changed = 0
    for card in cards:
        limit = card.last_review + timedelta(days=user.max_interval_days)
        if card.due > limit:
            card.due = limit
            changed += 1
    if changed:
        await session.commit()
    return changed


async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.secret, lifetime_seconds=60 * 60 * 24 * 30)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=CookieTransport(
        cookie_name="recall_auth",
        cookie_max_age=60 * 60 * 24 * 30,
        cookie_secure=settings.cookie_secure,
    ),
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_user = fastapi_users.current_user(active=True, verified=True)
