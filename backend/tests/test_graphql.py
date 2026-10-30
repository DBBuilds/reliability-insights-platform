from datetime import datetime

from fastapi.testclient import TestClient
from graphql import get_introspection_query

from insights import demo_data as demo
from insights.app import build_service, create_app
from insights.service import InsightsService
from insights.sources.fixtures import FixtureSource

QUERY = """
query($org: ID!, $start: Date!, $end: Date!) {
  orgMetrics(orgId: $org, start: $start, end: $end) {
    orgId start end staleSources
    incidents { total open timeToResolve { sampleSize medianMinutes } weekly { weekStart count partial } }
    delivery { deploys changeFailureRate }
    onCall { pages offHoursPages actionableShare noisiestAlerts { alertName pages } }
    support { requests resolutionRate firstResponse { medianMinutes } }
    insights { id level title detail }
  }
}
"""

client = TestClient(create_app())


def run(org, start="2026-08-03", end="2026-10-12", api=client):
    r = api.post("/graphql", json={"query": QUERY, "variables": {"org": org, "start": start, "end": end}})
    assert r.status_code == 200
    return r.json()


def test_org_metrics_over_http():
    body = run("payments")
    assert "errors" not in body
    data = body["data"]["orgMetrics"]
    assert data["incidents"]["total"] == 14
    assert data["onCall"]["noisiestAlerts"][0]["alertName"] == "PaymentsLatencyHigh"


def test_unknown_org_is_null_not_an_error():
    assert run("nope") == {"data": {"orgMetrics": None}}


def test_bad_window_errors_without_nulling_other_fields():
    body = client.post(
        "/graphql",
        json={
            "query": '{ orgs { id } bad: orgMetrics(orgId: "payments", '
            'start: "2026-09-02", end: "2026-09-01") { orgId } }'
        },
    ).json()
    assert body["data"]["bad"] is None and len(body["data"]["orgs"]) == 3
    assert "end must be after start" in body["errors"][0]["message"]


def test_unexpected_errors_are_masked():
    class Broken(FixtureSource):
        def incidents(self, *args):
            raise RuntimeError("internal detail")

    body = run("payments", api=TestClient(create_app(InsightsService(Broken()))))
    assert body["data"]["orgMetrics"] is None
    assert body["errors"][0]["message"] == "Unexpected error."


def test_invalid_date_explains_itself():
    body = run("payments", start="2026-13-01")
    assert "month must be in 1..12" in body["errors"][0]["message"]


def test_too_many_aliases_are_rejected():
    # Each alias reruns the resolver, so aliases are how one request multiplies its cost.
    query = "{ " + " ".join(f"a{i}: orgs {{ id }}" for i in range(11)) + " }"
    body = client.post("/graphql", json={"query": query}).json()
    assert body["data"] is None and "aliases" in body["errors"][0]["message"]


def test_graphiql_introspection_is_within_the_limits():
    assert "errors" not in client.post("/graphql", json={"query": get_introspection_query(descriptions=True)}).json()


def test_snapshot_data_is_read_as_of_its_snapshot_time(monkeypatch, tmp_path):
    # Otherwise every sync in a fixed snapshot looks stale against the wall clock.
    data = tmp_path / "snapshot.json"
    data.write_text(
        '{"as_of": "2026-10-26T06:00:00+00:00", "orgs": [], "incidents": [], "deploys": [], "pages": [], '
        '"support_requests": []}'
    )
    monkeypatch.setenv("INSIGHTS_DATA", str(data))
    assert build_service().now().isoformat() == "2026-10-26T06:00:00+00:00"


demo_client = TestClient(create_app(InsightsService(FixtureSource(demo.TARGET), now=demo.AS_OF)))

DETAIL_QUERY = """
query($org: ID!, $limit: Int!) {
  orgMetrics(orgId: $org, start: "2026-07-27", end: "2026-10-26") {
    delivery { deployFrequency { value sampleSize levels2024 } leadTime { value levels2024 } recoveryTime { value } }
    weekly { weekStart partial deploys incidents pages offHoursPages timeToResolve { medianMinutes } }
    recentIncidents(limit: $limit) { id orgId severity service title startedAt resolvedAt }
    onCall { byHour { weekday hour pages } }
    slos { id status budgetRemaining burnRate3d daily { day budgetRemaining } }
    syncs { stream lastSyncedAt stale }
    children { orgId incidents { total } }
  }
}
"""


def detail(org, limit=2):
    return demo_client.post("/graphql", json={"query": DETAIL_QUERY, "variables": {"org": org, "limit": limit}}).json()


def test_trends_dora_slos_and_children_over_http():
    body = detail("eng")
    assert "errors" not in body
    m = body["data"]["orgMetrics"]
    assert len(m["weekly"]) == 13 and not any(w["partial"] for w in m["weekly"])
    assert len(m["onCall"]["byHour"]) == 168
    assert [c["orgId"] for c in m["children"]] == [t.id for t in demo.TEAMS]
    assert sum(c["incidents"]["total"] for c in m["children"]) == sum(w["incidents"] for w in m["weekly"])
    first, second = (datetime.fromisoformat(i["startedAt"]) for i in m["recentIncidents"])
    assert first >= second
    assert {s["stream"]: s["stale"] for s in m["syncs"]} == {
        "incidents": False,
        "deploys": False,
        "pages": False,
        "support": True,
        "slis": False,
    }
    lead = m["delivery"]["leadTime"]
    assert lead["value"] < 24 * 60 and lead["levels2024"] == ["ELITE"]  # median under a day
    assert [s["id"] for s in m["slos"]] == sorted(f"{t.id}-{t.services[0]}" for t in demo.TEAMS)


def test_each_report_is_computed_once_per_request():
    calls = []

    class Counting(InsightsService):
        def report(self, *args):
            calls.append(args[0])
            return super().report(*args)

    query = " ".join(
        f'{alias}: orgMetrics(orgId: "eng", start: "2026-09-07", end: "2026-10-05") {{ children {{ orgId }} }}'
        for alias in ("a", "b")
    )
    TestClient(create_app(Counting(FixtureSource()))).post("/graphql", json={"query": "{" + query + "}"})
    assert sorted(calls) == ["eng", "payments", "search"]


def test_recent_incidents_limit_is_bounded():
    for limit in (0, 101):
        assert "limit must be between 1 and 100" in detail("payments", limit)["errors"][0]["message"]


def test_healthz():
    assert client.get("/healthz").json() == {"ok": True}
