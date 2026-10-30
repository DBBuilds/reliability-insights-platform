import { MockedProvider } from "@apollo/client/testing/react";
import { render, screen } from "@testing-library/react";
import { defaultOptions } from "./apollo";
import { Dashboard } from "./Dashboard";
import { ORG_METRICS } from "./queries";

const variables = { orgId: "search", start: "2026-09-14", end: "2026-10-12" };

const stat = (n: number, median: number | null, p90: number | null = null) => ({
  __typename: "DurationStat" as const,
  sampleSize: n,
  medianMinutes: median,
  p90Minutes: p90,
});

const metrics = {
  __typename: "OrgMetrics" as const,
  orgId: "search",
  start: variables.start,
  end: variables.end,
  staleSources: ["support"],
  incidents: {
    __typename: "IncidentMetrics" as const,
    total: 2,
    open: 1,
    timeToDetect: stat(2, null),
    timeToResolve: stat(1, null, null),
    weekly: [{ __typename: "WeeklyCount" as const, weekStart: "2026-09-14", count: 2, partial: false }],
  },
  delivery: { __typename: "DeliveryMetrics" as const, deploys: 0, changeFailureRate: null },
  onCall: {
    __typename: "OnCallMetrics" as const,
    pages: 12,
    offHoursPages: 5,
    actionableShare: 0.25,
    noisiestAlerts: [{ __typename: "AlertCount" as const, alertName: "IndexLag", pages: 10 }],
  },
  support: {
    __typename: "SupportMetrics" as const,
    requests: 9,
    resolutionRate: 0.5,
    firstResponse: stat(9, 42),
  },
  insights: [
    { __typename: "Insight" as const, id: "stale-data", level: "CRITICAL" as const, title: "Some data is stale", detail: null },
    { __typename: "Insight" as const, id: "noisy-alert", level: "WARNING" as const, title: "'IndexLag' paged 10 times", detail: null },
  ],
};

function renderWith(data: unknown, errors?: { message: string; path: string[] }[]) {
  return render(
    <MockedProvider
      defaultOptions={defaultOptions}
      mocks={[{ request: { query: ORG_METRICS, variables }, result: { data, errors } }]}
    >
      <Dashboard {...variables} />
    </MockedProvider>,
  );
}

test("shows stale data, insights, and says 'Not enough data' instead of zero", async () => {
  renderWith({ orgMetrics: metrics });
  expect(await screen.findByRole("status")).toHaveTextContent("Stale data: support");
  expect(screen.queryByText("Some data is stale")).not.toBeInTheDocument(); // banner covers it, no repeat
  expect(screen.getByText("2 total, 1 open")).toBeInTheDocument();
  expect(screen.getAllByText("Not enough data").length).toBeGreaterThan(0);
  expect(screen.getByText("No data")).toBeInTheDocument(); // change failure rate with no deploys
  expect(screen.getByText("42 min")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "WARNING" })).toBeInTheDocument(); // level is announced, not only colored
});

test("a panel that failed to load says so instead of showing zero", async () => {
  renderWith({ orgMetrics: { ...metrics, delivery: null } }, [{ message: "boom", path: ["orgMetrics", "delivery"] }]);
  expect(await screen.findByText("2 total, 1 open")).toBeInTheDocument(); // other panels still render
  expect(screen.getByRole("heading", { name: "Delivery" }).parentElement).toHaveTextContent("DeliveryCould not load");
});

test("unknown org renders a message, not a crash", async () => {
  renderWith({ orgMetrics: null });
  expect(await screen.findByRole("alert")).toHaveTextContent("Unknown org.");
});
