import { useState } from "react";
import type { View } from "./url";
import { customRange, lastDayOf, MAX_MONTHS, monthRange, PRESETS, type Window } from "./window";

type Props = {
  view: View;
  window: Window;
  latest: string; // the latest complete day, "YYYY-MM-DD"
  months?: string[]; // the static demo: custom ranges are these whole months ("YYYY-MM")
  onChange: (change: Partial<View>) => void;
};

const monthLabel = (m: string) =>
  new Date(`${m}-01T00:00:00Z`).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });

/** Window presets plus a custom range: any dates with the API, whole months on the static demo. */
export function WindowPicker({ view, window, latest, months, onChange }: Props) {
  const custom = Boolean(view.from && view.to);
  const today = new Date(Date.parse(`${latest}T00:00:00Z`) + 86_400_000); // the day after the latest complete one
  const [draft, setDraft] = useState({ from: view.from, to: view.to });
  const [problem, setProblem] = useState("");
  // When the view changes from outside (Back, a preset, a link), take its dates. Adjusting state during render,
  // not remounting, keeps focus in a date field while someone types.
  const [shown, setShown] = useState(view);
  if (shown.from !== view.from || shown.to !== view.to) {
    setShown(view);
    setDraft({ from: view.from, to: view.to });
    setProblem("");
  }
  const apply = (next: typeof draft, result: Window | { from: string; to: string } | string) => {
    setDraft(next);
    setProblem(typeof result === "string" ? result : "");
    if (typeof result !== "string") onChange(next);
  };
  const editDates = (change: Partial<typeof draft>) => {
    const next = { ...draft, ...change };
    apply(next, customRange(next.from, next.to, today));
  };
  // Moving one end of a month range pulls the other along (same order, at most MAX_MONTHS), so it never dead-ends.
  const editMonths = (side: "from" | "to", month: string) => {
    const list = months ?? [];
    const at = (m: string) => Math.max(0, list.indexOf(m));
    let [a, b] = [at(draft.from.slice(0, 7)), at(draft.to.slice(0, 7))];
    if (side === "from") {
      a = at(month);
      b = Math.min(Math.max(b, a), a + MAX_MONTHS - 1);
    } else {
      b = at(month);
      a = Math.max(Math.min(a, b), b - MAX_MONTHS + 1);
    }
    const result = monthRange(list[a] as string, list[b] as string);
    if (typeof result !== "string") apply(result, result);
  };
  const startCustom = () => {
    const last = months?.at(-1);
    const range = months && last ? monthRange(months[Math.max(0, months.length - 3)] as string, last) : null;
    onChange(range && typeof range !== "string" ? range : { from: window.start, to: lastDayOf(window) });
  };

  return (
    <>
      <label>
        Window{" "}
        <select
          value={custom ? "custom" : String(view.days)}
          onChange={(e) =>
            e.target.value === "custom" ? startCustom() : onChange({ days: Number(e.target.value), from: "", to: "" })
          }
        >
          {PRESETS.map((d) => (
            <option key={d} value={d}>
              Last {d} days
            </option>
          ))}
          <option value="custom">Custom range</option>
        </select>
      </label>
      {custom && months && (
        <>
          {(["from", "to"] as const).map((side) => (
            <label key={side}>
              {side === "from" ? "From" : "To"}{" "}
              <select value={draft[side].slice(0, 7)} onChange={(e) => editMonths(side, e.target.value)}>
                {months.map((m) => (
                  <option key={m} value={m}>
                    {monthLabel(m)}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </>
      )}
      {custom && !months && (
        <>
          <label>
            From{" "}
            <input
              type="date"
              value={draft.from}
              min="2000-01-01"
              max={latest}
              onChange={(e) => editDates({ from: e.target.value })}
            />
          </label>
          <label>
            To{" "}
            <input
              type="date"
              value={draft.to}
              min="2000-01-01"
              max={latest}
              onChange={(e) => editDates({ to: e.target.value })}
            />
          </label>
        </>
      )}
      {custom && <span aria-live="polite">{problem}</span>}
    </>
  );
}
