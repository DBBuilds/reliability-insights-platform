export function minutes(value: number | null | undefined): string {
  if (value == null) return "Not enough data";
  if (value < 60) return `${Math.round(value)} min`;
  const h = value / 60;
  return h < 48 ? `${h.toFixed(1)} h` : `${(h / 24).toFixed(1)} d`;
}

export function percent(value: number | null | undefined): string {
  return value == null ? "No data" : `${Math.round(value * 100)}%`;
}

/** Deploys per day, shown per week when under one a day. */
export function perDay(value: number | null | undefined): string {
  if (value == null) return "No deploys";
  return value >= 1 ? `${value.toFixed(1)} per day` : `${(value * 7).toFixed(1)} per week`;
}

/** "2024 DORA: High or Medium". The levels are survey clusters, so they are named, not colored. */
export function doraLevels(levels: readonly string[] | null | undefined): string | null {
  if (levels == null) return null;
  if (levels.length === 0) return "Between 2024 DORA levels";
  return `2024 DORA: ${levels.map((l) => l[0] + l.slice(1).toLowerCase()).join(" or ")}`;
}

/** Change vs. the previous window, or null when either side is missing or the change is under 10%. */
export function change(
  current: number | null | undefined,
  previous: number | null | undefined,
  lowerIsBetter: boolean,
): { pct: number; up: boolean; better: boolean } | null {
  if (current == null || previous == null || previous === 0) return null;
  const pct = Math.round((Math.abs(current - previous) / previous) * 100); // magnitude, so -29.5 and 29.5 both round to 30
  if (pct < 10) return null;
  const up = current > previous;
  return { pct, up, better: up !== lowerIsBetter };
}

/** "Oct 14, 03:00 UTC". UTC everywhere, like the windows. */
export function dateTime(iso: string): string {
  const d = new Date(iso);
  const day = d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
  return `${day}, ${d.toISOString().slice(11, 16)} UTC`;
}

/** "Oct 5" from "2026-10-05". */
export function shortDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** SLO objectives keep their nines: 0.999 is "99.9%", never a rounded "100%". */
export function objective(value: number | null | undefined): string {
  return value == null ? "No objective" : `${Number((value * 100).toFixed(3))}%`;
}
