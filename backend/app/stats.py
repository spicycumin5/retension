"""Per-pattern strength. Pure: takes cards and a time, no database."""
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median

from app import scheduling
from app.models import Card
from app.patterns import PATTERNS
from app.problem_bank import BANK, BankProblem

WEAKEST_SHOWN = 3


@dataclass
class PatternStats:
    pattern: str
    problems: int = 0
    due: int = 0
    lapses: int = 0
    avg_recall: float | None = None  # mean probability of recalling, right now
    holds_days: float | None = None  # median days until recall drops to 90%
    weakest: list[tuple[Card, float]] = field(default_factory=list)


def pattern_stats(cards: Iterable[Card], at: datetime, tz: str) -> list[PatternStats]:
    """Every catalog pattern, weakest tracked pattern first, then untracked ones in catalog order."""
    cutoff = scheduling.end_of_local_day(at, tz)
    by_pattern: dict[str, list[tuple[Card, float]]] = defaultdict(list)
    for card in cards:
        if card.suspended:
            continue
        recall = scheduling.retrievability(card.schedule_state(), at)
        for p in card.patterns:
            by_pattern[p].append((card, recall))

    tracked, untracked = [], []
    for slug in PATTERNS:
        entries = by_pattern.get(slug)
        if not entries:
            untracked.append(PatternStats(pattern=slug))
            continue
        entries.sort(key=lambda e: e[1])
        stabilities = [c.stability for c, _ in entries if c.stability is not None]
        tracked.append(
            PatternStats(
                pattern=slug,
                problems=len(entries),
                due=sum(1 for c, _ in entries if c.due < cutoff),
                lapses=sum(c.lapses for c, _ in entries),
                avg_recall=mean(r for _, r in entries),
                holds_days=median(stabilities) if stabilities else None,
                weakest=entries[:WEAKEST_SHOWN],
            )
        )
    tracked.sort(key=lambda s: (s.avg_recall, -s.due))
    return tracked + untracked


@dataclass
class Suggestion:
    pattern: str
    reason: str
    problem: BankProblem


def next_in_pattern(pattern: str, exclude: set[str]) -> BankProblem | None:
    return next((p for p in BANK.get(pattern, []) if p.slug not in exclude), None)


def suggest(stats: list[PatternStats], exclude: set[str], limit: int = 3, from_weak: int = 2) -> list[Suggestion]:
    """New problems to learn: the weakest tracked patterns first, then patterns not started yet.

    `stats` must be ordered as pattern_stats returns it; `exclude` holds slugs the user tracks or skipped.
    """
    picks: list[Suggestion] = []
    tracked = [s for s in stats if s.problems]
    for s in tracked:
        if len(picks) >= min(from_weak, limit):
            break
        if problem := next_in_pattern(s.pattern, exclude):
            picks.append(Suggestion(s.pattern, f"Lowest recall of your patterns, {round((s.avg_recall or 0) * 100)}%", problem))
    for s in stats:
        if len(picks) >= limit:
            break
        if s.problems == 0 and (problem := next_in_pattern(s.pattern, exclude)):
            picks.append(Suggestion(s.pattern, "A pattern you haven’t started", problem))
    return picks
