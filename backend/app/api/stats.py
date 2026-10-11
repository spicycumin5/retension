from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import clock
from app.db import get_session
from app.models import Card, DismissedImport, Problem, User
from app.patterns import PATTERNS, practice_url
from app.problem_bank import BankProblem
from app.schemas import BankProblemOut, PatternStatsOut, ProblemOut, SuggestionOut, WeakCardOut
from app.stats import next_in_pattern, pattern_stats, suggest
from app.users import current_user

router = APIRouter(tags=["stats"])


def _bank_out(p: BankProblem) -> BankProblemOut:
    return BankProblemOut(slug=p.slug, title=p.title, difficulty=p.difficulty, lc_number=p.lc_number, url=p.url)


async def _known_slugs(session: AsyncSession, user: User) -> set[str]:
    """Problems not to suggest: ones the user tracks (even paused) or chose not to track."""
    tracked = await session.scalars(
        select(Problem.slug).join(Card, Card.problem_id == Problem.id).where(Card.user_id == user.id)
    )
    dismissed = await session.scalars(select(DismissedImport.slug).where(DismissedImport.user_id == user.id))
    return set(tracked) | set(dismissed)


async def _active_cards(session: AsyncSession, user: User):
    return (
        await session.scalars(select(Card).where(Card.user_id == user.id, Card.suspended.is_(False)))
    ).unique().all()


@router.get("/stats/patterns", response_model=list[PatternStatsOut])
async def patterns(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    known = await _known_slugs(session, user)
    stats = pattern_stats(await _active_cards(session, user), clock.now(), user.timezone)
    out = []
    for s in stats:
        nxt = next_in_pattern(s.pattern, known)
        out.append(
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
                next_problem=_bank_out(nxt) if nxt else None,
            )
        )
    return out


@router.get("/suggestions", response_model=list[SuggestionOut])
async def suggestions(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    known = await _known_slugs(session, user)
    stats = pattern_stats(await _active_cards(session, user), clock.now(), user.timezone)
    return [
        SuggestionOut(pattern=s.pattern, name=PATTERNS[s.pattern], reason=s.reason, problem=_bank_out(s.problem))
        for s in suggest(stats, known)
    ]
