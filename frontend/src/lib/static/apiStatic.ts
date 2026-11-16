/** 静态版（GitHub Pages）的接口实现：题库内置、进度存浏览器、判题在浏览器里跑 Python */
import { ApiError, BASE_URL, tokenStore } from "../core";
import type {
  Bank,
  CaseIn,
  Chapter,
  FreeDraft,
  JudgeResult,
  Progress,
  ProgressRecord,
  Question,
  Snippet,
  Stats,
  Submission,
  TraceResponse,
  User,
} from "../types";
import { judgeLocal, runLocal, traceLocal } from "./judge";
import { runner } from "./runner";
import { loadState, newId, nowIso, saveState, withRecord, type LocalState } from "./store";

/* ------------------------------------------------------------------ 题库 */

interface RawQuestion {
  id: string;
  chapter_id: string;
  chapter: string;
  chapter_short?: string;
  no: number;
  title: string;
  topic: string;
  level: number;
  desc: string;
  hint: string;
  ref: string;
  explain: string;
  source?: string;
  cases: CaseIn[];
}

interface RawBank {
  chapters: Array<{ id: string; name: string; short: string; count: number }>;
  questions: RawQuestion[];
}

let bankCache: { chapters: Chapter[]; questions: RawQuestion[] } | null = null;
let bankLoading: Promise<{ chapters: Chapter[]; questions: RawQuestion[] }> | null = null;

async function loadRawBank() {
  if (bankCache) return bankCache;
  if (!bankLoading) {
    bankLoading = fetch(`${BASE_URL}bank.json`, { cache: "force-cache" })
      .then((res) => {
        if (!res.ok) throw new ApiError(`题库加载失败（HTTP ${res.status}）`);
        return res.json() as Promise<RawBank>;
      })
      .then((raw) => {
        bankCache = { chapters: raw.chapters ?? [], questions: raw.questions ?? [] };
        return bankCache;
      })
      .catch((err) => {
        bankLoading = null;
        throw err instanceof ApiError ? err : new ApiError("题库加载失败，刷新页面再试");
      });
  }
  return bankLoading;
}

function mergeQuestion(raw: RawQuestion, state: LocalState): Question {
  const record = state.records[raw.id];
  return {
    id: raw.id,
    chapter_id: raw.chapter_id,
    chapter: raw.chapter,
    no: raw.no,
    title: raw.title,
    topic: raw.topic,
    level: raw.level,
    desc: raw.desc,
    hint: raw.hint,
    ref: raw.ref,
    explain: raw.explain,
    source: raw.source ?? "",
    cases: raw.cases ?? [],
    last: record?.last ?? "",
    attempts: record?.attempts ?? 0,
    favorite: Boolean(record?.favorite),
    code: record?.code ?? "",
  };
}

function statsOf(questions: Question[], state: LocalState): Stats {
  const records = Object.values(state.records);
  const solved = questions.filter((q) => q.last === "pass").length;
  const tried = questions.filter((q) => q.attempts > 0).length;
  const favorite = questions.filter((q) => q.favorite).length;
  const attempts = records.reduce((sum, r) => sum + r.attempts, 0);
  const passes = records.reduce((sum, r) => sum + r.passes, 0);
  return {
    total: questions.length,
    solved,
    tried,
    favorite,
    attempts,
    passes,
    rate: attempts > 0 ? Math.round((passes * 100) / attempts) : 0,
  };
}

/* ------------------------------------------------------------------ 登录态 */

function currentUser(): User | null {
  return loadState().user;
}

// 刷新后：本地有"用户"就直接恢复登录态
const bootUser = currentUser();
if (bootUser) tokenStore.set("local", bootUser);

function signIn(username: string): User {
  const name = username.trim();
  if (name.length < 1) throw new ApiError("先起个名字吧");
  if (name.length > 32) throw new ApiError("名字太长了（最多 32 个字符）");
  const state = loadState();
  const user: User = state.user?.username === name
    ? state.user
    : { id: 1, username: name, created_at: nowIso() };
  saveState({ ...state, user });
  tokenStore.set("local", user);
  return user;
}

/* ------------------------------------------------------------------ 未完成的提交 */

const pending = new Map<string, { qid: string; code: string; stdin: string }>();

/* ------------------------------------------------------------------ 对外接口 */

