"""Fail if NEW_SCHEMA breaks clients of OLD_SCHEMA.

Breaking (graphql-core's definition): a removed type, field, enum value, or
argument; a changed field type; an output field going non-null to nullable; a new
required argument or input field. NOT flagged: an output field going nullable to
non-null. That is type-safe for clients but makes the field able to null its
parent at runtime, which is why tests/test_schema_contract.py keeps a separate
non-null budget.

Usage: python scripts/check_breaking.py old.graphql new.graphql
CI runs it with the schema from main as OLD. Dangerous (non-breaking) changes are
printed as warnings.
"""

import sys
from pathlib import Path

from graphql import build_schema, find_breaking_changes, find_dangerous_changes


def main(old_path: str, new_path: str) -> int:
    old, new = (build_schema(Path(p).read_text()) for p in (old_path, new_path))
    for change in find_dangerous_changes(old, new):
        print(f"warning: {change.type.name}: {change.description}")
    breaking = find_breaking_changes(old, new)
    for change in breaking:
        print(f"BREAKING: {change.type.name}: {change.description}")
    return 1 if breaking else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
