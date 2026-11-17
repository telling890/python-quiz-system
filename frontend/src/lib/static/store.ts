/** 静态版的本地持久化：进度、收藏、片段、草稿、提交历史、打卡统计全在 localStorage 里 */
import { dateKeyFromIso } from "../activity";
import type { LastStatus, Snippet, User } from "../types";

const KEY = "pyquiz.static.v1";

export interface LocalRecord {
  qid: string;
  attempts: number;
  passes: number;
  fails: number;
  last: LastStatus;
  favorite: boolean;
  code: string;
  updated: string;
}

export interface LocalSubmission {
  id: string;
  qid: string;
  status: string;
  total: number;
  created_at: string;
  duration_ms: number;
}

export interface LocalState {
  user: User | null;
  records: Record<string, LocalRecord>;
  snippets: Snippet[];
  draft: { code: string; stdin: string; updated: string };
  submissions: LocalSubmission[];
  /** 本地日期 → 当天判题次数（打卡热力图用；老数据没有这个字段） */
  activity: Record<string, number>;
}

const EMPTY: LocalState = {
  user: null,
  records: {},
  snippets: [],
  draft: { code: "", stdin: "", updated: "" },
  submissions: [],
  activity: {},
};

function blank(): LocalState {
  return { ...EMPTY, records: {}, snippets: [], submissions: [], draft: { ...EMPTY.draft }, activity: {} };
}

/** 老版本没有 activity 字段：从（最多 40 条）提交历史里尽量补出来 */
function activityFromSubmissions(submissions: LocalSubmission[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const item of submissions) {
    const key = dateKeyFromIso(item.created_at);
    if (key) counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

export function loadState(): LocalState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return blank();
    const parsed = JSON.parse(raw) as Partial<LocalState>;
    const submissions = parsed.submissions ?? [];
    return {
      user: parsed.user ?? null,
      records: parsed.records ?? {},
      snippets: parsed.snippets ?? [],
      draft: parsed.draft ?? { ...EMPTY.draft },
      submissions,
      activity: parsed.activity ?? activityFromSubmissions(submissions),
    };
  } catch {
    return blank();
  }
}

export function saveState(state: LocalState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* 隐私模式 / 配额满：静默失败，界面仍能用 */
  }
}

export function nowIso(): string {
  // 与后端 now_iso 一致：UTC + 秒
  return new Date().toISOString().slice(0, 19) + "+00:00";
}

export function emptyRecord(qid: string): LocalRecord {
  return {
    qid,
    attempts: 0,
    passes: 0,
    fails: 0,
    last: "",
    favorite: false,
    code: "",
    updated: nowIso(),
  };
}

export function newId(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
}

/** 更新一条记录（不存在就建） */
export function withRecord(
  state: LocalState,
  qid: string,
  mutate: (record: LocalRecord) => void,
): LocalState {
  const record = state.records[qid] ?? emptyRecord(qid);
  mutate(record);
  record.updated = nowIso();
  return { ...state, records: { ...state.records, [qid]: record } };
}

/** 记一次判题：今天的热力图格子 +1 */
export function bumpActivity(state: LocalState, dateKey: string): LocalState {
  if (!dateKey) return state;
  return { ...state, activity: { ...state.activity, [dateKey]: (state.activity[dateKey] ?? 0) + 1 } };
}
