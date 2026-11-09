import { urlForView, viewFromUrl } from "./url";

test("a view round-trips through the URL, leaving defaults out", () => {
  expect(urlForView({ org: "checkout", days: 90, from: "", to: "" })).toBe("?org=checkout&days=90");
  expect(viewFromUrl("?org=checkout&days=90")).toEqual({ org: "checkout", days: 90, from: "", to: "" });
  expect(urlForView({ org: "", days: 30, from: "", to: "" })).toBe("");
});

test("a custom range round-trips, and wins over days", () => {
  const view = { org: "eng", days: 30, from: "2026-01-01", to: "2026-03-31" };
  expect(urlForView(view)).toBe("?org=eng&from=2026-01-01&to=2026-03-31");
  expect(viewFromUrl("?org=eng&from=2026-01-01&to=2026-03-31&days=90")).toEqual({ ...view, days: 90 });
});

test("missing or unknown values fall back to the defaults", () => {
  expect(viewFromUrl("")).toEqual({ org: "", days: 30, from: "", to: "" });
  expect(viewFromUrl("?days=45")).toEqual({ org: "", days: 30, from: "", to: "" }); // not a preset
  expect(viewFromUrl("?weeks=13&org=")).toEqual({ org: "", days: 30, from: "", to: "" }); // old links: default window
  expect(viewFromUrl("?from=2026-01-01")).toEqual({ org: "", days: 30, from: "", to: "" }); // half a range
  expect(viewFromUrl("?from=yesterday&to=today")).toEqual({ org: "", days: 30, from: "", to: "" });
});
