import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Bug,
  CheckCircle2,
  ChevronRight,
  Circle,
  Filter,
  Play,
  RotateCcw,
  Search,
  Send,
  Star,
  XCircle,
} from "lucide-react";
import { api, ApiError, awaitSubmission } from "../lib/api";
import { useBank } from "../lib/bank";
import type { JudgeResult, Question, RunResult, Trace } from "../lib/types";
import { Badge, Button, Card, EmptyState, Modal, ProgressBar, Segmented, Spinner, cls, useToast } from "../components/ui";
import { PageTitle } from "../components/Layout";
import QuestionBody from "../components/QuestionBody";
import CodeEditor from "../components/CodeEditor";
import { JudgeResultView, RunResultView } from "../components/JudgeResult";
import TraceViewer from "../components/TraceViewer";
import { STARTER_CODE, bucketOf, chapterColor, questionCode, statusMeta } from "../lib/format";
import type { Bucket } from "../lib/format";

type Busy = "idle" | "run" | "judge" | "trace";

const BUCKET_OPTIONS: Array<{ value: Bucket; label: string }> = [
  { value: "all", label: "全部" },
  { value: "todo", label: "未通过" },
  { value: "fail", label: "错题" },
  { value: "pass", label: "已通过" },
  { value: "favorite", label: "收藏" },
];

function StatusDot({ last }: { last: Question["last"] }) {
  if (last === "pass") return <CheckCircle2 size={14} className="shrink-0 text-ok-400" />;
  if (last === "fail") return <XCircle size={14} className="shrink-0 text-bad-400" />;
  return <Circle size={14} className="shrink-0 text-fg-dim/50" />;
}

