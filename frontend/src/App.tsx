import { useQuery } from "@apollo/client/react";
import { useState } from "react";
import { Dashboard } from "./Dashboard";
import { fullDate, shortDate } from "./format";
import type { OrgsQuery } from "./gql/graphql";
import { ORGS } from "./queries";
import { demoAsOf } from "./demo";
import { completeWeeks, PRESETS } from "./window";

/** Orgs in tree order, each with its depth, so the picker can indent children under parents. */
export function orgTree(orgs: OrgsQuery["orgs"]): { id: string; name: string; depth: number }[] {
  const ids = new Set(orgs.map((o) => o.id));
  const out: { id: string; name: string; depth: number }[] = [];
  const walk = (parent: string | null, depth: number) => {
    for (const o of orgs.filter((x) => (x.parentId && ids.has(x.parentId) ? x.parentId : null) === parent)) {
      out.push({ id: o.id, name: o.name, depth });
      walk(o.id, depth + 1);
    }
  };
  walk(null, 0);
  return out;
}

export function App() {
  const { data, loading, error } = useQuery(ORGS);
  const [orgId, setOrgId] = useState("");
  const [weeks, setWeeks] = useState(4);
  const { start, end, previousStart } = completeWeeks(weeks, demoAsOf ? new Date(demoAsOf) : undefined);
  const tree = orgTree(data?.orgs ?? []);
  const selected = orgId || tree[0]?.id || "";
  const lastDay = new Date(Date.parse(`${end}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10);

  return (
    <main>
      <header>
        <h1>Reliability Insights</h1>
        <label>
          Org{" "}
          <select value={selected} onChange={(e) => setOrgId(e.target.value)} disabled={loading}>
            {tree.map((o) => (
              <option key={o.id} value={o.id}>
                {"   ".repeat(o.depth)}
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Window{" "}
          <select value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>
            {PRESETS.map((w) => (
              <option key={w} value={w}>
                Last {w} complete weeks
              </option>
            ))}
          </select>
        </label>
        <span className="muted">
          {shortDate(start)} to {shortDate(lastDay)}, UTC
        </span>
        {demoAsOf && <strong>Demo data as of {fullDate(demoAsOf)}</strong>}
      </header>
      {error && <p role="alert">Could not load orgs: {error.message}</p>}
      {selected && (
        <Dashboard
          orgId={selected}
          start={start}
          end={end}
          previousStart={previousStart}
          names={new Map(tree.map((o) => [o.id, o.name]))}
          onSelectOrg={setOrgId}
        />
      )}
    </main>
  );
}
