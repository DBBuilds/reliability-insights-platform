"""Normalized records. Every data source maps its vendor payload into these.

Keep these vendor-neutral: a connector for PagerDuty, incident.io, Jira, or a
support tool translates into these shapes, and nothing above this layer knows
which vendor the data came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class Severity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


@dataclass(frozen=True)
class Incident:
    id: str
    org_id: str
    severity: Severity
    started_at: datetime  # impact start (best estimate; may be backdated after review)
    detected_at: datetime | None  # first alert or report; None if unknown
    resolved_at: datetime | None  # None while open
    caused_by_deploy_id: str | None = None
    service: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class Deploy:
    id: str
    org_id: str
    service: str
    deployed_at: datetime
    committed_at: datetime | None = None  # first commit in the change; for lead time


@dataclass(frozen=True)
class Page:
    id: str
    org_id: str
    alert_name: str
    fired_at: datetime
    actionable: bool | None  # None = responder did not say; never assume either way


@dataclass(frozen=True)
class SupportRequest:
    id: str
    org_id: str
    channel: str
    opened_at: datetime
    first_human_response_at: datetime | None
    closed_at: datetime | None


@dataclass(frozen=True)
class Org:
    id: str
    name: str
    parent_id: str | None = None


@dataclass(frozen=True)
class Slo:
    id: str
    org_id: str
    service: str
    objective: float  # target share of good events, for example 0.999
    window_days: int  # the error budget resets over this many days

    def __post_init__(self) -> None:
        if not 0 < self.objective < 1 or self.window_days < 1:
            raise ValueError(f"SLO {self.id}: objective must be in (0, 1) and window_days >= 1")


@dataclass(frozen=True)
class SliDaily:
    """Good and total events for one SLO on one UTC day."""

    slo_id: str
    day: date
    good: int
    total: int

    def __post_init__(self) -> None:
        if not 0 <= self.good <= self.total:
            raise ValueError(f"SLI {self.slo_id} on {self.day}: need 0 <= good <= total")