export const staticApi = {
  /* -------------------------------------------------- 认证（本地昵称） */
  async register(input: { username: string; password?: string }) {
    const user = signIn(input.username);
    return { token: "local", expires_in: 0, user };
  },

  async login(input: { username: string; password?: string }) {
    const user = signIn(input.username);
    return { token: "local", expires_in: 0, user };
  },

  async me() {
    const user = currentUser();
    if (!user) throw new ApiError("还没有登录", { status: 401, code: "unauthorized" });
    return user;
  },

  /* -------------------------------------------------- 题库 / 进度 */
  async bank(): Promise<Bank> {
    const [raw, state] = await Promise.all([loadRawBank(), Promise.resolve(loadState())]);
    const questions = raw.questions.map((q) => mergeQuestion(q, state));
    return { questions, chapters: raw.chapters, stats: statsOf(questions, state) };
  },

  async question(qid: string): Promise<Question> {
    const [raw, state] = await Promise.all([loadRawBank(), Promise.resolve(loadState())]);
    const found = raw.questions.find((q) => q.id === qid);
    if (!found) throw new ApiError("没有这道题：" + qid, { status: 404 });
    return mergeQuestion(found, state);
  },

  async progress(): Promise<Progress> {
    const [raw, state] = await Promise.all([loadRawBank(), Promise.resolve(loadState())]);
    const questions = raw.questions.map((q) => mergeQuestion(q, state));
    const records: ProgressRecord[] = Object.values(state.records).map((r) => ({
      qid: r.qid,
      attempts: r.attempts,
      passes: r.passes,
      fails: r.fails,
      last: r.last,
      favorite: r.favorite,
      updated: r.updated,
    }));
    return { stats: statsOf(questions, state), records };
  },

  async setFavorite(qid: string, favorite: boolean) {
    const state = withRecord(loadState(), qid, (record) => {
      record.favorite = favorite;
    });
    saveState(state);
    return { qid, favorite };
  },

  /* -------------------------------------------------- 判题（浏览器内执行） */
  async submit(input: { qid?: string; code: string; stdin?: string }): Promise<Submission> {
    const id = newId();
    pending.set(id, { qid: input.qid ?? "", code: input.code, stdin: input.stdin ?? "" });
    return {
      id,
      qid: input.qid ?? "",
      status: "queued",
      result: {},
      error: "",
      created_at: nowIso(),
      finished_at: "",
      duration_ms: 0,
    };
  },

  async startAwait(id: string): Promise<Submission> {
    return judgeSubmission(id);
  },

  async submission(id: string): Promise<Submission> {
    // 静态版判题是瞬时的，正常不会走到这里
    return judgeSubmission(id);
  },

  async submissions(limit = 30) {
    const state = loadState();
    const items: Submission[] = state.submissions.slice(0, limit).map((item) => ({
      id: item.id,
      qid: item.qid,
      status: item.status as Submission["status"],
      result: { total: item.total },
      error: "",
      created_at: item.created_at,
      finished_at: item.created_at,
      duration_ms: item.duration_ms,
    }));
    return { items, limit };
  },

  async runFree(code: string, stdin = "") {
    runner.warmup();
    const run = await runLocal(code, stdin);
    return { mode: "free", run };
  },

  /* -------------------------------------------------- 片段 / 草稿 */
  async snippets() {
    const state = loadState();
    const snippets: Snippet[] = [...state.snippets].sort((a, b) => (a.updated < b.updated ? 1 : -1));
    return { snippets };
  },

  async saveSnippet(name: string, code: string) {
    const clean = name.trim();
    if (!clean) throw new ApiError("片段名字不能为空");
    const state = loadState();
    const existing = state.snippets.find((s) => s.name === clean);
    const updated = nowIso();
    const snippets = existing
      ? state.snippets.map((s) => (s.name === clean ? { ...s, code, updated } : s))
      : [...state.snippets, { name: clean, code, updated }];
    saveState({ ...state, snippets });
    return { created: !existing, name: clean };
  },

  async deleteSnippet(name: string) {
    const state = loadState();
    saveState({ ...state, snippets: state.snippets.filter((s) => s.name !== name) });
    return { removed: true, name };
  },

  async freeDraft(): Promise<FreeDraft> {
    const { draft } = loadState();
    return { code: draft.code, stdin: draft.stdin, updated: draft.updated };
  },

  async saveFreeDraft(code: string, stdin: string) {
    const state = loadState();
    const updated = nowIso();
    saveState({ ...state, draft: { code, stdin, updated } });
    return { saved: true, updated };
  },

  /* -------------------------------------------------- 单步追踪 */
  async trace(code: string, stdin = ""): Promise<TraceResponse> {
    return traceLocal(code, stdin);
  },
};

/** 真正执行一次判题（在浏览器里跑 Pyodide），并把进度写回 localStorage */
async function judgeSubmission(id: string): Promise<Submission> {
  const job = pending.get(id);
  if (!job) throw new ApiError("找不到这次提交，刷新页面再试");
  const raw = await loadRawBank();
  const question = job.qid ? raw.questions.find((q) => q.id === job.qid) : undefined;

  let result: JudgeResult;
  if (question) {
    result = await judgeLocal(job.code, question.cases ?? []);
  } else {
    const run = await runLocal(job.code, job.stdin, 20_000);
    const status: JudgeResult["status"] = run.timeout ? "timeout" : run.error ? "error" : "passed";
    result = {
      mode: "free",
      passed: status === "passed",
      status,
      total: 0,
      results: [],
      duration_ms: run.duration_ms,
      run,
      error: run.error,
    };
  }

  let state = loadState();
  if (job.qid) {
    const passed = result.status === "passed";
    state = withRecord(state, job.qid, (record) => {
      record.attempts += 1;
      if (passed) {
        record.passes += 1;
        record.last = "pass";
      } else {
        record.fails += 1;
        record.last = "fail";
      }
      record.code = job.code;
    });
  }
  state.submissions = [
    {
      id,
      qid: job.qid,
      status: result.status,
      total: result.total ?? 0,
      created_at: nowIso(),
      duration_ms: result.duration_ms ?? 0,
    },
    ...state.submissions,
  ].slice(0, 40);
  saveState(state);
  pending.delete(id);

  return {
    id,
    qid: job.qid,
    status: result.status,
    result,
    error: result.error ?? "",
    created_at: nowIso(),
    finished_at: nowIso(),
    duration_ms: result.duration_ms ?? 0,
  };
}

export async function staticAwaitSubmission(
  id: string,
  _options: { signal?: AbortSignal; timeoutMs?: number; onTick?: (s: Submission) => void } = {},
): Promise<Submission> {
  return judgeSubmission(id);
}
