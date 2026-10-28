export function minutes(value: number | null | undefined): string {
  if (value == null) return "Not enough data";
  if (value < 60) return `${Math.round(value)} min`;
  const h = value / 60;
  return h < 48 ? `${h.toFixed(1)} h` : `${(h / 24).toFixed(1)} d`;
}

export function percent(value: number | null | undefined): string {
  return value == null ? "No data" : `${Math.round(value * 100)}%`;
}
