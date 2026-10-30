"""Assembles metrics for one org and window. The GraphQL layer only maps this to types."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from insights import insights as rules
from insights import metrics as m
from insights.models import Incident, Slo
from insights.sources.base import DataSource

STALE_AFTER = timedelta(hours=26)  # daily syncs get a 2-hour grace period
STREAMS = ("incidents", "deploys", "pages", "support")  # a stream with no sync record counts as stale
MAX_WINDOW = timedelta(days=366)  # bounds the work one request can ask for
EARLIEST, LATEST = date(2000, 1, 1), date(2100, 1, 1)


class UserInputError(ValueError):
    """A bad argument from the caller. Its message is shown to API clients; other errors are masked."""


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, time.min, UTC), datetime.combine(end, time.min, UTC)


def _by_week(items: Iterable, when: Callable[[object], datetime]) -> dict[date, list]:
    weeks: dict[date, list] = {}
    for item in items:
        weeks.setdefault(m.utc_week(when(item)), []).append(item)
    return weeks


@dataclass(frozen=True)
class Week:
    week_start: date
    partial: bool
    deploys: int
    change_failure_rate: float | None
    lead_time: m.DurationStat
    incidents: int
    ttd: m.DurationStat
    ttr: m.DurationStat
    pages: int
    off_hours_pages: int


@dataclass(frozen=True)
class OrgReport:
    org_id: str
    start: date
    end: date
    incidents_total: int
    incidents_open: int
    by_severity: dict
    ttd: m.DurationStat
    ttr: m.DurationStat
    incident_weeks: list[m.WeeklyCount]
    deploys_total: int
    change_failure_rate: float | None
    pages_total: int
    off_hours_pages: int
    actionable_share: float | None
    noisiest: list[tuple[str, int]]
    support_total: int
    first_response: m.DurationStat
    resolution_rate: float | None
    stale_streams: list[str]
    insights: list[rules.InsightItem]
    weekly: list[Week]
    incidents: list[Incident]  # newest first
    deploy_frequency: tuple[float | None, int]  # (deploys per day for the median service, services)
    lead_time: m.DurationStat
    recovery_time: m.DurationStat
    by_hour: dict[tuple[int, int], int]
    slos: list[tuple[Slo, m.SloResult]]
    syncs: dict[str, datetime | None]


class InsightsService:
    def __init__(self, source: DataSource, now: datetime | None = None) -> None:
        self.source = source
        self._now = now

    def now(self) -> datetime:
        return self._now or datetime.now(UTC)

    def scope(self, org_id: str) -> list[str]:
        """The org plus every descendant. A parent's numbers roll up its children."""
        children: dict[str | None, list[str]] = {}
        for o in self.source.orgs():
            children.setdefault(o.parent_id, []).append(o.id)
        out, todo = [], [org_id]
        while todo:
            current = todo.pop()
            if current not in out:  # guards against a cycle in bad org data
                out.append(current)
                todo.extend(children.get(current, []))
        return out

    def _collect(self, fetch, orgs: list[str], lo: datetime, hi: datetime) -> list:
        # Dedupe by record id: an item tagged with several orgs in the subtree counts once.
        seen: dict[str, object] = {}
        for org in orgs:
            for item in fetch(org, lo, hi):
                seen.setdefault(item.id, item)
        return list(seen.values())

    def children(self, org_id: str) -> list[str]:
        return [o.id for o in self.source.orgs() if o.parent_id == org_id]

    def syncs(self, orgs: list[str]) -> dict[str, datetime | None]:
        """Oldest last sync per stream across orgs in scope; None if one of them never synced it.

        Orgs with no coverage at all (such as a parent that holds no records itself) are
        skipped, unless no org in scope has any. Streams beyond STREAMS count only where reported.
        """
        coverage = [c for c in (self.source.coverage(o) for o in orgs) if c] or [{}]
        extra = sorted({s for c in coverage for s in c} - set(STREAMS))
        out = {}
        for stream in (*STREAMS, *extra):
            times = [c.get(stream) for c in coverage if stream in STREAMS or stream in c]
            out[stream] = None if None in times else min(times)
        return out

    def report(self, org_id: str, start: date, end: date) -> OrgReport:
        if end <= start:
            raise UserInputError("end must be after start")
        if end - start > MAX_WINDOW:
            raise UserInputError(f"window must be at most {MAX_WINDOW.days} days")
        if start < EARLIEST or end > LATEST:
            raise UserInputError(f"dates must be between {EARLIEST} and {LATEST}")
        lo, hi = _bounds(start, end)
        span = hi - lo
        orgs = self.scope(org_id)
        incidents = self._collect(self.source.incidents, orgs, lo, hi)
        previous = self._collect(self.source.incidents, orgs, lo - span, lo)
        deploys = self._collect(self.source.deploys, orgs, lo, hi)
        previous_deploys = self._collect(self.source.deploys, orgs, lo - span, lo)
        pages = self._collect(self.source.pages, orgs, lo, hi)
        support = self._collect(self.source.support_requests, orgs, lo, hi)
        slos = {s.id: s for org in orgs for s in self.source.slos(org)}  # deduped like records
        slo_results = [
            (s, m.slo_result(s, self.source.sli_daily(s.id, end - timedelta(days=s.window_days), end), end))
            for s in sorted(slos.values(), key=lambda s: s.id)
        ]

        ttr = m.time_to_resolve(incidents)
        cfr = m.change_failure_rate(deploys, incidents)
        noisiest = m.noisiest_alerts(pages)
        share = m.actionable_share(pages)
        off_hours = [p for p in pages if m.is_off_hours(p.fired_at)]
        by_hour = m.pages_by_hour(pages)
        syncs = self.syncs(orgs)
        now = self.now()
        stale = [s for s, t in syncs.items() if t is None or now - t > STALE_AFTER]
        found = [
            rules.stale_sources(stale),
            rules.mttr_trend(ttr, m.time_to_resolve(previous)),
            rules.cfr_spike(
                m.failed_deploys(deploys, incidents),
                len(deploys),
                m.failed_deploys(previous_deploys, previous),
                len(previous_deploys),
            ),
            rules.noisy_alert(noisiest, len(pages), share),
            rules.off_hours_pages(len(off_hours), len(pages), by_hour),
            *(rules.error_budget(s.id, s.service, r.budget_remaining) for s, r in slo_results),
        ]
        weekly_deploys = _by_week(deploys, lambda d: d.deployed_at)
        weekly_incidents = _by_week(incidents, lambda i: i.started_at)
        weekly_pages = _by_week(pages, lambda p: p.fired_at)
        weekly_off_hours = _by_week(off_hours, lambda p: p.fired_at)
        weeks = []
        for week, partial in m.week_starts(start, end):
            wd, wi, wp = (g.get(week, []) for g in (weekly_deploys, weekly_incidents, weekly_pages))
            weeks.append(
                Week(
                    week_start=week,
                    partial=partial,
                    deploys=len(wd),
                    change_failure_rate=m.change_failure_rate(wd, incidents),
                    lead_time=m.lead_time(wd),
                    incidents=len(wi),
                    ttd=m.time_to_detect(wi),
                    ttr=m.time_to_resolve(wi),
                    pages=len(wp),
                    off_hours_pages=len(weekly_off_hours.get(week, [])),
                )
            )
        return OrgReport(
            org_id=org_id,
            start=start,
            end=end,
            incidents_total=len(incidents),
            incidents_open=m.open_count(incidents),
            by_severity=m.by_severity(incidents),
            ttd=m.time_to_detect(incidents),
            ttr=ttr,
            incident_weeks=m.weekly_counts((i.started_at for i in incidents), start, end),
            deploys_total=len(deploys),
            change_failure_rate=cfr,
            pages_total=len(pages),
            off_hours_pages=len(off_hours),
            actionable_share=share,
            noisiest=noisiest,
            support_total=len(support),
            first_response=m.first_response(support),
            resolution_rate=m.resolution_rate(support),
            stale_streams=stale,
            insights=[i for i in found if i is not None],
            weekly=weeks,
            incidents=sorted(incidents, key=lambda i: i.started_at, reverse=True),
            deploy_frequency=m.deploy_frequency(deploys, (end - start).days),
            lead_time=m.lead_time(deploys),
            recovery_time=m.recovery_time(incidents),
            by_hour=by_hour,
            slos=slo_results,
            syncs=syncs,
        )
