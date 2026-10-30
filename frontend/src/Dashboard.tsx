import { useQuery } from "@apollo/client/react";
import { ORG_METRICS } from "./queries";
import { Delivery, Freshness, Incidents, Insights, OnCall, Reliability, Slos, Support, Teams } from "./sections";

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
      <Freshness syncs={m.syncs} />
      <Insights insights={m.insights} staleShown={staleShown} />
      <Delivery m={m} previous={shown.previous} />
      <Reliability m={m} />
      <Incidents m={m} />
      <OnCall m={m} />
      <Slos m={m} />
      <Teams m={m} names={names} onSelect={onSelectOrg} />
      <Support m={m} />
    </div>
  );
}
