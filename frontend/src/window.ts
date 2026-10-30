const DAY = 86_400_000;
const iso = (x: Date) => x.toISOString().slice(0, 10);

/** A fixed window of the last `weeks` COMPLETE ISO weeks (Monday to Monday, UTC).

Fixed dates, not "last 28 days": the numbers don't shift between two reads, and
no partial week at the edge understates the trend. `previousStart` begins the window
of the same length just before, for comparisons.
*/
export function completeWeeks(
  weeks: number,
  today: Date = new Date(),
): { start: string; end: string; previousStart: string } {
  const d = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const end = d - ((new Date(d).getUTCDay() + 6) % 7) * DAY;
  const start = end - weeks * 7 * DAY;
  return {
    start: iso(new Date(start)),
    end: iso(new Date(end)),
    previousStart: iso(new Date(start - weeks * 7 * DAY)),
  };
}
