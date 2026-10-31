// Small SVG charts, no library. Marks follow the dataviz spec: 2px lines, columns at most
// 24px with a rounded data end, hairline axes, values reachable without hover (table view).
import { type KeyboardEvent, type PointerEvent, type ReactNode, useState } from "react";

const W = 400; // viewBox width; 1:1 on a phone, scales up on wider cards
const PAD = { top: 10, right: 44, bottom: 20, left: 44 };

export type Series = { name: string; values: (number | null)[]; color: string };

type ChartProps = {
  title: string;
  x: string[];
  series: Series[];
  kind?: "line" | "columns";
  band?: { name: string; low: (number | null)[]; high: (number | null)[] }; // shaded range under series 0
  format: (v: number) => string;
  height?: number;
  endLabel?: boolean; // value at the end of each line; off when the text beside the chart already says it
  tickUnit?: number; // round ticks in this unit, e.g. 60 for minutes shown as hours
};

/** Ticks: zero (or the minimum), the middle, and a round top, rounded in `unit`. */
function scale(values: number[], unit = 1): number[] {
  const low = Math.min(0, ...values);
  const max = Math.max(...values, 1e-9) / unit;
  const magnitude = 10 ** Math.floor(Math.log10(max));
  const top = ([1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((t) => t >= max) ?? max) * unit;
  return [low, (low + top) / 2, top];
}

export function Chart({
  title,
  x,
  series,
  kind = "line",
  band,
  format,
  height = 150,
  endLabel = true,
  tickUnit,
}: ChartProps) {
  const [active, setActive] = useState<number | null>(null);
  const known = [...series.flatMap((s) => s.values), ...(band?.high ?? [])].filter((v): v is number => v != null);
  const ticks = scale(known, known.some((v) => v >= (tickUnit ?? 1)) ? tickUnit : 1);
  const [low, , top] = ticks as [number, number, number];
  const n = x.length;
  const step = (W - PAD.left - PAD.right) / Math.max(n, 1);
  const px = (i: number) => PAD.left + step * (i + 0.5);
  const py = (v: number) => PAD.top + (1 - (v - low) / (top - low || 1)) * (height - PAD.top - PAD.bottom);
  const base = py(Math.max(low, 0));

  const path = (values: (number | null)[]) =>
    values.map((v, i) => (v == null ? "" : `${i && values[i - 1] != null ? "L" : "M"}${px(i)},${py(v)}`)).join("");
  const area = band
    ? band.high
        .map((h, i) => ({ i, h, l: band.low[i] }))
        .filter((p): p is { i: number; h: number; l: number } => p.h != null && p.l != null)
    : [];

  function pointAt(e: PointerEvent<SVGSVGElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const i = Math.floor(((e.clientX - box.left) * (W / box.width) - PAD.left) / step);
    setActive(Math.min(n - 1, Math.max(0, i)));
  }
  function keys(e: KeyboardEvent<SVGSVGElement>) {
    const moves: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1 };
    if (e.key in moves) {
      e.preventDefault();
      setActive((i) => Math.min(n - 1, Math.max(0, (i ?? n - 1) + (moves[e.key] ?? 0))));
    }
  }
  const lastLabels: number[] = []; // direct end labels, skipped when two would collide

  return (
    <figure>
      <figcaption>{title}</figcaption>
      {series.length > 1 && (
        <div className="legend">
          {series.map((s) => (
            <span key={s.name}>
              <span
                className={kind === "columns" ? "key box" : "key"}
                style={{ borderColor: s.color, background: kind === "columns" ? s.color : undefined }}
              />
              {s.name}
            </span>
          ))}
          {band && (
            <span>
              <span className="key box" style={{ background: series[0]?.color, opacity: 0.15 }} />
              {band.name}
            </span>
          )}
        </div>
      )}
      <svg
        viewBox={`0 0 ${W} ${height}`}
        role="img"
        aria-label={`${title}. Use the arrow keys to read each point; the table below lists every value.`}
        tabIndex={0}
        onPointerMove={pointAt}
        onPointerLeave={() => setActive(null)}
        onFocus={() => setActive((i) => i ?? n - 1)}
        onBlur={() => setActive(null)}
        onKeyDown={keys}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={py(t)}
              y2={py(t)}
              stroke={t === Math.max(low, 0) ? "var(--axis)" : "var(--border)"}
            />
            <text x={PAD.left - 6} y={py(t) + 4} textAnchor="end">
              {format(t)}
            </text>
          </g>
        ))}
        {[0, n - 1]
          .filter((i, k, all) => n > 0 && all.indexOf(i) === k)
          .map((i) => (
            <text key={i} x={px(i)} y={height - 4} textAnchor="middle">
              {x[i]}
            </text>
          ))}
        {area.length > 0 && (
          <path
            d={`${area.map((p, k) => `${k ? "L" : "M"}${px(p.i)},${py(p.h)}`).join("")}${[...area]
              .reverse()
              .map((p) => `L${px(p.i)},${py(p.l)}`)
              .join("")}Z`}
            fill={series[0]?.color}
            opacity={0.12}
          />
        )}
        {series.map((s) => (
          <g key={s.name}>
            {kind === "columns"
              ? s.values.map((v, i) => {
                  if (v == null || v === 0) return null;
                  const w = Math.min(24, step * 0.6);
                  const [x0, x1, y0] = [px(i) - w / 2, px(i) + w / 2, py(v)];
                  const r = Math.min(4, (base - y0) / 2, w / 2);
                  return (
                    <path
                      key={i}
                      fill={s.color}
                      d={`M${x0},${base}V${y0 + r}Q${x0},${y0} ${x0 + r},${y0}H${x1 - r}Q${x1},${y0} ${x1},${y0 + r}V${base}Z`}
                    />
                  );
                })
              : [
                  <path
                    key="line"
                    d={path(s.values)}
                    fill="none"
                    stroke={s.color}
                    strokeWidth={2}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />,
                  (() => {
                    const i = s.values.reduce<number>((last, v, k) => (v == null ? last : k), -1);
                    const v = s.values[i];
                    if (!endLabel || v == null || lastLabels.some((y) => Math.abs(y - py(v)) < 12)) return null;
                    lastLabels.push(py(v));
                    return (
                      <text key="end" x={px(i) + 8} y={py(v) + 4} style={{ fill: "var(--fg)" }}>
                        {format(v)}
                      </text>
                    );
                  })(),
                ]}
          </g>
        ))}
        {active != null && (
          <g pointerEvents="none">
            <line x1={px(active)} x2={px(active)} y1={PAD.top} y2={height - PAD.bottom} stroke="var(--muted)" />
            {kind === "line" &&
              series.map((s) => {
                const v = s.values[active];
                return v == null ? null : (
                  <circle
                    key={s.name}
                    cx={px(active)}
                    cy={py(v)}
                    r={4}
                    fill={s.color}
                    stroke="var(--surface)"
                    strokeWidth={2}
                  />
                );
              })}
          </g>
        )}
      </svg>
      <div className="readout" aria-live="polite">
        {active != null && (
          <>
            {x[active]}:{" "}
            {series.map((s) => (
              <span key={s.name}>
                {" "}
                <span className="key" style={{ borderColor: s.color }} />
                <strong>{s.values[active] == null ? "no data" : format(s.values[active] as number)}</strong>{" "}
                {s.name.toLowerCase()}
              </span>
            ))}
          </>
        )}
      </div>
      <DataTable
        head={["", ...series.map((s) => s.name), ...(band ? [band.name] : [])]}
        rows={x.map((label, i) => [
          label,
          ...series.map((s) => (s.values[i] == null ? "" : format(s.values[i] as number))),
          ...(band ? [band.high[i] == null ? "" : format(band.high[i] as number)] : []),
        ])}
      />
    </figure>
  );
}

