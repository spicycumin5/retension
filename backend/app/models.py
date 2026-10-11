import uuid
from datetime import date, datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import clock, scheduling
from app.db import Base, UTCDateTime


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    digest_hour: Mapped[int] = mapped_column(SmallInteger, default=8)
    daily_review_cap: Mapped[int] = mapped_column(SmallInteger, default=3)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_digest_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    leetcode_username: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64), unique=True, default=lambda: uuid.uuid4().hex
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)


class Problem(Base):
    """Global LeetCode problem metadata, shared by all users."""

    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    lc_number: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True)
    lc_tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    @property
    def url(self) -> str:
        return f"https://leetcode.com/problems/{self.slug}/"


class Card(Base):
    """One user's spaced-repetition state for one problem."""

    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("user_id", "problem_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))

    # FSRS state
    due: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[int] = mapped_column(SmallInteger)
    last_review: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[str] = mapped_column(Text, default="")
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)

    problem: Mapped[Problem] = relationship(lazy="joined")
    pattern_links: Mapped[list["CardPattern"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def patterns(self) -> list[str]:
        return sorted(link.pattern for link in self.pattern_links)

    def schedule_state(self) -> scheduling.CardState:
        return scheduling.CardState(
            due=self.due,
            state=self.state,
            stability=self.stability,
            difficulty=self.difficulty,
            last_review=self.last_review,
            reps=self.reps,
            lapses=self.lapses,
        )


class CardPattern(Base):
    __tablename__ = "card_patterns"

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    pattern: Mapped[str] = mapped_column(String(40), primary_key=True)


class Review(Base):
    """Append-only review log."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(SmallInteger)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime)


class DismissedImport(Base):
    """A LeetCode solve the user chose not to track, so import stops offering it."""

    __tablename__ = "dismissed_imports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    slug: Mapped[str] = mapped_column(String(200), primary_key=True)
