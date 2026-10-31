import { InMemoryCache } from "@apollo/client";
import { MockedProvider } from "@apollo/client/testing/react";
import { render, screen } from "@testing-library/react";
import axe from "axe-core";
import { cacheOptions, defaultOptions } from "./apollo";
import { Dashboard } from "./Dashboard";
import { ORG_METRICS } from "./queries";
import { metrics, previous, variables } from "./test-fixtures";

function renderWith(data: unknown, errors?: { message: string; path: string[] }[]) {
  return render(
    <MockedProvider
      defaultOptions={defaultOptions}
      mocks={[{ request: { query: ORG_METRICS, variables }, result: { data, errors } }]}
    >
      <Dashboard {...variables} names={new Map([["search", "Search"]])} onSelectOrg={() => {}} />
    </MockedProvider>,
  );
}

test("renders every section from one query", async () => {
  renderWith({ orgMetrics: metrics, previous });
  expect(await screen.findByRole("status")).toHaveTextContent("support: stale");
  for (const name of [
    "Insights",
    "Delivery (DORA)",
    "Reliability",
    "Incidents",
    "On-call",
    "SLOs",
    "Teams",
    "Support",
  ]) {
    expect(screen.getByRole("region", { name })).toBeInTheDocument();
  }
});

test("has no accessibility violations axe can find without a layout engine", async () => {
  const { container } = renderWith({ orgMetrics: metrics, previous });
  await screen.findByRole("status");
  const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  expect(results.violations.map((v) => `${v.id}: ${v.nodes[0]?.html}`)).toEqual([]);
});

test("a panel that failed to load says so instead of showing zero", async () => {
  renderWith({ orgMetrics: { ...metrics, delivery: null }, previous }, [
    { message: "boom", path: ["orgMetrics", "delivery"] },
  ]);
  expect(await screen.findByText("14 incidents, 1 open. Median time to resolve: 1.6 h.")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Delivery (DORA)" })).toHaveTextContent("Could not load.");
});

test("an insight id two orgs share never shows one org's insight on the other", async () => {
  // The API returns __typename, so Apollo would store {Insight, id} as one shared entity across orgs.
  const report = (orgId: string, title: string) => ({
    request: { query: ORG_METRICS, variables: { ...variables, orgId } },
    result: {
      data: {
        orgMetrics: {
          ...metrics,
          orgId,
          insights: [{ __typename: "Insight", id: "noisy-alert", level: "WARNING", title, detail: null }],
        },
        previous,
      },
    },
  });
  const view = (orgId: string) => (
    <MockedProvider
      cache={new InMemoryCache(cacheOptions)}
      defaultOptions={defaultOptions}
      mocks={[report("platform", "Platform alert"), report("search", "Search alert")]}
    >
      <Dashboard {...variables} orgId={orgId} names={new Map()} onSelectOrg={() => {}} />
    </MockedProvider>
  );
  const { rerender } = render(view("platform"));
  expect(await screen.findByText("Platform alert")).toBeInTheDocument();
  rerender(view("search"));
  expect(await screen.findByText("Search alert")).toBeInTheDocument();
  rerender(view("platform")); // served from the cache
  expect(await screen.findByText("Platform alert")).toBeInTheDocument();
});

test("unknown org renders a message, not a crash", async () => {
  renderWith({ orgMetrics: null, previous: null });
  expect(await screen.findByRole("alert")).toHaveTextContent("Unknown org.");
});
