import { urlForView, viewFromUrl } from "./url";

test("a view round-trips through the URL, leaving defaults out", () => {
  expect(urlForView({ org: "checkout", weeks: 13 })).toBe("?org=checkout&weeks=13");
  expect(viewFromUrl("?org=checkout&weeks=13")).toEqual({ org: "checkout", weeks: 13 });
  expect(urlForView({ org: "", weeks: 4 })).toBe("");
});

test("missing or unknown values fall back to the defaults", () => {
  expect(viewFromUrl("")).toEqual({ org: "", weeks: 4 });
  expect(viewFromUrl("?weeks=5")).toEqual({ org: "", weeks: 4 }); // not a preset
  expect(viewFromUrl("?weeks=abc&org=")).toEqual({ org: "", weeks: 4 });
});
