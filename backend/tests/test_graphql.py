from fastapi.testclient import TestClient
from graphql import get_introspection_query

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


def test_healthz():
    assert client.get("/healthz").json() == {"ok": True}
