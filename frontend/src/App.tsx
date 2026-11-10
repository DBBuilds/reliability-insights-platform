import { useQuery } from "@apollo/client/react";
import { useEffect, useState } from "react";
import { Dashboard } from "./Dashboard";
import { dateRange } from "./format";
import type { OrgsQuery } from "./gql/graphql";
import { ORGS } from "./queries";
import { setTheme, storedTheme, THEMES, type Theme } from "./theme";
import { demoAsOf } from "./demo";
import { urlForView, type View, viewFromUrl } from "./url";
import { WindowPicker } from "./WindowPicker";
import { customRange, demoMonths, isDemoRange, lastDayOf, lastDays, latestDay } from "./window";

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
  // The org and window live in the URL, so any view can be bookmarked or shared; Back steps through them.
  const [view, setView] = useState(() => viewFromUrl(window.location.search));
  const [theme, pickTheme] = useState(storedTheme);
  useEffect(() => {
    const onBack = () => setView(viewFromUrl(window.location.search));
    window.addEventListener("popstate", onBack);
    return () => window.removeEventListener("popstate", onBack);
  }, []);
  const go = (change: Partial<View>) => {
    const next = { ...view, ...change };
    setView(next);
    // Adjusting a custom range replaces the entry, so Back doesn't step through every keystroke.
    const editingRange = Boolean(view.from && view.to && next.from && next.to && next.org === view.org);
    window.history[editingRange ? "replaceState" : "pushState"](
      null,
      "",
      `${window.location.pathname}${urlForView(next)}`,
    );
  };
  // A valid custom range wins over the preset. The static demo can answer only the whole-month ranges it
  // exported, so any other range in a link falls back to the preset there.
  // Demo data stops at its snapshot, so both demo modes count windows back from it (`make demo` sets VITE_AS_OF).
  const pinned = demoAsOf || import.meta.env.VITE_AS_OF;
  const today = pinned ? new Date(pinned) : new Date();
  const months = demoAsOf ? demoMonths(today) : undefined;
  const answerable = view.from && view.to && (!months || isDemoRange(view.from, view.to, months));
  const range = answerable ? customRange(view.from, view.to, today) : null;
  const current = range && typeof range !== "string" ? range : lastDays(view.days, today);
  const { start, end, previousStart } = current;
  const tree = orgTree(data?.orgs ?? []);
  const selected = view.org || tree[0]?.id || "";

  return (
    <main>
      <header>
        <h1>Reliability Insights</h1>
        <label>
          Org{" "}
          <select value={selected} onChange={(e) => go({ org: e.target.value })} disabled={loading}>
            {tree.map((o) => (
              <option key={o.id} value={o.id}>
                {"   ".repeat(o.depth)}
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <WindowPicker view={view} window={current} latest={latestDay(today)} months={months} onChange={go} />
        <span className="muted">{dateRange(start, lastDayOf(current))}, UTC</span>
        <div className="aside">
          {demoAsOf && <strong>Demo with synthetic data</strong>}
          <label>
            Theme{" "}
            <select
              value={theme}
              onChange={(e) => {
                const next = e.target.value as Theme;
                setTheme(next);
                pickTheme(next);
              }}
            >
              {THEMES.map((t) => (
                <option key={t} value={t}>
                  {t[0]?.toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>
      {error && <p role="alert">Could not load orgs: {error.message}</p>}
      {selected && (
        <Dashboard
          orgId={selected}
          start={start}
          end={end}
          previousStart={previousStart}
          names={new Map(tree.map((o) => [o.id, o.name]))}
          onSelectOrg={(org) => go({ org })}
        />
      )}
    </main>
  );
}
