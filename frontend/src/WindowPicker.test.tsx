import { fireEvent, render, screen } from "@testing-library/react";
import { WindowPicker } from "./WindowPicker";

const preset = { org: "eng", days: 30, from: "", to: "" };
const window = { start: "2026-09-26", end: "2026-10-26", previousStart: "2026-08-27" };

test("presets change the window, and custom starts from the window on screen", () => {
  const onChange = vi.fn();
  render(<WindowPicker view={preset} window={window} latest="2026-10-25" onChange={onChange} />);
  const select = screen.getByLabelText("Window");
  fireEvent.change(select, { target: { value: "365" } });
  expect(onChange).toHaveBeenLastCalledWith({ days: 365, from: "", to: "" });
  fireEvent.change(select, { target: { value: "custom" } });
  expect(onChange).toHaveBeenLastCalledWith({ from: "2026-09-26", to: "2026-10-25" });
});

test("custom dates apply only when valid, and say why when not", () => {
  const onChange = vi.fn();
  const custom = { ...preset, from: "2026-09-26", to: "2026-10-25" };
  render(<WindowPicker view={custom} window={window} latest="2026-10-25" onChange={onChange} />);
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-11-01" } });
  expect(onChange).not.toHaveBeenCalled();
  expect(screen.getByText("The start must be on or before the end.")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-07-01" } });
  expect(onChange).toHaveBeenLastCalledWith({ from: "2026-07-01", to: "2026-10-25" });
});

test("an outside change (Back, a preset) updates the dates without remounting, so typing keeps focus", () => {
  const a = { ...preset, from: "2026-09-26", to: "2026-10-25" };
  const ui = (view: typeof a) => <WindowPicker view={view} window={window} latest="2026-10-25" onChange={() => {}} />;
  const { rerender } = render(ui(a));
  const from = screen.getByLabelText("From");
  rerender(ui({ ...a, from: "2026-01-01", to: "2026-03-31" }));
  expect(screen.getByLabelText("From")).toBe(from); // same element: focus would survive
  expect(screen.getByLabelText("From")).toHaveValue("2026-01-01");
  expect(screen.getByLabelText("To")).toHaveValue("2026-03-31");
});

test("the demo offers whole months for a custom range, and explains invalid choices", () => {
  const onChange = vi.fn();
  const months = ["2026-07", "2026-08", "2026-09"];
  const custom = { ...preset, from: "2026-07-01", to: "2026-09-30" };
  render(<WindowPicker view={custom} window={window} latest="2026-10-25" months={months} onChange={onChange} />);
  expect(screen.getAllByRole("option", { name: /2026/ }).map((o) => o.textContent)).toContain("Aug 2026");
  fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-09" } });
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-08" } });
  expect(screen.getByText("The start must be on or before the end.")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-09" } });
  expect(onChange).toHaveBeenLastCalledWith({ from: "2026-09-01", to: "2026-09-30" });
});

test("choosing a custom range in the demo starts from its last three months", () => {
  const onChange = vi.fn();
  render(
    <WindowPicker
      view={preset}
      window={window}
      latest="2026-10-25"
      months={["2026-06", "2026-07", "2026-08", "2026-09"]}
      onChange={onChange}
    />,
  );
  fireEvent.change(screen.getByLabelText("Window"), { target: { value: "custom" } });
  expect(onChange).toHaveBeenLastCalledWith({ from: "2026-07-01", to: "2026-09-30" });
});
