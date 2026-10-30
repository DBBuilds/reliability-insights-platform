from datetime import UTC, date, datetime, timedelta, timezone

from insights import metrics as m
from insights.models import Deploy, Incident, Page, Severity, SliDaily, Slo, SupportRequest

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
    assert m.change_failure_rate(deploys, incidents) == 0.5 and m.failed_deploys(deploys, incidents) == 2
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


def dep(i, service="svc", deployed_min=0, lead_min=None):
    at = T0 + timedelta(minutes=deployed_min)
    return Deploy(f"d{i}", "o", service, at, at - timedelta(minutes=lead_min) if lead_min is not None else None)


def test_week_starts_flag_partial_edges():
    assert m.week_starts(date(2026, 9, 9), date(2026, 9, 21)) == [(date(2026, 9, 7), True), (date(2026, 9, 14), False)]


def test_lead_time_uses_deploys_with_a_commit_time():
    deploys = [dep(1, lead_min=60), dep(2, lead_min=120), dep(3, lead_min=180), dep(4)]
    assert m.lead_time(deploys) == m.DurationStat(3, 120, 180)


def test_recovery_time_counts_only_resolved_deploy_caused_incidents():
    incidents = [inc(1, resolve=30, deploy="d"), inc(2, resolve=60, deploy="d"), inc(3, resolve=90, deploy="d")]
    incidents += [inc(4, resolve=999), inc(5, resolve=None, deploy="d")]
    assert m.recovery_time(incidents) == m.DurationStat(3, 60, 90)


def test_deploy_frequency_is_the_median_service_per_day():
    deploys = [dep(i, "a") for i in range(14)] + [dep(i, "b") for i in range(7)] + [dep(99, "c")]
    assert m.deploy_frequency(deploys, days=7) == (1.0, 3)  # a: 2/day, b: 1/day, c: 1/7 per day
    assert m.deploy_frequency([], days=7) == (None, 0)


def test_dora_levels_follow_the_2024_ranges():
    hour, day = 60, 1440
    assert m.dora_levels("lead_time", 23 * hour) == ["ELITE"]
    assert m.dora_levels("lead_time", day) == ["HIGH"]  # half-open: one day is no longer Elite
    assert m.dora_levels("lead_time", 200 * day) == []  # slower than every published range
    assert m.dora_levels("deploy_frequency", 1 / 10) == ["MEDIUM"]
    assert m.dora_levels("recovery_time", 2 * hour) == ["HIGH", "MEDIUM"]  # the report gives both the same range
    assert m.dora_levels("recovery_time", 3 * day) == []  # the report's gap between one day and one week
    assert m.dora_levels("lead_time", None) is None


def test_pages_by_hour_uses_local_time_and_fills_every_cell():
    local = timezone(timedelta(hours=-7))
    pages = [Page("a", "o", "x", datetime(2026, 9, 8, 2, 30, tzinfo=local), None)] * 2  # Tuesday 02:30 local
    cells = m.pages_by_hour(pages)
    assert len(cells) == 168 and cells[(1, 2)] == 2 and sum(cells.values()) == 2


def test_slo_budget_burn_and_status():
    slo = Slo("s", "o", "api", objective=0.99, window_days=4)
    days = [
        SliDaily("s", date(2026, 10, d), good=1000 - bad, total=1000) for d, bad in [(1, 5), (2, 5), (3, 20), (4, 0)]
    ]
    r = m.slo_result(slo, days, end=date(2026, 10, 5))
    # budget = 1% of 4000 = 40 bad events; 30 used
    assert (r.attainment, r.budget_remaining, r.status) == (0.9925, 0.25, "OK")
    assert r.burn_rate_1d == 0.0 and r.burn_rate_3d == round(25 / 3000 / 0.01, 2)
    assert [left for _, left in r.daily] == [0.875, 0.75, 0.25, 0.25]


def test_slo_status_burning_and_exhausted():
    slo = Slo("s", "o", "api", objective=0.99, window_days=10)  # budget: 100 bad events over 10,000

    def last_3_days_bad(bad):
        return [SliDaily("s", date(2026, 10, d), good=1000 - (bad if d > 7 else 0), total=1000) for d in range(1, 11)]

    end = date(2026, 10, 11)
    assert m.slo_result(slo, last_3_days_bad(15), end).status == "BURNING"  # 1.5x for 3 days, 55% left
    assert m.slo_result(slo, last_3_days_bad(40), end).status == "EXHAUSTED"  # 120 bad
    assert m.slo_result(slo, last_3_days_bad(5), end).status == "OK"  # 0.5x


def test_slo_without_data_is_null_not_zero():
    r = m.slo_result(Slo("s", "o", "api", objective=0.99, window_days=30), [], end=date(2026, 10, 5))
    assert (r.attainment, r.budget_remaining, r.status, r.daily) == (None, None, None, [])
