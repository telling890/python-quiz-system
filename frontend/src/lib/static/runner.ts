/** 主线程侧的解释器管理：串行排队 + 超时看门狗（超时就杀掉 Worker 重建，绝不冻住页面） */
import { ApiError } from "../core";

type Kind = "run" | "trace";

interface Job {
  id: number;
  kind: Kind;
  code: string;
  stdin: string;
  timeoutMs: number;
  resolve: (value: string) => void;
  reject: (reason: unknown) => void;
  timer?: number;
}

/** 首次调用要把 10MB 左右的 Pyodide 拉下来，给足时间 */
const BOOT_TIMEOUT = 120_000;
const DEFAULT_TIMEOUT = 15_000;

class PyRunner {
  private worker: Worker | null = null;
  private queue: Job[] = [];
  private current: Job | null = null;
  private seq = 0;
  private booted = false;

  /** 跑一段代码，返回 worker 里的 JSON 字符串 */
  call(kind: Kind, code: string, stdin: string, timeoutMs = DEFAULT_TIMEOUT): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      this.queue.push({ id: ++this.seq, kind, code, stdin, timeoutMs, resolve, reject });
      this.drain();
    });
  }

  private ensureWorker(): Worker {
    if (this.worker) return this.worker;
    const worker = new Worker(new URL("./pyodide.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent) => this.onMessage(event.data);
    worker.onerror = (event: ErrorEvent) => {
      this.fail("解释器加载失败：" + (event.message || "未知错误"));
      this.dispose();
    };
    this.worker = worker;
    return worker;
  }

  private drain() {
    if (this.current || this.queue.length === 0) return;
    const job = this.queue.shift()!;
    this.current = job;
    const worker = this.ensureWorker();
    const limit = this.booted ? job.timeoutMs : BOOT_TIMEOUT;
    job.timer = window.setTimeout(() => {
      this.fail("执行超时（可能是死循环），已强制中断。浏览器版没有服务端沙箱，请自己检查循环条件。");
      this.dispose();
    }, limit);
    worker.postMessage({ id: job.id, kind: job.kind, code: job.code, stdin: job.stdin });
  }

  private onMessage(data: { id: number; ok: boolean; data?: string; error?: string }) {
    const job = this.current;
    if (!job || data.id !== job.id) return;
    if (job.timer) window.clearTimeout(job.timer);
    this.current = null;
    this.booted = true;
    if (data.ok) job.resolve(data.data ?? "");
    else job.reject(new ApiError(data.error || "解释器执行失败"));
    this.drain();
  }

  private fail(message: string) {
    const job = this.current;
    if (job) {
      if (job.timer) window.clearTimeout(job.timer);
      this.current = null;
      job.reject(new ApiError(message, { code: "timeout" }));
    }
    this.drain();
  }

  /** 杀掉当前 Worker；下次调用会重新加载 Pyodide */
  private dispose() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
    this.booted = false;
  }

  /** 预热：进刷题页时就开始下载解释器，别等按下判题 */
  warmup() {
    if (this.worker) return;
    const worker = this.ensureWorker();
    worker.postMessage({ id: -1, kind: "run", code: "pass", stdin: "" });
  }
}

export const runner = new PyRunner();
