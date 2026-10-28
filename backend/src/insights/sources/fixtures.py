"""A JSON-file data source for local development, demos, and tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from insights.models import Deploy, Incident, Org, Page, Severity, SupportRequest

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "sample.json"


def _dt(value: str | None) -> datetime | None:
    """ISO-8601, or "@now" (sample data that should always look freshly synced)."""
    if not value:
        return None
    return datetime.now(UTC) if value == "@now" else datetime.fromisoformat(value)


def _in(ts: datetime, start: datetime, end: datetime) -> bool:
    return start <= ts < end


class FixtureSource:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        raw = json.loads(Path(path).read_text())
        self._orgs = [Org(**o) for o in raw["orgs"]]
        self._incidents = [
            Incident(
                id=i["id"],
                org_id=i["org_id"],
                severity=Severity(i["severity"]),
                started_at=_dt(i["started_at"]),
                detected_at=_dt(i.get("detected_at")),
                resolved_at=_dt(i.get("resolved_at")),
                caused_by_deploy_id=i.get("caused_by_deploy_id"),
            )
            for i in raw["incidents"]
        ]
        self._deploys = [Deploy(**{**d, "deployed_at": _dt(d["deployed_at"])}) for d in raw["deploys"]]
        self._pages = [Page(**{**p, "fired_at": _dt(p["fired_at"])}) for p in raw["pages"]]
        self._support = [
            SupportRequest(
                id=s["id"],
                org_id=s["org_id"],
                channel=s["channel"],
                opened_at=_dt(s["opened_at"]),
                first_human_response_at=_dt(s.get("first_human_response_at")),
                closed_at=_dt(s.get("closed_at")),
            )
            for s in raw["support_requests"]
        ]
        self._coverage = {k: {s: _dt(t) for s, t in v.items()} for k, v in raw.get("coverage", {}).items()}

    def orgs(self) -> list[Org]:
        return list(self._orgs)

    def incidents(self, org_id, start, end):
        return [i for i in self._incidents if i.org_id == org_id and _in(i.started_at, start, end)]

    def deploys(self, org_id, start, end):
        return [d for d in self._deploys if d.org_id == org_id and _in(d.deployed_at, start, end)]

    def pages(self, org_id, start, end):
        return [p for p in self._pages if p.org_id == org_id and _in(p.fired_at, start, end)]

    def support_requests(self, org_id, start, end):
        return [s for s in self._support if s.org_id == org_id and _in(s.opened_at, start, end)]

    def coverage(self, org_id):
        return dict(self._coverage.get(org_id, {}))
