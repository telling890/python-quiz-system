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

const TOKEN_KEY = "pyquiz.token";
const USER_KEY = "pyquiz.user";

/* ------------------------------------------------------------------ 令牌 */

export const tokenStore = {
  get(): string {
    try {
      return localStorage.getItem(TOKEN_KEY) || "";
    } catch {
      return "";
    }
  },
  set(token: string, user?: User) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      /* 隐私模式下 localStorage 可能不可写，忽略 */
    }
  },
  cachedUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      /* ignore */
    }
  },
};

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

let unauthorizedHandler: (() => void) | null = null;
export function onUnauthorized(fn: (() => void) | null) {
  unauthorizedHandler = fn;
}

/* ------------------------------------------------------------------ 请求 */

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  /** 不自动跳登录（登录接口自身用） */
  silentAuth?: boolean;
}

interface Envelope<T> {
  ok: boolean;
  data?: T;
  error?: { code?: string; message?: string; request_id?: string } | string;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, silentAuth } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") throw err;
    throw new ApiError("连不上服务器，检查后端是否在跑（http://127.0.0.1:8000）");
  }

  const text = await response.text();
  let payload: Envelope<T> | null = null;
  if (text) {
    try {
      payload = JSON.parse(text) as Envelope<T>;
    } catch {
      payload = null;
    }
  }

  if (response.status === 401 && !silentAuth) {
    tokenStore.clear();
    unauthorizedHandler?.();
  }

  if (!response.ok || !payload || payload.ok !== true) {
    const rawError = payload?.error;
    const message =
      typeof rawError === "string"
        ? rawError
        : rawError?.message || `请求失败（HTTP ${response.status}）`;
    throw new ApiError(message, {
      status: response.status,
      code: typeof rawError === "object" ? rawError?.code : undefined,
      requestId: typeof rawError === "object" ? rawError?.request_id : undefined,
    });
  }

  return payload.data as T;
}

/* ------------------------------------------------------------------ 认证 */

export const api = {
  register(input: { username: string; password: string; code?: string }) {
    return request<AuthPayload>("/api/v1/auth/register", {
      method: "POST",
      body: { username: input.username, password: input.password, code: input.code || "" },
      silentAuth: true,
    });
  },

  login(input: { username: string; password: string }) {
    return request<AuthPayload>("/api/v1/auth/login", {
      method: "POST",
      body: input,
      silentAuth: true,
    });
  },

  me() {
    return request<User>("/api/v1/auth/me", { silentAuth: true });
  },

  /* -------------------------------------------------------------- 题库/进度 */

  bank(signal?: AbortSignal) {
    return request<Bank>("/api/v1/bank", { signal });
  },

  question(qid: string) {
    return request<Question>(`/api/v1/questions/${encodeURIComponent(qid)}`);
  },

  progress() {
    return request<Progress>("/api/v1/progress");
  },

  setFavorite(qid: string, favorite: boolean) {
    return request<{ qid: string; favorite: boolean }>(
      `/api/v1/progress/${encodeURIComponent(qid)}/favorite`,
      { method: "POST", body: { favorite } },
    );
  },

  /* -------------------------------------------------------------- 判题 */

  submit(input: { qid?: string; code: string; stdin?: string }) {
    return request<Submission>("/api/v1/submissions", {
      method: "POST",
      body: { qid: input.qid ?? null, code: input.code, stdin: input.stdin ?? "" },
    });
  },

  submission(id: string) {
    return request<Submission>(`/api/v1/submissions/${encodeURIComponent(id)}`);
  },

  submissions(limit = 30) {
    return request<{ items: Submission[]; limit: number }>(`/api/v1/submissions?limit=${limit}`);
  },

  runFree(code: string, stdin = "") {
    return request<{ mode: string; run: RunResult }>("/api/v1/run", {
      method: "POST",
      body: { code, stdin },
    });
  },

  /* -------------------------------------------------------------- 片段/草稿 */

  snippets() {
    return request<{ snippets: Snippet[] }>("/api/v1/snippets");
  },

  saveSnippet(name: string, code: string) {
    return request<{ created: boolean; name: string }>("/api/v1/snippets", {
      method: "POST",
      body: { name, code },
    });
  },

  deleteSnippet(name: string) {
    return request<{ removed: boolean; name: string }>(
      `/api/v1/snippets/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    );
  },

  freeDraft() {
    return request<FreeDraft>("/api/v1/free");
  },

  saveFreeDraft(code: string, stdin: string) {
    return request<{ saved: boolean; updated: string }>("/api/v1/free", {
      method: "PUT",
      body: { code, stdin },
    });
  },

  /* -------------------------------------------------------------- 其它统计 */

  /**
   * 单步执行追踪：只有兼容层 /api/trace 提供（v1 暂无等价接口）。
   * 它不走 {ok,data} 信封，所以单独发请求、单独解析。
   */
  async trace(code: string, stdin = ""): Promise<TraceResponse> {
    const token = tokenStore.get();
    const response = await fetch("/api/trace", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ code, stdin }),
    });
    const payload = (await response.json()) as {
      ok?: boolean;
      error?: string;
      trace?: TraceResponse["trace"];
      summary?: string;
    };
    if (!response.ok || !payload.ok || !payload.trace) {
      throw new ApiError(payload.error || `单步执行失败（HTTP ${response.status}）`, {
        status: response.status,
      });
    }
    return { trace: payload.trace, summary: payload.summary ?? "" };
  },
};

/* ------------------------------------------------------------------ 轮询 */

const TERMINAL = new Set(["passed", "failed", "timeout", "error"]);

export function isTerminal(status: string): boolean {
  return TERMINAL.has(status);
}

/**
 * 判题是异步的：POST 拿到 id 后轮询结果。
 * 后端按 IP 限流 120 次/分钟，所以起步 800ms、逐步放宽到 1.6s。
 */
export async function awaitSubmission(
  id: string,
  options: { signal?: AbortSignal; timeoutMs?: number; onTick?: (s: Submission) => void } = {},
): Promise<Submission> {
  const { signal, timeoutMs = 60_000, onTick } = options;
  const started = Date.now();
  let delay = 800;
  for (;;) {
    const item = await api.submission(id);
    onTick?.(item);
    if (isTerminal(item.status)) return item;
    if (Date.now() - started > timeoutMs) {
      throw new ApiError("判题排队太久，稍后再试（结果仍会保留在服务器上）");
    }
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, delay);
      signal?.addEventListener(
        "abort",
        () => {
          clearTimeout(timer);
          reject(new DOMException("aborted", "AbortError"));
        },
        { once: true },
      );
    });
    delay = Math.min(1600, delay + 250);
  }
}
