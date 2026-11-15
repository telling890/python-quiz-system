import { AlertTriangle, CheckCircle2, Clock, Terminal, XCircle } from "lucide-react";
import type { JudgeCaseResult, JudgeResult, RunResult } from "../lib/types";
import { cls } from "./ui";
import { fmtDuration } from "../lib/format";

const CASE_TONE: Record<JudgeCaseResult["status"], { ring: string; text: string; label: string }> = {
  pass: { ring: "border-ok-500/40 bg-ok-500/10", text: "text-ok-400", label: "通过" },
  fail: { ring: "border-bad-500/40 bg-bad-500/10", text: "text-bad-400", label: "输出不符" },
  timeout: { ring: "border-warn-400/40 bg-warn-400/10", text: "text-warn-400", label: "超时" },
  error: { ring: "border-bad-500/40 bg-bad-500/10", text: "text-bad-400", label: "运行报错" },
};

function Line({ text, tone }: { text: string; tone?: string }) {
  return (
    <div className={cls("whitespace-pre-wrap break-all px-2 py-0.5 font-mono text-[0.78rem]", tone)}>
      {text === "" ? <span className="text-fg-dim">（空行）</span> : text}
    </div>
  );
}

/** 首行差异：把不同位置标红，方便一眼定位 */
function DiffView({ item }: { item: JudgeCaseResult }) {
  const expect = item.expect_lines ?? [];
  const actual = item.actual_lines ?? [];
  const rows = Math.max(expect.length, actual.length);
  const diffLine = item.first_diff ? item.first_diff.line - 1 : -1;

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <div className="overflow-hidden rounded-lg border border-line bg-ink-900">
        <div className="border-b border-line px-2 py-1 text-[0.68rem] font-semibold text-fg-dim">期望输出</div>
        <div className="max-h-48 overflow-auto py-1">
          {rows === 0 ? <Line text="" /> : null}
          {Array.from({ length: Math.max(rows, expect.length) }).map((_, i) => (
            <Line
              key={`e-${i}`}
              text={expect[i] ?? ""}
              tone={i === diffLine ? "bg-bad-500/15 text-bad-400" : "text-fg-muted"}
            />
          ))}
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-line bg-ink-900">
        <div className="border-b border-line px-2 py-1 text-[0.68rem] font-semibold text-fg-dim">实际输出</div>
        <div className="max-h-48 overflow-auto py-1">
          {rows === 0 ? <Line text="" /> : null}
          {Array.from({ length: Math.max(rows, actual.length) }).map((_, i) => (
            <Line
              key={`a-${i}`}
              text={actual[i] ?? ""}
              tone={i === diffLine ? "bg-bad-500/15 text-bad-400" : "text-fg-muted"}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function CaseCard({ item }: { item: JudgeCaseResult }) {
  const tone = CASE_TONE[item.status];
  return (
    <div className={cls("rounded-xl border px-3 py-2.5", tone.ring)}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-xs font-semibold">
          <span className={tone.text}>用例 {item.index + 1}</span>
          <span className={cls("rounded-full px-1.5 py-0.5 text-[0.66rem]", tone.text)}>{tone.label}</span>
        </span>
        {item.timeout ? (
          <span className="flex items-center gap-1 text-[0.68rem] text-warn-400">
            <Clock size={11} /> 超时
          </span>
        ) : null}
      </div>

      {item.status === "pass" ? (
        <p className="mt-1 truncate text-[0.7rem] text-fg-dim">
          输入 <code className="text-fg-muted">{item.stdin ? item.stdin.replace(/\n/g, "⏎") : "（无）"}</code>
        </p>
      ) : (
        <div className="mt-2 space-y-2">
          <div className="text-[0.7rem] text-fg-dim">
            输入：<code className="text-fg-muted">{item.stdin ? item.stdin.replace(/\n/g, "⏎") : "（无）"}</code>
          </div>
          {item.error ? (
            <pre className="max-h-40 overflow-auto rounded-lg border border-bad-500/30 bg-ink-950/60 px-2 py-1.5 font-mono text-[0.75rem] leading-relaxed text-bad-400">
              {item.error}
            </pre>
          ) : null}
          {item.status === "fail" ? <DiffView item={item} /> : null}
          {item.truncated ? (
            <p className="text-[0.68rem] text-warn-400">输出超过上限，已被截断（检查是不是打印太多）</p>
          ) : null}
        </div>
      )}
    </div>
  );
}

export function JudgeResultView({ result }: { result: JudgeResult }) {
  const passedCount = result.results.filter((r) => r.status === "pass").length;
  const ok = result.status === "passed";

  return (
    <div className="animate-fade-in space-y-3">
      <div
        className={cls(
          "flex flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2.5",
          ok ? "border-ok-500/40 bg-ok-500/10" : "border-bad-500/40 bg-bad-500/10",
        )}
      >
        <div className="flex items-center gap-2">
          {ok ? <CheckCircle2 size={17} className="text-ok-400" /> : <XCircle size={17} className="text-bad-400" />}
          <span className={cls("text-sm font-semibold", ok ? "text-ok-400" : "text-bad-400")}>
            {ok ? "全部用例通过" : result.status === "timeout" ? "执行超时" : result.status === "error" ? "代码报错" : "还有用例没通过"}
          </span>
          {result.total > 0 ? (
            <span className="text-xs tabular-nums text-fg-muted">
              {passedCount}/{result.total} 用例
            </span>
          ) : null}
        </div>
        <span className="text-[0.7rem] tabular-nums text-fg-dim">
          {result.duration_ms > 0 ? fmtDuration(result.duration_ms) : ""}
        </span>
      </div>

      {result.results.length === 0 && result.error ? (
        <pre className="overflow-auto rounded-lg border border-bad-500/30 bg-ink-950/60 px-3 py-2 font-mono text-[0.75rem] text-bad-400">
          {result.error}
        </pre>
      ) : null}

      <div className="space-y-2">
        {result.results.map((item) => (
          <CaseCard key={item.index} item={item} />
        ))}
      </div>
    </div>
  );
}

/** 自由编程的「直接跑一遍」结果 */
export function RunResultView({ run, label = "运行输出" }: { run: RunResult; label?: string }) {
  return (
    <div className="animate-fade-in space-y-2">
      <div className="flex items-center justify-between text-[0.7rem]">
        <span className="flex items-center gap-1.5 font-semibold text-fg-muted">
          <Terminal size={12} /> {label}
        </span>
        <span className="tabular-nums text-fg-dim">
          {run.timeout ? "超时" : run.error ? "有报错" : "正常结束"} · {fmtDuration(run.duration_ms)}
        </span>
      </div>
      {run.error ? (
        <pre className="max-h-56 overflow-auto rounded-lg border border-bad-500/30 bg-ink-950/60 px-3 py-2 font-mono text-[0.75rem] leading-relaxed text-bad-400">
          {run.error}
        </pre>
      ) : null}
      <pre className="max-h-72 min-h-16 overflow-auto rounded-lg border border-line bg-ink-950/60 px-3 py-2 font-mono text-[0.78rem] leading-relaxed text-fg-muted">
        {run.output ? run.output : <span className="text-fg-dim">（没有输出）</span>}
      </pre>
      {run.truncated ? (
        <p className="flex items-center gap-1 text-[0.68rem] text-warn-400">
          <AlertTriangle size={11} /> 输出过长已截断
        </p>
      ) : null}
    </div>
  );
}
