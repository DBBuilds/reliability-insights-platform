"""GraphQL schema. THE CONTRACT between backend and frontend.

Rules (enforced by tests/test_schema_contract.py against ../schema/schema.graphql):
- New fields are nullable. A non-null field that errors or is missing nulls its
  whole parent, up to the entire query, for every client.
- Never remove or rename a field a deployed client selects; deprecate first.
- A frontend query that selects a new field merges only after the backend that
  serves it is deployed to production.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

import strawberry
from graphql import GraphQLError
from strawberry.extensions import MaskErrors, MaxAliasesLimiter
from strawberry.types import Info

from insights import metrics as m
from insights.insights import InsightLevel as _Level
from insights.models import Incident, Slo
from insights.service import MAX_WINDOW, InsightsService, OrgReport, UserInputError, Week

InsightLevel = strawberry.enum(_Level, description="How urgent an insight is.")


@strawberry.enum
class SeverityLevel(Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


@strawberry.enum(description="Software delivery performance levels from the 2024 DORA report.")
class DoraLevel(Enum):
    ELITE = "ELITE"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@strawberry.enum(description="EXHAUSTED: no budget left. BURNING: 3-day burn rate >= 1. Else OK.")
class SloStatus(Enum):
    OK = "OK"
    BURNING = "BURNING"
    EXHAUSTED = "EXHAUSTED"


@strawberry.type
class Org:
    id: strawberry.ID
    name: str
    parent_id: strawberry.ID | None


@strawberry.type(description="Minutes. Null statistics mean too few samples; see sampleSize.")
class DurationStat:
    sample_size: int
    median_minutes: float | None
    p90_minutes: float | None

    @staticmethod
    def of(s: m.DurationStat) -> DurationStat:
        return DurationStat(sample_size=s.sample_size, median_minutes=s.median_minutes, p90_minutes=s.p90_minutes)


@strawberry.type(description="A value, its sample size, and the 2024 DORA levels whose published range contains it.")
class DoraMetric:
    value: float | None = strawberry.field(description="Null with too few samples.")
    sample_size: int | None
    levels_2024: list[DoraLevel] | None = strawberry.field(
        description="Empty when the value falls between published ranges. The levels are survey clusters, not targets."
    )

    @staticmethod
    def of(value: float | None, sample_size: int, metric: str) -> DoraMetric:
        levels = m.dora_levels(metric, value)
        return DoraMetric(
            value=value,
            sample_size=sample_size,
            levels_2024=None if levels is None else [DoraLevel(level) for level in levels],
        )


@strawberry.type(description="One UTC ISO week. Partial weeks understate; compare complete weeks.")
class WeeklyPoint:
    week_start: date | None
    partial: bool | None
    deploys: int | None
    change_failure_rate: float | None
    lead_time: DurationStat | None
    incidents: int | None
    time_to_detect: DurationStat | None
    time_to_resolve: DurationStat | None
    pages: int | None
    off_hours_pages: int | None

    @staticmethod
    def of(w: Week) -> WeeklyPoint:
        return WeeklyPoint(
            week_start=w.week_start,
            partial=w.partial,
            deploys=w.deploys,
            change_failure_rate=w.change_failure_rate,
            lead_time=DurationStat.of(w.lead_time),
            incidents=w.incidents,
            time_to_detect=DurationStat.of(w.ttd),
            time_to_resolve=DurationStat.of(w.ttr),
            pages=w.pages,
            off_hours_pages=w.off_hours_pages,
        )


@strawberry.type
class IncidentItem:
    id: strawberry.ID | None
    org_id: strawberry.ID | None
    severity: SeverityLevel | None
    service: str | None
    title: str | None
    started_at: datetime | None
    detected_at: datetime | None
    resolved_at: datetime | None = strawberry.field(description="Null while open.")

    @staticmethod
    def of(i: Incident) -> IncidentItem:
        return IncidentItem(
            id=strawberry.ID(i.id),
            org_id=strawberry.ID(i.org_id),
            severity=SeverityLevel(i.severity.value),
            service=i.service,
            title=i.title,
            started_at=i.started_at,
            detected_at=i.detected_at,
            resolved_at=i.resolved_at,
        )


@strawberry.type(description="Pages in one weekday (0 = Monday) and hour, in each page's own time zone.")
class PageHourCount:
    weekday: int | None
    hour: int | None
    pages: int | None


@strawberry.type
class SloDay:
    day: date | None
    budget_remaining: float | None = strawberry.field(description="Share of the window's budget left after this day.")


@strawberry.type(description="An SLO over its own window, which ends at the query's end date.")
class SloMetrics:
    id: strawberry.ID | None
    service: str | None
    objective: float | None
    window_days: int | None
    attainment: float | None = strawberry.field(description="Good events / all events.")
    budget_remaining: float | None = strawberry.field(
        description="Share of the error budget left; negative when overspent."
    )
    burn_rate_1d: float | None = strawberry.field(description="1 spends the budget exactly over the window.")
    burn_rate_3d: float | None
    status: SloStatus | None
    daily: list[SloDay] | None

    @staticmethod
    def of(slo: Slo, r: m.SloResult) -> SloMetrics:
        return SloMetrics(
            id=strawberry.ID(slo.id),
            service=slo.service,
            objective=slo.objective,
            window_days=slo.window_days,
            attainment=r.attainment,
            budget_remaining=r.budget_remaining,
            burn_rate_1d=r.burn_rate_1d,
            burn_rate_3d=r.burn_rate_3d,
            status=SloStatus(r.status) if r.status else None,
            daily=[SloDay(day=d, budget_remaining=left) for d, left in r.daily],
        )


@strawberry.type
class StreamSync:
    stream: str | None
    last_synced_at: datetime | None = strawberry.field(
        description="Oldest across orgs in scope; null if one never synced."
    )
    stale: bool | None


@strawberry.type(description="Count for an ISO week starting Monday. Partial weeks understate; compare complete weeks.")
class WeeklyCount:
    week_start: date
    count: int
    partial: bool


@strawberry.type
class SeverityCount:
    severity: SeverityLevel
    count: int


@strawberry.type
class IncidentMetrics:
    total: int
    open: int
    by_severity: list[SeverityCount]
    time_to_detect: DurationStat | None
    time_to_resolve: DurationStat | None
    weekly: list[WeeklyCount] = strawberry.field(deprecation_reason="Use OrgMetrics.weekly.")


@strawberry.type
class DeliveryMetrics:
    deploys: int
    change_failure_rate: float | None = strawberry.field(description="0..1, null with no deploys.")
    deploy_frequency: DoraMetric | None = strawberry.field(
        description="Deploys per day for the median service, among services that deployed in the window."
    )
    lead_time: DoraMetric | None = strawberry.field(description="Minutes from commit to deploy, median.")
    recovery_time: DoraMetric | None = strawberry.field(
        description="Failed deployment recovery time: minutes from start to resolve of deploy-caused incidents, median."
    )


@strawberry.type
class AlertCount:
    alert_name: str
    pages: int


@strawberry.type
class OnCallMetrics:
    pages: int
    off_hours_pages: int
    actionable_share: float | None = strawberry.field(description="0..1 among pages a responder marked.")
    noisiest_alerts: list[AlertCount]
    by_hour: list[PageHourCount] | None


@strawberry.type
class SupportMetrics:
    requests: int
    first_response: DurationStat | None = strawberry.field(description="To the first human reply. Bots excluded.")
    resolution_rate: float | None = strawberry.field(description="0..1. Depends on threads being closed consistently.")


@strawberry.type
class Insight:
    id: strawberry.ID
    level: InsightLevel
    title: str
    detail: str | None


@strawberry.type
class OrgMetrics:
    org_id: strawberry.ID
    start: date
    end: date
    stale_sources: list[str] = strawberry.field(
        description="Streams with no recent successful sync. Treat their numbers as suspect."
    )
    incidents: IncidentMetrics | None
    delivery: DeliveryMetrics | None
    on_call: OnCallMetrics | None
    support: SupportMetrics | None
    insights: list[Insight]
    weekly: list[WeeklyPoint] | None
    slos: list[SloMetrics] | None
    syncs: list[StreamSync] | None
    report: strawberry.Private[OrgReport]

    @strawberry.field(description="Newest first; limit 1 to 100.")
    def recent_incidents(self, limit: int = 20) -> list[IncidentItem] | None:
        if not 1 <= limit <= 100:
            raise UserInputError("limit must be between 1 and 100")
        return [IncidentItem.of(i) for i in self.report.incidents[:limit]]

    @strawberry.field(description="Direct child orgs over the same window. Computed only when selected.")
    def children(self, info: Info) -> list[OrgMetrics] | None:
        return [OrgMetrics.of(_report(info, c, self.start, self.end)) for c in _service(info).children(self.org_id)]

    @staticmethod
    def of(r: OrgReport) -> OrgMetrics:
        return OrgMetrics(
            report=r,
            org_id=strawberry.ID(r.org_id),
            start=r.start,
            end=r.end,
            stale_sources=r.stale_streams,
            incidents=IncidentMetrics(
                total=r.incidents_total,
                open=r.incidents_open,
                by_severity=[SeverityCount(severity=SeverityLevel(s.value), count=c) for s, c in r.by_severity.items()],
                time_to_detect=DurationStat.of(r.ttd),
                time_to_resolve=DurationStat.of(r.ttr),
                weekly=[
                    WeeklyCount(week_start=w.week_start, count=w.count, partial=w.partial) for w in r.incident_weeks
                ],
            ),
            delivery=DeliveryMetrics(
                deploys=r.deploys_total,
                change_failure_rate=r.change_failure_rate,
                deploy_frequency=DoraMetric.of(*r.deploy_frequency, "deploy_frequency"),
                lead_time=DoraMetric.of(r.lead_time.median_minutes, r.lead_time.sample_size, "lead_time"),
                recovery_time=DoraMetric.of(
                    r.recovery_time.median_minutes, r.recovery_time.sample_size, "recovery_time"
                ),
            ),
            on_call=OnCallMetrics(
                pages=r.pages_total,
                off_hours_pages=r.off_hours_pages,
                actionable_share=r.actionable_share,
                noisiest_alerts=[AlertCount(alert_name=n, pages=c) for n, c in r.noisiest],
                by_hour=[PageHourCount(weekday=d, hour=h, pages=n) for (d, h), n in r.by_hour.items()],
            ),
            support=SupportMetrics(
                requests=r.support_total,
                first_response=DurationStat.of(r.first_response),
                resolution_rate=r.resolution_rate,
            ),
            insights=[
                Insight(id=strawberry.ID(i.id), level=i.level, title=i.title, detail=i.detail) for i in r.insights
            ],
            weekly=[WeeklyPoint.of(w) for w in r.weekly],
            slos=[SloMetrics.of(slo, result) for slo, result in r.slos],
            syncs=[StreamSync(stream=s, last_synced_at=t, stale=s in r.stale_streams) for s, t in r.syncs.items()],
        )


def _service(info: Info) -> InsightsService:
    return info.context["service"]


def _report(info: Info, org_id: str, start: date, end: date) -> OrgReport:
    """One report per org and window per request, however many aliases or parents select it."""
    reports = info.context.setdefault("reports", {})
    if (org_id, start, end) not in reports:
        reports[org_id, start, end] = _service(info).report(org_id, start, end)
    return reports[org_id, start, end]


@strawberry.type
class Query:
    @strawberry.field(description="Orgs the caller can see.")
    def orgs(self, info: Info) -> list[Org]:
        return [Org(id=strawberry.ID(o.id), name=o.name, parent_id=o.parent_id) for o in _service(info).source.orgs()]

    @strawberry.field(
        description=f"Metrics for one org over a fixed window [start, end) of at most {MAX_WINDOW.days} days. "
        "Null if the org is unknown."
    )
    def org_metrics(self, info: Info, org_id: strawberry.ID, start: date, end: date) -> OrgMetrics | None:
        service = _service(info)
        if org_id not in {o.id for o in service.source.orgs()}:
            return None
        return OrgMetrics.of(_report(info, str(org_id), start, end))


def _is_unexpected(error: GraphQLError) -> bool:
    """Server-side failures get a generic message. Syntax, validation, and bad input keep theirs."""
    original = error.original_error
    return original is not None and not isinstance(original, GraphQLError | UserInputError)


schema = strawberry.Schema(
    query=Query,
    # A fresh instance per request. The alias cap stops one request from rerunning a resolver many times.
    extensions=[
        lambda: MaxAliasesLimiter(max_alias_count=10),
        lambda: MaskErrors(should_mask_error=_is_unexpected),
    ],
)
