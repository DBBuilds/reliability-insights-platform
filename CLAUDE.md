# Agent instructions for this repo

## The schema is the contract

- `schema/schema.graphql` is generated from `backend/src/insights/schema.py` and
  committed. The frontend generates its types from it. After any schema change:
  `make schema`, then commit both `schema/` and `frontend/src/gql/`.
- **New fields are nullable.** A non-null field that errors or is missing nulls
  its parent, up to the whole query. `tests/test_schema_contract.py` fails on any
  non-null field not listed in `schema/non_null_fields.txt`; adding one there is a
  deliberate decision for the PR reviewer.
- **Never remove or rename a field a deployed client selects.** Deprecate, ship the
  frontend without it, then remove. CI runs `scripts/check_breaking.py` against main.
- **A frontend query that selects a new field merges only after the backend serving
  it is in production.** Verify with a real request against prod, more than once
  (a fleet mid-deploy answers both ways). A feature flag on the UI does not protect
  the query.

## Metrics

- Definitions live in `backend/src/insights/metrics.py` as pure functions with
  tests. Change a definition only with a test that failed before the change.
- Too few samples is `None`, never 0. Open items are counted, not dropped.
  Windows are fixed `[start, end)` dates. Edge weeks are flagged partial.
- A source that has stopped syncing must show as stale, never as a confident zero.

## Before pushing

- `make check` locally. CI is extra evidence, not a substitute.
- Probe the real thing: run `make api` and send the query you changed, with more
  than one org. Mocked tests prove request shape, not that the data is right.

## Writing

No em dashes, American English, no ticket IDs in code (write the condition instead).
