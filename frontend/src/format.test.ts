import { minutes, percent } from "./format";
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

test("completeWeeks ends on the Monday of the current week", () => {
  // Wednesday 2026-10-14 -> window Sep 14 to Oct 12
  expect(completeWeeks(4, new Date("2026-10-14T15:00:00Z"))).toEqual({ start: "2026-09-14", end: "2026-10-12" });
  // A Monday is itself the end of the last complete week
  expect(completeWeeks(1, new Date("2026-10-12T00:30:00Z"))).toEqual({ start: "2026-10-05", end: "2026-10-12" });
});
