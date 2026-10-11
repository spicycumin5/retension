from datetime import timedelta

from app import clock
from app.patterns import PATTERNS
from app.problem_bank import BANK
from tests.conftest import FAKE_RECENT
from tests.test_api import add
from tests.test_import import solve


def test_bank_covers_every_pattern():
    assert set(BANK) == set(PATTERNS)
    for pattern, problems in BANK.items():
        assert len(problems) >= 3, pattern
        assert len({p.slug for p in problems}) == len(problems), pattern
        assert all(p.difficulty in {"Easy", "Medium", "Hard"} for p in problems)


async def test_new_user_gets_starter_patterns(user_client):
    s = (await user_client.get("/suggestions")).json()
    assert [(x["pattern"], x["problem"]["slug"]) for x in s] == [
        ("arrays-hashing", "contains-duplicate"),
        ("two-pointers", "valid-palindrome"),
        ("sliding-window", "best-time-to-buy-and-sell-stock"),
    ]
    assert s[0]["reason"] == "A pattern you haven’t started"
    assert s[0]["problem"]["url"] == "https://leetcode.com/problems/contains-duplicate/"


async def test_weakest_patterns_come_first_and_skip_tracked(user_client):
    await add(user_client, "contains-duplicate", rating=1)  # arrays-hashing, failed
    await add(user_client, "739", rating=4)  # monotonic-stack, solved cold
    clock.travel(timedelta(days=3))

    s = (await user_client.get("/suggestions")).json()
    assert [x["pattern"] for x in s] == ["arrays-hashing", "monotonic-stack", "two-pointers"]
    assert s[0]["problem"]["slug"] == "valid-anagram"  # contains-duplicate is already tracked
    assert s[0]["reason"].startswith("Lowest recall of your patterns, ")
    assert s[1]["problem"]["slug"] == "next-greater-element-i"


async def test_skipped_imports_are_not_suggested(user_client):
    FAKE_RECENT["coder"] = [solve("contains-duplicate", 1)]
    await user_client.patch("/users/me", json={"leetcode_username": "coder"})
    await user_client.post("/import/leetcode/dismiss", json={"slug": "contains-duplicate"})
    s = (await user_client.get("/suggestions")).json()
    assert s[0]["problem"]["slug"] == "valid-anagram"


async def test_pattern_stats_include_next_problem(user_client):
    await add(user_client, "739")
    stats = {s["pattern"]: s for s in (await user_client.get("/stats/patterns")).json()}
    assert stats["monotonic-stack"]["next_problem"]["slug"] == "next-greater-element-i"
    assert stats["trees"]["next_problem"]["slug"] == "invert-binary-tree"
