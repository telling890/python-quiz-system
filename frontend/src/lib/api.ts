/**
 * 前端唯一的接口层。
 *
 * 两种运行模式，页面代码完全一样：
 *  - 默认：走 HTTP（FastAPI 的 /api/v1 + 异步判题轮询）
 *  - VITE_STATIC=1：静态版（GitHub Pages），题库内置、进度存浏览器、
 *    判题用 Pyodide 在浏览器里跑 Python（见 lib/static/）
 */
import { IS_STATIC } from "./core";
import { httpApi, httpAwaitSubmission } from "./httpApi";
import { staticApi, staticAwaitSubmission } from "./static/apiStatic";
import type {
  AuthPayload,
  Bank,
  FreeDraft,
  Progress,
  Question,
  RunResult,
  Snippet,
  Submission,
  TraceResponse,
  User,
} from "./types";

export { ApiError, tokenStore, onUnauthorized, isTerminal } from "./core";
export { IS_STATIC, BASE_URL, BASENAME, SITE_URL } from "./core";

/** 两个实现共同遵守的契约（页面只认它） */
export interface QuizApi {
  register(input: { username: string; password?: string; code?: string }): Promise<AuthPayload>;
  login(input: { username: string; password?: string }): Promise<AuthPayload>;
  me(): Promise<User>;
  bank(signal?: AbortSignal): Promise<Bank>;
  question(qid: string): Promise<Question>;
  progress(): Promise<Progress>;
  setFavorite(qid: string, favorite: boolean): Promise<{ qid: string; favorite: boolean }>;
  submit(input: { qid?: string; code: string; stdin?: string }): Promise<Submission>;
  submission(id: string): Promise<Submission>;
  submissions(limit?: number): Promise<{ items: Submission[]; limit: number }>;
  runFree(code: string, stdin?: string): Promise<{ mode: string; run: RunResult }>;
  snippets(): Promise<{ snippets: Snippet[] }>;
  saveSnippet(name: string, code: string): Promise<{ created: boolean; name: string }>;
  deleteSnippet(name: string): Promise<{ removed: boolean; name: string }>;
  freeDraft(): Promise<FreeDraft>;
  saveFreeDraft(code: string, stdin: string): Promise<{ saved: boolean; updated: string }>;
  trace(code: string, stdin?: string): Promise<TraceResponse>;
}

export const api: QuizApi = IS_STATIC ? (staticApi as QuizApi) : (httpApi as QuizApi);

/** 判题结果：HTTP 版轮询，静态版当场在浏览器里算完 */
export const awaitSubmission = IS_STATIC ? staticAwaitSubmission : httpAwaitSubmission;
