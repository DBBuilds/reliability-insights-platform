/** A fixed window of the last `weeks` COMPLETE ISO weeks (Monday to Monday, UTC).

Fixed dates, not "last 28 days": the numbers don't shift between two reads, and
no partial week at the edge understates the trend.
*/
export function completeWeeks(weeks: number, today: Date = new Date()): { start: string; end: string } {
  const d = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const sinceMonday = (d.getUTCDay() + 6) % 7;
  const end = new Date(d.getTime() - sinceMonday * 86_400_000);
  const start = new Date(end.getTime() - weeks * 7 * 86_400_000);
  const iso = (x: Date) => x.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}
