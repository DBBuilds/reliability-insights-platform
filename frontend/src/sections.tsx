// Dashboard sections. Each leads with a one-line takeaway; detail sits behind it, collapsed.
// A section whose data is null failed to load and says so instead of showing zeros.
import { type ReactNode, useId } from "react";
import { Chart, DataTable, Heatmap, Sparkline, Table } from "./charts";
import { change, dateTime, doraLevels, minutes, objective, perDay, percent, shortDate } from "./format";
import type { OrgMetricsQuery } from "./gql/graphql";

export type Metrics = NonNullable<OrgMetricsQuery["orgMetrics"]>;
type Previous = OrgMetricsQuery["previous"];

const TONES: Record<string, string> = {
  CRITICAL: "critical",
  WARNING: "warning",
  INFO: "info",
  SEV1: "critical",
  SEV2: "serious",
  SEV3: "warning",
  OK: "good",
  BURNING: "warning",
  EXHAUSTED: "critical",
};
const sentence = (s: string) => s[0] + s.slice(1).toLowerCase();

/** A colored dot beside a text label: color never carries meaning alone. */
export function Badge({ value, label = sentence(value) }: { value: string; label?: string }) {
  return <span className={`badge tone-${TONES[value] ?? "none"}`}>{label}</span>;
}

export function Section(props: { title: string; takeaway: ReactNode; children?: ReactNode; open?: boolean }) {
  const id = useId();
  return (
    <section className="section" aria-labelledby={id}>
      <h2 id={id}>{props.title}</h2>
      {props.children ? (
        <details open={props.open}>
          <summary>{props.takeaway}</summary>
          {props.children}
        </details>
      ) : (
        <p>{props.takeaway}</p>
      )}
    </section>
  );
}

const failed = (title: string) => <Section title={title} takeaway="Could not load." />;
const week = (w: { weekStart: string | null; partial: boolean | null }) =>
  w.weekStart ? `${shortDate(w.weekStart)}${w.partial ? " (partial)" : ""}` : "";

export function Freshness({ syncs }: { syncs: Metrics["syncs"] }) {
  if (!syncs) return <p>Sync status could not load.</p>;
  const stale = syncs.filter((s) => s.stale);
  return (
    <div role="status">
      <ul className="syncs" aria-label="Data sources">
        {syncs.map((s) => (
          <li key={s.stream}>
            {s.stale ? (
              <Badge
                value="CRITICAL"
                label={`${s.stream}: stale${s.lastSyncedAt ? ` since ${dateTime(s.lastSyncedAt)}` : ", never synced"}`}
              />
            ) : (
              <Badge value="OK" label={`${s.stream}: synced`} />
            )}
          </li>
        ))}
      </ul>
      {stale.length > 0 && <p>Numbers from stale sources may read low.</p>}
    </div>
  );
}

