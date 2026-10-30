import json
from datetime import UTC, date, datetime

import pytest

from insights.models import SliDaily, Slo
from insights.sources.fixtures import FixtureSource

OCT_1, OCT_2 = datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 2, tzinfo=UTC)


def write(tmp_path, **records):
    raw = {"orgs": [{"id": "o", "name": "O"}], "incidents": [], "deploys": [], "pages": [], "support_requests": []}
    path = tmp_path / "data.json"
    path.write_text(json.dumps(raw | records))
    return path


def test_older_files_load_with_new_fields_empty():
    source = FixtureSource()
    lo, hi = datetime(2026, 8, 3, tzinfo=UTC), datetime(2026, 10, 12, tzinfo=UTC)
    assert source.as_of is None and source.slos("payments") == []
    assert all(i.service is None and i.title is None for i in source.incidents("payments", lo, hi))
    assert all(d.committed_at is None for d in source.deploys("payments", lo, hi))


def test_new_fields_are_read(tmp_path):
    source = FixtureSource(
        write(
            tmp_path,
            as_of="2026-10-26T06:00:00+00:00",
            incidents=[
                {"id": "i", "org_id": "o", "severity": "SEV2", "started_at": "2026-10-01T10:00:00-04:00"}
                | {"service": "api", "title": "api: elevated error rate"}
            ],
            deploys=[
                {"id": "d", "org_id": "o", "service": "api", "deployed_at": "2026-10-01T10:00:00-04:00"}
                | {"committed_at": "2026-09-30T16:00:00-04:00"}
            ],
            slos=[{"id": "s", "org_id": "o", "service": "api", "objective": 0.999, "window_days": 30}],
            sli_daily=[{"slo_id": "s", "day": "2026-10-01", "good": 999, "total": 1000}],
        )
    )
    assert source.as_of == datetime(2026, 10, 26, 6, tzinfo=UTC)
    assert source.incidents("o", OCT_1, OCT_2)[0].title == "api: elevated error rate"
    assert source.deploys("o", OCT_1, OCT_2)[0].committed_at.isoformat() == "2026-09-30T16:00:00-04:00"
    assert source.slos("o") == [Slo("s", "o", "api", 0.999, 30)]
    assert source.sli_daily("s", date(2026, 10, 1), date(2026, 10, 2)) == [SliDaily("s", date(2026, 10, 1), 999, 1000)]
    assert source.sli_daily("s", date(2026, 10, 2), date(2026, 10, 3)) == []


def test_timestamps_need_an_offset(tmp_path):
    # Without an offset, off-hours can't be judged and comparisons with the UTC window fail.
    path = write(tmp_path, deploys=[{"id": "d", "org_id": "o", "service": "api", "deployed_at": "2026-10-01T10:00:00"}])
    with pytest.raises(ValueError, match="offset"):
        FixtureSource(path)


@pytest.mark.parametrize(
    "make",
    [
        lambda: Slo("s", "o", "api", objective=1.0, window_days=30),
        lambda: Slo("s", "o", "api", objective=0.999, window_days=0),
        lambda: SliDaily("s", date(2026, 10, 1), good=1001, total=1000),
        lambda: SliDaily("s", date(2026, 10, 1), good=-1, total=1000),
    ],
)
def test_slo_records_reject_impossible_values(make):
    with pytest.raises(ValueError):
        make()
