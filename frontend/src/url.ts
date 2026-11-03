import { PRESETS } from "./window";

export type View = { org: string; weeks: number };
const DEFAULT_WEEKS = PRESETS[0] as number;

/** The org and window from a query string like "?org=checkout&weeks=13". Unknown values fall back to defaults. */
export function viewFromUrl(search: string): View {
  const params = new URLSearchParams(search);
  const weeks = Number(params.get("weeks"));
  return { org: params.get("org") ?? "", weeks: PRESETS.includes(weeks) ? weeks : DEFAULT_WEEKS };
}

/** The query string for a view, leaving defaults out so a plain link stays plain. */
export function urlForView({ org, weeks }: View): string {
  const params = new URLSearchParams();
  if (org) params.set("org", org);
  if (weeks !== DEFAULT_WEEKS) params.set("weeks", String(weeks));
  const query = params.toString();
  return query ? `?${query}` : "";
}
