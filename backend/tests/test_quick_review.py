from datetime import datetime, timedelta

from sqlalchemy import select

from app import clock, scheduling
from app.db import SessionLocal
from app.models import Review
from tests.test_api import add


async def review_until_eligible(client, card: dict) -> dict:
    for _ in range(6):
        if card["quick_eligible"]:
            return card
        clock.travel(datetime.fromisoformat(card["due"]) - clock.now() + timedelta(hours=1))
        card = (await client.post(f"/cards/{card['id']}/reviews", json={"rating": 4})).json()
    raise AssertionError("card never became quick-eligible")


def test_eligibility_threshold():
    base = scheduling.new_card(clock.now())
    assert not scheduling.quick_eligible(base)
    assert not scheduling.quick_eligible(scheduling.CardState(due=base.due, state=2, stability=20.9))
    assert scheduling.quick_eligible(scheduling.CardState(due=base.due, state=2, stability=21))


async def test_new_card_is_not_eligible(user_client):
    card = await add(user_client, "1", rating=3)
    assert card["quick_eligible"] is False
    r = await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 3, "mode": "quick"})
    assert r.status_code == 409


async def test_quick_review_flow(user_client):
    card = await review_until_eligible(user_client, await add(user_client, "1", rating=4))
    clock.travel(datetime.fromisoformat(card["due"]) - clock.now() + timedelta(hours=1))

    r = await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 4, "mode": "quick"})
    assert r.status_code == 422  # can't earn "Easy" from an outline

    r = await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 3, "mode": "quick", "duration_sec": 110})
    assert r.status_code == 200
    assert r.json()["reps"] == card["reps"] + 1

    async with SessionLocal() as session:
        modes = (await session.scalars(select(Review.mode).where(Review.card_id == card["id"]).order_by(Review.id))).all()
    assert modes[-1] == "quick" and set(modes[:-1]) == {"full"}
