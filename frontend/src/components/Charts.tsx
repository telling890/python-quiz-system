import { useId } from "react";
import { cls } from "./ui";

/* ------------------------------------------------------------------
   手写 SVG 图表：不引第三方图表库，体积小、主题可控
   ------------------------------------------------------------------ */

export interface Slice {
  label: string;
  value: number;
  color: string;
}

/** 环形图（通过/未通过、章节占比） */
export function Donut({
  slices,
  size = 168,
  thickness = 16,
  centerLabel,
  centerValue,
}: {
  slices: Slice[];
  size?: number;
  thickness?: number;
  centerLabel?: string;
  centerValue?: string;
}) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-ink-700)" strokeWidth={thickness} />
        {total > 0 &&
          slices.map((s) => {
            const len = (s.value / total) * c;
            const dash = `${Math.max(len - 2, 0)} ${c - Math.max(len - 2, 0)}`;
            const el = (
              <circle
                key={s.label}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={s.color}
                strokeWidth={thickness}
                strokeDasharray={dash}
                strokeDashoffset={-offset}
                strokeLinecap="round"
                style={{ transition: "stroke-dasharray .6s ease, stroke-dashoffset .6s ease" }}
              />
            );
            offset += len;
            return el;
          })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tabular-nums text-fg">{centerValue ?? total}</span>
        {centerLabel ? <span className="mt-0.5 text-[0.7rem] text-fg-dim">{centerLabel}</span> : null}
      </div>
    </div>
  );
}

export function Legend({ slices, total }: { slices: Slice[]; total?: number }) {
  const sum = total ?? slices.reduce((s, x) => s + x.value, 0);
  return (
    <ul className="flex w-full flex-col gap-2">
      {slices.map((s) => (
        <li key={s.label} className="flex items-center gap-2 text-xs">
          <span className="size-2 shrink-0 rounded-full" style={{ background: s.color }} />
          <span className="flex-1 truncate text-fg-muted">{s.label}</span>
          <span className="tabular-nums font-semibold text-fg">{s.value}</span>
          <span className="w-10 text-right tabular-nums text-fg-dim">
            {sum > 0 ? `${Math.round((s.value / sum) * 100)}%` : "—"}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** 折线 / 面积趋势图 */
export function Trend({
  points,
  height = 150,
  color = "var(--color-brand-400)",
  formatValue = (v: number) => `${v}`,
}: {
  points: Array<{ label: string; value: number }>;
  height?: number;
  color?: string;
  formatValue?: (v: number) => string;
}) {
  const gid = useId().replace(/[:]/g, "");
  const w = 100;
  const h = 100;
  const pad = 4;
  if (points.length === 0) {
    return (
      <div className="flex h-36 items-center justify-center text-xs text-fg-dim">还没有数据，先做几道题吧</div>
    );
  }
  const values = points.map((p) => p.value);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const x = (i: number) => (points.length === 1 ? w / 2 : pad + (i * (w - pad * 2)) / (points.length - 1));
  const y = (v: number) => h - pad - ((v - min) / span) * (h - pad * 2);

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(2)},${y(p.value).toFixed(2)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(2)},${h - pad} L${x(0).toFixed(2)},${h - pad} Z`;

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ height, width: "100%" }}>
        <defs>
          <linearGradient id={`fill-${gid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={0}
            x2={w}
            y1={h * f}
            y2={h * f}
            stroke="var(--color-line)"
            strokeWidth={0.5}
            strokeDasharray="2 2"
          />
        ))}
        <path d={area} fill={`url(#fill-${gid})`} />
        <path d={line} fill="none" stroke={color} strokeWidth={1.6} strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p, i) => (
          <circle key={`${p.label}-${i}`} cx={x(i)} cy={y(p.value)} r={points.length > 24 ? 0.8 : 1.5} fill={color} />
        ))}
      </svg>
      <div className="mt-1.5 flex justify-between text-[0.68rem] text-fg-dim">
        <span>{points[0]?.label}</span>
        <span className="tabular-nums">
          {formatValue(min)} – {formatValue(max)}
        </span>
        <span>{points[points.length - 1]?.label}</span>
      </div>
    </div>
  );
}

/** 横向条形对比（章节进度） */
export function BarRow({
  label,
  value,
  max,
  tone = "#6366f1",
  suffix,
  onClick,
}: {
  label: string;
  value: number;
  max: number;
  tone?: string;
  suffix?: string;
  onClick?: () => void;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const Wrapper = onClick ? "button" : "div";
  return (
    <Wrapper
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={cls(
        "group w-full text-left",
        onClick && "rounded-lg px-1.5 py-1 transition-colors hover:bg-ink-800/70",
      )}
    >
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="truncate text-xs text-fg-muted group-hover:text-fg">{label}</span>
        <span className="shrink-0 tabular-nums text-[0.7rem] text-fg-dim">
          {value}
          {suffix ?? ` / ${max}`}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${pct}%`, background: tone }}
        />
      </div>
    </Wrapper>
  );
}
