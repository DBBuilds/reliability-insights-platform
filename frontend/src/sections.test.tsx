import { fireEvent, render, screen } from "@testing-library/react";
import { Delivery, Freshness, Incidents, Insights, OnCall, Reliability, Slos, Support, Teams } from "./sections";
import { metrics, previous } from "./test-fixtures";

const without = (field: keyof typeof metrics) => ({ ...metrics, [field]: null });
const loadFailure = (ui: React.ReactElement) => {
  render(ui);
  expect(screen.getByText("Could not load.")).toBeInTheDocument();
};

test("freshness names stale sources with their last sync, and says what that means", () => {
  render(<Freshness syncs={metrics.syncs} />);
  expect(screen.getByRole("status")).toHaveTextContent("support: stale since Oct 14, 03:00 UTC");
  expect(screen.getByText("incidents: synced")).toBeInTheDocument();
  expect(screen.getByText("Numbers from stale sources may read low.")).toBeInTheDocument();
  expect(screen.getByText("Data updated Oct 26, 04:00 UTC.")).toBeInTheDocument(); // the newest sync
});

test("every metric explains itself behind a labeled toggle", () => {
  render(<Delivery m={metrics} previous={previous} />);
  expect(screen.getByLabelText("About change failure rate")).toBeInTheDocument();
  expect(
    screen.getByText(/deploys linked to at least one incident; a deploy that caused two counts once/),
  ).toBeInTheDocument();
  for (const Part of [Reliability, OnCall, Slos, Support]) render(<Part m={metrics} />);
  for (const name of ["reliability", "on-call", "SLOs", "support"]) {
    expect(screen.getByLabelText(`About ${name}`)).toBeInTheDocument();
  }
});

test("a source that never synced says so", () => {
  render(<Freshness syncs={[{ stream: "pages", lastSyncedAt: null, stale: true }]} />);
  expect(screen.getByText("pages: stale, never synced")).toBeInTheDocument();
});

test("insights skip the stale one the freshness row already shows, and label each level", () => {
  render(<Insights insights={metrics.insights} staleShown />);
  expect(screen.queryByText("Some data is stale")).not.toBeInTheDocument();
  expect(screen.getByText("Warning")).toBeInTheDocument();
  render(<Insights insights={[]} staleShown={false} />);
  expect(screen.getByText("Nothing needs attention.")).toBeInTheDocument();
});

test("delivery tiles show the value, its 2024 DORA levels, and real changes only", () => {
  render(<Delivery m={metrics} previous={previous} />);
  expect(screen.getByText("3.5 per week")).toBeInTheDocument();
  expect(screen.getByText("2024 DORA: High or Medium")).toBeInTheDocument();
  expect(screen.getByText(/30% better than the previous period/)).toBeInTheDocument(); // lead time 1800 to 1269 min
  expect(screen.getByText(/25% better/)).toBeInTheDocument(); // deploys 0.4 to 0.5 per day
  expect(screen.getAllByText(/than the previous period/)).toHaveLength(2); // recovery +4% and CFR flat: hidden
});

test("delivery with too little data says so instead of zero", () => {
  const sparse = { ...metrics.delivery!, leadTime: { value: null, levels2024: null } };
  render(<Delivery m={{ ...metrics, delivery: sparse }} previous={null} />);
  expect(screen.getByText("Not enough data")).toBeInTheDocument();
  loadFailure(<Delivery m={without("delivery")} previous={previous} />);
});

test("reliability leads with totals and the median, with charts behind it", () => {
  render(<Reliability m={metrics} />);
  expect(screen.getByText("14 incidents, 1 open. Median time to resolve: 1.6 h.")).toBeInTheDocument();
  expect(screen.getByText("By severity: SEV1 0, SEV2 5.")).toBeInTheDocument();
  expect(screen.getAllByRole("img")).toHaveLength(2);
  expect(screen.getByText("2.5")).toBeInTheDocument(); // count axis mid tick, not rounded to a misleading 3
  loadFailure(<Reliability m={without("incidents")} />);
});

test("incidents lead with what is open and expand to details", () => {
  render(<Incidents m={metrics} />);
  expect(screen.getByText("Open now: edge-proxy: partial outage.")).toBeInTheDocument();
  expect(screen.getByText(/Oct 20, 19:00 UTC, 1.5 h/)).toBeInTheDocument();
  expect(screen.getByText(/Resolved: not yet/)).toBeInTheDocument();
  render(<Incidents m={{ ...metrics, recentIncidents: [] }} />);
  expect(screen.getByText("No incidents in this window.")).toBeInTheDocument();
  loadFailure(<Incidents m={without("recentIncidents")} />);
});

test("on-call shows shares, not counts already in an insight", () => {
  render(<OnCall m={metrics} />);
  expect(screen.getByText("400 pages, 60% off-hours, 48% of marked pages actionable.")).toBeInTheDocument();
  expect(screen.getByText("NodeDiskPressure: 33%")).toBeInTheDocument();
  loadFailure(<OnCall m={without("onCall")} />);
});

test("SLOs lead with the one closest to running out", () => {
  render(<Slos m={metrics} />);
  expect(screen.getByText("2 SLOs, none burning. Least budget left: auth.")).toBeInTheDocument();
  expect(screen.getByText(/12% of the error budget left/)).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 3 })[0]).toHaveTextContent("auth (99.9% good over 30 days) Ok"); // lowest first
  render(<Slos m={{ ...metrics, slos: [] }} />);
  expect(screen.getByText("No SLOs for this org.")).toBeInTheDocument();
  loadFailure(<Slos m={without("slos")} />);
});

test("teams compare children and open one on click; a team with no children shows nothing", () => {
  const onSelect = vi.fn();
  const names = new Map([
    ["payments", "Payments"],
    ["search", "Search"],
  ]);
  render(<Teams m={metrics} names={names} onSelect={onSelect} />);
  expect(screen.getByText("2 teams. Most incidents: Search.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSelect).toHaveBeenCalledWith("search");
  expect(
    render(<Teams m={{ ...metrics, children: [] }} names={names} onSelect={onSelect} />).container,
  ).toBeEmptyDOMElement();
});

test("counts of one read naturally", () => {
  const one = { ...metrics, incidents: { ...metrics.incidents!, total: 1, open: 0 }, slos: metrics.slos!.slice(0, 1) };
  render(<Reliability m={one} />);
  expect(screen.getByText(/^1 incident, 0 open\./)).toBeInTheDocument();
  render(<Slos m={one} />);
  expect(screen.getByText("1 SLO, none burning.")).toBeInTheDocument();
});

test("support is one line", () => {
  render(<Support m={metrics} />);
  expect(screen.getByText("117 requests. Median first response: 25 min. Resolved: 89%.")).toBeInTheDocument();
  loadFailure(<Support m={without("support")} />);
});
