from datetime import timedelta

from app import clock
from app.patterns import PATTERNS, PRACTICE_TAG
from tests.conftest import signup
from tests.test_api import add


def test_every_pattern_has_a_practice_tag():
    assert set(PRACTICE_TAG) == set(PATTERNS)


async def test_new_user_sees_all_patterns_untracked(user_client):
    stats = (await user_client.get("/stats/patterns")).json()
    assert [s["pattern"] for s in stats] == list(PATTERNS)
    assert all(s["problems"] == 0 and s["avg_recall"] is None for s in stats)
    assert stats[0]["practice_url"] == "https://leetcode.com/problemset/?topicSlugs=hash-table"


async def test_weakest_pattern_first(user_client):
    await add(user_client, "200", rating=1)  # graphs + union-find, failed
    await add(user_client, "739", rating=4)  # monotonic-stack, solved cold
    clock.travel(timedelta(days=3))

    stats = (await user_client.get("/stats/patterns")).json()
    tracked = [s for s in stats if s["problems"]]
    assert {s["pattern"] for s in tracked} == {"graphs", "union-find", "monotonic-stack"}
    assert tracked[-1]["pattern"] == "monotonic-stack"
    assert tracked[0]["avg_recall"] < tracked[-1]["avg_recall"]
    graphs = next(s for s in tracked if s["pattern"] == "graphs")
    assert graphs["due"] == 1
    assert graphs["weakest"][0]["problem"]["slug"] == "number-of-islands"
    assert 0 < graphs["weakest"][0]["recall"] < 1
    assert graphs["holds_days"] > 0
    # Untracked patterns follow, in catalog order.
    untracked = [s["pattern"] for s in stats[len(tracked):]]
    assert untracked == [p for p in PATTERNS if p not in {"graphs", "union-find", "monotonic-stack"}]


async def test_paused_problems_are_excluded(user_client):
    card = await add(user_client, "739")
    await user_client.patch(f"/cards/{card['id']}", json={"suspended": True})
    stats = (await user_client.get("/stats/patterns")).json()
    assert all(s["problems"] == 0 for s in stats)


async def test_stats_are_per_user(user_client, make_client):
    await add(user_client, "739")
    async with make_client() as other:
        await signup(other, "b@example.com")
        stats = (await other.get("/stats/patterns")).json()
        assert all(s["problems"] == 0 for s in stats)
