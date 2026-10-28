from fastapi.testclient import TestClient

from insights.app import create_app

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


def run(org, start="2026-08-03", end="2026-10-12"):
    r = client.post("/graphql", json={"query": QUERY, "variables": {"org": org, "start": start, "end": end}})
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


def test_healthz():
    assert client.get("/healthz").json() == {"ok": True}
