# A 5-minute tour

Each stop is a link into the [live demo](https://dbbuilds.github.io/reliability-insights-platform/),
what to look at, and the design choice it shows. The data is synthetic; the backend
computed every number at build time from 24 months of seeded records.

## 1. The org view (1 minute)

[Engineering, last 90 days](https://dbbuilds.github.io/reliability-insights-platform/?org=eng&days=90)

- The header says **Jul 28 to Oct 25, 2026, UTC**: complete days with fixed dates, so
  the numbers don't drift between two reads. The window menu offers 30, 90, 180, and
  365 days; with the API (`make demo`) it also takes a custom range.
- The freshness row marks **support: stale since Oct 14**. A source that stopped
  syncing reads as stale, never as a quiet zero.
- **Insights** come first: what needs attention, each needing a minimum sample and
  change before it shows.
- **Delivery (DORA)**: recovery reads "2024 DORA: High or Medium". The report gives
  both the same range, and its levels are survey clusters, not grades, so they are
  named, not colored. Open any ⓘ for the definition and data source.

## 2. A risky release (1 minute)

[Checkout, last 90 days](https://dbbuilds.github.io/reliability-insights-platform/?org=checkout&days=90)

- "Change failure rate more than doubled". The insight needs at least 20 deploys in
  each period and 5 failed deploys: a move from 0 to 4 failures never becomes a headline.
- Open **Reliability**: median time to resolve jumps the week of Sep 7, when the
  release's incidents took longer to fix. Focus the chart and use the arrow keys;
  every chart also has a table view.
- Switch to [365 days](https://dbbuilds.github.io/reliability-insights-platform/?org=checkout&days=365): "Median time to resolve up 67%".
  A trend insight also needs a rank test to say chance doesn't explain it, because
  medians of a dozen incidents move 25% by chance about half the time.

## 3. Not enough data is not zero (30 seconds)

[Payments, last 30 days](https://dbbuilds.github.io/reliability-insights-platform/?org=payments)

- Two resolved incidents, so median time to resolve says **Not enough data**. Under 3
  samples is null, never 0. Switch to 90 days: "down 62%".

## 4. On-call load (1 minute)

[Search, last 90 days](https://dbbuilds.github.io/reliability-insights-platform/?org=search&days=90)

- The heatmap shows pages by **local** hour, so a night hotspot means the
  responder's night. The busiest off-hours slot is named in the insight.
- `IndexLag` sends most pages; the noisy-alert insight needs at least 30 pages and
  half of all pages.
- [Platform](https://dbbuilds.github.io/reliability-insights-platform/?org=platform&days=90)
  has one open incident: counted in "1 open", left out of the time-to-resolve median.
- Weekly counts fade the partial weeks at a window's edges, which always undercount.

## 5. Error budgets (30 seconds)

[Identity, last 90 days](https://dbbuilds.github.io/reliability-insights-platform/?org=identity&days=90)

- The SLO burn-down shows most of the 30-day budget gone in the first week. Status
  is OK because the burn stopped; the error-budget insight still warns because so
  little is left.

## 6. Under the hood (1 minute)

- **One contract:** [`schema/schema.graphql`](../schema/schema.graphql) is generated
  and committed. Every new field is nullable; tests fail on an unreviewed non-null
  field, and CI blocks breaking changes against `main`.
- **Definitions as pure functions with tests:**
  [`metrics.py`](../backend/src/insights/metrics.py),
  [`insights.py`](../backend/src/insights/insights.py).
- **The demo is the real code path:** [`export_demo.py`](../backend/src/insights/export_demo.py)
  runs every UI query through the GraphQL schema for every org and window. The
  generator's story beats are asserted in
  [`test_demo_data.py`](../backend/tests/test_demo_data.py).
- **Previews:** every pull request publishes its own copy of the demo at `/pr-<number>/`.
