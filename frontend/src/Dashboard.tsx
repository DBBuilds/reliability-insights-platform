import { useQuery } from "@apollo/client/react";
import { minutes, percent } from "./format";
import { ORG_METRICS } from "./queries";

type Props = { orgId: string; start: string; end: string };

export function Dashboard({ orgId, start, end }: Props) {
  const { data, loading, error } = useQuery(ORG_METRICS, { variables: { orgId, start, end } });
  if (loading && !data) return <p>Loading…</p>;
  const m = data?.orgMetrics;
  if (!m) return <p role="alert">{error ? `Could not load metrics: ${error.message}` : "Unknown org."}</p>;
  const ttr = m.incidents?.timeToResolve;
  // The stale banner already says it; don't repeat it as an insight.
  const insights = m.insights.filter((i) => !(i.id === "stale-data" && m.staleSources.length > 0));

  return (
    <section aria-label="metrics">
      {m.staleSources.length > 0 && (
        <p className="banner" role="status">
          Stale data: {m.staleSources.join(", ")}. These numbers may read low.
        </p>
      )}

      {insights.length > 0 && (
        <ul className="insights">
          {insights.map((i) => (
            <li key={i.id}>
              <span className={`dot ${i.level.toLowerCase()}`} aria-label={i.level} /> <strong>{i.title}</strong>
              {i.detail && <span className="muted"> {i.detail}</span>}
            </li>
          ))}
        </ul>
      )}

      <div className="cards">
        <Card title="Incidents" lead={`${m.incidents?.total ?? 0} total, ${m.incidents?.open ?? 0} open`}>
          <Row label="Median time to resolve" value={minutes(ttr?.medianMinutes)} />
          <Row label="p90 time to resolve" value={minutes(ttr?.p90Minutes)} />
          <Row label="Median time to detect" value={minutes(m.incidents?.timeToDetect?.medianMinutes)} />
        </Card>
        <Card title="Delivery" lead={`${m.delivery?.deploys ?? 0} deploys`}>
          <Row label="Change failure rate" value={percent(m.delivery?.changeFailureRate)} />
        </Card>
        <Card title="On-call" lead={`${m.onCall?.pages ?? 0} pages`}>
          <Row label="Off hours" value={String(m.onCall?.offHoursPages ?? 0)} />
          <Row label="Actionable" value={percent(m.onCall?.actionableShare)} />
        </Card>
        <Card title="Support" lead={`${m.support?.requests ?? 0} requests`}>
          <Row label="Median first response" value={minutes(m.support?.firstResponse?.medianMinutes)} />
          <Row label="Resolved" value={percent(m.support?.resolutionRate)} />
        </Card>
      </div>

      <details>
        <summary>Incidents per week</summary>
        <ul className="weeks">
          {(m.incidents?.weekly ?? []).map((w) => (
            <li key={w.weekStart} className={w.partial ? "partial" : undefined}>
              {w.weekStart}: {w.count}
              {w.partial && <span className="muted"> (partial week)</span>}
            </li>
          ))}
        </ul>
      </details>

      <details>
        <summary>Noisiest alerts</summary>
        <ol>
          {(m.onCall?.noisiestAlerts ?? []).map((a) => (
            <li key={a.alertName}>
              {a.alertName}: {a.pages} pages
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

function Card({ title, lead, children }: { title: string; lead: string; children: React.ReactNode }) {
  return (
    <article className="card">
      <h2>{title}</h2>
      <p className="lead">{lead}</p>
      <dl>{children}</dl>
    </article>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
