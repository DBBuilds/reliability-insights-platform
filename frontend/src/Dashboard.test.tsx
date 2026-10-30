import { MockedProvider } from "@apollo/client/testing/react";
import { render, screen } from "@testing-library/react";
import axe from "axe-core";
import { defaultOptions } from "./apollo";
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

test("unknown org renders a message, not a crash", async () => {
  renderWith({ orgMetrics: null, previous: null });
  expect(await screen.findByRole("alert")).toHaveTextContent("Unknown org.");
});
