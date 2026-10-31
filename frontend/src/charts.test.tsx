import { fireEvent, render, screen, within } from "@testing-library/react";
import { Chart, Heatmap, Sparkline } from "./charts";

const chart = (
  <Chart
    title="Median time to resolve"
    x={["Oct 5", "Oct 12", "Oct 19"]}
    series={[
      { name: "Resolve", values: [90, null, 120], color: "red" },
      { name: "Detect", values: [9, 8, 7], color: "blue" },
    ]}
    format={(v) => `${v} min`}
  />
);

test("a line chart reads out every series by keyboard, starting at the latest point", () => {
  render(chart);
  const plot = screen.getByRole("img", { name: /Median time to resolve/ });
  fireEvent.focus(plot);
  expect(document.querySelector(".readout")).toHaveTextContent("Oct 19: 120 min resolve 7 min detect");
  fireEvent.keyDown(plot, { key: "ArrowLeft" });
  expect(document.querySelector(".readout")).toHaveTextContent("Oct 12: no data resolve 8 min detect");
});

test("every chart has a table with the same values, and a legend for two series", () => {
  render(chart);
  expect(screen.getByText("Resolve", { selector: ".legend span" })).toBeInTheDocument();
  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("row")).toHaveLength(4);
  expect(within(table).getByRole("row", { name: /Oct 12/ })).toHaveTextContent("Oct 128 min");
});

test("columns draw nothing for zero or missing weeks", () => {
  const { container } = render(
    <Chart
      title="Incidents"
      kind="columns"
      x={["a", "b", "c"]}
      series={[{ name: "n", values: [2, 0, null], color: "red" }]}
      format={String}
    />,
  );
  expect(container.querySelectorAll("svg path")).toHaveLength(1);
});

test("the heatmap reads out a hovered cell and lists every cell in its table", () => {
  const { container } = render(<Heatmap cells={[{ weekday: 1, hour: 2, pages: 12 }]} />);
  const cells = container.querySelectorAll("rect");
  expect(cells).toHaveLength(168);
  fireEvent.pointerEnter(cells[24 + 2] as Element); // Tuesday 02:00
  expect(document.querySelector(".readout")).toHaveTextContent("Tue 02:00: 12 pages");
  expect(screen.getByRole("row", { name: /^Tue/ })).toHaveTextContent("Tue001200");
});

test("a sparkline needs two points", () => {
  expect(render(<Sparkline values={[null, 3]} />).container).toBeEmptyDOMElement();
});
