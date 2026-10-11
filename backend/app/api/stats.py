from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import clock
from app.db import get_session
from app.models import Card, User
from app.patterns import PATTERNS, practice_url
from app.schemas import PatternStatsOut, ProblemOut, WeakCardOut
from app.stats import pattern_stats
from app.users import current_user

router = APIRouter(tags=["stats"])


@router.get("/stats/patterns", response_model=list[PatternStatsOut])
async def patterns(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    cards = (
        await session.scalars(select(Card).where(Card.user_id == user.id, Card.suspended.is_(False)))
    ).unique().all()
    return [
        PatternStatsOut(
            pattern=s.pattern,
            name=PATTERNS[s.pattern],
            practice_url=practice_url(s.pattern),
            problems=s.problems,
            due=s.due,
            lapses=s.lapses,
            avg_recall=s.avg_recall,
            holds_days=s.holds_days,
            weakest=[
                WeakCardOut(card_id=c.id, problem=ProblemOut.model_validate(c.problem), recall=r)
                for c, r in s.weakest
            ],
        )
        for s in pattern_stats(cards, clock.now(), user.timezone)
    ]
