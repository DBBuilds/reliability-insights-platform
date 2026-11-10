import { PRESETS } from "./window";

/** A preset (`days`) or, when both are set, a custom range of inclusive dates (`from`, `to`). */
export type View = { org: string; days: number; from: string; to: string };
const DEFAULT_DAYS = PRESETS[0] as number;
const date = (v: string | null) => (v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : "");

/** The view from a query string like "?org=checkout&days=90" or "?from=2026-01-01&to=2026-03-31".
Unknown or incomplete values fall back to the defaults. */
export function viewFromUrl(search: string): View {
  const params = new URLSearchParams(search);
  const days = Number(params.get("days"));
  const [from, to] = [date(params.get("from")), date(params.get("to"))];
  return {
    org: params.get("org") ?? "",
    days: PRESETS.includes(days) ? days : DEFAULT_DAYS,
    ...(from && to ? { from, to } : { from: "", to: "" }),
  };
}

/** The query string for a view, leaving defaults out so a plain link stays plain. */
export function urlForView({ org, days, from, to }: View): string {
  const params = new URLSearchParams();
  if (org) params.set("org", org);
  if (from && to) {
    params.set("from", from);
    params.set("to", to);
  } else if (days !== DEFAULT_DAYS) params.set("days", String(days));
  const query = params.toString();
  return query ? `?${query}` : "";
}
