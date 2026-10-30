"""The data-source contract. Add a vendor by implementing this protocol."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from insights.models import Deploy, Incident, Org, Page, SliDaily, Slo, SupportRequest


class DataSource(Protocol):
    """Read-only access to normalized records for one org, in [start, end)."""

    def orgs(self) -> list[Org]: ...

    def incidents(self, org_id: str, start: datetime, end: datetime) -> list[Incident]: ...

    def deploys(self, org_id: str, start: datetime, end: datetime) -> list[Deploy]: ...

    def pages(self, org_id: str, start: datetime, end: datetime) -> list[Page]: ...

    def support_requests(self, org_id: str, start: datetime, end: datetime) -> list[SupportRequest]: ...

    def slos(self, org_id: str) -> list[Slo]: ...

    def sli_daily(self, slo_id: str, start: date, end: date) -> list[SliDaily]:
        """Daily SLI counts for days in [start, end)."""
        ...

    def coverage(self, org_id: str) -> dict[str, datetime | None]:
        """Last successful sync time per stream ('incidents', 'pages', ...), or None if never.

        The API reports staleness from this so a stopped sync shows as stale, not
        as a confident zero.
        """
        ...
