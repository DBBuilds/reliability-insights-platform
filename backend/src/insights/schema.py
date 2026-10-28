"""GraphQL schema. THE CONTRACT between backend and frontend.

Rules (enforced by tests/test_schema_contract.py against ../schema/schema.graphql):
- New fields are nullable. A non-null field that errors or is missing nulls its
  whole parent, up to the entire query, for every client.
- Never remove or rename a field a deployed client selects; deprecate first.
- A frontend query that selects a new field merges only after the backend that
  serves it is deployed to production.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

import strawberry
from strawberry.types import Info

from insights import metrics as m
from insights.insights import InsightLevel as _Level
from insights.service import InsightsService, OrgReport

InsightLevel = strawberry.enum(_Level, description="How urgent an insight is.")


@strawberry.enum
class SeverityLevel(Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


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
    weekly: list[WeeklyCount]


@strawberry.type
class DeliveryMetrics:
    deploys: int
    change_failure_rate: float | None = strawberry.field(description="0..1, null with no deploys.")


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

    @staticmethod
    def of(r: OrgReport) -> OrgMetrics:
        return OrgMetrics(
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
            delivery=DeliveryMetrics(deploys=r.deploys_total, change_failure_rate=r.change_failure_rate),
            on_call=OnCallMetrics(
                pages=r.pages_total,
                off_hours_pages=r.off_hours_pages,
                actionable_share=r.actionable_share,
                noisiest_alerts=[AlertCount(alert_name=n, pages=c) for n, c in r.noisiest],
            ),
            support=SupportMetrics(
                requests=r.support_total,
                first_response=DurationStat.of(r.first_response),
                resolution_rate=r.resolution_rate,
            ),
            insights=[
                Insight(id=strawberry.ID(i.id), level=i.level, title=i.title, detail=i.detail) for i in r.insights
            ],
        )


def _service(info: Info) -> InsightsService:
    return info.context["service"]


@strawberry.type
class Query:
    @strawberry.field(description="Orgs the caller can see.")
    def orgs(self, info: Info) -> list[Org]:
        return [Org(id=strawberry.ID(o.id), name=o.name, parent_id=o.parent_id) for o in _service(info).source.orgs()]

    @strawberry.field(description="Metrics for one org over a fixed window [start, end). Null if the org is unknown.")
    def org_metrics(self, info: Info, org_id: strawberry.ID, start: date, end: date) -> OrgMetrics | None:
        service = _service(info)
        if org_id not in {o.id for o in service.source.orgs()}:
            return None
        return OrgMetrics.of(service.report(str(org_id), start, end))


schema = strawberry.Schema(query=Query)
