import { customRange, lastDays } from "./window";

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
