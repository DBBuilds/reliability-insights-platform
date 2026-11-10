import { customRange, demoMonths, isDemoRange, lastDays, monthRange } from "./window";

test("lastDays ends at the latest complete UTC day and keeps a same-length previous window", () => {
  // Monday 2026-10-26, 06:00 UTC: Oct 25 is the latest complete day.
  expect(lastDays(30, new Date("2026-10-26T06:00:00Z"))).toEqual({
    start: "2026-09-26",
    end: "2026-10-26",
    previousStart: "2026-08-27",
  });
  // Late evening in a US time zone is already the next day in UTC; the window follows UTC.
  expect(lastDays(1, new Date("2026-10-25T23:30:00-07:00"))).toMatchObject({ start: "2026-10-25", end: "2026-10-26" });
});

test("customRange turns inclusive dates into a window, or explains what's wrong", () => {
  const today = new Date("2026-10-26T06:00:00Z");
  expect(customRange("2026-01-01", "2026-03-31", today)).toEqual({
    start: "2026-01-01",
    end: "2026-04-01",
    previousStart: "2025-10-03", // 90 days before Jan 1
  });
  expect(customRange("2026-03-01", "2026-02-01", today)).toBe("The start must be on or before the end.");
  expect(customRange("2025-01-01", "2026-03-01", today)).toBe("Pick 366 days or fewer.");
  expect(customRange("2026-10-20", "2026-10-26", today)).toBe("The latest complete day is Oct 25, 2026.");
  expect(customRange("", "2026-03-01", today)).toBe("Pick both dates.");
  expect(customRange("2026-02-30", "2026-03-01", today)).toBe("Pick both dates."); // not a real date
});

test("demoMonths lists the complete months inside the demo data, like the exporter", () => {
  // backend/tests/test_export_demo.py pins the same first and last month.
  const months = demoMonths(new Date("2026-10-26T06:00:00Z"));
  expect([months[0], months.at(-1), months.length]).toEqual(["2024-11", "2026-09", 23]);
});

test("monthRange turns whole months into inclusive dates, up to 12 months", () => {
  expect(monthRange("2025-01", "2025-03")).toEqual({ from: "2025-01-01", to: "2025-03-31" });
  expect(monthRange("2024-02", "2024-02")).toEqual({ from: "2024-02-01", to: "2024-02-29" }); // leap year
  expect(monthRange("2025-03", "2025-01")).toBe("The start must be on or before the end.");
  expect(monthRange("2025-01", "2026-01")).toBe("Pick 12 months or fewer.");
});

test("the demo answers only whole-month ranges it exported", () => {
  const months = demoMonths(new Date("2026-10-26T06:00:00Z"));
  expect(isDemoRange("2025-01-01", "2025-03-31", months)).toBe(true);
  expect(isDemoRange("2025-01-02", "2025-03-31", months)).toBe(false); // not a month start
  expect(isDemoRange("2025-01-01", "2026-01-31", months)).toBe(false); // 13 months
  expect(isDemoRange("2024-10-01", "2024-12-31", months)).toBe(false); // before the data
});
