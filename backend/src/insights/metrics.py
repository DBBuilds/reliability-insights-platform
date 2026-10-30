"""Metric definitions as pure functions. No I/O here, so every rule is unit-testable.

Conventions that hold everywhere:
- Durations are minutes. Medians and p90s, never means (one 3-day incident would
  dominate a mean).
- A statistic with too few samples is None, not 0. The API returns the sample
  size next to it so the UI can say "not enough data".
- Open items are excluded from duration stats and counted separately, because
  dropping them silently makes a team that never closes anything look fast.
- Windows are half-open [start, end) and fixed (explicit dates). Rolling
  "last N days" windows shift by a day between two reads and make numbers
  appear to change when nothing happened.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from insights.models import Deploy, Incident, Page, Severity, SupportRequest

MIN_SAMPLE = 3  # below this, duration stats are None


@dataclass(frozen=True)
class DurationStat:
    sample_size: int
    median_minutes: float | None
    p90_minutes: float | None


@dataclass(frozen=True)
class WeeklyCount:
    week_start: date
    count: int
    partial: bool  # True when the window covers only part of this week


def percentile(values: Sequence[float], pct: float) -> float | None:
    """Nearest-rank percentile (pct in 0..100). Deterministic and easy to reproduce by hand."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def duration_stat(minutes: Iterable[float], min_sample: int = MIN_SAMPLE) -> DurationStat:
    values = [m for m in minutes if m >= 0]  # negative = bad source data; drop, don't clamp
    if len(values) < min_sample:
        return DurationStat(len(values), None, None)
    return DurationStat(len(values), round(median(values), 1), round(percentile(values, 90), 1))


def _minutes(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 60


def time_to_detect(incidents: Iterable[Incident]) -> DurationStat:
    """MTTD: impact start to detection, for incidents with a known detection time."""
    return duration_stat(_minutes(i.started_at, i.detected_at) for i in incidents if i.detected_at)


def time_to_resolve(incidents: Iterable[Incident]) -> DurationStat:
    """MTTR: impact start to resolution, resolved incidents only (open ones are counted separately)."""
    return duration_stat(_minutes(i.started_at, i.resolved_at) for i in incidents if i.resolved_at)


def open_count(incidents: Iterable[Incident]) -> int:
    return sum(1 for i in incidents if i.resolved_at is None)


def by_severity(incidents: Iterable[Incident]) -> dict[Severity, int]:
    counts = Counter(i.severity for i in incidents)
    return {s: counts.get(s, 0) for s in Severity}


def change_failure_rate(deploys: Sequence[Deploy], incidents: Iterable[Incident]) -> float | None:
    """Share of deploys in the window linked to an incident. None with no deploys."""
    if not deploys:
        return None
    ids = {d.id for d in deploys}
    failed = {i.caused_by_deploy_id for i in incidents if i.caused_by_deploy_id in ids}
    return round(len(failed) / len(ids), 4)


def is_off_hours(ts: datetime, start_hour: int = 9, end_hour: int = 18) -> bool:
    """Weekend, or outside [start_hour, end_hour) in the timestamp's own timezone."""
    return ts.weekday() >= 5 or not (start_hour <= ts.hour < end_hour)


def actionable_share(pages: Sequence[Page]) -> float | None:
    """Share of pages the responder marked actionable, among pages that were marked at all."""
    marked = [p for p in pages if p.actionable is not None]
    return round(sum(p.actionable for p in marked) / len(marked), 4) if marked else None


def noisiest_alerts(pages: Iterable[Page], top: int = 5) -> list[tuple[str, int]]:
    return Counter(p.alert_name for p in pages).most_common(top)


def first_response(requests: Iterable[SupportRequest]) -> DurationStat:
    """Opened to first HUMAN response. Bot replies must be excluded upstream by the connector."""
    return duration_stat(
        _minutes(r.opened_at, r.first_human_response_at) for r in requests if r.first_human_response_at
    )


def resolution_rate(requests: Sequence[SupportRequest]) -> float | None:
    """Closed / all. Depends on how consistently people close threads: report it with that caveat."""
    return round(sum(1 for r in requests if r.closed_at) / len(requests), 4) if requests else None


def weekly_counts(timestamps: Iterable[datetime], start: date, end: date) -> list[WeeklyCount]:
    """Counts per ISO week (Monday start) across [start, end). Edge weeks are flagged partial.

    Weeks are UTC, like the window bounds. Partial weeks always understate. Compare complete weeks only.
    """
    first_monday = start - timedelta(days=start.weekday())
    counts: Counter[date] = Counter()
    for ts in timestamps:
        d = ts.astimezone(UTC).date()
        if start <= d < end:
            counts[d - timedelta(days=d.weekday())] += 1
    out, week = [], first_monday
    while week < end:
        partial = week < start or week + timedelta(days=7) > end
        out.append(WeeklyCount(week, counts.get(week, 0), partial))
        week += timedelta(days=7)
    return out


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current - previous) / previous * 100, 1)
