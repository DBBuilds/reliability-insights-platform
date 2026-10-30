from insights import insights as rules
from insights.metrics import DurationStat


def test_mttr_trend_needs_a_real_change():
    assert rules.mttr_trend(DurationStat(5, 110, 200), DurationStat(5, 100, 180)) is None
    worse = rules.mttr_trend(DurationStat(5, 150, 300), DurationStat(5, 100, 180))
    assert worse.level == rules.InsightLevel.WARNING and "up 50%" in worse.title


def test_mttr_trend_is_silent_without_enough_samples():
    assert rules.mttr_trend(DurationStat(2, None, None), DurationStat(5, 100, 180)) is None
    assert rules.mttr_trend(DurationStat(4, 165, 286), DurationStat(5, 100, 180)) is None  # 4 resolved: too few


def test_noisy_alert_needs_volume_and_a_majority_of_pages():
    assert rules.noisy_alert([("A", 20)], pages=32, share=0.1) is None  # 62%, but too few pages to call it
    assert rules.noisy_alert([("A", 40)], pages=100, share=0.1) is None  # 40%: spread across alerts
    hit = rules.noisy_alert([("A", 60)], pages=100, share=0.2)
    assert "'A' paged 60 times" in hit.title and "20%" in hit.detail


def test_cfr_spike_needs_volume_and_a_real_change():
    assert rules.cfr_spike(6, 19, 1, 50) is None  # too few deploys
    assert rules.cfr_spike(4, 55, 0, 51) is None  # 0 to 4 failures: too few to call a spike
    assert rules.cfr_spike(6, 100, 2, 100) is None  # tripled, but only +4 points
    assert rules.cfr_spike(15, 100, 10, 100) is None  # +5 points, but not double
    hit = rules.cfr_spike(11, 42, 3, 50)
    assert hit.level == rules.InsightLevel.WARNING and "6%" in hit.detail and "26%" not in hit.title + hit.detail


def test_off_hours_pages_names_the_busiest_off_hours_slot():
    cells = {(d, h): 0 for d in range(7) for h in range(24)} | {(1, 10): 50, (1, 2): 9}  # Tue 10:00 is work time
    assert rules.off_hours_pages(19, 19, cells) is None  # too few pages
    assert rules.off_hours_pages(40, 100, cells) is None  # under half
    hit = rules.off_hours_pages(60, 100, cells)
    assert "Tue 02:00" in hit.detail and "9 pages" in hit.detail


def test_error_budget_warns_when_nearly_spent():
    assert rules.error_budget("s", "api", 0.26) is None
    assert rules.error_budget("s", "api", None) is None
    assert rules.error_budget("s", "api", 0.25).level == rules.InsightLevel.WARNING
    spent = rules.error_budget("s", "api", -0.1)
    assert spent.level == rules.InsightLevel.CRITICAL and spent.id == "error-budget:s"


def test_stale_sources():
    assert rules.stale_sources([]) is None
    assert rules.stale_sources(["support"]).level == rules.InsightLevel.CRITICAL
