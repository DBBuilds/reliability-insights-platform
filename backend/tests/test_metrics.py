from datetime import UTC, date, datetime, timedelta, timezone

from insights import metrics as m
from insights.models import Deploy, Incident, Page, Severity, SupportRequest

T0 = datetime(2026, 9, 7, 10, 0, tzinfo=UTC)  # a Monday, 10:00


def inc(i, start_min=0, detect=5, resolve=60, deploy=None):
    s = T0 + timedelta(minutes=start_min)
    return Incident(
        id=f"i{i}",
        org_id="o",
        severity=Severity.SEV3,
        started_at=s,
        detected_at=s + timedelta(minutes=detect) if detect is not None else None,
        resolved_at=s + timedelta(minutes=resolve) if resolve is not None else None,
        caused_by_deploy_id=deploy,
    )


def test_percentile_is_nearest_rank():
    assert m.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9
    assert m.percentile([5], 90) == 5
    assert m.percentile([], 90) is None


def test_median_even_and_odd():
    assert m.median([3, 1, 2]) == 2
    assert m.median([4, 1, 2, 3]) == 2.5


def test_too_few_samples_is_null_not_zero():
    s = m.duration_stat([10, 20])
    assert (s.sample_size, s.median_minutes, s.p90_minutes) == (2, None, None)


def test_negative_durations_are_dropped_not_clamped():
    assert m.duration_stat([-5, 10, 20, 30]).sample_size == 3


def test_mttr_excludes_open_incidents_and_counts_them_separately():
    incidents = [inc(1, resolve=30), inc(2, resolve=60), inc(3, resolve=90), inc(4, resolve=None)]
    assert m.time_to_resolve(incidents).median_minutes == 60
    assert m.time_to_resolve(incidents).sample_size == 3
    assert m.open_count(incidents) == 1


def test_mttd_skips_unknown_detection():
    incidents = [inc(1, detect=2), inc(2, detect=4), inc(3, detect=6), inc(4, detect=None)]
    assert m.time_to_detect(incidents).sample_size == 3


def test_change_failure_rate_counts_each_failed_deploy_once():
    deploys = [Deploy(f"d{i}", "o", "svc", T0) for i in range(4)]
    incidents = [inc(1, deploy="d0"), inc(2, deploy="d0"), inc(3, deploy="d1"), inc(4, deploy="other")]
    assert m.change_failure_rate(deploys, incidents) == 0.5
    assert m.change_failure_rate([], incidents) is None


def test_off_hours():
    assert not m.is_off_hours(T0)  # Monday 10:00
    assert m.is_off_hours(T0.replace(hour=22))
    assert m.is_off_hours(T0 + timedelta(days=5))  # Saturday


def test_actionable_share_ignores_unmarked_pages():
    pages = [Page("a", "o", "x", T0, True), Page("b", "o", "x", T0, False), Page("c", "o", "x", T0, None)]
    assert m.actionable_share(pages) == 0.5
    assert m.actionable_share([Page("c", "o", "x", T0, None)]) is None


def test_resolution_rate_and_first_response():
    reqs = [
        SupportRequest("1", "o", "#c", T0, T0 + timedelta(minutes=10), T0 + timedelta(hours=1)),
        SupportRequest("2", "o", "#c", T0, T0 + timedelta(minutes=20), None),
        SupportRequest("3", "o", "#c", T0, T0 + timedelta(minutes=30), T0 + timedelta(hours=2)),
        SupportRequest("4", "o", "#c", T0, None, None),
    ]
    assert m.resolution_rate(reqs) == 0.5
    assert m.first_response(reqs).median_minutes == 20


def test_weekly_counts_flag_partial_edge_weeks():
    # Wed Sep 9 to Wed Sep 23: first and last weeks are partial, the middle one is complete.
    weeks = m.weekly_counts([T0 + timedelta(days=d) for d in (3, 8, 9, 15)], date(2026, 9, 9), date(2026, 9, 23))
    assert [(w.week_start, w.count, w.partial) for w in weeks] == [
        (date(2026, 9, 7), 1, True),
        (date(2026, 9, 14), 2, False),
        (date(2026, 9, 21), 1, True),
    ]


def test_weekly_counts_bucket_by_utc_date_like_the_window():
    # Sep 13 20:00 at -07:00 is Sep 14 03:00 UTC: inside the window, so it must be counted.
    ts = datetime(2026, 9, 14, 3, 0, tzinfo=UTC).astimezone(timezone(timedelta(hours=-7)))
    weeks = m.weekly_counts([ts], date(2026, 9, 14), date(2026, 9, 21))
    assert [(w.week_start, w.count) for w in weeks] == [(date(2026, 9, 14), 1)]


def test_pct_change_guards():
    assert m.pct_change(150, 100) == 50.0
    assert m.pct_change(1, 0) is None
    assert m.pct_change(None, 1) is None
