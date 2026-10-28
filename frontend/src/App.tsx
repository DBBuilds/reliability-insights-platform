import { useQuery } from "@apollo/client/react";
import { useState } from "react";
import { Dashboard } from "./Dashboard";
import { ORGS } from "./queries";
import { completeWeeks } from "./window";

export function App() {
  const { data, loading, error } = useQuery(ORGS);
  const [orgId, setOrgId] = useState<string>("");
  const window = completeWeeks(4);
  const orgs = data?.orgs ?? [];
  const selected = orgId || orgs[0]?.id || "";

  return (
    <main>
      <header>
        <h1>Reliability Insights</h1>
        <label>
          Org{" "}
          <select value={selected} onChange={(e) => setOrgId(e.target.value)} disabled={loading}>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <span className="muted">
          {window.start} to {window.end} (last 4 complete weeks)
        </span>
      </header>
      {error && <p role="alert">Could not load orgs: {error.message}</p>}
      {selected && <Dashboard orgId={selected} start={window.start} end={window.end} />}
    </main>
  );
}
