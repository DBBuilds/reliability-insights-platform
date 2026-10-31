import json
from datetime import UTC, datetime

import pytest
from graphql import parse

from insights import export_demo


def test_key_matches_the_frontend():
    # frontend/src/demo.test.ts pins the same strings: both sides must name files the same way.
    variables = {"orgId": "eng", "start": "2026-09-28", "end": "2026-10-26", "previousStart": "2026-08-31"}
    assert export_demo.key("OrgMetrics", variables) == "OrgMetrics/2026-10-26_eng_2026-08-31_2026-09-28"
    assert export_demo.key("Orgs", {}) == "Orgs"


def test_windows_are_the_complete_weeks_before_the_snapshot():
    assert export_demo.windows(datetime(2026, 10, 26, 6, tzinfo=UTC)) == [
        {"start": "2026-09-28", "end": "2026-10-26", "previousStart": "2026-08-31"},
        {"start": "2026-08-31", "end": "2026-10-26", "previousStart": "2026-07-06"},
        {"start": "2026-07-27", "end": "2026-10-26", "previousStart": "2026-04-27"},
    ]


def test_exports_every_frontend_operation_for_every_org_and_window(tmp_path):
    written = export_demo.export(tmp_path)
    operations = json.loads(export_demo.OPERATIONS.read_text()).values()
    assert {k.split("/")[0] for k in written} == {parse(text).definitions[0].name.value for text in operations}
    assert len(written) == 1 + 6 * 3  # Orgs, plus 6 orgs x 3 windows
    eng = json.loads((tmp_path / "OrgMetrics/2026-10-26_eng_2026-04-27_2026-07-27.json").read_text())
    assert eng["data"]["orgMetrics"]["incidents"]["total"] == 68  # the same number the live API returns


@pytest.mark.parametrize(
    "operation, error",
    [
        ("query Mystery { orgs { id } }", "no variables known for operation Mystery"),
        ("query Orgs { orgs { nope } }", "Cannot query field 'nope'"),
    ],
)
def test_unknown_operations_and_graphql_errors_fail_the_export(tmp_path, monkeypatch, operation, error):
    operations = tmp_path / "operations.json"
    operations.write_text(json.dumps({"sha256:x": operation}))
    monkeypatch.setattr(export_demo, "OPERATIONS", operations)
    with pytest.raises(SystemExit, match=error):
        export_demo.export(tmp_path / "out")
