/** 判定与运行：在浏览器里逐用例执行（对应后端 judge/worker.py 的 judge_question / run_free_code） */
import type { CaseIn, JudgeCaseResult, JudgeResult, RunResult, Trace } from "../types";
import { ApiError } from "../core";
import { judgeCase } from "./compare";
import { runner } from "./runner";

export async function runLocal(code: string, stdin: string, timeoutMs = 15_000): Promise<RunResult> {
  try {
    const raw = await runner.call("run", code, stdin, timeoutMs);
    const parsed = JSON.parse(raw) as { output?: string; error?: string; duration_ms?: number };
    return {
      output: parsed.output ?? "",
      error: parsed.error ?? "",
      timeout: false,
      truncated: false,
      syntax: false,
      duration_ms: parsed.duration_ms ?? 0,
    };
  } catch (err) {
    const timeout = err instanceof ApiError && err.code === "timeout";
    return {
      output: "",
      error: timeout
        ? "执行超时（可能是死循环），已强制中断"
        : String((err as Error)?.message ?? err),
      timeout,
      truncated: false,
      syntax: false,
      duration_ms: 0,
    };
  }
}

export async function judgeLocal(code: string, cases: CaseIn[]): Promise<JudgeResult> {
  const results: JudgeCaseResult[] = [];
  let duration = 0;
  let passed = true;

  for (let i = 0; i < cases.length; i += 1) {
    const item = cases[i];
    const run = await runLocal(code, item.stdin ?? "", 20_000);
    duration += run.duration_ms;
    const verdict = judgeCase(
      i,
      item.stdin ?? "",
      item.expect ?? "",
      run.output,
      run.error,
      { timeout: run.timeout, truncated: run.truncated, raw: Boolean(item.raw) },
    );
    results.push(verdict);
    if (verdict.status !== "pass") {
      passed = false;
      break; // 与后端一致：第一个不通过就停
    }
  }

  const status: JudgeResult["status"] = results.some((r) => r.status === "timeout")
    ? "timeout"
    : results.some((r) => r.status === "error")
      ? "error"
      : passed
        ? "passed"
        : "failed";

  return { mode: "judge", passed, status, total: cases.length, results, duration_ms: duration };
}

export function describeTrace(trace: Trace): string {
  const steps = trace.steps ?? [];
  if (trace.error) return trace.error;
  if (trace.timeout) return `执行超时，追踪在第 ${steps.length} 步被打断（检查循环条件）`;
  if (trace.truncated) return `记录到前 ${steps.length} 步就停了（循环太长，或者写成了死循环）`;
  return "";
}

export async function traceLocal(
  code: string,
  stdin: string,
): Promise<{ trace: Trace; summary: string }> {
  const raw = await runner.call("trace", code, stdin, 20_000);
  const trace = JSON.parse(raw) as Trace;
  return { trace, summary: describeTrace(trace) };
}
