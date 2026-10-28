"""Rule-based insights: short callouts a leader can act on.

Each rule needs a minimum sample and a minimum change, so a move from 2 to 3
incidents never becomes a red "50% worse" headline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from insights.metrics import DurationStat, pct_change


class InsightLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class InsightItem:
    id: str
    level: InsightLevel
    title: str
    detail: str | None = None


def mttr_trend(current: DurationStat, previous: DurationStat, threshold_pct: float = 25.0) -> InsightItem | None:
    change = pct_change(current.median_minutes, previous.median_minutes)
    if change is None or abs(change) < threshold_pct:
        return None
    worse = change > 0
    return InsightItem(
        id="mttr-trend",
        level=InsightLevel.WARNING if worse else InsightLevel.INFO,
        title=f"Median time to resolve {'up' if worse else 'down'} {abs(change):.0f}% vs. the previous period",
        # The current median is already on the Incidents card; show only the comparison point.
        detail=f"It was {previous.median_minutes:.0f} min the period before "
        f"({current.sample_size} resolved incidents).",
    )


def noisy_alert(top: list[tuple[str, int]], share: float | None, min_pages: int = 10) -> InsightItem | None:
    if not top or top[0][1] < min_pages:
        return None
    name, count = top[0]
    extra = f" Only {share:.0%} of marked pages were actionable." if share is not None and share < 0.5 else ""
    return InsightItem(
        id="noisy-alert",
        level=InsightLevel.WARNING,
        title=f"'{name}' paged {count} times",
        detail=f"Tune or delete it in this week's ops review.{extra}",
    )


def stale_sources(stale: list[str]) -> InsightItem | None:
    if not stale:
        return None
    return InsightItem(
        id="stale-data",
        level=InsightLevel.CRITICAL,
        title="Some data is stale",
        detail=f"No successful sync recently for: {', '.join(sorted(stale))}. Numbers for these may read low.",
    )
