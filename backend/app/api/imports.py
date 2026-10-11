import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import leetcode
from app.db import get_session
from app.models import Card, DismissedImport, Problem, User
from app.ratelimit import rate_limit
from app.schemas import DismissIn, ImportItem, ImportOut
from app.users import current_user

router = APIRouter(prefix="/import/leetcode", tags=["import"])


@router.get("", response_model=ImportOut, dependencies=[Depends(rate_limit("import", 10, 60))])
async def recent_solves(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if not user.leetcode_username:
        raise HTTPException(409, "Add your LeetCode username in Settings to import solves.")
    try:
        solves = await leetcode.recent_accepted(user.leetcode_username)
    except leetcode.ResolveError as e:
        raise HTTPException(404, f"{e}. Check the username in Settings.")
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach LeetCode right now. Try again shortly.")

    tracked = set(
        await session.scalars(
            select(Problem.slug).join(Card, Card.problem_id == Problem.id).where(Card.user_id == user.id)
        )
    )
    dismissed = set(await session.scalars(select(DismissedImport.slug).where(DismissedImport.user_id == user.id)))
    items = [
        ImportItem(
            slug=s.slug,
            title=s.title,
            url=f"https://leetcode.com/problems/{s.slug}/",
            solved_at=s.solved_at,
        )
        for s in solves
        if s.slug not in tracked and s.slug not in dismissed
    ]
    return ImportOut(
        username=user.leetcode_username,
        items=items,
        already_tracked=sum(1 for s in solves if s.slug in tracked),
    )


@router.post("/dismiss", status_code=204)
async def dismiss(body: DismissIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if not await session.get(DismissedImport, (user.id, body.slug)):
        session.add(DismissedImport(user_id=user.id, slug=body.slug))
        await session.commit()
