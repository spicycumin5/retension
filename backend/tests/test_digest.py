from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app import clock, digest, email
from app.db import SessionLocal
from app.models import User
from tests.conftest import signup
from tests.test_api import add

SEOUL = ZoneInfo("Asia/Seoul")


def seoul(days_from_now: int, hour: int, minute: int = 0) -> datetime:
    day = (clock.now() + timedelta(days=days_from_now)).astimezone(SEOUL).date()
    return datetime.combine(day, time(hour, minute), tzinfo=SEOUL)


async def run(at: datetime) -> digest.RunResult:
    async with SessionLocal() as session:
        return await digest.send_due_digests(session, at)


def digests() -> list[email.Message]:
    return [m for m in email.sender.outbox if "re-solve" in m.subject]


@pytest.fixture
async def seoul_user(client):
    await signup(client, "s@example.com", tz="Asia/Seoul")
    await add(client, "200", rating=1)  # due in ~1 day
    await add(client, "1", rating=1)
    return client


async def test_sends_once_at_local_digest_hour(seoul_user):
    assert (await run(seoul(3, 7, 30))).sent == 0  # before 08:00 Seoul

    result = await run(seoul(3, 8, 5))
    assert result.sent == 1
    [msg] = digests()
    assert msg.to == "s@example.com"
    assert msg.subject == "2 problems to re-solve today"
    assert "https://leetcode.com/problems/number-of-islands/" in msg.text
    assert "/unsubscribe?token=" in msg.text
    assert msg.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "/api/email/unsubscribe?token=" in msg.headers["List-Unsubscribe"]

    assert (await run(seoul(3, 9, 5))).sent == 0  # already sent today
    assert (await run(seoul(4, 8, 5))).sent == 1  # next day, still due
    assert len(digests()) == 2


async def test_missed_hour_still_sends_later_that_day(seoul_user):
    assert (await run(seoul(3, 14))).sent == 1


async def test_nothing_due_sends_nothing(seoul_user):
    # Digest hour 0 means it's always digest time; the cards were just logged so none are due today.
    await seoul_user.patch("/users/me", json={"digest_hour": 0})
    result = await run(clock.now())
    assert result.sent == 0 and result.skipped_nothing_due == 1
    assert digests() == []


async def test_respects_cap_and_reports_overflow(seoul_user):
    await seoul_user.patch("/users/me", json={"daily_review_cap": 1})
    await run(seoul(3, 8))
    [msg] = digests()
    assert msg.subject == "1 problem to re-solve today"
    assert "1 more overdue" in msg.text


async def test_disabled_and_unverified_users_are_skipped(seoul_user, make_client):
    await seoul_user.patch("/users/me", json={"digest_enabled": False})
    async with make_client() as other:
        await other.post("/auth/register", json={"email": "u@example.com", "password": "hunter2hunter2"})
    email.sender.outbox.clear()
    assert (await run(seoul(3, 8))).sent == 0
    assert digests() == []


async def test_failed_send_is_retried_next_run(seoul_user, monkeypatch):
    real_send = email.sender.send

    async def boom(message):
        raise RuntimeError("provider down")

    monkeypatch.setattr(email.sender, "send", boom)
    assert (await run(seoul(3, 8))).failed == 1
    monkeypatch.setattr(email.sender, "send", real_send)
    assert (await run(seoul(3, 9))).sent == 1


async def test_day_is_recorded_before_sending(seoul_user, monkeypatch):
    # If the job dies right after the send, the next run must not send the same digest again.
    real_send = email.sender.send
    recorded = []

    async def check_then_send(message):
        async with SessionLocal() as session:
            user = await session.scalar(select(User).where(User.email == "s@example.com"))
            recorded.append(user.last_digest_on)
        await real_send(message)

    monkeypatch.setattr(email.sender, "send", check_then_send)
    at = seoul(3, 8)
    assert (await run(at)).sent == 1
    assert recorded == [at.date()]


async def test_unsubscribe(seoul_user):
    await run(seoul(3, 8))
    token = digests()[0].text.split("unsubscribe?token=")[1].split()[0]

    assert (await seoul_user.post("/email/unsubscribe", params={"token": "nope"})).status_code == 404
    assert (await seoul_user.post("/email/unsubscribe", params={"token": token})).status_code == 204
    assert (await seoul_user.get("/users/me")).json()["digest_enabled"] is False
    assert (await run(seoul(4, 8))).sent == 0


async def test_digest_settings_validation(seoul_user):
    r = await seoul_user.patch("/users/me", json={"digest_hour": 21, "digest_enabled": True})
    assert r.status_code == 200 and r.json()["digest_hour"] == 21
    assert (await seoul_user.patch("/users/me", json={"digest_hour": -1})).status_code == 422
