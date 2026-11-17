/** 打卡热力图的本地计算：静态版没有后端，用同一套规则在浏览器里算 */
import type { Activity, ActivityDay } from "./types";

const pad = (n: number) => String(n).padStart(2, "0");

/** 本地日历日 → YYYY-MM-DD。不能用 toISOString()，那是 UTC 日期，东八区的凌晨会差一天 */
export function dateKeyOf(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** ISO 时间串 → 本地日期键（解析不了返回空串） */
export function dateKeyFromIso(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : dateKeyOf(date);
}

function shiftDays(date: Date, delta: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + delta);
  return next;
}

/**
 * 从「日期 → 判题次数」造出连续 N 天的数据与统计。
 *
 * 连续打卡的判定和后端一致：今天还没做题、但昨天做了，连续记录先算「活着」；
 * 今天和昨天都没有才算断。
 */
export function buildActivity(counts: Record<string, number>, days: number): Activity {
  const today = new Date();
  const todayKey = dateKeyOf(today);

  const list: ActivityDay[] = [];
  for (let i = days - 1; i >= 0; i -= 1) {
    const key = dateKeyOf(shiftDays(today, -i));
    list.push({ date: key, count: counts[key] ?? 0 });
  }

  let cursor = list.length - 1;
  if (cursor >= 0 && list[cursor].count === 0) cursor -= 1; // 今天没做，看昨天
  let streak = 0;
  while (cursor >= 0 && list[cursor].count > 0) {
    streak += 1;
    cursor -= 1;
  }

  let best = 0;
  let run = 0;
  let bestEnd = "";
  for (const point of list) {
    if (point.count > 0) {
      run += 1;
      if (run > best) {
        best = run;
        bestEnd = point.date;
      }
    } else {
      run = 0;
    }
  }

  return {
    days: list,
    today: todayKey,
    today_count: list.length > 0 ? list[list.length - 1].count : 0,
    total: list.reduce((sum, point) => sum + point.count, 0),
    active_days: list.filter((point) => point.count > 0).length,
    streak,
    best_streak: best,
    best_streak_end: bestEnd,
    timezone_minutes: -new Date().getTimezoneOffset(),
  };
}
