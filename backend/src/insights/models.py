"""Normalized records. Every data source maps its vendor payload into these.

Keep these vendor-neutral: a connector for PagerDuty, incident.io, Jira, or a
support tool translates into these shapes, and nothing above this layer knows
which vendor the data came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class Deploy:
    id: str
    org_id: str
    service: str
    deployed_at: datetime


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
