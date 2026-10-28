"""The schema is the contract. These tests fail before a risky change ships.

1. Drift: the committed schema/schema.graphql must match the code. The frontend
   generates its types from that file, so a mismatch means the two sides disagree.
2. Non-null budget: every non-null field is listed in schema/non_null_fields.txt.
   Adding one fails here on purpose: a non-null field that errors or is missing
   nulls its parent object, up to the whole query. Make new fields nullable, or
   add the field to the list in the same PR with a reviewer's sign-off.
3. Breaking changes vs. the committed baseline are checked in CI against main
   (scripts/check_breaking.py), where the old schema is available.
"""

from pathlib import Path

from graphql import GraphQLNonNull, GraphQLObjectType, build_schema

from insights.schema import schema

ROOT = Path(__file__).resolve().parents[2]
SDL = ROOT / "schema" / "schema.graphql"
ALLOW = ROOT / "schema" / "non_null_fields.txt"


def non_null_fields(sdl: str) -> set[str]:
    out = set()
    for name, t in build_schema(sdl).type_map.items():
        if isinstance(t, GraphQLObjectType) and not name.startswith("__"):
            out |= {f"{name}.{f}" for f, d in t.fields.items() if isinstance(d.type, GraphQLNonNull)}
    return out


def test_committed_schema_matches_code():
    assert SDL.read_text().strip() == schema.as_str().strip(), (
        "schema/schema.graphql is out of date: run `make schema` and commit it"
    )


def test_no_unreviewed_non_null_fields():
    allowed = {line.strip() for line in ALLOW.read_text().splitlines() if line.strip() and not line.startswith("#")}
    added = sorted(non_null_fields(schema.as_str()) - allowed)
    assert not added, f"New non-null fields {added}: make them nullable, or add to {ALLOW.name} deliberately"
