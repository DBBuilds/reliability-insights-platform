# Contributing

Thanks for helping. The short version:

1. `make setup`, then `make demo` to see the dashboard locally.
2. Write the test first and watch it fail, then make the change.
3. `make check` before you push. CI runs the same steps, plus a breaking-change
   check of the GraphQL schema against `main`.
4. If you changed a query or a metric, run `make api` and send it for more than one org.

The rules every change keeps (nullable new fields, null instead of 0 for too few
samples, stale instead of quiet, fixed windows, no em dashes, American English) are
in [CLAUDE.md](CLAUDE.md). It is written for coding agents and applies to people too.
Metric definitions and their caveats are in [BLUEPRINT.md](BLUEPRINT.md).

Pull requests from branches in this repo get a preview of the demo at
`https://dbbuilds.github.io/reliability-insights-platform/pr-<number>/`. Pull requests
from forks don't, because their CI token can't publish.
