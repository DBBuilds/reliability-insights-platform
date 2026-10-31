import { ApolloClient, InMemoryCache } from "@apollo/client";
import { defaultOptions } from "./apollo";
import { demoKey, demoLink } from "./demo";
import { ORGS, ORG_METRICS } from "./queries";

const client = () => new ApolloClient({ link: demoLink, cache: new InMemoryCache(), defaultOptions });

afterEach(() => vi.unstubAllGlobals());

test("demoKey matches the backend exporter", () => {
  // backend/tests/test_export_demo.py pins the same strings.
  const variables = { orgId: "eng", start: "2026-09-28", end: "2026-10-26", previousStart: "2026-08-31" };
  expect(demoKey("OrgMetrics", variables)).toBe("OrgMetrics/2026-10-26_eng_2026-08-31_2026-09-28");
  expect(demoKey("Orgs", {})).toBe("Orgs");
});

test("the demo answers from the exported file", async () => {
  const fetch = vi.fn(async () =>
    Response.json({ data: { orgs: [{ id: "eng", name: "Engineering", parentId: null }] } }),
  );
  vi.stubGlobal("fetch", fetch);
  const { data } = await client().query({ query: ORGS });
  expect(fetch).toHaveBeenCalledWith("/demo/Orgs.json");
  expect(data?.orgs[0]?.name).toBe("Engineering");
});

test("a choice the demo didn't export explains itself instead of showing a blank page", async () => {
  vi.stubGlobal("fetch", async () => new Response("<!doctype html>", { status: 404 }));
  const variables = { orgId: "eng", start: "2026-01-05", end: "2026-02-02", previousStart: "2025-12-08" };
  const { error } = await client().query({ query: ORG_METRICS, variables });
  expect(error?.message).toBe("This demo covers the last 4, 8, or 13 complete weeks before its snapshot.");
});
