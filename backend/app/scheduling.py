"""Spaced-repetition rules. Pure functions: no database, no clock."""
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import IntEnum
from typing import TypeVar
from zoneinfo import ZoneInfo

import fsrs

# Re-solving a problem is a day-scale activity, so skip FSRS's minute-scale
# learning steps and go straight to day intervals.
_scheduler = fsrs.Scheduler(
    desired_retention=0.9,
    learning_steps=(),
    relearning_steps=(),
    enable_fuzzing=True,
)

BALANCE_FRACTION = 0.15

# Bounds and default for the user's "longest gap between reviews" setting.
MIN_MAX_INTERVAL_DAYS = 7
DEFAULT_MAX_INTERVAL_DAYS = 180
NO_MAX_INTERVAL_DAYS = 36500  # FSRS's own ceiling; effectively "no limit"

# A problem qualifies for a quick (approach-only) review once a solve holds this long.
QUICK_MIN_STABILITY_DAYS = 21


class UserRating(IntEnum):
    FAILED = 1
    HINT = 2
    SLOW = 3
    COLD = 4


_TO_FSRS = {
    UserRating.FAILED: fsrs.Rating.Again,
    UserRating.HINT: fsrs.Rating.Hard,
    UserRating.SLOW: fsrs.Rating.Good,
    UserRating.COLD: fsrs.Rating.Easy,
}


def to_fsrs_rating(rating: UserRating) -> fsrs.Rating:
    return _TO_FSRS[rating]


@dataclass(frozen=True)
class CardState:
    due: datetime
    state: int
    stability: float | None = None
    difficulty: float | None = None
    last_review: datetime | None = None
    reps: int = 0
    lapses: int = 0

    def to_fsrs(self) -> fsrs.Card:
        return fsrs.Card(
            state=fsrs.State(self.state),
            stability=self.stability,
            difficulty=self.difficulty,
            due=self.due,
            last_review=self.last_review,
        )


def quick_eligible(card: CardState) -> bool:
    return card.stability is not None and card.stability >= QUICK_MIN_STABILITY_DAYS


# Outlining an approach is a weaker test than solving, so it can't earn "Easy".
QUICK_RATINGS = (UserRating.FAILED, UserRating.HINT, UserRating.SLOW)


def new_card(at: datetime) -> CardState:
    return CardState(due=at, state=fsrs.State.Learning.value)


def local_date(dt: datetime, tz: str) -> date:
    return dt.astimezone(ZoneInfo(tz)).date()


def end_of_local_day(dt: datetime, tz: str) -> datetime:
    """First instant of the next local day, as an aware datetime."""
    zone = ZoneInfo(tz)
    tomorrow = dt.astimezone(zone).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=zone)


def balance_window(review_at: datetime, due: datetime, tz: str) -> tuple[date, date]:
    """Local-date range the load balancer may move a due date within."""
    interval = max((due - review_at).days, 1)
    spread = max(1, round(interval * BALANCE_FRACTION))
    target = local_date(due, tz)
    earliest = local_date(review_at, tz) + timedelta(days=1)
    return max(target - timedelta(days=spread), earliest), target + timedelta(days=spread)


def balance(
    review_at: datetime,
    due: datetime,
    tz: str,
    load: Mapping[date, int],
    cap: int,
    latest: date | None = None,
    not_before: datetime | None = None,
    spill: bool = False,
) -> datetime:
    """Move `due` to a lighter day nearby if its day already has `cap` or more cards.

    `latest` bounds how late it may move (the user's maximum interval).
    `not_before` is the earliest it may land (now, for a backdated solve that is
    already overdue). With `spill`, a card whose whole window is full moves on to
    the first later day with room, so problems added in bulk spread out instead
    of piling onto the same few days.
    """
    day = local_date(due, tz)
    target = day
    lo, hi = balance_window(review_at, due, tz)
    if not_before is not None:
        floor = local_date(not_before, tz)
        target, lo, hi = max(target, floor), max(lo, floor), max(hi, floor)
    if latest is not None:
        hi = max(min(hi, latest), lo)
    if load.get(target, 0) < cap:
        best = target
    else:
        days = [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]
        # Lightest day wins, then closest to target, then later (spacing longer is safer).
        best = min(days, key=lambda d: (load.get(d, 0), abs((d - target).days), -(d - target).days))
        if spill and load.get(best, 0) >= cap:
            # Past the max interval if need be: a full queue would make it wait that long anyway.
            best = hi + timedelta(days=1)
            while load.get(best, 0) >= cap:
                best += timedelta(days=1)
    if best == day:
        return due
    moved = due + timedelta(days=(best - day).days)
    return moved if not_before is None else max(moved, not_before)


def review(
    card: CardState,
    rating: UserRating,
    at: datetime,
    *,
    tz: str = "UTC",
    load: Mapping[date, int] | None = None,
    cap: int | None = None,
    duration_sec: int | None = None,
    max_interval_days: int | None = None,
    now: datetime | None = None,
) -> CardState:
    """Apply a rating at `at`. `now` differs from `at` only for a backdated solve."""
    updated, _ = _scheduler.review_card(
        card.to_fsrs(),
        to_fsrs_rating(rating),
        review_datetime=at,
        review_duration=duration_sec * 1000 if duration_sec else None,
    )
    due = updated.due
    latest = None
    if max_interval_days is not None:
        limit = at + timedelta(days=max_interval_days)
        due = min(due, limit)
        latest = local_date(limit, tz)
    if load is not None and cap is not None:
        due = balance(at, due, tz, load, cap, latest=latest, not_before=now, spill=card.reps == 0)
    lapsed = rating == UserRating.FAILED and card.reps > 0
    return CardState(
        due=due,
        state=updated.state.value,
        stability=updated.stability,
        difficulty=updated.difficulty,
        last_review=at,
        reps=card.reps + 1,
        lapses=card.lapses + (1 if lapsed else 0),
    )


def retrievability(card: CardState, at: datetime) -> float:
    if card.last_review is None:
        return 0.0
    return _scheduler.get_card_retrievability(card.to_fsrs(), at)


T = TypeVar("T")


def build_queue(
    cards: Iterable[T], state_of: Callable[[T], CardState], at: datetime, tz: str, cap: int
) -> tuple[list[T], int]:
    """Cards due by the end of the user's local day, least-remembered first.

    Returns (today's queue limited to `cap`, number of extra due cards left over).
    """
    cutoff = end_of_local_day(at, tz)
    due = [c for c in cards if state_of(c).due < cutoff]
    due.sort(key=lambda c: (retrievability(state_of(c), at), state_of(c).due))
    return due[:cap], max(len(due) - cap, 0)
