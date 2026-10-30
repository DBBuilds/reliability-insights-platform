"""Rule-based insights: short callouts a leader can act on.

Each rule needs a minimum sample and a minimum change, so a move from 2 to 3
incidents never becomes a red "50% worse" headline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from insights.metrics import DurationStat, is_off_hours_slot, pct_change

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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


def mttr_trend(
    current: DurationStat, previous: DurationStat, threshold_pct: float = 25.0, min_sample: int = 5
) -> InsightItem | None:
    if min(current.sample_size, previous.sample_size) < min_sample:
        return None
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


def noisy_alert(
    top: list[tuple[str, int]], pages: int, share: float | None, min_pages: int = 30, min_share: float = 0.5
) -> InsightItem | None:
    """One alert sends at least half of all pages."""
    if not top or top[0][1] < max(min_pages, min_share * pages):
        return None
    name, count = top[0]
    extra = f" Only {share:.0%} of marked pages were actionable." if share is not None and share < 0.5 else ""
    return InsightItem(
        id="noisy-alert",
        level=InsightLevel.WARNING,
        title=f"'{name}' paged {count} times",
        detail=f"Tune or delete it in this week's ops review.{extra}",
    )


def cfr_spike(
    failed: int, deploys: int, previous_failed: int, previous_deploys: int, min_deploys: int = 20, min_failed: int = 5
) -> InsightItem | None:
    """Change failure rate at least doubled and rose at least 5 points, with enough deploys and failures."""
    if min(deploys, previous_deploys) < min_deploys or failed < min_failed:
        return None
    current, previous = failed / deploys, previous_failed / previous_deploys
    if current < 2 * previous or current - previous < 0.05:
        return None
    return InsightItem(
        id="cfr-spike",
        level=InsightLevel.WARNING,
        title="Change failure rate more than doubled vs. the previous period",
        detail=f"It was {previous:.0%} the period before ({previous_deploys} deploys). Review what shipped.",
    )


def off_hours_pages(
    off_hours: int, pages: int, by_hour: dict[tuple[int, int], int], min_pages: int = 20
) -> InsightItem | None:
    """At least half of pages arrive outside working hours."""
    if pages < min_pages or off_hours < 0.5 * pages:
        return None
    (day, hour), count = max(((slot, n) for slot, n in by_hour.items() if is_off_hours_slot(*slot)), key=lambda c: c[1])
    return InsightItem(
        id="off-hours-pages",
        level=InsightLevel.WARNING,
        title="Most pages arrive outside working hours",
        detail=f"Busiest: {DAYS[day]} {hour:02d}:00 local ({count} pages). Fix or reschedule what fires then.",
    )


def error_budget(slo_id: str, service: str, remaining: float | None, threshold: float = 0.25) -> InsightItem | None:
    if remaining is None or remaining > threshold:
        return None
    spent = remaining <= 0
    return InsightItem(
        id=f"error-budget:{slo_id}",
        level=InsightLevel.CRITICAL if spent else InsightLevel.WARNING,
        title=f"Error budget for {service} is {'spent' if spent else 'nearly spent'}",
        detail="Pause risky changes to it until the budget recovers.",
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
