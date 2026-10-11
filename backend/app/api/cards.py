from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import clock, scheduling
from app.db import get_session
from app.models import Card, CardPattern, Problem, Review, User
from app.patterns import default_patterns
from app.schemas import CardCreate, CardOut, CardUpdate, ProblemOut, QueueOut, ReviewIn
from app.users import current_user

router = APIRouter(tags=["cards"])


def apply_state(card: Card, s: scheduling.CardState) -> None:
    card.due, card.state = s.due, s.state
    card.stability, card.difficulty = s.stability, s.difficulty
    card.last_review, card.reps, card.lapses = s.last_review, s.reps, s.lapses


def to_out(card: Card, at: datetime) -> CardOut:
    return CardOut(
        id=card.id,
        problem=ProblemOut.model_validate(card.problem),
        due=card.due,
        last_review=card.last_review,
        reps=card.reps,
        lapses=card.lapses,
        notes=card.notes,
        suspended=card.suspended,
        patterns=card.patterns,
        retrievability=scheduling.retrievability(card.schedule_state(), at),
    )


async def _load_by_day(
    session: AsyncSession, user: User, at: datetime, exclude_card_id: int
) -> Counter[date]:
    """How many of the user's active cards fall due on each local day in the next year."""
    dues = await session.scalars(
        select(Card.due).where(
            Card.user_id == user.id,
            Card.id != exclude_card_id,
            Card.suspended.is_(False),
            Card.due >= at,
            Card.due < at + timedelta(days=366),
        )
    )
    return Counter(scheduling.local_date(d, user.timezone) for d in dues)


# How far back an imported solve may be dated.
MAX_BACKDATE = timedelta(days=90)


async def _review(
    session: AsyncSession,
    user: User,
    card: Card,
    rating: scheduling.UserRating,
    duration_sec: int | None,
    at: datetime | None = None,
) -> None:
    at = at or clock.now()
    new = scheduling.review(
        card.schedule_state(),
        rating,
        at,
        tz=user.timezone,
        load=await _load_by_day(session, user, at, card.id),
        cap=user.daily_review_cap,
        duration_sec=duration_sec,
    )
    apply_state(card, new)
    session.add(Review(card_id=card.id, rating=int(rating), duration_sec=duration_sec, reviewed_at=at))


async def _get_card(session: AsyncSession, user: User, card_id: int) -> Card:
    card = await session.get(Card, card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(404, "Card not found")
    return card


@router.post("/cards", response_model=CardOut, status_code=201)
async def create_card(
    body: CardCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    problem = await session.get(Problem, body.problem_id)
    if problem is None:
        raise HTTPException(404, "Problem not found")
    exists = await session.scalar(
        select(Card.id).where(Card.user_id == user.id, Card.problem_id == problem.id)
    )
    if exists:
        raise HTTPException(409, "You already track this problem")

    now = clock.now()
    solved_at = body.solved_at or now
    if solved_at > now + timedelta(minutes=5) or solved_at < now - MAX_BACKDATE:
        raise HTTPException(422, "Solved time must be within the last 90 days")
    solved_at = min(solved_at, now)

    patterns = body.patterns if body.patterns is not None else default_patterns(problem.lc_tags)
    first = scheduling.new_card(solved_at)
    card = Card(
        user_id=user.id,
        problem=problem,
        notes=body.notes,
        due=first.due,
        state=first.state,
        pattern_links=[CardPattern(pattern=p) for p in patterns],
    )
    session.add(card)
    await session.flush()
    await _review(session, user, card, body.rating, body.duration_sec, at=solved_at)
    await session.commit()
    return to_out(card, now)


@router.get("/cards", response_model=list[CardOut])
async def list_cards(
    pattern: str | None = None,
    status: Literal["all", "due", "active", "suspended"] = "all",
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    at = clock.now()
    q = select(Card).where(Card.user_id == user.id).order_by(Card.due)
    if pattern:
        q = q.where(Card.id.in_(select(CardPattern.card_id).where(CardPattern.pattern == pattern)))
    if status == "suspended":
        q = q.where(Card.suspended.is_(True))
    elif status in ("due", "active"):
        q = q.where(Card.suspended.is_(False))
    if status == "due":
        q = q.where(Card.due < scheduling.end_of_local_day(at, user.timezone))
    cards = (await session.scalars(q)).unique().all()
    return [to_out(c, at) for c in cards]


@router.patch("/cards/{card_id}", response_model=CardOut)
async def update_card(
    card_id: int,
    body: CardUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(session, user, card_id)
    if body.patterns is not None:
        card.pattern_links = [CardPattern(pattern=p) for p in body.patterns]
    if body.notes is not None:
        card.notes = body.notes
    if body.suspended is not None:
        card.suspended = body.suspended
    await session.commit()
    return to_out(card, clock.now())


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(session, user, card_id)
    await session.delete(card)
    await session.commit()
    return Response(status_code=204)


@router.post("/cards/{card_id}/reviews", response_model=CardOut)
async def review_card(
    card_id: int,
    body: ReviewIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(session, user, card_id)
    if card.suspended:
        raise HTTPException(409, "Card is suspended")
    await _review(session, user, card, body.rating, body.duration_sec)
    await session.commit()
    return to_out(card, clock.now())


@router.get("/queue/today", response_model=QueueOut)
async def today(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    at = clock.now()
    tz = ZoneInfo(user.timezone)
    cards = (
        await session.scalars(
            select(Card).where(
                Card.user_id == user.id,
                Card.suspended.is_(False),
                Card.due < scheduling.end_of_local_day(at, user.timezone),
            )
        )
    ).unique().all()
    queue, overflow = scheduling.build_queue(cards, Card.schedule_state, at, user.timezone, user.daily_review_cap)

    start_of_day = datetime.combine(at.astimezone(tz).date(), time.min, tzinfo=tz)
    reviewed_today = await session.scalar(
        select(func.count(Review.id))
        .join(Card, Card.id == Review.card_id)
        .where(Card.user_id == user.id, Review.reviewed_at >= start_of_day)
    )
    return QueueOut(cards=[to_out(c, at) for c in queue], overflow=overflow, reviewed_today=reviewed_today or 0)
