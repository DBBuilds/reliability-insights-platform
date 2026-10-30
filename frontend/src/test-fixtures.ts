// One realistic org report for UI tests: 4 complete weeks, a stale source, an open incident.
// No __typename fields: the Apollo cache doesn't need them here, and the generated types don't declare them.
import type { OrgMetricsQuery } from "./gql/graphql";

export const variables = { orgId: "eng", start: "2026-09-28", end: "2026-10-26", previousStart: "2026-08-31" };

const weeks = ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"];
const stat = (medianMinutes: number | null, p90Minutes: number | null = null) => ({
  medianMinutes,
  p90Minutes,
});
const dora = (value: number | null, levels2024: ("ELITE" | "HIGH" | "MEDIUM" | "LOW")[] | null) => ({
  value,
  levels2024,
});

export const metrics: NonNullable<OrgMetricsQuery["orgMetrics"]> = {
  orgId: "eng",
  syncs: [
    { stream: "incidents", lastSyncedAt: "2026-10-26T04:00:00+00:00", stale: false },
    { stream: "support", lastSyncedAt: "2026-10-14T03:00:00+00:00", stale: true },
  ],
  insights: [
    { id: "stale-data", level: "CRITICAL", title: "Some data is stale", detail: null },
    { id: "noisy-alert", level: "WARNING", title: "'IndexLag' paged 75 times", detail: "Tune it." },
  ],
  delivery: {
    deploys: 217,
    changeFailureRate: 0.03,
    deployFrequency: dora(0.5, ["HIGH"]),
    leadTime: dora(1269, ["ELITE"]),
    recoveryTime: dora(99, ["HIGH", "MEDIUM"]),
  },
  weekly: weeks.map((weekStart, i) => ({
    weekStart,
    partial: false,
    deploys: 50 + i,
    changeFailureRate: 0.02 * (i + 1),
    leadTime: stat(1200 + 10 * i),
    incidents: i + 2,
    timeToDetect: stat(9),
    timeToResolve: stat(i === 0 ? null : 90 + 10 * i, i === 0 ? null : 280),
  })),
  incidents: {
    total: 14,
    open: 1,
    bySeverity: [
      { severity: "SEV1", count: 0 },
      { severity: "SEV2", count: 5 },
    ],
    timeToResolve: stat(96, 288),
  },
  recentIncidents: [
    {
      id: "platform-i11",
      severity: "SEV3",
      service: "edge-proxy",
      title: "edge-proxy: partial outage",
      startedAt: "2026-10-25T15:30:00+00:00",
      detectedAt: "2026-10-25T15:38:00+00:00",
      resolvedAt: null,
    },
    {
      id: "checkout-i23",
      severity: "SEV2",
      service: "cart",
      title: "cart: latency above target",
      startedAt: "2026-10-20T14:00:00-05:00",
      detectedAt: "2026-10-20T14:07:00-05:00",
      resolvedAt: "2026-10-20T15:30:00-05:00",
    },
  ],
  onCall: {
    pages: 400,
    offHoursPages: 240,
    actionableShare: 0.48,
    noisiestAlerts: [{ alertName: "NodeDiskPressure", pages: 132 }],
    byHour: [
      { weekday: 0, hour: 2, pages: 12 },
      { weekday: 1, hour: 10, pages: 3 },
    ],
  },
  slos: [
    {
      id: "payments-payments-api",
      service: "payments-api",
      objective: 0.999,
      windowDays: 30,
      budgetRemaining: 0.63,
      burnRate1d: 0.3,
      burnRate3d: 0.35,
      status: "OK",
      daily: [{ day: "2026-10-25", budgetRemaining: 0.63 }],
    },
    {
      id: "identity-auth",
      service: "auth",
      objective: 0.999,
      windowDays: 30,
      budgetRemaining: 0.12,
      burnRate1d: 0.24,
      burnRate3d: 0.38,
      status: "OK",
      daily: [
        { day: "2026-09-26", budgetRemaining: 0.9 },
        { day: "2026-10-25", budgetRemaining: 0.12 },
      ],
    },
  ],
  support: { requests: 117, resolutionRate: 0.89, firstResponse: stat(25) },
  children: [
    {
      orgId: "payments",
      staleSources: [],
      incidents: { total: 3, open: 0, timeToResolve: stat(132) },
      delivery: { deploys: 40, changeFailureRate: 0.025 },
      onCall: { pages: 50, offHoursPages: 15 },
    },
    {
      orgId: "search",
      staleSources: ["support"],
      incidents: { total: 5, open: 0, timeToResolve: stat(84) },
      delivery: { deploys: 49, changeFailureRate: 0.04 },
      onCall: { pages: 120, offHoursPages: 90 },
    },
  ],
};

export const previous: OrgMetricsQuery["previous"] = {
  delivery: {
    changeFailureRate: 0.03,
    deployFrequency: { value: 0.4 },
    leadTime: { value: 1800 },
    recoveryTime: { value: 95 },
  },
};