export function Insights({ insights, staleShown }: { insights: Metrics["insights"]; staleShown: boolean }) {
  // The freshness row already says what is stale; don't repeat it here.
  const shown = insights.filter((i) => !(i.id === "stale-data" && staleShown));
  if (shown.length === 0) return <Section title="Insights" takeaway="Nothing needs attention." />;
  return (
    <section className="section" aria-label="Insights">
      <h2>Insights</h2>
      <ul className="insights">
        {shown.map((i) => (
          <li key={i.id}>
            <Badge value={i.level} /> <strong>{i.title}</strong>
            {i.detail && <span className="muted"> {i.detail}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Tile(props: {
  label: string;
  value: string;
  levels?: readonly string[] | null;
  delta: ReturnType<typeof change>;
  trend?: (number | null)[];
}) {
  const level = doraLevels(props.levels);
  return (
    <div className="tile">
      <span className="muted">{props.label}</span>
      <span className="value">{props.value}</span>
      {level && <span>{level}</span>}
      {props.delta && (
        <span>
          <span className={`delta-arrow ${props.delta.better ? "better" : "worse"}`} aria-hidden="true">
            {props.delta.up ? "▲" : "▼"}
          </span>{" "}
          {props.delta.pct}% {props.delta.better ? "better" : "worse"} than the previous period
        </span>
      )}
      {props.trend && <Sparkline values={props.trend} />}
    </div>
  );
}

export function Delivery({ m, previous }: { m: Metrics; previous: Previous }) {
  const d = m.delivery;
  if (!d) return failed("Delivery (DORA)");
  const p = previous?.delivery;
  const weeks = m.weekly ?? [];
  return (
    <section className="section" aria-label="Delivery (DORA)">
      <h2>Delivery (DORA)</h2>
      <div className="tiles">
        <Tile
          label="Deploys per service"
          value={perDay(d.deployFrequency?.value)}
          levels={d.deployFrequency?.levels2024}
          delta={change(d.deployFrequency?.value, p?.deployFrequency?.value, false)}
          trend={weeks.map((w) => w.deploys)}
        />
        <Tile
          label="Lead time"
          value={minutes(d.leadTime?.value)}
          levels={d.leadTime?.levels2024}
          delta={change(d.leadTime?.value, p?.leadTime?.value, true)}
          trend={weeks.map((w) => w.leadTime?.medianMinutes ?? null)}
        />
        <Tile
          label="Change failure rate"
          value={percent(d.changeFailureRate)}
          delta={change(d.changeFailureRate, p?.changeFailureRate, true)}
          trend={weeks.map((w) => w.changeFailureRate)}
        />
        <Tile
          label="Recovery from a failed deploy"
          value={minutes(d.recoveryTime?.value)}
          levels={d.recoveryTime?.levels2024}
          delta={change(d.recoveryTime?.value, p?.recoveryTime?.value, true)}
        />
      </div>
      <DataTable
        summary="Weekly numbers"
        head={["Week", "Deploys", "Change failure rate", "Lead time"]}
        rows={weeks.map((w) => [week(w), w.deploys, percent(w.changeFailureRate), minutes(w.leadTime?.medianMinutes)])}
      />
    </section>
  );
}

export function Reliability({ m }: { m: Metrics }) {
  const i = m.incidents;
  if (!i) return failed("Reliability");
  const weeks = m.weekly ?? [];
  const severities = i.bySeverity.map((s) => `${s.severity} ${s.count}`).join(", ");
  return (
    <Section
      title="Reliability"
      takeaway={`${i.total} incidents, ${i.open} open. Median time to resolve: ${minutes(i.timeToResolve?.medianMinutes)}.`}
    >
      <p>By severity: {severities}.</p>
      <div className="charts">
        <Chart
          title="Median time to detect and resolve, per week"
          x={weeks.map(week)}
          series={[
            {
              name: "Resolve",
              values: weeks.map((w) => w.timeToResolve?.medianMinutes ?? null),
              color: "var(--series-1)",
            },
            {
              name: "Detect",
              values: weeks.map((w) => w.timeToDetect?.medianMinutes ?? null),
              color: "var(--series-2)",
            },
          ]}
          band={{
            name: "Resolve, median to p90",
            low: weeks.map((w) => w.timeToResolve?.medianMinutes ?? null),
            high: weeks.map((w) => w.timeToResolve?.p90Minutes ?? null),
          }}
          format={minutes}
          tickUnit={60}
        />
        <Chart
          title="Incidents per week"
          kind="columns"
          x={weeks.map(week)}
          series={[{ name: "Incidents", values: weeks.map((w) => w.incidents), color: "var(--series-1)" }]}
          format={(v) => (Number.isInteger(v) ? String(v) : v.toFixed(1))}
        />
      </div>
    </Section>
  );
}

export function Incidents({ m }: { m: Metrics }) {
  const list = m.recentIncidents;
  if (!list) return failed("Incidents");
  if (list.length === 0) return <Section title="Incidents" takeaway="No incidents in this window." />;
  const open = list.filter((i) => !i.resolvedAt);
  const duration = (i: (typeof list)[number]) =>
    i.startedAt && i.resolvedAt ? (Date.parse(i.resolvedAt) - Date.parse(i.startedAt)) / 60_000 : null;
  const longest = Math.max(1, ...list.map((i) => duration(i) ?? 0));
  const name = (i: (typeof list)[number]) => i.title ?? i.service ?? i.id ?? "Incident";
  const takeaway = open[0]
    ? `Open now: ${name(open[0])}.`
    : `None open. Latest: ${name(list[0] as (typeof list)[number])}.`;
  return (
    <Section title="Incidents" takeaway={takeaway}>
      <p className="muted">The {list.length} most recent, newest first. Bars compare how long each took.</p>
      <ul className="incidents">
        {list.map((i) => (
          <li key={i.id}>
            <details>
              <summary>
                {i.severity && <Badge value={i.severity} label={i.severity} />} {name(i)}
                <span className="muted">
                  {" "}
                  {i.startedAt && dateTime(i.startedAt)}, {i.resolvedAt ? minutes(duration(i)) : "open"}
                </span>
                {duration(i) != null && (
                  <span
                    className="bar"
                    style={{ display: "block", width: `${((duration(i) as number) / longest) * 100}%` }}
                  />
                )}
              </summary>
              <p>
                Service: {i.service ?? "unknown"}. Detected: {i.detectedAt ? dateTime(i.detectedAt) : "unknown"}.
                Resolved: {i.resolvedAt ? dateTime(i.resolvedAt) : "not yet"}.
              </p>
            </details>
          </li>
        ))}
      </ul>
    </Section>
  );
}

export function OnCall({ m }: { m: Metrics }) {
  const o = m.onCall;
  if (!o) return failed("On-call");
  if (o.pages === 0) return <Section title="On-call" takeaway="No pages in this window." />;
  return (
    <Section
      title="On-call"
      takeaway={`${o.pages} pages, ${percent(o.offHoursPages / o.pages)} off-hours, ${percent(o.actionableShare)} of marked pages actionable.`}
    >
      <div className="charts">
        {o.byHour && (
          <Heatmap cells={o.byHour.map((c) => ({ weekday: c.weekday ?? 0, hour: c.hour ?? 0, pages: c.pages ?? 0 }))} />
        )}
        <div>
          <h3>Noisiest alerts, share of all pages</h3>
          <ol>
            {o.noisiestAlerts.map((a) => (
              <li key={a.alertName}>
                {a.alertName}: {percent(a.pages / o.pages)}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Section>
  );
}

export function Slos({ m }: { m: Metrics }) {
  const slos = m.slos;
  if (!slos) return failed("SLOs");
  if (slos.length === 0) return <Section title="SLOs" takeaway="No SLOs for this org." />;
  const ranked = [...slos].sort((a, b) => (a.budgetRemaining ?? 1) - (b.budgetRemaining ?? 1));
  const atRisk = slos.filter((s) => s.status !== "OK").length;
  return (
    <Section
      title="SLOs"
      takeaway={`${slos.length} SLOs, ${atRisk ? `${atRisk} burning or exhausted` : "none burning"}. Least budget left: ${ranked[0]?.service}.`}
    >
      <div className="charts">
        {ranked.map((s) => {
          const left = s.budgetRemaining;
          const tone = s.status === "EXHAUSTED" ? "critical" : left != null && left <= 0.25 ? "warning" : "";
          return (
            <div key={s.id}>
              <h3>
                {s.service}{" "}
                <span className="muted">
                  ({objective(s.objective)} good over {s.windowDays} days)
                </span>{" "}
                {s.status && <Badge value={s.status} />}
              </h3>
              <p>
                {left == null ? "No data" : `${percent(left)} of the error budget left`}. Burn rate:{" "}
                {s.burnRate1d ?? "no data"} today, {s.burnRate3d ?? "no data"} over 3 days (1 spends the budget
                exactly).
              </p>
              <div className={`meter ${tone && `tone-${tone}`}`} aria-hidden="true">
                <div style={{ width: `${Math.max(0, left ?? 0) * 100}%` }} />
              </div>
              <Chart
                title="Budget left by day"
                x={(s.daily ?? []).map((d) => (d.day ? shortDate(d.day) : ""))}
                series={[
                  {
                    name: "Budget left",
                    values: (s.daily ?? []).map((d) => d.budgetRemaining),
                    color: "var(--series-1)",
                  },
                ]}
                format={percent}
                height={120}
                endLabel={false}
              />
            </div>
          );
        })}
      </div>
    </Section>
  );
}

export function Teams({
  m,
  names,
  onSelect,
}: {
  m: Metrics;
  names: Map<string, string>;
  onSelect: (id: string) => void;
}) {
  const kids = m.children;
  if (!kids) return failed("Teams");
  if (kids.length === 0) return null;
  const busiest = [...kids].sort((a, b) => (b.incidents?.total ?? 0) - (a.incidents?.total ?? 0))[0];
  return (
    <Section
      title="Teams"
      takeaway={`${kids.length} teams. Most incidents: ${names.get(busiest?.orgId ?? "") ?? busiest?.orgId}.`}
    >
      <p className="muted">Select a team to open it.</p>
      <Table
        head={[
          "Team",
          "Incidents",
          "Open",
          "Median to resolve",
          "Deploys",
          "Change failure rate",
          "Pages",
          "Off-hours",
          "Stale data",
        ]}
        rows={kids.map((k) => [
          <button key={k.orgId} type="button" className="link" onClick={() => onSelect(k.orgId)}>
            {names.get(k.orgId) ?? k.orgId}
          </button>,
          k.incidents?.total ?? "Could not load",
          k.incidents?.open ?? "",
          minutes(k.incidents?.timeToResolve?.medianMinutes),
          k.delivery?.deploys ?? "Could not load",
          percent(k.delivery?.changeFailureRate),
          k.onCall?.pages ?? "Could not load",
          k.onCall?.pages ? percent(k.onCall.offHoursPages / k.onCall.pages) : "",
          k.staleSources.join(", ") || "None",
        ])}
      />
    </Section>
  );
}

export function Support({ m }: { m: Metrics }) {
  const s = m.support;
  if (!s) return failed("Support");
  return (
    <Section
      title="Support"
      takeaway={`${s.requests} requests. Median first response: ${minutes(s.firstResponse?.medianMinutes)}. Resolved: ${percent(s.resolutionRate)}.`}
    />
  );
}
