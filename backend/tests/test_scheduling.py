from collections import Counter
from datetime import datetime, timedelta, timezone

import fsrs
import pytest

from app import scheduling as s
from app.scheduling import CardState, UserRating

T0 = datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc)


def first(rating: UserRating, at: datetime = T0, **kw) -> CardState:
    return s.review(s.new_card(at), rating, at, **kw)


def test_rating_mapping():
    assert s.to_fsrs_rating(UserRating.FAILED) == fsrs.Rating.Again
    assert s.to_fsrs_rating(UserRating.HINT) == fsrs.Rating.Hard
    assert s.to_fsrs_rating(UserRating.SLOW) == fsrs.Rating.Good
    assert s.to_fsrs_rating(UserRating.COLD) == fsrs.Rating.Easy


def test_first_review_goes_straight_to_day_intervals():
    for rating in UserRating:
        card = first(rating)
        assert card.due - T0 >= timedelta(days=1)
        assert card.reps == 1 and card.lapses == 0


def test_better_ratings_give_longer_first_intervals():
    failed, cold = first(UserRating.FAILED), first(UserRating.COLD)
    assert cold.due > failed.due


def test_intervals_grow_with_successful_reviews():
    card = first(UserRating.SLOW)
    prev_interval = card.due - T0
    for _ in range(4):
        at = card.due
        card = s.review(card, UserRating.SLOW, at)
        interval = card.due - at
        assert interval > prev_interval
        prev_interval = interval


def test_failing_counts_a_lapse_and_shrinks_interval():
    card = first(UserRating.SLOW)
    for _ in range(3):
        card = s.review(card, UserRating.SLOW, card.due)
    long_interval = card.due - card.last_review
    at = card.due
    failed = s.review(card, UserRating.FAILED, at)
    assert failed.lapses == 1
    assert failed.due - at < long_interval


def test_balance_keeps_due_when_day_has_room():
    due = T0 + timedelta(days=20)
    load = {s.local_date(due, "UTC"): 2}
    assert s.balance(T0, due, "UTC", load, cap=3) == due


def test_balance_moves_off_a_full_day_within_window():
    due = T0 + timedelta(days=20)
    target = s.local_date(due, "UTC")
    lo, hi = s.balance_window(T0, due, "UTC")
    load = Counter({lo + timedelta(days=i): 3 for i in range((hi - lo).days + 1)})
    load[target + timedelta(days=2)] = 0
    moved = s.balance(T0, due, "UTC", load, cap=3)
    assert s.local_date(moved, "UTC") == target + timedelta(days=2)
    assert moved.time() == due.time()


def test_balance_never_moves_to_today_or_earlier():
    due = T0 + timedelta(days=1)
    load = {s.local_date(due, "UTC"): 5}
    moved = s.balance(T0, due, "UTC", load, cap=3)
    assert s.local_date(moved, "UTC") > s.local_date(T0, "UTC")


def test_review_applies_balancing(monkeypatch):
    shifted = T0 + timedelta(days=42)
    calls = []

    def fake_balance(review_at, due, tz, load, cap, latest=None):
        calls.append((review_at, tz, cap))
        return shifted

    monkeypatch.setattr(s, "balance", fake_balance)
    card = first(UserRating.COLD, tz="Asia/Seoul", load={}, cap=3)
    assert card.due == shifted
    assert calls == [(T0, "Asia/Seoul", 3)]


def test_queue_orders_by_retrievability_and_caps():
    at = T0 + timedelta(days=30)
    fresh = first(UserRating.SLOW, at=T0 + timedelta(days=27))  # due ~day 29
    stale = first(UserRating.HINT, at=T0)
    not_due = first(UserRating.COLD, at=at)
    cards = {"fresh": fresh, "stale": stale, "not_due": not_due}
    queue, overflow = s.build_queue(cards, cards.get, at, "UTC", cap=1)
    assert queue == ["stale"]
    assert overflow == 1


def test_queue_uses_local_day():
    # At 12:00 UTC it is Oct 10 in New York (due before midnight there) but already 21:00 in Seoul,
    # whose day ends at 15:00 UTC, before the 03:00 UTC due time.
    card = CardState(due=datetime(2026, 10, 11, 3, tzinfo=timezone.utc), state=2, stability=5, difficulty=5,
                     last_review=T0 - timedelta(days=5), reps=1)
    at = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    assert s.build_queue([card], lambda c: c, at, "America/New_York", 3)[0] == [card]
    assert s.build_queue([card], lambda c: c, at, "Asia/Seoul", 3)[0] == []


@pytest.mark.parametrize("tz", ["UTC", "Asia/Seoul", "America/Los_Angeles"])
def test_end_of_local_day_is_after_now(tz):
    end = s.end_of_local_day(T0, tz)
    assert timedelta(0) < end - T0 <= timedelta(days=1)


def test_max_interval_caps_due_date():
    card = first(UserRating.COLD)
    for _ in range(4):
        card = s.review(card, UserRating.COLD, card.due)
    uncapped = card
    capped = s.review(uncapped, UserRating.COLD, uncapped.due, max_interval_days=30)
    free = s.review(uncapped, UserRating.COLD, uncapped.due)
    assert free.due - uncapped.due > timedelta(days=30)
    assert capped.due - uncapped.due == timedelta(days=30)


def test_balancing_never_pushes_past_max_interval():
    at = T0
    limit = at + timedelta(days=30)
    lo, _ = s.balance_window(at, limit, "UTC")
    full = {lo + timedelta(days=i): 9 for i in range(60)}
    full[s.local_date(limit, "UTC") + timedelta(days=1)] = 0  # tempting free day just past the cap
    moved = s.balance(at, limit, "UTC", full, cap=3, latest=s.local_date(limit, "UTC"))
    assert moved <= limit
