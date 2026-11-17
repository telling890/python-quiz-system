/** 有后端时的 HTTP 实现（v1 接口 + 异步判题轮询） */
import { ApiError, fireUnauthorized, isTerminal, tokenStore } from "./core";
import type {
  Activity,
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

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
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
    fireUnauthorized();
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

export const httpApi = {
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

  bank(signal?: AbortSignal) {
    return request<Bank>("/api/v1/bank", { signal });
  },

  question(qid: string) {
    return request<Question>(`/api/v1/questions/${encodeURIComponent(qid)}`);
  },

  progress() {
    return request<Progress>("/api/v1/progress");
  },

  activity(days = 182) {
    // 时区偏移交给服务端：否则北京时间凌晨做的题会被算到前一天
    const tz = -new Date().getTimezoneOffset();
    return request<Activity>(`/api/v1/activity?days=${days}&tz=${tz}`);
  },

  setFavorite(qid: string, favorite: boolean) {
    return request<{ qid: string; favorite: boolean }>(
      `/api/v1/progress/${encodeURIComponent(qid)}/favorite`,
      { method: "POST", body: { favorite } },
    );
  },

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

/**
 * 判题是异步的：POST 拿到 id 后轮询结果。
 * 后端按 IP 限流 120 次/分钟，所以起步 800ms、逐步放宽到 1.6s。
 */
export async function httpAwaitSubmission(
  id: string,
  options: { signal?: AbortSignal; timeoutMs?: number; onTick?: (s: Submission) => void } = {},
): Promise<Submission> {
  const { signal, timeoutMs = 60_000, onTick } = options;
  const started = Date.now();
  let delay = 800;
  for (;;) {
    const item = await httpApi.submission(id);
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
