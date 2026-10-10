"""Dev-only helpers. Mounted only when ENV=dev."""
from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import clock

router = APIRouter(prefix="/dev", tags=["dev"])


class TravelIn(BaseModel):
    days: float = Field(ge=-3650, le=3650)


class ClockOut(BaseModel):
    now: datetime


@router.post("/time-travel", response_model=ClockOut)
async def time_travel(body: TravelIn):
    return ClockOut(now=clock.travel(timedelta(days=body.days)))


@router.post("/time-reset", response_model=ClockOut)
async def time_reset():
    clock.reset()
    return ClockOut(now=clock.now())


@router.get("/clock", response_model=ClockOut)
async def get_clock():
    return ClockOut(now=clock.now())
