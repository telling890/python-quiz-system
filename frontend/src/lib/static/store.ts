/** 静态版的本地持久化：进度、收藏、片段、草稿、提交历史全在 localStorage 里 */
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
}

const EMPTY: LocalState = {
  user: null,
  records: {},
  snippets: [],
  draft: { code: "", stdin: "", updated: "" },
  submissions: [],
};

export function loadState(): LocalState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...EMPTY, records: {}, snippets: [], submissions: [], draft: { ...EMPTY.draft } };
    const parsed = JSON.parse(raw) as Partial<LocalState>;
    return {
      user: parsed.user ?? null,
      records: parsed.records ?? {},
      snippets: parsed.snippets ?? [],
      draft: parsed.draft ?? { ...EMPTY.draft },
      submissions: parsed.submissions ?? [],
    };
  } catch {
    return { ...EMPTY, records: {}, snippets: [], submissions: [], draft: { ...EMPTY.draft } };
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
