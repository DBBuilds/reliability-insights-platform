# Reliability insights platform (reference implementation)

A working skeleton of a reliability and operational-load dashboard: incidents,
time to detect and resolve, deploys and change failure rate, on-call pages, and
support load, with rule-based insights, org rollups, and data-freshness checks.
Public tools only. **Read [BLUEPRINT.md](BLUEPRINT.md)** for the design, the
metric definitions, and the roadmap.

| Part | Stack |
|---|---|
| `backend/` | Python 3.11+, FastAPI, Strawberry GraphQL, uv |
| `frontend/` | Node 22.12+, React 19, Vite 8, Apollo Client 4, GraphQL Codegen, Vitest |
| `schema/` | The GraphQL contract (generated, committed) and the reviewed non-null list |
| `scripts/` | `check_breaking.py`: breaking-change check against main |

It ships with synthetic data (`backend/data/sample.json`): three orgs (a parent
and two teams), ten weeks of incidents, deploys, pages, and support requests, and
one deliberately stale support sync.

## Rebuild in a new repo

Prerequisites: [uv](https://docs.astral.sh/uv/) and Node 22.12 or newer
(`frontend/.nvmrc`). On a Mac: `brew install uv node`.

```bash
cp -R reliability-insights-platform/ ~/src/insights && cd ~/src/insights
git init -b main
make setup        # uv sync + npm ci from the lockfiles
make check        # lint, typecheck, all tests, contract drift, production build
make api          # terminal 1: http://localhost:8000/graphql (GraphiQL in the browser)
make web          # terminal 2: http://localhost:5173
git add . && git commit -m "Initial reliability insights skeleton"
```

If your company mirrors package registries, `make setup` resolves through your
configured npm and pip indexes. If a mirror holds back very new releases, delete
`backend/uv.lock` or `frontend/package-lock.json` and re-lock (`uv lock`,
`npm install`); the version ranges are deliberately loose.

## Daily work

| Change | Do |
|---|---|
| A metric's definition | Edit `backend/src/insights/metrics.py`; write the test first and watch it fail |
| A new field | Add it to `schema.py` as **nullable**, `make schema`, use it in a frontend query only after the backend is in production |
| A new data source | Implement `DataSource` in `backend/src/insights/sources/`; record per-stream sync time |
| A new panel | Add fields to `frontend/src/queries.ts`, `npm run codegen`, render in `Dashboard.tsx` |

Before pushing: `make check`, then run `make api` and send the query you changed for
more than one org.

## What's verified

On 2026-10-14, on macOS arm64 (uv 0.12, Node 22.23):

- Backend: 27 tests (metrics edge cases, insight thresholds, rollup dedupe, staleness,
  GraphQL over HTTP, contract drift, non-null budget); ruff clean.
- Contract guards fail when they should: an unreviewed non-null field, stale SDL, a
  removed field, and a non-null to nullable change each fail.
- Frontend: typecheck, 5 tests, production build.
- End to end: API plus Vite dev proxy in a browser; the stale-support banner and the
  parent-org rollup render, with no console errors.
- Clean-room rebuild: a fresh `git init` copy, `make setup` and `make check` against
  the public registries, all green, no contract drift.
- `npm audit`: runtime dependencies 0 vulnerabilities. The dev toolchain reports a
  high-severity advisory in `braces` (GHSA-vfj7-8cjw-p6xm), reached only through
  `@graphql-codegen/cli`, with no fixed `braces` release as of 2026-10-14. It does not
  ship in the built app. Re-run `npm audit` when you rebuild.

## Next steps

Phase 1 of the roadmap in BLUEPRINT.md: one real incident-tool connector, a
Postgres store with a `sync_state` table, auth from your SSO proxy, and a deploy
target (a container behind the proxy, with the built `frontend/dist` served
statically from the same origin so `/graphql` needs no CORS).
