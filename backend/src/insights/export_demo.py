"""Write the static demo: the API's answer to every frontend operation, for every org and preset
window, computed in-process from data/demo.json.  Run: make demo-build

The frontend's demo link (frontend/src/demo.ts) fetches demo/<key>.json, so key() must match its demoKey().
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from graphql import OperationDefinitionNode, parse

from insights import demo_data
from insights.schema import schema
from insights.service import InsightsService
from insights.sources.fixtures import FixtureSource

ROOT = Path(__file__).resolve().parents[3]
OPERATIONS = ROOT / "frontend" / "src" / "gql" / "persisted-documents.json"  # written by codegen
OUT = ROOT / "frontend" / "public" / "demo"
DAYS = (30, 90, 180, 365)  # the dashboard's window presets
MAX_MONTHS = 12  # the longest custom range the static demo offers (inside the API's 366-day cap)


def key(operation: str, variables: dict[str, str]) -> str:
    """The operation name, then the variable values sorted by variable name."""
    return operation + ("/" + "_".join(variables[k] for k in sorted(variables)) if variables else "")


def windows(as_of: datetime) -> list[dict[str, str]]:
    """The last N complete UTC days before `as_of`, like the frontend's lastDays()."""
    end = as_of.astimezone(UTC).date()
    return [
        {"start": str(end - timedelta(days=n)), "end": str(end), "previousStart": str(end - timedelta(days=2 * n))}
        for n in DAYS
    ]


def _next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def months(start: date, end: date) -> list[date]:
    """First days of the calendar months that lie wholly inside [start, end): the demo's custom choices.

    The frontend's demoMonths() lists the same months, so every choice it offers has a file.
    """
    month = start if start.day == 1 else _next_month(start)
    out = []
    while _next_month(month) <= end:
        out.append(month)
        month = _next_month(month)
    return out


def month_windows(choices: list[date]) -> list[dict[str, str]]:
    """Every range of 1 to MAX_MONTHS consecutive months, with the same-length previous period."""
    out = []
    for i, first in enumerate(choices):
        for last in choices[i : i + MAX_MONTHS]:
            end = _next_month(last)
            out.append({"start": str(first), "end": str(end), "previousStart": str(first - (end - first))})
    return out


def export(out: Path = OUT) -> list[str]:
    source = FixtureSource(demo_data.TARGET)
    service = InsightsService(source, now=source.as_of)
    variable_sets = {
        "Orgs": [{}],
        "OrgMetrics": [
            {"orgId": o.id, **w}
            for o in source.orgs()
            for w in windows(source.as_of) + month_windows(months(demo_data.START, demo_data.END))
        ],
    }
    shutil.rmtree(out, ignore_errors=True)  # generated; no stale files from an older export
    # One context for the whole export: its report cache then computes each org and window once, however
    # many files need it (a parent's children, other ranges' previous periods). Safe: the data is fixed.
    context = {"service": service}
    written = []
    for text in json.loads(OPERATIONS.read_text()).values():
        [operation] = [d for d in parse(text).definitions if isinstance(d, OperationDefinitionNode)]
        name = operation.name.value
        if name not in variable_sets:
            sys.exit(f"export_demo: no variables known for operation {name}; add them to variable_sets")
        for variables in variable_sets[name]:
            result = schema.execute_sync(text, variable_values=variables, context_value=context)
            if result.errors:
                sys.exit(f"export_demo: {name} {variables}: {result.errors[0].message}")
            path = out / f"{key(name, variables)}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"data": result.data}, separators=(",", ":")))
            written.append(key(name, variables))
    return written


def main() -> None:
    written = export()
    print(f"wrote {len(written)} files to {OUT}")


if __name__ == "__main__":
    main()