/** The accessible twin of every chart: the same values as a table, collapsed. */
export function DataTable({
  head,
  rows,
  summary = "Table",
}: {
  head: string[];
  rows: ReactNode[][];
  summary?: string;
}) {
  return (
    <details>
      <summary>{summary}</summary>
      <Table head={head} rows={rows} />
    </details>
  );
}

export function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={i} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) =>
                c === 0 ? (
                  <th key={c} scope="row">
                    {cell}
                  </th>
                ) : (
                  <td key={c}>{cell}</td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Trend inside a stat tile: gray line, current period as an accent dot. Decorative; the table has the values. */
export function Sparkline({ values }: { values: (number | null)[] }) {
  const known = values.filter((v): v is number => v != null);
  if (known.length < 2) return null;
  const [w, h] = [96, 28];
  const [lo, hi] = [Math.min(...known), Math.max(...known)];
  const at = (i: number, v: number) => [
    4 + (i / (values.length - 1)) * (w - 8),
    4 + (1 - (v - lo) / (hi - lo || 1)) * (h - 8),
  ];
  const points = values.flatMap((v, i) => (v == null ? [] : [at(i, v)]));
  const [ex, ey] = points.at(-1) as number[];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: w }} aria-hidden="true">
      <polyline
        points={points.map((p) => p.join(",")).join(" ")}
        fill="none"
        stroke="var(--axis)"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <circle cx={ex} cy={ey} r={4} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
    </svg>
  );
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** Pages by weekday and local hour. One hue, darker is more; zero is neutral gray. */
export function Heatmap({ cells }: { cells: { weekday: number; hour: number; pages: number }[] }) {
  const [active, setActive] = useState<(typeof cells)[number] | null>(null);
  const max = Math.max(1, ...cells.map((c) => c.pages));
  const [left, top, cw, ch] = [32, 14, (W - 32) / 24, 14];
  const grid = DAYS.map((_, d) =>
    Array.from({ length: 24 }, (_, h) => cells.find((c) => c.weekday === d && c.hour === h)?.pages ?? 0),
  );
  return (
    <figure>
      <figcaption>Pages by local hour</figcaption>
      <svg
        viewBox={`0 0 ${W} ${top + 7 * ch}`}
        role="img"
        aria-label="Pages by weekday and local hour. The table below lists every value."
        onPointerLeave={() => setActive(null)}
      >
        {[0, 6, 12, 18].map((hr) => (
          <text key={hr} x={left + hr * cw} y={10}>
            {String(hr).padStart(2, "0")}:00
          </text>
        ))}
        {DAYS.map((day, d) => (
          <g key={day}>
            <text x={0} y={top + d * ch + 11}>
              {day}
            </text>
            {(grid[d] ?? []).map((pages, h) => (
              <rect
                key={h}
                x={left + h * cw + 1}
                y={top + d * ch + 1}
                width={cw - 2}
                height={ch - 2}
                rx={2}
                fill={`var(--heat-${pages ? Math.ceil((pages / max) * 4) : 0})`}
                stroke={active?.weekday === d && active.hour === h ? "var(--fg)" : "none"}
                onPointerEnter={() => setActive({ weekday: d, hour: h, pages })}
              />
            ))}
          </g>
        ))}
      </svg>
      <div className="legend muted" aria-hidden="true">
        Fewer
        {[1, 2, 3, 4].map((s) => (
          <span key={s} className="key box" style={{ background: `var(--heat-${s})` }} />
        ))}
        More
      </div>
      <div className="readout" aria-live="polite">
        {active && (
          <>
            {DAYS[active.weekday]} {String(active.hour).padStart(2, "0")}:00: <strong>{active.pages}</strong> pages
          </>
        )}
      </div>
      <DataTable
        head={["", ...Array.from({ length: 24 }, (_, h) => String(h).padStart(2, "0"))]}
        rows={DAYS.map((day, d) => [day, ...(grid[d] ?? [])])}
      />
    </figure>
  );
}
