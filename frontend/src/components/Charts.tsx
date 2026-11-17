import { useId } from "react";
import type { ActivityDay } from "../lib/types";
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

/* ------------------------------------------------------------------ 打卡热力图 */

function parseDayKey(key: string): Date | null {
  const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
  if (!matched) return null;
  return new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]));
}

/** 判题次数 → 深浅。0 用底色，越多越浓（同一套色在浅色/深色主题下都成立） */
function heatStyle(count: number): { background: string; opacity: number } {
  if (count <= 0) return { background: "var(--color-ink-700)", opacity: 1 };
  if (count <= 2) return { background: "var(--color-brand-500)", opacity: 0.28 };
  if (count <= 4) return { background: "var(--color-brand-500)", opacity: 0.45 };
  if (count <= 7) return { background: "var(--color-brand-500)", opacity: 0.65 };
  if (count <= 10) return { background: "var(--color-brand-500)", opacity: 0.82 };
  return { background: "var(--color-brand-500)", opacity: 1 };
}

/**
 * GitHub 风格打卡热力图：一列一周（周一在上），一格一天。
 *
 * 数据要按日期升序、只传要显示的那一段（调用方决定 26 周还是 52 周），
 * 这里负责补齐首尾空格子让每一列都从周一开始。
 */
export function Heatmap({ points }: { points: ActivityDay[] }) {
  if (points.length === 0) {
    return <p className="py-8 text-center text-xs text-fg-dim">还没有打卡记录，做一道题就有格子了</p>;
  }

  const first = parseDayKey(points[0]?.date ?? "");
  const lead = first ? (first.getDay() + 6) % 7 : 0;
  const cells: Array<ActivityDay | null> = [];
  for (let i = 0; i < lead; i += 1) cells.push(null);
  for (const point of points) cells.push(point);
  while (cells.length % 7 !== 0) cells.push(null);

  const columns: Array<Array<ActivityDay | null>> = [];
  for (let i = 0; i < cells.length; i += 7) columns.push(cells.slice(i, i + 7));

  // 月份标签放在「这一列第一天所在月份」变化的位置
  const labels: string[] = [];
  let previousMonth = -1;
  for (const column of columns) {
    const day = column.find((cell): cell is ActivityDay => Boolean(cell));
    const date = day ? parseDayKey(day.date) : null;
    if (!date) {
      labels.push("");
      continue;
    }
    const month = date.getMonth();
    if (month !== previousMonth) {
      labels.push(`${month + 1}月`);
      previousMonth = month;
    } else {
      labels.push("");
    }
  }

  return (
    <div className="w-full">
      <div className="overflow-x-auto pb-1">
        <div className="w-max">
          <div className="flex gap-[3px]">
            {labels.map((label, i) => (
              <div key={`m-${i}`} className="w-3.5 whitespace-nowrap text-[0.56rem] text-fg-dim">
                {label}
              </div>
            ))}
          </div>
          <div className="mt-1 flex gap-[3px]">
            {columns.map((column, i) => (
              <div key={`w-${i}`} className="flex flex-col gap-[3px]">
                {column.map((cell, j) =>
                  cell ? (
                    <div
                      key={`${cell.date}`}
                      title={`${cell.date} · ${cell.count > 0 ? `判题 ${cell.count} 次` : "没有做题"}`}
                      className={cls(
                        "size-3.5 rounded-[2px] transition-colors",
                        cell.count === 0 && "border border-line-soft",
                      )}
                      style={heatStyle(cell.count)}
                    />
                  ) : (
                    <div key={`blank-${i}-${j}`} className="size-3.5" />
                  ),
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-end gap-1.5 text-[0.6rem] text-fg-dim">
        <span>少</span>
        {[0, 1, 3, 6, 9, 14].map((count) => (
          <span
            key={count}
            className="size-2.5 rounded-[2px]"
            style={heatStyle(count)}
            title={`${count} 次`}
          />
        ))}
        <span>多</span>
      </div>
    </div>
  );
}

