"""Per-pattern strength. Pure: takes cards and a time, no database."""
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median

from app import scheduling
from app.models import Card
from app.patterns import PATTERNS

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
