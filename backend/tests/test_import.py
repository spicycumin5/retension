from datetime import datetime, timedelta, timezone

import httpx

from app import clock, leetcode
from tests.conftest import FAKE_RECENT, REAL_RECENT_ACCEPTED
from tests.test_api import add


def solve(slug: str, days_ago: float) -> leetcode.Solve:
    return leetcode.Solve(slug=slug, title=slug.replace("-", " ").title(), solved_at=clock.now() - timedelta(days=days_ago))


async def test_requires_username(user_client):
    r = await user_client.get("/import/leetcode")
    assert r.status_code == 409 and "Settings" in r.json()["detail"]


async def test_username_validation_and_clearing(user_client):
    assert (await user_client.patch("/users/me", json={"leetcode_username": "bad name!"})).status_code == 422
    r = await user_client.patch("/users/me", json={"leetcode_username": "  coder_1  "})
    assert r.json()["leetcode_username"] == "coder_1"
    r = await user_client.patch("/users/me", json={"leetcode_username": ""})
    assert r.json()["leetcode_username"] is None


async def test_unknown_leetcode_user(user_client):
    await user_client.patch("/users/me", json={"leetcode_username": "ghost"})
    r = await user_client.get("/import/leetcode")
    assert r.status_code == 404 and "ghost" in r.json()["detail"]


async def test_lists_untracked_undismissed_solves(user_client):
    FAKE_RECENT["coder"] = [solve("two-sum", 0.5), solve("daily-temperatures", 1), solve("number-of-islands", 2)]
    await user_client.patch("/users/me", json={"leetcode_username": "coder"})
    await add(user_client, "two-sum")

    body = (await user_client.get("/import/leetcode")).json()
    assert [i["slug"] for i in body["items"]] == ["daily-temperatures", "number-of-islands"]
    assert body["already_tracked"] == 1
    assert body["items"][0]["url"] == "https://leetcode.com/problems/daily-temperatures/"

    assert (await user_client.post("/import/leetcode/dismiss", json={"slug": "number-of-islands"})).status_code == 204
    assert (await user_client.post("/import/leetcode/dismiss", json={"slug": "number-of-islands"})).status_code == 204
    body = (await user_client.get("/import/leetcode")).json()
    assert [i["slug"] for i in body["items"]] == ["daily-temperatures"]


async def test_import_schedules_from_solve_time(user_client):
    r = await user_client.post("/problems/resolve", json={"query": "daily-temperatures"})
    pid = r.json()["problem"]["id"]
    solved_at = clock.now() - timedelta(days=3)
    r = await user_client.post("/cards", json={"problem_id": pid, "rating": 3, "solved_at": solved_at.isoformat()})
    assert r.status_code == 201
    card = r.json()
    assert abs(datetime.fromisoformat(card["last_review"]) - solved_at) < timedelta(seconds=1)
    # A "Solved slowly" first review comes back ~2 days later, so it's already due.
    assert [c["id"] for c in (await user_client.get("/queue/today")).json()["cards"]] == [card["id"]]


async def test_solved_at_bounds(user_client):
    pid = (await user_client.post("/problems/resolve", json={"query": "1"})).json()["problem"]["id"]
    for bad in [clock.now() - timedelta(days=91), clock.now() + timedelta(hours=1)]:
        r = await user_client.post("/cards", json={"problem_id": pid, "rating": 3, "solved_at": bad.isoformat()})
        assert r.status_code == 422
    r = await user_client.post("/cards", json={"problem_id": pid, "rating": 3, "solved_at": "2026-01-01T00:00:00"})
    assert r.status_code == 422  # naive datetimes are rejected


async def test_recent_accepted_parses_and_keeps_latest_per_problem(monkeypatch):
    payload = {
        "data": {
            "matchedUser": {"username": "coder"},
            "recentAcSubmissionList": [
                {"title": "Two Sum", "titleSlug": "two-sum", "timestamp": "1790000000"},
                {"title": "Coin Change", "titleSlug": "coin-change", "timestamp": "1790000500"},
                {"title": "Two Sum", "titleSlug": "two-sum", "timestamp": "1790001000"},
            ],
        }
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    real_client = httpx.AsyncClient
    monkeypatch.setattr(leetcode.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw))
    solves = await REAL_RECENT_ACCEPTED("coder")
    assert [(s.slug, s.solved_at) for s in solves] == [
        ("two-sum", datetime.fromtimestamp(1790001000, tz=timezone.utc)),
        ("coin-change", datetime.fromtimestamp(1790000500, tz=timezone.utc)),
    ]
