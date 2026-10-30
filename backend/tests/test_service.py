from datetime import UTC, date, datetime

import pytest

from insights.models import Org
from insights.service import STREAMS, InsightsService
from insights.sources.fixtures import FixtureSource

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


@pytest.fixture
def service():
    return InsightsService(FixtureSource(), now=NOW)


def test_report_shape(service):
    r = service.report("payments", date(2026, 8, 3), date(2026, 10, 12))
    assert r.incidents_total == 14 and r.incidents_open == 1
    assert r.ttr.sample_size == 13 and r.ttr.median_minutes is not None
    assert sum(w.count for w in r.incident_weeks) == r.incidents_total
    assert r.deploys_total == 90 and 0 <= r.change_failure_rate <= 1


def test_stale_stream_is_reported_not_hidden(service):
    r = service.report("search", date(2026, 8, 3), date(2026, 10, 12))
    assert r.stale_streams == ["support"]
    assert r.insights[0].id == "stale-data"


@pytest.mark.parametrize(
    "start, end",
    [
        (date(2026, 9, 1), date(2026, 9, 1)),  # empty
        (date(2025, 10, 12), date(2026, 10, 14)),  # 367 days
        (date(1, 1, 2), date(1, 1, 9)),  # out of range: the comparison window would start before year 1
    ],
)
def test_bad_window_is_rejected(service, start, end):
    with pytest.raises(ValueError):
        service.report("payments", start, end)


def test_longest_window_is_allowed(service):
    assert service.report("payments", date(2025, 10, 12), date(2026, 10, 13)).incidents_total == 14


def test_parent_rolls_up_children_without_double_counting(service):
    parent = service.report("eng", date(2026, 8, 3), date(2026, 10, 12))
    kids = [service.report(o, date(2026, 8, 3), date(2026, 10, 12)) for o in ("payments", "search")]
    assert parent.incidents_total == sum(k.incidents_total for k in kids) == 22
    assert parent.deploys_total == 230
    assert parent.stale_streams == ["support"]  # inherited from the stale child


def test_parent_is_stale_when_a_child_never_synced_a_stream():
    class TwoTeams(FixtureSource):
        def orgs(self):
            return [Org("parent", "Parent"), Org("a", "A", "parent"), Org("b", "B", "parent")]

        def coverage(self, org_id):
            return {"a": dict.fromkeys(STREAMS, NOW), "b": {"incidents": NOW}}.get(org_id, {})

    r = InsightsService(TwoTeams(), now=NOW).report("parent", date(2026, 9, 7), date(2026, 10, 5))
    assert r.stale_streams == ["deploys", "pages", "support"]


def test_org_with_no_connected_sources_is_stale_not_zero():
    class Empty(FixtureSource):
        def orgs(self):
            return [Org("lonely", "Lonely")]

    r = InsightsService(Empty(), now=NOW).report("lonely", date(2026, 8, 3), date(2026, 10, 12))
    assert r.incidents_total == 0
    assert r.stale_streams == ["incidents", "deploys", "pages", "support"]
    assert r.insights[0].id == "stale-data"
