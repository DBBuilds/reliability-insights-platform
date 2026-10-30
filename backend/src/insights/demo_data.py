"""Generate data/demo.json: 26 weeks of synthetic data that tell a story.  Run: make demo-data

Same seed, same bytes: tests/test_demo_data.py fails if the committed file drifts from
this generator, and asserts each story beat through the real service:

1. Checkout ships a risky release mid-quarter: change failure rate jumps, SEV2s cluster.
2. Payments cuts its median time to resolve steadily across the half year.
3. Search's on-call is paged at night far more than other teams.
4. One Platform alert dominates its pages and is rarely actionable.
5. Identity's login SLO burns most of its error budget early in the 30-day window.
6. Search's support sync stopped 12 days before the snapshot, so it shows stale.
7. A Platform incident is still open at the snapshot: counted, not dropped.

Timestamps carry each team's local offset, so off-hours means the responder's local time.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SEED = 2026
AS_OF = datetime(2026, 10, 26, 6, 0, tzinfo=UTC)  # snapshot time: Monday morning, after the nightly syncs
END = AS_OF.date()
START = END - timedelta(weeks=26)  # records cover [START, END)
RISKY_RELEASE = (date(2026, 9, 7), date(2026, 9, 28))  # Checkout, weeks 7 to 9 of the last quarter
SUPPORT_STOPPED = END - timedelta(days=12)  # Search's support sync
TARGET = Path(__file__).resolve().parents[2] / "data" / "demo.json"
STREAMS = ("incidents", "deploys", "pages", "support", "slis")


@dataclass(frozen=True)
class Team:
    id: str
    name: str
    zone: str
    services: tuple[str, ...]
    alerts: tuple[str, ...]
    deploys_per_day: float  # weekdays
    pages_per_day: float  # weekdays; weekends get 40%
    resolve_minutes: float  # typical time to resolve
    lead_hours: float  # typical commit-to-deploy time
    slo_objective: float  # for the first service


TEAMS = (
    Team(
        "payments", "Payments", "America/New_York", ("payments-api", "ledger", "payouts"),
        ("PaymentsLatencyHigh", "LedgerLag", "PayoutFailures"), 2.0, 2.0, 120, 20, 0.999,
    ),
    Team(
        "checkout", "Checkout", "America/Chicago", ("checkout-web", "cart", "pricing"),
        ("CheckoutErrors", "CartLatencyHigh", "PricingStale"), 3.0, 2.0, 90, 10, 0.999,
    ),
    Team(
        "search", "Search", "America/Los_Angeles", ("search-api", "indexer"),
        ("SearchLatencyHigh", "IndexLag", "QueryErrors"), 2.0, 2.0, 100, 30, 0.995,
    ),
    Team(
        "identity", "Identity", "Europe/London", ("auth", "sessions", "profiles"),
        ("LoginErrors", "TokenLatencyHigh", "SessionStoreFull"), 1.0, 1.5, 80, 48, 0.999,
    ),
    Team(
        "platform", "Platform", "Asia/Kolkata", ("edge-proxy", "k8s", "ci-runners", "observability"),
        ("NodeDiskPressure", "PodCrashLooping", "EdgeProxy5xx", "CIQueueBacklog"), 1.5, 2.0, 110, 72, 0.9995,
    ),
)  # fmt: skip

SEVERITY_WEIGHTS = {"SEV1": 2, "SEV2": 13, "SEV3": 50, "SEV4": 35}
RISKY_SEVERITY_WEIGHTS = {"SEV2": 70, "SEV3": 30}
SYMPTOMS = ("elevated error rate", "latency above target", "failed health checks", "partial outage")


def _poisson(rng: random.Random, mean: float) -> int:
    count, product, limit = 0, rng.random(), math.exp(-mean)
    while product > limit:
        count, product = count + 1, product * rng.random()
    return count


def _lognormal(rng: random.Random, median: float, spread: float = 0.6) -> float:
    return rng.lognormvariate(math.log(median), spread)


def _days() -> list[date]:
    return [START + timedelta(days=n) for n in range((END - START).days)]


def _local(team: Team, day: date, hour: float) -> datetime:
    """A local time on `day`, `hour` hours after local midnight (may roll into the next day)."""
    return datetime.combine(day, time.min, ZoneInfo(team.zone)) + timedelta(hours=hour)


def _iso(ts: datetime | None) -> str | None:
    return None if ts is None else ts.replace(second=0, microsecond=0).isoformat()


def _inside(ts: datetime) -> bool:
    return START <= ts.astimezone(UTC).date() < END


def _team_data(rng: random.Random, team: Team) -> dict[str, list[dict]]:
    deploys, incidents, pages, support, sli = [], [], [], [], []
    for day in _days():
        weekday = day.weekday() < 5
        risky = team.id == "checkout" and RISKY_RELEASE[0] <= day < RISKY_RELEASE[1]

        for _ in range(_poisson(rng, team.deploys_per_day) if weekday else 0):
            at = _local(team, day, rng.uniform(10, 17))
            deploy = {"id": "", "org_id": team.id, "service": rng.choice(team.services), "deployed_at": at}
            deploy["committed_at"] = at - timedelta(hours=_lognormal(rng, team.lead_hours))
            deploys.append(deploy)
            if rng.random() < (0.3 if risky else 0.04):
                incidents.append(_incident(rng, team, at + timedelta(hours=rng.uniform(0.2, 6)), deploy, risky))
        for _ in range(_poisson(rng, 0.08)):  # incidents not caused by a deploy, at any hour
            incidents.append(_incident(rng, team, _local(team, day, rng.uniform(0, 24)), None, False))

        for _ in range(_poisson(rng, team.pages_per_day * (1 if weekday else 0.4))):
            hour = rng.uniform(9, 18) if rng.random() < 0.8 else rng.uniform(0, 24)
            pages.append(_page(rng, team, _local(team, day, hour), rng.choice(team.alerts), 0.7))
        if team.id == "search":  # nightly reindex pages the rotation
            for _ in range(_poisson(rng, 2.5)):
                pages.append(_page(rng, team, _local(team, day, rng.uniform(0, 5)), "IndexLag", 0.6))
        if team.id == "platform":  # one alert fires all day and rarely needs action
            for _ in range(_poisson(rng, 4)):
                pages.append(_page(rng, team, _local(team, day, rng.uniform(0, 24)), "NodeDiskPressure", 0.1))

        stopped = team.id == "search" and day >= SUPPORT_STOPPED
        for _ in range(_poisson(rng, 1.5) if weekday and not stopped else 0):
            opened = _local(team, day, rng.uniform(9, 18))
            replied = opened + timedelta(minutes=_lognormal(rng, 25)) if rng.random() < 0.9 else None
            closed = opened + timedelta(hours=_lognormal(rng, 6)) if rng.random() < 0.85 else None
            support.append(
                {
                    "id": "",
                    "org_id": team.id,
                    "channel": f"#{team.id}-help",
                    "opened_at": opened,
                    "first_human_response_at": replied,
                    "closed_at": closed,
                }
            )

        sli.append(_sli_day(rng, team, day, risky))

    if team.id == "platform":
        still_open = _incident(rng, team, _local(team, END - timedelta(days=1), 21), None, False)
        incidents.append(still_open | {"resolved_at": None})

    records = {"deploys": deploys, "incidents": incidents, "pages": pages, "support_requests": support}
    for kind, rows in records.items():
        key = {"deploys": "deployed_at", "incidents": "started_at", "pages": "fired_at"}.get(kind, "opened_at")
        rows[:] = sorted((r for r in rows if _inside(r[key])), key=lambda r: r[key])
        for n, row in enumerate(rows):
            row["id"] = f"{team.id}-{kind[0]}{n}"
            for field, value in row.items():
                if isinstance(value, datetime):
                    row[field] = _iso(value if value <= AS_OF else None)  # not yet happened at the snapshot
    for incident in incidents:  # link by id, now that deploys have ids
        if incident["caused_by_deploy_id"]:
            incident["caused_by_deploy_id"] = incident["caused_by_deploy_id"]["id"]
    return records | {"sli_daily": sli}


def _incident(rng: random.Random, team: Team, start: datetime, deploy: dict | None, risky: bool) -> dict:
    weights = RISKY_SEVERITY_WEIGHTS if risky else SEVERITY_WEIGHTS
    resolve = team.resolve_minutes
    if team.id == "payments":  # steady improvement: from 300 minutes at START to 60 at END
        resolve = 300 - 240 * (start.astimezone(UTC).date() - START).days / (END - START).days
    service = deploy["service"] if deploy else rng.choice(team.services)
    return {
        "id": "",
        "org_id": team.id,
        "severity": rng.choices(list(weights), list(weights.values()))[0],
        "service": service,
        "title": f"{service}: {rng.choice(SYMPTOMS)}",
        "started_at": start,
        "detected_at": start + timedelta(minutes=_lognormal(rng, 8)) if rng.random() < 0.95 else None,
        "resolved_at": start + timedelta(minutes=_lognormal(rng, resolve, 0.7)),
        "caused_by_deploy_id": deploy,
    }


def _page(rng: random.Random, team: Team, at: datetime, alert: str, actionable_odds: float) -> dict:
    marked = rng.random() < 0.75
    return {
        "id": "",
        "org_id": team.id,
        "alert_name": alert,
        "fired_at": at,
        "actionable": (rng.random() < actionable_odds) if marked else None,
    }


def _sli_day(rng: random.Random, team: Team, day: date, risky: bool) -> dict:
    budget = 1 - team.slo_objective
    bad_share = budget * rng.uniform(0.2, 0.5)
    if risky:
        bad_share *= 1.5
    if team.id == "identity" and END - timedelta(days=30) <= day < END - timedelta(days=26):
        bad_share = budget * 4.5  # a 4-day login outage early in the 30-day window
    total = int(200_000 * (1 if day.weekday() < 5 else 0.6) * rng.uniform(0.9, 1.1))
    good = total - round(total * bad_share)
    return {"slo_id": f"{team.id}-{team.services[0]}", "day": day.isoformat(), "good": good, "total": total}


def generate() -> dict:
    rng = random.Random(SEED)
    data: dict = {
        "_comment": "Synthetic demo data from insights.demo_data; regenerate with `make demo-data`, never edit.",
        "as_of": _iso(AS_OF),
        "orgs": [{"id": "eng", "name": "Engineering", "parent_id": None}]
        + [{"id": t.id, "name": t.name, "parent_id": "eng"} for t in TEAMS],
        "slos": [
            {"id": f"{t.id}-{t.services[0]}", "org_id": t.id, "service": t.services[0], "objective": t.slo_objective}
            | {"window_days": 30}
            for t in TEAMS
        ],
        "coverage": {},
    }
    synced = _iso(AS_OF - timedelta(hours=2))
    for team in TEAMS:
        for kind, rows in _team_data(rng, team).items():
            data.setdefault(kind, []).extend(rows)
        data["coverage"][team.id] = dict.fromkeys(STREAMS, synced)
    data["coverage"]["search"]["support"] = _iso(datetime.combine(SUPPORT_STOPPED, time(3), UTC))
    return data


def render(data: dict | None = None) -> str:
    """JSON with one record per line: compact, and diffs stay readable."""
    data = generate() if data is None else data
    parts = []
    for key, value in data.items():
        if isinstance(value, list):
            rows = ",\n".join(json.dumps(row, sort_keys=True) for row in value)
            parts.append(f"{json.dumps(key)}: [\n{rows}\n]")
        else:
            parts.append(f"{json.dumps(key)}: {json.dumps(value, sort_keys=True)}")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def main() -> None:
    TARGET.write_text(render())
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
