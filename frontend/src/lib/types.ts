/** 与后端 backend/app/schemas.py、serializers.py 一一对应的类型 */

export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface AuthPayload {
  token: string;
  expires_in: number;
  user: User;
}

export interface CaseIn {
  stdin: string;
  expect: string;
  raw?: boolean;
}

export type LastStatus = "" | "pass" | "fail";

export interface Question {
  id: string;
  chapter_id: string;
  chapter: string;
  no: number;
  title: string;
  topic: string;
  level: number;
  desc: string;
  hint: string;
  ref: string;
  explain: string;
  source: string;
  cases: CaseIn[];
  /** 当前用户状态 */
  last: LastStatus;
  attempts: number;
  favorite: boolean;
  code: string;
}

export interface Chapter {
  id: string;
  name: string;
  short: string;
  count: number;
}

export interface Stats {
  total: number;
  solved: number;
  tried: number;
  favorite: number;
  attempts: number;
  passes: number;
  /** 通过率（按作答次数算，0-100） */
  rate: number;
}

export interface Bank {
  questions: Question[];
  chapters: Chapter[];
  stats: Stats;
}

export interface ProgressRecord {
  qid: string;
  attempts: number;
  passes: number;
  fails: number;
  last: LastStatus;
  favorite: boolean;
  updated: string;
}

export interface Progress {
  stats: Stats;
  records: ProgressRecord[];
}

export interface RunResult {
  output: string;
  error: string;
  timeout: boolean;
  truncated: boolean;
  syntax: boolean;
  duration_ms: number;
}

export type JudgeStatus = "pass" | "fail" | "timeout" | "error";

export interface JudgeCaseResult {
  index: number;
  stdin: string;
  expect: string;
  actual: string;
  error: string;
  timeout: boolean;
  truncated: boolean;
  expect_lines: string[];
  actual_lines: string[];
  status: JudgeStatus;
  /** 第一个不一致的位置（行号从 1 开始；两侧可能为 null 表示某一侧没有这行） */
  first_diff: { line: number; expect: string | null; actual: string | null } | null;
}

export interface JudgeResult {
  mode: "judge" | "free";
  passed: boolean;
  status: "passed" | "failed" | "timeout" | "error";
  total: number;
  results: JudgeCaseResult[];
  duration_ms: number;
  error?: string;
  run?: RunResult;
}

export type SubmissionStatus =
  | "queued"
  | "running"
  | "passed"
  | "failed"
  | "timeout"
  | "error";

export interface Submission {
  id: string;
  qid: string;
  status: SubmissionStatus;
  /** queued/running 时是空对象，终态后是 JudgeResult */
  result: Partial<JudgeResult>;
  error: string;
  created_at: string;
  finished_at: string;
  duration_ms: number;
}

export interface TraceStep {
  line: number;
  event: string;
  func: string;
  depth: number;
  vars: Array<[string, string]>;
  hidden: number;
  out: string;
}

export interface Trace {
  steps: TraceStep[];
  error: string;
  timeout: boolean;
  truncated: boolean;
  output: string;
  syntax: boolean;
}

export interface TraceResponse {
  trace: Trace;
  summary: string;
}

export interface Snippet {
  name: string;
  code: string;
  updated: string;
}

/** 打卡热力图的单日数据 */
export interface ActivityDay {
  /** 本地日期 YYYY-MM-DD */
  date: string;
  count: number;
}

export interface Activity {
  /** 按日期升序，最后一条是今天 */
  days: ActivityDay[];
  today: string;
  today_count: number;
  total: number;
  active_days: number;
  /** 当前连续打卡天数（今天没做但昨天做了，仍算活着） */
  streak: number;
  best_streak: number;
  best_streak_end: string;
  timezone_minutes: number;
}

export interface FreeDraft {
  code: string;
  stdin: string;
  updated: string;
}
