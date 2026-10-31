import { change, dateTime, doraLevels, fullDate, minutes, objective, percent, perDay, shortDate } from "./format";
import { completeWeeks } from "./window";

test("minutes formats and says when there is too little data", () => {
  expect(minutes(null)).toBe("Not enough data");
  expect(minutes(45)).toBe("45 min");
  expect(minutes(150)).toBe("2.5 h");
  expect(minutes(60 * 72)).toBe("3.0 d");
});

test("percent", () => {
  expect(percent(0.0556)).toBe("6%");
  expect(percent(undefined)).toBe("No data");
});

test("objective keeps its nines", () => {
  expect(objective(0.999)).toBe("99.9%");
  expect(objective(0.9995)).toBe("99.95%");
  expect(percent(0.999)).toBe("100%"); // why percent() is wrong here
});

test("perDay switches to per week under one a day", () => {
  expect(perDay(2.04)).toBe("2.0 per day");
  expect(perDay(0.5)).toBe("3.5 per week");
  expect(perDay(null)).toBe("No deploys");
});

test("doraLevels names overlaps and gaps", () => {
  expect(doraLevels(["HIGH", "MEDIUM"])).toBe("2024 DORA: High or Medium");
  expect(doraLevels([])).toBe("Between 2024 DORA levels");
  expect(doraLevels(null)).toBeNull();
});

test("change ignores small moves and knows which way is better", () => {
  expect(change(105, 100, true)).toBeNull(); // 5%: not worth showing
  expect(change(1269, 1800, true)).toEqual({ pct: 30, up: false, better: true }); // lead time fell 29.5%
  expect(change(2331, 1800, true)).toEqual({ pct: 30, up: true, better: false }); // rose 29.5%: same rounding
  expect(change(0.4, 0.5, false)).toEqual({ pct: 20, up: false, better: false }); // deploys fell
  expect(change(1, null, true)).toBeNull();
  expect(change(1, 0, true)).toBeNull();
});

test("dates read in UTC", () => {
  expect(dateTime("2026-10-20T14:00:00-05:00")).toBe("Oct 20, 19:00 UTC");
  expect(shortDate("2026-10-05")).toBe("Oct 5");
  expect(fullDate("2026-10-26T06:00:00+00:00")).toBe("Oct 26, 2026");
});

test("completeWeeks ends on the Monday of the current week", () => {
  // Wednesday 2026-10-14 -> window Sep 14 to Oct 12, previous window starts Aug 17
  expect(completeWeeks(4, new Date("2026-10-14T15:00:00Z"))).toEqual({
    start: "2026-09-14",
    end: "2026-10-12",
    previousStart: "2026-08-17",
  });
  // A Monday is itself the end of the last complete week
  expect(completeWeeks(1, new Date("2026-10-12T00:30:00Z"))).toMatchObject({ start: "2026-10-05", end: "2026-10-12" });
});
