"""Write the static demo: the API's answer to every frontend operation, for every org and preset
window, computed in-process from data/demo.json.  Run: make demo-build

The frontend's demo link (frontend/src/demo.ts) fetches demo/<key>.json, so key() must match its demoKey().
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from graphql import OperationDefinitionNode, parse

from insights import demo_data
from insights.schema import schema
from insights.service import InsightsService
from insights.sources.fixtures import FixtureSource

ROOT = Path(__file__).resolve().parents[3]
OPERATIONS = ROOT / "frontend" / "src" / "gql" / "persisted-documents.json"  # written by codegen
OUT = ROOT / "frontend" / "public" / "demo"
WEEKS = (4, 8, 13)  # the dashboard's window presets


def key(operation: str, variables: dict[str, str]) -> str:
    """The operation name, then the variable values sorted by variable name."""
    return operation + ("/" + "_".join(variables[k] for k in sorted(variables)) if variables else "")


def windows(as_of: datetime) -> list[dict[str, str]]:
    """The last N complete ISO weeks before `as_of`, like the frontend's completeWeeks()."""
    day = as_of.astimezone(UTC).date()
    end = day - timedelta(days=day.weekday())
    return [
        {"start": str(end - timedelta(weeks=n)), "end": str(end), "previousStart": str(end - timedelta(weeks=2 * n))}
        for n in WEEKS
    ]


def export(out: Path = OUT) -> list[str]:
    source = FixtureSource(demo_data.TARGET)
    service = InsightsService(source, now=source.as_of)
    variable_sets = {
        "Orgs": [{}],
        "OrgMetrics": [{"orgId": o.id, **w} for o in source.orgs() for w in windows(source.as_of)],
    }
    shutil.rmtree(out, ignore_errors=True)  # generated; no stale files from an older export
    written = []
    for text in json.loads(OPERATIONS.read_text()).values():
        [operation] = [d for d in parse(text).definitions if isinstance(d, OperationDefinitionNode)]
        name = operation.name.value
        if name not in variable_sets:
            sys.exit(f"export_demo: no variables known for operation {name}; add them to variable_sets")
        for variables in variable_sets[name]:
            result = schema.execute_sync(text, variable_values=variables, context_value={"service": service})
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