export default function Practice() {
  const { qid } = useParams<{ qid: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { questions, chapters, stats, loading, patchQuestion, toggleFavorite, find } = useBank();

  const chapterFilter = searchParams.get("chapter") ?? "all";
  const bucket = (searchParams.get("bucket") as Bucket) || "all";
  const [keyword, setKeyword] = useState("");
  const [busy, setBusy] = useState<Busy>("idle");
  const [judgeResult, setJudgeResult] = useState<JudgeResult | null>(null);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [traceSummary, setTraceSummary] = useState("");
  const [traceOpen, setTraceOpen] = useState(false);
  const [listOpen, setListOpen] = useState(false);

  const current = qid ? find(qid) : undefined;
  const [code, setCode] = useState("");
  const draftRef = useRef<Record<string, string>>({});
  const abortRef = useRef<AbortController | null>(null);

  const filtered = useMemo(() => {
    const text = keyword.trim().toLowerCase();
    return questions.filter((q) => {
      if (chapterFilter !== "all" && q.chapter_id !== chapterFilter) return false;
      if (bucket !== "all" && !bucketOf(q).includes(bucket)) return false;
      if (!text) return true;
      return (
        q.title.toLowerCase().includes(text) ||
        q.topic.toLowerCase().includes(text) ||
        q.desc.toLowerCase().includes(text) ||
        questionCode(q).includes(text)
      );
    });
  }, [questions, chapterFilter, bucket, keyword]);

  // 没有指定题目时，自动进入第一道未通过的题
  useEffect(() => {
    if (qid || loading || questions.length === 0) return;
    const target = questions.find((q) => q.last !== "pass") ?? questions[0];
    navigate(`/practice/${encodeURIComponent(target.id)}`, { replace: true });
  }, [qid, loading, questions, navigate]);

  // 切换题目：恢复草稿 / 已保存代码 / 模板
  useEffect(() => {
    if (!current) return;
    const saved = draftRef.current[current.id] ?? current.code;
    setCode(saved && saved.trim() ? saved : STARTER_CODE);
    setJudgeResult(null);
    setRunResult(null);
    setTrace(null);
    setTraceOpen(false);
  }, [current?.id]);

  const stdinForRun = useMemo(() => {
    const first = current?.cases?.[0];
    return first?.stdin ?? "";
  }, [current]);

  const setQuery = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(searchParams);
      if (!value || value === "all") next.delete(key);
      else next.set(key, value);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const updateCode = (next: string) => {
    setCode(next);
    if (current) draftRef.current[current.id] = next;
  };

  const goto = (target: Question | undefined) => {
    if (!target) return;
    navigate(`/practice/${encodeURIComponent(target.id)}`);
  };

  const neighbor = (delta: number) => {
    if (!current || filtered.length === 0) return;
    const index = filtered.findIndex((q) => q.id === current.id);
    const next = filtered[Math.min(filtered.length - 1, Math.max(0, (index < 0 ? 0 : index) + delta))];
    goto(next);
  };

  const onFavorite = async () => {
    if (!current) return;
    try {
      await toggleFavorite(current.id);
      toast.ok(current.favorite ? "已取消收藏" : "已加入收藏");
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "收藏失败");
    }
  };

  const onRun = async () => {
    if (!current || busy !== "idle") return;
    if (!code.trim()) {
      toast.warn("先写点代码再运行");
      return;
    }
    setBusy("run");
    setRunResult(null);
    try {
      const res = await api.runFree(code, stdinForRun);
      setRunResult(res.run);
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "运行失败");
    } finally {
      setBusy("idle");
    }
  };

  const onJudge = async () => {
    if (!current || busy !== "idle") return;
    if (!code.trim()) {
      toast.warn("代码是空的，写点东西再判题");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy("judge");
    setJudgeResult(null);
    try {
      const created = await api.submit({ qid: current.id, code });
      const final = await awaitSubmission(created.id, { signal: controller.signal });
      const result = final.result as JudgeResult;
      setJudgeResult(result);
      const passed = final.status === "passed";
      const attempts = (current.attempts ?? 0) + 1;
      patchQuestion(current.id, {
        last: passed ? "pass" : "fail",
        attempts,
        code,
      });
      if (passed) toast.ok("全部用例通过 ✅");
      else toast.warn(final.error ? `没通过：${final.error}` : "还有用例没过，看看差异");
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return;
      toast.bad(err instanceof ApiError ? err.message : "判题失败");
    } finally {
      setBusy("idle");
    }
  };

  const onTrace = async () => {
    if (!current || busy !== "idle") return;
    if (!code.trim()) {
      toast.warn("先写点代码再追踪");
      return;
    }
    setBusy("trace");
    try {
      const res = await api.trace(code, stdinForRun);
      setTrace(res.trace);
      setTraceSummary(res.summary);
      setTraceOpen(true);
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "追踪失败");
    } finally {
      setBusy("idle");
    }
  };

  const resetCode = () => {
    if (!current) return;
    updateCode(current.code && current.code.trim() ? current.code : STARTER_CODE);
    setJudgeResult(null);
    setRunResult(null);
    toast.info("已恢复到上次保存的代码");
  };

  useEffect(() => () => abortRef.current?.abort(), []);

  const status = current ? statusMeta(current.last) : null;

  const listPanel = (
    <div className="flex h-full flex-col">
      <div className="space-y-2 border-b border-line px-3 py-3">
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-dim" />
          <input
            className="input py-1.5 pl-8 text-xs"
            placeholder="搜题号、标题、知识点…"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setQuery("chapter", "all")}
            className={cls(
              "rounded-md px-2 py-1 text-[0.7rem] transition-colors",
              chapterFilter === "all" ? "bg-brand-500/20 text-brand-300" : "text-fg-dim hover:bg-ink-800 hover:text-fg",
            )}
          >
            全部
          </button>
          {chapters.map((chapter) => (
            <button
              key={chapter.id}
              type="button"
              onClick={() => setQuery("chapter", chapter.id)}
              className={cls(
                "rounded-md px-2 py-1 text-[0.7rem] transition-colors",
                chapterFilter === chapter.id
                  ? "bg-brand-500/20 text-brand-300"
                  : "text-fg-dim hover:bg-ink-800 hover:text-fg",
              )}
            >
              {chapter.short}
            </button>
          ))}
        </div>
        <Segmented
          size="sm"
          value={bucket}
          onChange={(next) => setQuery("bucket", next)}
          options={BUCKET_OPTIONS}
          className="w-full"
        />
        <div className="flex items-center justify-between text-[0.66rem] text-fg-dim">
          <span>
            {filtered.length} 道 · 已通过 {stats.solved}/{stats.total}
          </span>
          <span className="tabular-nums">{Math.round((stats.solved / (stats.total || 1)) * 100)}%</span>
        </div>
        <ProgressBar value={stats.solved} max={stats.total || 1} height={4} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-1">
        {loading ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : filtered.length === 0 ? (
          <p className="px-3 py-8 text-center text-xs text-fg-dim">没有符合条件的题目</p>
        ) : (
          filtered.map((q) => {
            const active = q.id === current?.id;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => goto(q)}
                className={cls(
                  "flex w-full items-center gap-2 px-3 py-2 text-left transition-colors",
                  active ? "bg-brand-500/12" : "hover:bg-ink-800/60",
                )}
              >
                <StatusDot last={q.last} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="font-mono text-[0.66rem]"
                      style={{ color: chapterColor(chapters, q.chapter_id) }}
                    >
                      {questionCode(q)}
                    </span>
                    {q.favorite ? <Star size={10} className="fill-warn-400 text-warn-400" /> : null}
                    {q.attempts > 0 ? (
                      <span className="text-[0.62rem] text-fg-dim">×{q.attempts}</span>
                    ) : null}
                  </span>
                  <span
                    className={cls(
                      "block truncate text-[0.8rem]",
                      active ? "font-medium text-fg" : "text-fg-muted",
                    )}
                  >
                    {q.title}
                  </span>
                </span>
                <ChevronRight size={13} className="shrink-0 text-fg-dim/60" />
              </button>
            );
          })
        )}
      </div>
    </div>
  );

  return (
    <div className="animate-rise">
      <PageTitle
        title="刷题"
        subtitle="写完按 Ctrl+Enter 判题；单步追踪能看清每一行在干什么。"
        right={
          <>
            <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setListOpen(true)} icon={<Filter size={14} />}>
              题目列表
            </Button>
            <Button variant="ghost" size="sm" onClick={() => neighbor(-1)} disabled={!current}>
              <ArrowLeft size={14} /> 上一题
            </Button>
            <Button variant="ghost" size="sm" onClick={() => neighbor(1)} disabled={!current}>
              下一题 <ArrowRight size={14} />
            </Button>
          </>
        }
      />

      <div className="grid gap-3 lg:grid-cols-[19rem_1fr]">
        <Card className="hidden h-[calc(100dvh-11rem)] overflow-hidden lg:sticky lg:top-4 lg:block">
          {listPanel}
        </Card>

        <Modal open={listOpen} onClose={() => setListOpen(false)} title="选择题目" width="max-w-md">
          <div className="h-[60vh] -mx-5 -my-4">{listPanel}</div>
        </Modal>

        {current ? (
          <div className="grid min-w-0 gap-3 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] xl:items-start">
            <Card className="px-4 py-4 sm:px-5 xl:sticky xl:top-4 xl:max-h-[calc(100dvh-2rem)] xl:overflow-y-auto">
              {status && current.last === "fail" ? (
                <div className="mb-3 flex items-center gap-2 rounded-lg border border-bad-500/30 bg-bad-500/10 px-2.5 py-1.5 text-[0.72rem] text-bad-400">
                  <Bug size={13} /> 上次没通过（作答 {current.attempts} 次），改完再判一次。
                </div>
              ) : null}
              <QuestionBody
                question={current}
                chapters={chapters}
                favoriteSlot={
                  <button
                    type="button"
                    onClick={onFavorite}
                    className={cls(
                      "flex items-center gap-1 rounded-md border px-1.5 py-1 text-[0.66rem] transition-colors",
                      current.favorite
                        ? "border-warn-400/40 bg-warn-400/10 text-warn-400"
                        : "border-line text-fg-dim hover:text-fg",
                    )}
                  >
                    <Star size={11} className={current.favorite ? "fill-warn-400" : undefined} />
                    {current.favorite ? "已收藏" : "收藏"}
                  </button>
                }
              />
            </Card>

            <div className="min-w-0 space-y-3">
              <Card className="overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
                  <div className="flex items-center gap-1.5 text-[0.7rem] text-fg-dim">
                    <span className="font-mono text-fg-muted">main.py</span>
                    <span className="text-fg-dim/50">·</span>
                    <span>Ctrl+Enter 判题</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Button variant="ghost" size="sm" onClick={resetCode} icon={<RotateCcw size={13} />} disabled={busy !== "idle"}>
                      重置
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={onTrace}
                      loading={busy === "trace"}
                      disabled={busy !== "idle"}
                      icon={<Bug size={13} />}
                    >
                      单步追踪
                    </Button>
                    <Button
                      variant="soft"
                      size="sm"
                      onClick={onRun}
                      loading={busy === "run"}
                      disabled={busy !== "idle"}
                      icon={<Play size={13} />}
                    >
                      运行
                    </Button>
                    <Button size="sm" onClick={onJudge} loading={busy === "judge"} disabled={busy !== "idle"} icon={<Send size={13} />}>
                      判题
                    </Button>
                  </div>
                </div>
                <div className="p-2">
                  <CodeEditor
                    value={code}
                    onChange={updateCode}
                    onRun={onJudge}
                    height="clamp(240px, 46vh, 560px)"
                    placeholder="# 在这里写代码…"
                  />
                </div>
              </Card>

              {busy === "judge" ? (
                <Card className="flex items-center gap-2 px-4 py-3 text-xs text-fg-muted">
                  <Spinner size={14} /> 判题进行中：提交已进队列，正在轮询结果…
                </Card>
              ) : null}

              {judgeResult ? (
                <Card className="px-4 py-3 sm:px-5">
                  <JudgeResultView result={judgeResult} />
                </Card>
              ) : null}

              {runResult ? (
                <Card className="px-4 py-3 sm:px-5">
                  <RunResultView run={runResult} label="运行输出（stdin 取自用例 1）" />
                </Card>
              ) : null}

              <div className="flex items-center justify-between px-1 pb-2 text-[0.7rem] text-fg-dim">
                <span>{status ? <Badge tone={status.tone}>{status.label}</Badge> : null}</span>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => neighbor(-1)}>
                    上一题
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => neighbor(1)}>
                    下一题
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Card>
            <EmptyState
              icon={<Search size={20} />}
              title={loading ? "正在载入题库…" : "选一道题开始"}
              hint="左边列表里挑一道，或者直接从概览页点「继续刷题」。"
              action={
                questions.length > 0 ? (
                  <Button size="sm" onClick={() => goto(questions[0])}>
                    从第一题开始
                  </Button>
                ) : null
              }
            />
          </Card>
        )}
      </div>

      <Modal
        open={traceOpen}
        onClose={() => setTraceOpen(false)}
        title="执行过程单步追踪"
        width="max-w-5xl"
      >
        {trace ? <TraceViewer code={code} trace={trace} summary={traceSummary} /> : null}
      </Modal>
    </div>
  );
}
