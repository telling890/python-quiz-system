import type { User } from "./types";

/* ------------------------------------------------------------------ 构建模式 */

/** 静态版（GitHub Pages）：没有后端，题库内置、进度存 localStorage、判题用 Pyodide 在浏览器里跑 */
export const IS_STATIC = import.meta.env.VITE_STATIC === "1";

/** 站点根路径：/app/ 或 /python-quiz-system/ 或 / */
export const BASE_URL = import.meta.env.BASE_URL || "/";

/** 前端路由 basename（去掉尾部斜杠，根路径时为空串） */
export const BASENAME = BASE_URL.replace(/\/$/, "");

/* ------------------------------------------------------------------ 错误 */

export class ApiError extends Error {
  status: number;
  code: string;
  requestId: string;

  constructor(message: string, opts: { status?: number; code?: string; requestId?: string } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = opts.status ?? 0;
    this.code = opts.code ?? "network_error";
    this.requestId = opts.requestId ?? "";
  }

  get isAuth() {
    return this.status === 401;
  }

  get isRateLimited() {
    return this.status === 429;
  }
}

/* ------------------------------------------------------------------ 令牌 */

export const tokenStore = {
  get(): string {
    try {
      return localStorage.getItem("pyquiz.token") || "";
    } catch {
      return "";
    }
  },
  set(token: string, user?: User) {
    try {
      localStorage.setItem("pyquiz.token", token);
      if (user) localStorage.setItem("pyquiz.user", JSON.stringify(user));
    } catch {
      /* 隐私模式忽略 */
    }
  },
  cachedUser(): User | null {
    try {
      const raw = localStorage.getItem("pyquiz.user");
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  },
  clear() {
    try {
      localStorage.removeItem("pyquiz.token");
      localStorage.removeItem("pyquiz.user");
    } catch {
      /* ignore */
    }
  },
};

let unauthorizedHandler: (() => void) | null = null;
export function onUnauthorized(fn: (() => void) | null) {
  unauthorizedHandler = fn;
}
export function fireUnauthorized() {
  unauthorizedHandler?.();
}

/* ------------------------------------------------------------------ 判题状态 */

const TERMINAL = new Set(["passed", "failed", "timeout", "error"]);

export function isTerminal(status: string): boolean {
  return TERMINAL.has(status);
}
