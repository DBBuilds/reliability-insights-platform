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

from insights.models import Deploy, Incident, Page, Severity, SliDaily, Slo, SupportRequest

MIN_SAMPLE = 3  # below this, duration stats are None

# DORA software delivery performance levels from the 2024 Accelerate State of DevOps report
# (v.2024.3, p.13). They are survey clusters, not targets. Ranges are read as half-open
# [low, high), with a month as 30 days. High and Medium share a recovery range, and no level
# covers recovery between one day and one week.
_HOUR, _DAY = 60, 1440  # minutes
_WEEK, _MONTH = 7 * _DAY, 30 * _DAY
DORA_2024 = {
    "lead_time": {"ELITE": (0, _DAY), "HIGH": (_DAY, _WEEK), "MEDIUM": (_WEEK, _MONTH), "LOW": (_MONTH, 182 * _DAY)},
    "deploy_frequency": {  # deploys per day
        "ELITE": (1, math.inf),
        "HIGH": (1 / 7, 1),
        "MEDIUM": (1 / 30, 1 / 7),
        "LOW": (1 / 182, 1 / 30),
    },
    "recovery_time": {"ELITE": (0, _HOUR), "HIGH": (_HOUR, _DAY), "MEDIUM": (_HOUR, _DAY), "LOW": (_WEEK, _MONTH)},
}


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


def lead_time(deploys: Iterable[Deploy]) -> DurationStat:
    """Commit to deploy, for deploys with a known commit time."""
    return duration_stat(_minutes(d.committed_at, d.deployed_at) for d in deploys if d.committed_at)


def recovery_time(incidents: Iterable[Incident]) -> DurationStat:
    """Failed deployment recovery time: start to resolve, for resolved incidents a deploy caused."""
    return duration_stat(
        _minutes(i.started_at, i.resolved_at) for i in incidents if i.resolved_at and i.caused_by_deploy_id
    )


def deploy_frequency(deploys: Iterable[Deploy], days: int) -> tuple[float | None, int]:
    """Deploys per day for the median service, among services that deployed. Returns (value, services).

    Per service, not per org: an org's total grows with its size, while DORA's levels describe one service.
    """
    per_service = Counter(d.service for d in deploys)
    if not per_service:
        return None, 0
    return round(median([n / days for n in per_service.values()]), 3), len(per_service)


def dora_levels(metric: str, value: float | None) -> list[str] | None:
    """The 2024 DORA levels whose range contains `value` (minutes, or deploys per day)."""
    if value is None:
        return None
    return [level for level, (low, high) in DORA_2024[metric].items() if low <= value < high]


def failed_deploys(deploys: Iterable[Deploy], incidents: Iterable[Incident]) -> int:
    """Deploys linked to at least one incident; a deploy that caused two incidents counts once."""
    ids = {d.id for d in deploys}
    return len({i.caused_by_deploy_id for i in incidents if i.caused_by_deploy_id in ids})


def change_failure_rate(deploys: Sequence[Deploy], incidents: Iterable[Incident]) -> float | None:
    """Share of deploys in the window linked to an incident. None with no deploys."""
    if not deploys:
        return None
    return round(failed_deploys(deploys, incidents) / len({d.id for d in deploys}), 4)


def is_off_hours(ts: datetime) -> bool:
    """Weekend, or outside 09:00 to 18:00 in the timestamp's own timezone."""
    return is_off_hours_slot(ts.weekday(), ts.hour)


def is_off_hours_slot(weekday: int, hour: int) -> bool:
    return weekday >= 5 or not 9 <= hour < 18


def pages_by_hour(pages: Iterable[Page]) -> dict[tuple[int, int], int]:
    """Pages per (weekday, hour), 0 = Monday, in each page's own offset like is_off_hours. All 168 cells."""
    counts = Counter((p.fired_at.weekday(), p.fired_at.hour) for p in pages)
    return {(day, hour): counts.get((day, hour), 0) for day in range(7) for hour in range(24)}


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


def week_starts(start: date, end: date) -> list[tuple[date, bool]]:
    """(Monday, partial) for each ISO week overlapping [start, end). Edge weeks that the window cuts are partial."""
    week, out = start - timedelta(days=start.weekday()), []
    while week < end:
        out.append((week, week < start or week + timedelta(days=7) > end))
        week += timedelta(days=7)
    return out


def utc_week(ts: datetime) -> date:
    """Monday of the UTC week. Weeks are UTC, like the window bounds."""
    d = ts.astimezone(UTC).date()
    return d - timedelta(days=d.weekday())


def weekly_counts(timestamps: Iterable[datetime], start: date, end: date) -> list[WeeklyCount]:
    """Counts per ISO week (Monday start) across [start, end). Partial weeks understate: compare complete weeks."""
    counts = Counter(utc_week(ts) for ts in timestamps if start <= ts.astimezone(UTC).date() < end)
    return [WeeklyCount(week, counts.get(week, 0), partial) for week, partial in week_starts(start, end)]


@dataclass(frozen=True)
class SloResult:
    attainment: float | None  # good / total over the window
    budget_remaining: float | None  # share of the window's error budget left; negative when overspent
    burn_rate_1d: float | None
    burn_rate_3d: float | None
    status: str | None  # OK, BURNING, or EXHAUSTED
    daily: list[tuple[date, float]]  # budget remaining after each day


def slo_result(slo: Slo, days: Sequence[SliDaily], end: date) -> SloResult:
    """Error budget over the SLO's window [end - window_days, end), from daily good and total counts.

    Burn rate = (bad / total) / (1 - objective): 1 spends the budget exactly over the window.
    BURNING when the 3-day rate is >= 1, adapted from the ticket alert in Google's SRE Workbook
    ("Alerting on SLOs"); with daily data its 6-hour short window can't be applied.
    """
    days = sorted((d for d in days if end - timedelta(days=slo.window_days) <= d.day < end), key=lambda d: d.day)
    allowed = 1 - slo.objective
    total = sum(d.total for d in days)
    if not total:
        return SloResult(None, None, None, None, None, [])
    budget, bad, daily = allowed * total, 0, []
    for d in days:
        bad += d.total - d.good
        daily.append((d.day, round(1 - bad / budget, 4)))

    def burn_rate(last_days: int) -> float | None:
        recent = [d for d in days if d.day >= end - timedelta(days=last_days)]
        recent_total = sum(d.total for d in recent)
        return round(sum(d.total - d.good for d in recent) / recent_total / allowed, 2) if recent_total else None

    remaining, burn_3d = daily[-1][1], burn_rate(3)
    status = "EXHAUSTED" if remaining <= 0 else "BURNING" if burn_3d is not None and burn_3d >= 1 else "OK"
    return SloResult(round((total - bad) / total, 5), remaining, burn_rate(1), burn_3d, status, daily)


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current - previous) / previous * 100, 1)
