from collections import Counter
from datetime import datetime, timedelta

from app import clock
from tests.conftest import signup


async def add(client, query: str, rating: int = 3, **extra) -> dict:
    r = await client.post("/problems/resolve", json={"query": query})
    assert r.status_code == 200, r.text
    problem_id = r.json()["problem"]["id"]
    r = await client.post("/cards", json={"problem_id": problem_id, "rating": rating, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def test_unverified_user_is_blocked(client):
    await client.post("/auth/register", json={"email": "u@example.com", "password": "hunter2hunter2"})
    await client.post("/auth/login", data={"username": "u@example.com", "password": "hunter2hunter2"})
    assert (await client.get("/users/me")).json()["is_verified"] is False
    assert (await client.get("/queue/today")).status_code == 403


async def test_anonymous_is_blocked(client):
    assert (await client.get("/cards")).status_code == 401


async def test_resolve_by_url_number_and_slug(user_client):
    for q in ["https://leetcode.com/problems/daily-temperatures/description/", "739", "Daily Temperatures"]:
        r = await user_client.post("/problems/resolve", json={"query": q})
        assert r.status_code == 200, (q, r.text)
        body = r.json()
        assert body["problem"]["slug"] == "daily-temperatures"
        assert body["default_patterns"] == ["monotonic-stack"]
        assert body["card_id"] is None


async def test_resolve_unknown_problem(user_client):
    r = await user_client.post("/problems/resolve", json={"query": "not-a-real-problem"})
    assert r.status_code == 404


async def test_full_review_flow(user_client):
    card = await add(user_client, "739", rating=3, duration_sec=900)
    assert card["reps"] == 1
    assert card["patterns"] == ["monotonic-stack"]
    first_due = datetime.fromisoformat(card["due"])

    # Logged today, nothing due yet.
    q = (await user_client.get("/queue/today")).json()
    assert q["cards"] == [] and q["reviewed_today"] == 1

    # Duplicate add is rejected, and resolve now reports the card.
    r = await user_client.post("/cards", json={"problem_id": card["problem"]["id"], "rating": 3})
    assert r.status_code == 409
    r = await user_client.post("/problems/resolve", json={"query": "739"})
    assert r.json()["card_id"] == card["id"]

    clock.travel(timedelta(days=4))
    q = (await user_client.get("/queue/today")).json()
    assert [c["id"] for c in q["cards"]] == [card["id"]]
    assert q["reviewed_today"] == 0

    r = await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 4, "duration_sec": 300})
    assert r.status_code == 200
    reviewed = r.json()
    assert reviewed["reps"] == 2
    assert datetime.fromisoformat(reviewed["due"]) - clock.now() > first_due - datetime.fromisoformat(card["last_review"])
    assert (await user_client.get("/queue/today")).json()["cards"] == []


async def test_queue_respects_cap_and_reports_overflow(user_client):
    for q in ["739", "1", "200"]:
        await add(user_client, q, rating=1)
    await user_client.patch("/users/me", json={"daily_review_cap": 2})
    clock.travel(timedelta(days=3))
    q = (await user_client.get("/queue/today")).json()
    assert len(q["cards"]) == 2 and q["overflow"] == 1


async def test_bulk_additions_spread_across_days(user_client):
    await user_client.patch("/users/me", json={"daily_review_cap": 1})
    cards = [await add(user_client, q, rating=3) for q in ["739", "1", "217", "200"]]
    assert len({datetime.fromisoformat(c["due"]).date() for c in cards}) == 4


async def test_overdue_imports_spread_from_today(user_client):
    await user_client.patch("/users/me", json={"daily_review_cap": 2})
    solved_at = (clock.now() - timedelta(days=30)).isoformat()
    cards = [await add(user_client, q, rating=3, solved_at=solved_at) for q in ["739", "1", "217", "200"]]
    assert all(datetime.fromisoformat(c["due"]) >= clock.now() - timedelta(seconds=5) for c in cards)
    assert len((await user_client.get("/queue/today")).json()["cards"]) == 2
    days = Counter(datetime.fromisoformat(c["due"]).date() for c in cards)
    assert sorted(days.values()) == [2, 2]


async def test_patch_patterns_notes_suspend_and_filters(user_client):
    card = await add(user_client, "200")
    assert card["patterns"] == ["graphs", "union-find"]

    r = await user_client.patch(f"/cards/{card['id']}", json={"patterns": ["graphs"], "notes": "flood fill"})
    assert r.json()["patterns"] == ["graphs"] and r.json()["notes"] == "flood fill"
    r = await user_client.patch(f"/cards/{card['id']}", json={"patterns": ["nope"]})
    assert r.status_code == 422

    await add(user_client, "1")
    assert [c["id"] for c in (await user_client.get("/cards?pattern=graphs")).json()] == [card["id"]]

    await user_client.patch(f"/cards/{card['id']}", json={"suspended": True})
    clock.travel(timedelta(days=30))
    due_ids = [c["id"] for c in (await user_client.get("/cards?status=due")).json()]
    assert card["id"] not in due_ids and len(due_ids) == 1
    r = await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 3})
    assert r.status_code == 409


async def test_delete_card(user_client):
    card = await add(user_client, "1")
    assert (await user_client.delete(f"/cards/{card['id']}")).status_code == 204
    assert (await user_client.get("/cards")).json() == []


async def test_users_cannot_touch_each_others_cards(user_client, make_client):
    card = await add(user_client, "1")
    async with make_client() as other:
        await signup(other, "b@example.com")
        assert (await other.get("/cards")).json() == []
        assert (await other.post(f"/cards/{card['id']}/reviews", json={"rating": 3})).status_code == 404
        assert (await other.delete(f"/cards/{card['id']}")).status_code == 404


async def test_settings_validation(user_client):
    assert (await user_client.patch("/users/me", json={"timezone": "Mars/Base"})).status_code == 422
    assert (await user_client.patch("/users/me", json={"digest_hour": 24})).status_code == 422
    r = await user_client.patch("/users/me", json={"timezone": "Asia/Seoul", "digest_hour": 7})
    assert r.status_code == 200 and r.json()["timezone"] == "Asia/Seoul"


async def test_max_interval_setting(user_client):
    me = (await user_client.get("/users/me")).json()
    assert me["max_interval_days"] == 180
    assert (await user_client.patch("/users/me", json={"max_interval_days": 3})).status_code == 422
    assert (await user_client.patch("/users/me", json={"max_interval_days": 14})).status_code == 200

    card = await add(user_client, "1", rating=4)
    for _ in range(4):
        clock.travel(datetime.fromisoformat(card["due"]) - clock.now() + timedelta(hours=1))
        card = (await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 4})).json()
        gap = datetime.fromisoformat(card["due"]) - datetime.fromisoformat(card["last_review"])
        assert gap <= timedelta(days=14)


async def test_lowering_max_interval_pulls_in_scheduled_reviews(user_client):
    card = await add(user_client, "1", rating=4)
    for _ in range(3):
        clock.travel(datetime.fromisoformat(card["due"]) - clock.now() + timedelta(hours=1))
        card = (await user_client.post(f"/cards/{card['id']}/reviews", json={"rating": 4})).json()
    last = datetime.fromisoformat(card["last_review"])
    assert datetime.fromisoformat(card["due"]) - last > timedelta(days=30)

    await user_client.patch("/users/me", json={"max_interval_days": 30})
    [updated] = (await user_client.get("/cards")).json()
    assert datetime.fromisoformat(updated["due"]) - last == timedelta(days=30)
