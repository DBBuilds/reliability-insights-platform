"""Write the GraphQL SDL to ../schema/schema.graphql.  Run: uv run python -m insights.export_schema"""

from pathlib import Path

from insights.schema import schema

TARGET = Path(__file__).resolve().parents[3] / "schema" / "schema.graphql"


def main() -> None:
    TARGET.write_text(schema.as_str() + "\n")
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
