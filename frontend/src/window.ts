const DAY = 86_400_000;

/** The window presets, in days. The demo exporter exports exactly these. */
export const PRESETS = [30, 90, 180, 365];
export const MAX_DAYS = 366; // the API's cap

/** ISO dates; `end` is exclusive. `previousStart` begins the window of the same length just before. */
export type Window = { start: string; end: string; previousStart: string };

const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
const utcDay = (d: Date) => Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());

/** "YYYY-MM-DD" as a UTC day, never through local time (which can land a day early); null if not a real date. */
function parseDay(value: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!m) return null;
  const ms = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return iso(ms) === value ? ms : null;
}

function window(start: number, end: number): Window {
  return { start: iso(start), end: iso(end), previousStart: iso(start - (end - start)) };
}

/** The last `days` complete UTC days before `today`. Fixed dates, not "the last 24 hours x N": two reads agree. */
export function lastDays(days: number, today: Date = new Date()): Window {
  const end = utcDay(today);
  return window(end - days * DAY, end);
}

/** The latest complete UTC day before `today`, as "YYYY-MM-DD". */
export function latestDay(today: Date = new Date()): string {
  return iso(utcDay(today) - DAY);
}

/** The last day inside a window (its `end` is exclusive). */
export function lastDayOf(w: Window): string {
  return iso((parseDay(w.end) as number) - DAY);
}

/** A window from inclusive dates, or a short message saying what's wrong. */
export function customRange(from: string, to: string, today: Date = new Date()): Window | string {
  const start = parseDay(from);
  const last = parseDay(to);
  if (start == null || last == null) return "Pick both dates.";
  if (start > last) return "The start must be on or before the end.";
  if ((last - start) / DAY + 1 > MAX_DAYS) return `Pick ${MAX_DAYS} days or fewer.`;
  if (last >= utcDay(today)) {
    const latest = new Date(utcDay(today) - DAY);
    return `The latest complete day is ${latest.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })}.`;
  }
  return window(start, last + DAY);
}
