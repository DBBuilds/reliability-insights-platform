"""Assembles metrics for one org and window. The GraphQL layer only maps this to types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from insights import insights as rules
from insights import metrics as m
from insights.sources.base import DataSource

STALE_AFTER = timedelta(hours=26)  # daily syncs get a 2-hour grace period
STREAMS = ("incidents", "deploys", "pages", "support")  # a stream with no sync record counts as stale


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, time.min, UTC), datetime.combine(end, time.min, UTC)


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

    def stale_streams(self, orgs: list[str]) -> list[str]:
        synced: dict[str, list[datetime | None]] = {s: [] for s in STREAMS}
        for org in orgs:
            for stream, ts in self.source.coverage(org).items():
                synced.setdefault(stream, []).append(ts)
        now = self.now()
        return [
            stream
            for stream, times in synced.items()
            # Stale if never synced anywhere in scope, or if any org in scope is behind.
            if not times or any(t is None or now - t > STALE_AFTER for t in times)
        ]

    def report(self, org_id: str, start: date, end: date) -> OrgReport:
        if end <= start:
            raise ValueError("end must be after start")
        lo, hi = _bounds(start, end)
        span = hi - lo
        orgs = self.scope(org_id)
        incidents = self._collect(self.source.incidents, orgs, lo, hi)
        previous = self._collect(self.source.incidents, orgs, lo - span, lo)
        deploys = self._collect(self.source.deploys, orgs, lo, hi)
        pages = self._collect(self.source.pages, orgs, lo, hi)
        support = self._collect(self.source.support_requests, orgs, lo, hi)

        ttr = m.time_to_resolve(incidents)
        noisiest = m.noisiest_alerts(pages)
        share = m.actionable_share(pages)
        stale = self.stale_streams([o for o in orgs if self.source.coverage(o)] or orgs)
        found = [
            rules.stale_sources(stale),
            rules.mttr_trend(ttr, m.time_to_resolve(previous)),
            rules.noisy_alert(noisiest, share),
        ]
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
            change_failure_rate=m.change_failure_rate(deploys, incidents),
            pages_total=len(pages),
            off_hours_pages=sum(1 for p in pages if m.is_off_hours(p.fired_at)),
            actionable_share=share,
            noisiest=noisiest,
            support_total=len(support),
            first_response=m.first_response(support),
            resolution_rate=m.resolution_rate(support),
            stale_streams=stale,
            insights=[i for i in found if i is not None],
        )
