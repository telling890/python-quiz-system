import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight, Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";
import type { Trace } from "../lib/types";
import { Button, cls } from "./ui";

const EVENT_LABEL: Record<string, { label: string; tone: string }> = {
  call: { label: "进入函数", tone: "text-aqua-400" },
  line: { label: "下一行", tone: "text-fg-muted" },
  return: { label: "返回", tone: "text-warn-400" },
  exception: { label: "异常", tone: "text-bad-400" },
};

/** 单步执行追踪播放器：左侧源码高亮当前行，右侧变量与累计输出 */
export default function TraceViewer({ code, trace, summary }: { code: string; trace: Trace; summary: string }) {
  const steps = trace.steps ?? [];
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(400);
  const codeRef = useRef<HTMLDivElement>(null);

  const step = steps[Math.min(index, Math.max(steps.length - 1, 0))];
  const lines = useMemo(() => code.split("\n"), [code]);
  const last = steps.length - 1;

  useEffect(() => {
    if (!playing) return;
    if (index >= last) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => setIndex((i) => Math.min(i + 1, last)), speed);
    return () => window.clearTimeout(timer);
  }, [playing, index, last, speed]);

  useEffect(() => {
    const el = codeRef.current?.querySelector<HTMLElement>("[data-active='true']");
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [index]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") setIndex((i) => Math.min(i + 1, last));
      if (event.key === "ArrowLeft") setIndex((i) => Math.max(i - 1, 0));
      if (event.key === " ") {
        event.preventDefault();
        setPlaying((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [last]);

  const meta = step ? EVENT_LABEL[step.event] ?? { label: step.event, tone: "text-fg-muted" } : null;

  return (
    <div className="space-y-3">
      {summary ? (
        <div className="rounded-lg border border-warn-400/40 bg-warn-400/10 px-3 py-2 text-xs text-warn-400">
          {summary}
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-[1.15fr_1fr]">
        {/* 源码 */}
        <div className="overflow-hidden rounded-xl border border-line bg-ink-950/70">
          <div className="flex items-center justify-between border-b border-line px-3 py-1.5 text-[0.68rem] text-fg-dim">
            <span className="font-mono">main.py</span>
            <span className="tabular-nums">
              {steps.length > 0 ? `第 ${index + 1} / ${steps.length} 步` : "没有记录到执行步骤"}
            </span>
          </div>
          <div ref={codeRef} className="max-h-[46vh] overflow-auto py-1">
            {lines.map((text, i) => {
              const lineNo = i + 1;
              const active = step?.line === lineNo;
              return (
                <div
                  key={i}
                  data-active={active ? "true" : "false"}
                  className={cls(
                    "flex gap-3 px-2 font-mono text-[0.76rem] leading-[1.55]",
                    active ? "bg-brand-500/20" : "hover:bg-ink-800/40",
                  )}
                >
                  <span
                    className={cls(
                      "w-8 shrink-0 select-none text-right tabular-nums",
                      active ? "text-brand-300" : "text-fg-dim/60",
                    )}
                  >
                    {lineNo}
                  </span>
                  <span className={cls("whitespace-pre-wrap break-words", active ? "text-fg" : "text-fg-muted")}>
                    {text || " "}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* 变量面板 */}
        <div className="flex flex-col gap-2">
          <div className="rounded-xl border border-line bg-ink-900/60 px-3 py-2">
            <div className="flex items-center justify-between">
              <span className="text-[0.7rem] font-semibold text-fg-muted">
                {step ? (
                  <>
                    行 {step.line} · <span className={meta?.tone}>{meta?.label}</span> · {step.func}()
                  </>
                ) : (
                  "等待执行"
                )}
              </span>
              {step && step.depth > 0 ? (
                <span className="rounded bg-aqua-400/15 px-1.5 py-0.5 text-[0.64rem] text-aqua-400">
                  嵌套 {step.depth} 层
                </span>
              ) : null}
            </div>
          </div>

          <div className="min-h-24 rounded-xl border border-line bg-ink-900/60">
            <div className="border-b border-line px-3 py-1.5 text-[0.68rem] font-semibold text-fg-dim">局部变量</div>
            <div className="max-h-44 overflow-auto p-2">
              {step && step.vars.length > 0 ? (
                <ul className="space-y-1">
                  {step.vars.map(([name, value]) => (
                    <li key={name} className="flex items-start gap-2 rounded-lg bg-ink-950/50 px-2 py-1">
                      <span className="shrink-0 font-mono text-[0.72rem] text-brand-300">{name}</span>
                      <span className="ml-auto max-w-[60%] break-all text-right font-mono text-[0.72rem] text-fg-muted">
                        {value}
                      </span>
                    </li>
                  ))}
                  {step.hidden > 0 ? (
                    <li className="px-2 text-[0.66rem] text-fg-dim">还有 {step.hidden} 个变量未展示</li>
                  ) : null}
                </ul>
              ) : (
                <p className="px-1 py-2 text-[0.72rem] text-fg-dim">当前作用域还没有变量</p>
              )}
            </div>
          </div>

          <div className="min-h-24 flex-1 rounded-xl border border-line bg-ink-900/60">
            <div className="border-b border-line px-3 py-1.5 text-[0.68rem] font-semibold text-fg-dim">累计输出</div>
            <pre className="max-h-44 overflow-auto px-3 py-2 font-mono text-[0.74rem] leading-relaxed text-fg-muted">
              {step?.out ? step.out : <span className="text-fg-dim">（还没有输出）</span>}
            </pre>
          </div>
        </div>
      </div>

      {trace.error ? (
        <pre className="max-h-32 overflow-auto rounded-lg border border-bad-500/30 bg-ink-950/60 px-3 py-2 font-mono text-[0.74rem] text-bad-400">
          {trace.error}
        </pre>
      ) : null}

      {trace.truncated || trace.timeout ? (
        <p className="flex items-center gap-1.5 text-[0.7rem] text-warn-400">
          <AlertTriangle size={12} />
          {trace.timeout ? "执行超时，追踪被提前中断" : "步数达到上限，追踪被截断"}
        </p>
      ) : null}

      {/* 控制条 */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-ink-900/60 px-3 py-2">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setIndex(0)} disabled={index === 0} title="回到第一步">
            <RotateCcw size={14} />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
            <ChevronLeft size={16} />
          </Button>
          <Button
            variant={playing ? "soft" : "primary"}
            size="sm"
            onClick={() => setPlaying((p) => !p)}
            disabled={steps.length === 0}
            icon={playing ? <Pause size={14} /> : <Play size={14} />}
          >
            {playing ? "暂停" : "播放"}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIndex((i) => Math.min(last, i + 1))}
            disabled={index >= last}
          >
            <ChevronRight size={16} />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setIndex(last)} disabled={index >= last} title="跳到末尾">
            <SkipForward size={14} />
          </Button>
        </div>

        <input
          type="range"
          min={0}
          max={Math.max(last, 0)}
          value={Math.min(index, Math.max(last, 0))}
          onChange={(e) => setIndex(Number(e.target.value))}
          className="h-1.5 min-w-32 flex-1 cursor-pointer appearance-none rounded-full bg-ink-700 accent-brand-500"
          aria-label="执行步骤"
        />

        <div className="flex items-center gap-1.5 text-[0.68rem] text-fg-dim">
          <SkipBack size={12} />
          <select
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="rounded-md border border-line bg-ink-900 px-1.5 py-1 text-[0.68rem] text-fg-muted"
            aria-label="播放速度"
          >
            <option value={800}>0.5×</option>
            <option value={400}>1×</option>
            <option value={180}>2×</option>
            <option value={80}>5×</option>
          </select>
        </div>
      </div>
      <p className="text-[0.66rem] text-fg-dim">键盘 ← → 切步，空格播放/暂停。追踪最多记录 800 步、5 秒。</p>
    </div>
  );
}
