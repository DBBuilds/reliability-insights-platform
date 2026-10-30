"""The demo snapshot: reproducible, and each story beat shows through the real service.

Thresholds leave a margin around the generated values, so a small generator change
doesn't break them but a lost story beat does.
"""

import json
from datetime import UTC, datetime, time, timedelta

import pytest

from insights import demo_data as demo
from insights.service import InsightsService
from insights.sources.fixtures import FixtureSource

QUARTER = (demo.END - timedelta(weeks=13), demo.END)
TEAMS = [t.id for t in demo.TEAMS]


@pytest.fixture(scope="module")
def source():
    return FixtureSource(demo.TARGET)


@pytest.fixture(scope="module")
def service(source):
    return InsightsService(source, now=source.as_of)


def test_committed_file_matches_the_generator():
    assert demo.TARGET.read_text() == demo.render(), "run `make demo-data` and commit backend/data/demo.json"


def test_shape(source):
    assert source.as_of == demo.AS_OF
    assert [o.id for o in source.orgs()] == ["eng", "payments", "checkout", "search", "identity", "platform"]
    raw = json.loads(demo.TARGET.read_text())
    lo, hi = (datetime.combine(d, time.min, UTC) for d in (demo.START, demo.END))
    for stream, field in [
        ("incidents", "started_at"),
        ("deploys", "deployed_at"),
        ("pages", "fired_at"),
        ("support_requests", "opened_at"),
    ]:
        assert all(lo <= datetime.fromisoformat(r[field]) < hi for r in raw[stream]), stream


def test_checkout_risky_release_raises_failures_and_sev2s(service):
    start, end = demo.RISKY_RELEASE
    risky = service.report("checkout", start, end)
    before = service.report("checkout", start - (end - start), start)
    assert risky.change_failure_rate >= 0.2 and risky.change_failure_rate >= 2.5 * before.change_failure_rate
    assert risky.by_severity["SEV2"] >= 3 * max(1, before.by_severity["SEV2"])


def test_payments_cuts_time_to_resolve(service):
    r = service.report("payments", *QUARTER)
    trend = next(i for i in r.insights if i.id == "mttr-trend")
    assert "down" in trend.title


def test_search_on_call_is_paged_off_hours_most(service):
    share = {t: (r := service.report(t, *QUARTER)).off_hours_pages / r.pages_total for t in TEAMS}
    assert share["search"] >= 0.65 and share["search"] == max(share.values())


def test_platform_has_one_noisy_alert_that_is_rarely_actionable(service):
    r = service.report("platform", *QUARTER)
    name, pages = r.noisiest[0]
    assert name == "NodeDiskPressure" and pages >= 0.5 * r.pages_total
    share = {t: service.report(t, *QUARTER).actionable_share for t in TEAMS}
    assert share["platform"] <= 0.35 and share["platform"] == min(share.values())


def test_identity_burns_its_error_budget_early_in_the_window(service):
    def slo(org):
        [(_, result)] = service.report(org, *QUARTER).slos
        return result

    spent = 1 - slo("identity").budget_remaining
    assert 0.6 <= spent < 1 and 1 - slo("identity").daily[6][1] >= 0.5 * spent  # most of it in the first week
    assert all(1 - slo(t).budget_remaining < 0.6 for t in TEAMS if t != "identity")


def test_the_quarter_view_tells_the_story_and_nothing_else(service):
    expected = {
        "eng": ["stale-data", "off-hours-pages", "error-budget:identity-auth"],
        "payments": ["mttr-trend"],
        "checkout": ["mttr-trend", "cfr-spike"],
        "search": ["stale-data", "noisy-alert", "off-hours-pages"],
        "identity": ["error-budget:identity-auth"],
        "platform": ["noisy-alert", "off-hours-pages"],
    }
    assert {org: [i.id for i in service.report(org, *QUARTER).insights] for org in expected} == expected


def test_search_support_sync_stopped_and_shows_stale(service, source):
    assert service.report("search", *QUARTER).stale_streams == ["support"]
    assert service.report("eng", *QUARTER).stale_streams == ["support"]
    assert all(service.report(t, *QUARTER).stale_streams == [] for t in TEAMS if t != "search")
    stopped = datetime.combine(demo.SUPPORT_STOPPED, time.min, UTC)
    assert source.support_requests("search", stopped, datetime.combine(demo.END, time.min, UTC)) == []


def test_an_open_incident_is_counted_not_dropped(service):
    r = service.report("platform", *QUARTER)
    assert r.incidents_open == 1 and r.ttr.sample_size == r.incidents_total - 1
