from insights import insights as rules
from insights.metrics import DurationStat


def test_mttr_trend_needs_a_real_change():
    assert rules.mttr_trend(DurationStat(5, 110, 200), DurationStat(5, 100, 180)) is None
    worse = rules.mttr_trend(DurationStat(5, 150, 300), DurationStat(5, 100, 180))
    assert worse.level == rules.InsightLevel.WARNING and "up 50%" in worse.title


def test_mttr_trend_is_silent_without_enough_samples():
    assert rules.mttr_trend(DurationStat(2, None, None), DurationStat(5, 100, 180)) is None


def test_noisy_alert_needs_volume():
    assert rules.noisy_alert([("A", 9)], 0.1) is None
    hit = rules.noisy_alert([("A", 30)], 0.2)
    assert "'A' paged 30 times" in hit.title and "20%" in hit.detail


def test_stale_sources():
    assert rules.stale_sources([]) is None
    assert rules.stale_sources(["support"]).level == rules.InsightLevel.CRITICAL
