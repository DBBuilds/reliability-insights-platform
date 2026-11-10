import { useQuery } from "@apollo/client/react";
import { ORG_METRICS } from "./queries";
import { Delivery, Freshness, Guard, Incidents, Insights, OnCall, Reliability, Slos, Support, Teams } from "./sections";

type Props = {
  orgId: string;
  start: string;
  end: string;
  previousStart: string;
  names: Map<string, string>;
  onSelectOrg: (id: string) => void;
};

export function Dashboard({ orgId, start, end, previousStart, names, onSelectOrg }: Props) {
  const { data, previousData, loading, error } = useQuery(ORG_METRICS, {
    variables: { orgId, start, end, previousStart },
  });
  // While a new org or window loads, keep the last render, dimmed, instead of flashing.
  const shown = data ?? previousData;
  if (!shown) return loading ? <p>Loading…</p> : <p role="alert">Could not load metrics: {error?.message}</p>;
  const m = shown.orgMetrics;
  if (!m) return <p role="alert">{error ? `Could not load metrics: ${error.message}` : "Unknown org."}</p>;
  const staleShown = (m.syncs ?? []).some((s) => s.stale);

  return (
    <div className={loading ? "refreshing" : undefined} aria-busy={loading}>
      <Guard title="Data sources" data={m}>
        <Freshness syncs={m.syncs} />
      </Guard>
      <Guard title="Insights" data={m}>
        <Insights insights={m.insights} staleShown={staleShown} />
      </Guard>
      <Guard title="Delivery (DORA)" data={m}>
        <Delivery m={m} previous={shown.previous} />
      </Guard>
      <Guard title="Reliability" data={m}>
        <Reliability m={m} />
      </Guard>
      <Guard title="Incidents" data={m}>
        <Incidents m={m} />
      </Guard>
      <Guard title="On-call" data={m}>
        <OnCall m={m} />
      </Guard>
      <Guard title="SLOs" data={m}>
        <Slos m={m} />
      </Guard>
      <Guard title="Teams" data={m}>
        <Teams m={m} names={names} onSelect={onSelectOrg} />
      </Guard>
      <Guard title="Support" data={m}>
        <Support m={m} />
      </Guard>
    </div>
  );
}
