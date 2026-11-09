import { useState } from "react";
import type { View } from "./url";
import { customRange, lastDayOf, PRESETS, type Window } from "./window";

type Props = {
  view: View;
  window: Window;
  latest: string; // the latest complete day, "YYYY-MM-DD"
  allowCustom: boolean; // the static demo can only answer its presets
  onChange: (change: Partial<View>) => void;
};

/** Window presets, plus a custom range that applies once both dates are valid. */
export function WindowPicker({ view, window, latest, allowCustom, onChange }: Props) {
  const custom = allowCustom && Boolean(view.from && view.to);
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
  const edit = (change: Partial<typeof draft>) => {
    const next = { ...draft, ...change };
    setDraft(next);
    const result = customRange(next.from, next.to, today);
    setProblem(typeof result === "string" ? result : "");
    if (typeof result !== "string") onChange(next);
  };

  return (
    <>
      <label>
        Window{" "}
        <select
          value={custom ? "custom" : String(view.days)}
          onChange={(e) =>
            e.target.value === "custom"
              ? onChange({ from: window.start, to: lastDayOf(window) })
              : onChange({ days: Number(e.target.value), from: "", to: "" })
          }
        >
          {PRESETS.map((d) => (
            <option key={d} value={d}>
              Last {d} days
            </option>
          ))}
          {allowCustom && <option value="custom">Custom range</option>}
        </select>
      </label>
      {custom && (
        <>
          <label>
            From{" "}
            <input
              type="date"
              value={draft.from}
              min="2000-01-01"
              max={latest}
              onChange={(e) => edit({ from: e.target.value })}
            />
          </label>
          <label>
            To{" "}
            <input
              type="date"
              value={draft.to}
              min="2000-01-01"
              max={latest}
              onChange={(e) => edit({ to: e.target.value })}
            />
          </label>
          <span aria-live="polite">{problem}</span>
        </>
      )}
    </>
  );
}
