import type { Chapter, LastStatus, Question, Stats } from "./types";

/* ------------------------------------------------------------------ 章节配色 */

// 章节配色：选的是深浅两种背景都够看的中间调（不是 400 系浅色）
const TONES = ["#6366f1", "#0891b2", "#059669", "#d97706", "#db2777", "#7c3aed", "#ea580c"];

/** 章节 → 稳定颜色（按章节在列表中的序号，换顺序也不跳色） */
export function chapterColor(chapters: Chapter[], chapterId: string): string {
  const index = chapters.findIndex((c) => c.id === chapterId);
  return TONES[(index < 0 ? 0 : index) % TONES.length];
}

/* ------------------------------------------------------------------ 难度 */

export function levelMeta(level: number): { label: string; tone: "ok" | "warn" | "bad"; dots: string } {
  if (level <= 1) return { label: "入门", tone: "ok", dots: "●○○" };
  if (level === 2) return { label: "进阶", tone: "warn", dots: "●●○" };
  return { label: "挑战", tone: "bad", dots: "●●●" };
}

/* ------------------------------------------------------------------ 状态 */

export function statusMeta(last: LastStatus): { label: string; tone: "ok" | "bad" | "neutral" } {
  if (last === "pass") return { label: "已通过", tone: "ok" };
  if (last === "fail") return { label: "未通过", tone: "bad" };
  return { label: "未尝试", tone: "neutral" };
}

/** 题目分类（用于列表筛选） */
export type Bucket = "all" | "todo" | "fail" | "pass" | "favorite";

export function bucketOf(q: Question): Exclude<Bucket, "all">[] {
  const keys: Exclude<Bucket, "all">[] = [];
  if (q.favorite) keys.push("favorite");
  if (q.last === "pass") keys.push("pass");
  else if (q.last === "fail") keys.push("fail");
  if (q.last !== "pass") keys.push("todo");
  return keys;
}

/* ------------------------------------------------------------------ 数字 */

export function pct(value: number, total: number): number {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

export function solutionRate(stats: Stats): number {
  return pct(stats.solved, stats.total);
}

/* ------------------------------------------------------------------ 时间 */

export function parseTime(iso: string): Date | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function timeAgo(iso: string): string {
  const date = parseTime(iso);
  if (!date) return "—";
  const diff = Date.now() - date.getTime();
  if (diff < 0) return "刚刚";
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} 个月前`;
  return `${Math.floor(months / 12)} 年前`;
}

export function fmtDuration(ms: number | null | undefined): string {
  // 没测到（undefined / NaN）才算未知；0 是「测了但很快」，别显示成「—」
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return "—";
  if (ms < 0.1) return "<0.1 ms";
  if (ms < 1000) return `${Number.isInteger(ms) ? ms : ms.toFixed(1)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function fmtDateTime(iso: string): string {
  const date = parseTime(iso);
  if (!date) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function dayKey(iso: string): string {
  const date = parseTime(iso);
  if (!date) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getMonth() + 1}/${pad(date.getDate())}`;
}

/* ------------------------------------------------------------------ 导出 */

export function downloadText(filename: string, content: string, mime = "text/plain;charset=utf-8") {
  // BOM 让 Excel 正确识别 UTF-8 中文
  const blob = new Blob([mime.startsWith("text/csv") ? "\ufeff" + content : content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function toCsv(rows: Array<Array<string | number>>): string {
  return rows
    .map((row) =>
      row
        .map((cell) => {
          const text = String(cell ?? "");
          return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
        })
        .join(","),
    )
    .join("\n");
}

/* ------------------------------------------------------------------ 杂项 */

export function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** 题号展示：第 3 章第 5 题 → 3-5 */
export function questionCode(q: Question): string {
  const chapterIndex = q.chapter_id.replace(/\D/g, "") || q.chapter;
  return `${chapterIndex}-${String(q.no).padStart(2, "0")}`;
}

export const STARTER_CODE = `# 在这里写 Python 代码。\n# 需要输入时用 input()，程序会自动喂 stdin。\n\n`;

export const FREE_STARTER = `# 自由编程：写什么都可以，Ctrl+Enter 运行\n\nname = input()\nprint(f"你好，{name}！")\n`;
