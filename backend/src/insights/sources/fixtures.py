"""A JSON-file data source for local development, demos, and tests."""

from __future__ import annotations

import json
from bisect import bisect_left
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from insights.models import Deploy, Incident, Org, Page, Severity, SliDaily, Slo, SupportRequest

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "sample.json"


def _dt(value: str | None) -> datetime | None:
    """ISO-8601 with a UTC offset, or "@now" (sample data that should always look freshly synced)."""
    if not value:
        return None
    if value == "@now":
        return datetime.now(UTC)
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None:
        raise ValueError(f"timestamp {value!r} has no UTC offset")
    return ts


class _ByOrg:
    """Records per org, sorted by time, so a window is two binary searches instead of a scan.

    A window comes back in file order, as a scan would return it (ties in counts keep their order).
    """

    def __init__(self, records: list, when: Callable) -> None:
        self._rows: dict[str, list] = {}
        for n, r in enumerate(records):
            self._rows.setdefault(r.org_id, []).append((when(r), n, r))
        for rows in self._rows.values():
            rows.sort(key=lambda row: (row[0], row[1]))

    def window(self, org_id: str, start: datetime, end: datetime) -> list:
        rows = self._rows.get(org_id, [])
        lo, hi = (bisect_left(rows, t, key=lambda row: row[0]) for t in (start, end))
        return [r for _, _, r in sorted(rows[lo:hi], key=lambda row: row[1])]


class FixtureSource:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        raw = json.loads(Path(path).read_text())
        self.as_of = _dt(raw.get("as_of"))  # set for a fixed snapshot; read it at this time, not now
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
                service=i.get("service"),
                title=i.get("title"),
            )
            for i in raw["incidents"]
        ]
        self._deploys = [
            Deploy(**{**d, "deployed_at": _dt(d["deployed_at"]), "committed_at": _dt(d.get("committed_at"))})
            for d in raw["deploys"]
        ]
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
        self._by_org = {
            "incidents": _ByOrg(self._incidents, lambda i: i.started_at),
            "deploys": _ByOrg(self._deploys, lambda d: d.deployed_at),
            "pages": _ByOrg(self._pages, lambda p: p.fired_at),
            "support": _ByOrg(self._support, lambda s: s.opened_at),
        }
        self._slos = [Slo(**s) for s in raw.get("slos", [])]
        self._sli = [SliDaily(**{**d, "day": date.fromisoformat(d["day"])}) for d in raw.get("sli_daily", [])]
        self._coverage = {k: {s: _dt(t) for s, t in v.items()} for k, v in raw.get("coverage", {}).items()}

    def orgs(self) -> list[Org]:
        return list(self._orgs)

    def incidents(self, org_id, start, end):
        return self._by_org["incidents"].window(org_id, start, end)

    def deploys(self, org_id, start, end):
        return self._by_org["deploys"].window(org_id, start, end)

    def pages(self, org_id, start, end):
        return self._by_org["pages"].window(org_id, start, end)

    def support_requests(self, org_id, start, end):
        return self._by_org["support"].window(org_id, start, end)

    def slos(self, org_id):
        return [s for s in self._slos if s.org_id == org_id]

    def sli_daily(self, slo_id, start, end):
        return [d for d in self._sli if d.slo_id == slo_id and start <= d.day < end]

    def coverage(self, org_id):
        return dict(self._coverage.get(org_id, {}))
