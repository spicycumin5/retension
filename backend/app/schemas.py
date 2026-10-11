from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import patterns as pattern_catalog
from app.scheduling import UserRating


class ResolveIn(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    lc_number: int | None
    title: str
    difficulty: str | None
    lc_tags: list[str]
    url: str


class ResolveOut(BaseModel):
    problem: ProblemOut
    default_patterns: list[str]
    card_id: int | None  # set if the user already tracks this problem


class PatternOut(BaseModel):
    slug: str
    name: str


def _validate_patterns(value: list[str] | None) -> list[str] | None:
    return None if value is None else pattern_catalog.validate(value)


class CardCreate(BaseModel):
    problem_id: int
    rating: UserRating
    duration_sec: int | None = Field(default=None, ge=0, le=60 * 60 * 6)
    patterns: list[str] | None = None  # None = use defaults from LeetCode tags
    notes: str = Field(default="", max_length=10_000)
    _p = field_validator("patterns")(_validate_patterns)


class CardUpdate(BaseModel):
    patterns: list[str] | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    suspended: bool | None = None
    _p = field_validator("patterns")(_validate_patterns)


class ReviewIn(BaseModel):
    rating: UserRating
    duration_sec: int | None = Field(default=None, ge=0, le=60 * 60 * 6)


class CardOut(BaseModel):
    id: int
    problem: ProblemOut
    due: datetime
    last_review: datetime | None
    reps: int
    lapses: int
    notes: str
    suspended: bool
    patterns: list[str]
    retrievability: float


class QueueOut(BaseModel):
    cards: list[CardOut]
    overflow: int
    reviewed_today: int


class WeakCardOut(BaseModel):
    card_id: int
    problem: ProblemOut
    recall: float


class PatternStatsOut(BaseModel):
    pattern: str
    name: str
    practice_url: str
    problems: int
    due: int
    lapses: int
    avg_recall: float | None
    holds_days: float | None
    weakest: list[WeakCardOut]
