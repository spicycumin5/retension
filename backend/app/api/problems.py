import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import leetcode
from app.db import get_session
from app.models import Card, Problem, User
from app.patterns import PATTERNS, default_patterns
from app.ratelimit import rate_limit
from app.schemas import PatternOut, ProblemOut, ResolveIn, ResolveOut
from app.users import current_user

router = APIRouter(tags=["problems"])


@router.get("/patterns", response_model=list[PatternOut])
async def list_patterns():
    return [PatternOut(slug=slug, name=name) for slug, name in PATTERNS.items()]


async def _get_or_fetch(session: AsyncSession, query: str) -> Problem:
    try:
        slug, number = leetcode.parse_query(query)
    except leetcode.ResolveError as e:
        raise HTTPException(422, str(e))

    cached = await session.scalar(
        select(Problem).where(Problem.lc_number == number if number else Problem.slug == slug)
    )
    if cached:
        return cached

    try:
        if number:
            slug = await leetcode.slug_for_number(number)
        info = await leetcode.fetch_problem(slug)
    except leetcode.ResolveError as e:
        raise HTTPException(404, str(e))
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach LeetCode right now. Try again shortly.")

    # A different query (number vs slug) may already have cached it.
    existing = await session.scalar(
        select(Problem).where(
            or_(Problem.slug == info.slug, Problem.lc_number == info.lc_number)
            if info.lc_number
            else Problem.slug == info.slug
        )
    )
    if existing:
        return existing
    problem = Problem(
        slug=info.slug,
        lc_number=info.lc_number,
        title=info.title,
        difficulty=info.difficulty,
        lc_tags=info.lc_tags,
    )
    session.add(problem)
    try:
        await session.commit()
    except IntegrityError:  # concurrent insert of the same problem
        await session.rollback()
        return await session.scalar(select(Problem).where(Problem.slug == info.slug))
    return problem


@router.post(
    "/problems/resolve",
    response_model=ResolveOut,
    dependencies=[Depends(rate_limit("resolve", 30, 60))],
)
async def resolve(
    body: ResolveIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    problem = await _get_or_fetch(session, body.query)
    card_id = await session.scalar(
        select(Card.id).where(Card.user_id == user.id, Card.problem_id == problem.id)
    )
    return ResolveOut(
        problem=ProblemOut.model_validate(problem),
        default_patterns=default_patterns(problem.lc_tags),
        card_id=card_id,
    )
