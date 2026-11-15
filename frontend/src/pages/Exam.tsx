import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Award,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileText,
  Play,
  RotateCcw,
  Send,
  Timer,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import { api, ApiError, awaitSubmission } from "../lib/api";
import { useBank } from "../lib/bank";
import type { JudgeResult, Question } from "../lib/types";
import { Badge, Button, Card, CardHeader, Modal, ProgressBar, Segmented, Spinner, cls, useToast } from "../components/ui";
import { PageTitle } from "../components/Layout";
import QuestionBody from "../components/QuestionBody";
import CodeEditor from "../components/CodeEditor";
import { chapterColor, fmtDuration, questionCode, STARTER_CODE } from "../lib/format";

type Strategy = "weighted" | "random" | "order" | "untouched";
type Screen = "setup" | "running" | "report";

interface Item {
  qid: string;
  code: string;
  status: "todo" | "pass" | "fail";
  casesPassed: number;
  casesTotal: number;
  durationMs: number;
}

interface Paper {
  size: number;
  chapters: string[];
  strategy: Strategy;
  minutes: number;
  items: Item[];
  startedAt: number;
  finishedAt: number;
}

const STORAGE_KEY = "pyquiz.exam.paper.v1";

const STRATEGY_OPTIONS: Array<{ value: Strategy; label: string; hint: string }> = [
  { value: "weighted", label: "错题加权", hint: "没通过的题出现概率更高，适合突击" },
  { value: "random", label: "随机抽题", hint: "题库里均匀抽，覆盖面广" },
  { value: "order", label: "顺序出卷", hint: "按章节顺序，适合系统复习" },
  { value: "untouched", label: "只考没做过", hint: "还没碰过的题优先，摸底用" },
];

function loadPaper(): Paper | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Paper;
    if (!parsed?.items?.length) return null;
    return parsed;
  } catch {
    return null;
  }
}

function savePaper(paper: Paper | null) {
  try {
    if (paper) localStorage.setItem(STORAGE_KEY, JSON.stringify(paper));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* 隐私模式忽略 */
  }
}

function pickWeighted(pool: Question[], size: number, strategy: Strategy): Question[] {
  if (strategy === "order") {
    return [...pool].sort((a, b) => a.id.localeCompare(b.id)).slice(0, size);
  }
  const weighted = pool.map((q) => ({
    q,
    weight:
      strategy === "random"
        ? 1
        : strategy === "untouched"
          ? q.attempts === 0
            ? 3
            : 0.05
          : q.last === "fail"
            ? 4
            : q.attempts === 0
              ? 2
              : 0.6,
  }));
  const picked: Question[] = [];
  const remaining = [...weighted];
  while (picked.length < size && remaining.length > 0) {
    const total = remaining.reduce((sum, item) => sum + item.weight, 0);
    let ticket = Math.random() * total;
    let index = 0;
    for (let i = 0; i < remaining.length; i += 1) {
      ticket -= remaining[i].weight;
      if (ticket <= 0) {
        index = i;
        break;
      }
    }
    picked.push(remaining[index].q);
    remaining.splice(index, 1);
  }
  return picked;
}

export default function Exam() {
  const { questions, chapters, loading } = useBank();
  const toast = useToast();
  const navigate = useNavigate();

  const [screen, setScreen] = useState<Screen>("setup");
  const [paper, setPaper] = useState<Paper | null>(null);
  const [index, setIndex] = useState(0);
  const [size, setSize] = useState(10);
  const [strategy, setStrategy] = useState<Strategy>("weighted");
  const [minutes, setMinutes] = useState(30);
  const [selected, setSelected] = useState<string[]>([]);
  const [judging, setJudging] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [review, setReview] = useState<JudgeResult | null>(null);
  const codeDraft = useRef<Record<string, string>>({});

  // 恢复未交的试卷
  useEffect(() => {
    const saved = loadPaper();
    if (saved && !saved.finishedAt) {
      setPaper(saved);
      setScreen("running");
      setIndex(0);
      toast.info("已恢复上次还没交的试卷");
    }
  }, [toast]);

  useEffect(() => {
    if (screen !== "running") return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [screen]);

  const currentItem = paper?.items[index];
  const currentQuestion = useMemo(
    () => (currentItem ? questions.find((q) => q.id === currentItem.qid) : undefined),
    [currentItem, questions],
  );

  const remainingMs = paper && paper.minutes > 0 ? paper.startedAt + paper.minutes * 60_000 - now : -1;

  const updatePaper = useCallback((updater: (prev: Paper) => Paper) => {
    setPaper((prev) => {
      if (!prev) return prev;
      const next = updater(prev);
      savePaper(next);
      return next;
    });
  }, []);

  const submitPaper = useCallback(
    (auto = false) => {
      if (!paper) return;
      const final: Paper = { ...paper, finishedAt: Date.now() };
      savePaper(final);
      setPaper(final);
      setScreen("report");
      setConfirmOpen(false);
      toast[auto ? "warn" : "ok"](auto ? "时间到，已自动交卷" : "已交卷，看看成绩吧");
    },
    [paper, toast],
  );

  // 倒计时归零自动交卷
  useEffect(() => {
    if (screen === "running" && remainingMs >= 0 && remainingMs <= 0) {
      submitPaper(true);
    }
  }, [screen, remainingMs, submitPaper]);

  const generate = () => {
    const chapterPool = selected.length > 0 ? selected : chapters.map((c) => c.id);
    const pool = questions.filter((q) => chapterPool.includes(q.chapter_id));
    if (pool.length === 0) {
      toast.warn("这个范围里没有题目，换个章节试试");
      return;
    }
    const chosen = pickWeighted(pool, Math.min(size, pool.length), strategy);
    const items: Item[] = chosen.map((q) => ({
      qid: q.id,
      code: q.code && q.code.trim() ? q.code : STARTER_CODE,
      status: "todo",
      casesPassed: 0,
      casesTotal: q.cases.length,
      durationMs: 0,
    }));
    const next: Paper = {
      size: items.length,
      chapters: chapterPool,
      strategy,
      minutes,
      items,
      startedAt: Date.now(),
      finishedAt: 0,
    };
    savePaper(next);
    setPaper(next);
    setIndex(0);
    setReview(null);
    setScreen("running");
    toast.ok(`已生成 ${items.length} 道题的试卷${minutes > 0 ? `，限时 ${minutes} 分钟` : "，不限时"}`);
  };

  const onJudge = async () => {
    if (!paper || !currentItem || !currentQuestion || judging) return;
    const code = currentItem.code;
    if (!code.trim()) {
      toast.warn("还没写代码");
      return;
    }
    setJudging(true);
    setReview(null);
    try {
      const created = await api.submit({ qid: currentItem.qid, code });
      const final = await awaitSubmission(created.id);
      const result = final.result as JudgeResult;
      const passed = final.status === "passed";
      const casesPassed = result.results?.filter((r) => r.status === "pass").length ?? 0;
      setReview(result);
      updatePaper((prev) => ({
        ...prev,
        items: prev.items.map((item, i) =>
          i === index
            ? {
                ...item,
                status: passed ? "pass" : "fail",
                casesPassed,
                casesTotal: result.total ?? item.casesTotal,
                durationMs: final.duration_ms,
              }
            : item,
        ),
      }));
      toast[passed ? "ok" : "warn"](passed ? "这题过了" : `用例 ${casesPassed}/${result.total} 通过`);
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "判题失败");
    } finally {
      setJudging(false);
    }
  };

  const goto = (next: number) => {
    if (!paper) return;
    const clamped = Math.min(paper.items.length - 1, Math.max(0, next));
    setIndex(clamped);
    setReview(null);
  };

  const restart = () => {
    savePaper(null);
    setPaper(null);
    setScreen("setup");
    setReview(null);
  };

  const answered = paper ? paper.items.filter((item) => item.status !== "todo").length : 0;
  const passed = paper ? paper.items.filter((item) => item.status === "pass").length : 0;
  const score = paper && paper.items.length > 0 ? Math.round((passed / paper.items.length) * 100) : 0;
  const usedMs = paper ? (paper.finishedAt || now) - paper.startedAt : 0;

  /* ------------------------------------------------------------ 配置页 */
  if (screen === "setup" || !paper) {
    return (
      <div className="animate-rise">
        <PageTitle
          title="模拟组卷"
          subtitle="按范围与策略抽一套卷子，逐题判分，交卷后出报告。"
          right={
            loadPaper()?.finishedAt ? (
              <Button variant="ghost" size="sm" onClick={restart} icon={<RotateCcw size={14} />}>
                清空上次试卷
              </Button>
            ) : null
          }
        />

        <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
          <Card className="px-4 py-4 sm:px-5">
            <h2 className="text-[0.95rem] font-semibold">组卷配置</h2>

            <div className="mt-4 space-y-4">
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-xs font-medium text-fg-muted">题目数量</span>
                  <span className="text-xs tabular-nums text-brand-300">{size} 道</span>
                </div>
                <input
                  type="range"
                  min={3}
                  max={30}
                  step={1}
                  value={size}
                  onChange={(e) => setSize(Number(e.target.value))}
                  className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-ink-700 accent-brand-500"
                />
                <div className="mt-1 flex justify-between text-[0.62rem] text-fg-dim">
                  <span>3</span>
                  <span>建议 10～15 道</span>
                  <span>30</span>
                </div>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-xs font-medium text-fg-muted">章节范围</span>
                  <button
                    type="button"
                    className="text-[0.66rem] text-brand-300 hover:underline"
                    onClick={() => setSelected([])}
                  >
                    全选（不限）
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {chapters.map((chapter) => {
                    const active = selected.length === 0 || selected.includes(chapter.id);
                    return (
                      <button
                        key={chapter.id}
                        type="button"
                        onClick={() =>
                          setSelected((prev) => {
                            if (prev.length === 0) return [chapter.id];
                            const next = prev.includes(chapter.id)
                              ? prev.filter((id) => id !== chapter.id)
                              : [...prev, chapter.id];
                            return next.length === chapters.length ? [] : next;
                          })
                        }
                        className={cls(
                          "rounded-lg border px-2.5 py-1 text-[0.72rem] transition-colors",
                          active
                            ? "border-brand-500/40 bg-brand-500/15 text-brand-300"
                            : "border-line text-fg-dim hover:text-fg",
                        )}
                      >
                        {chapter.name}
                        <span className="ml-1 text-[0.62rem] opacity-70">{chapter.count}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="mb-1.5 block text-xs font-medium text-fg-muted">出题策略</span>
                <div className="grid gap-1.5 sm:grid-cols-2">
                  {STRATEGY_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setStrategy(opt.value)}
                      className={cls(
                        "rounded-xl border px-3 py-2 text-left transition-colors",
                        strategy === opt.value
                          ? "border-brand-500/40 bg-brand-500/12"
                          : "border-line hover:bg-ink-800/50",
                      )}
                    >
                      <span className={cls("text-[0.8rem] font-medium", strategy === opt.value ? "text-brand-300" : "text-fg")}>
                        {opt.label}
                      </span>
                      <span className="mt-0.5 block text-[0.64rem] text-fg-dim">{opt.hint}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span className="mb-1.5 block text-xs font-medium text-fg-muted">限时</span>
                <Segmented
                  value={String(minutes)}
                  onChange={(value) => setMinutes(Number(value))}
                  options={[
                    { value: "0", label: "不限时" },
                    { value: "15", label: "15 分钟" },
                    { value: "30", label: "30 分钟" },
                    { value: "45", label: "45 分钟" },
                  ]}
                />
              </div>
            </div>

            <div className="mt-5 flex items-center gap-2">
              <Button onClick={generate} loading={loading} disabled={questions.length === 0} icon={<FileText size={15} />} size="lg">
                生成试卷
              </Button>
              <span className="text-[0.68rem] text-fg-dim">
                从 {selected.length > 0 ? selected.length : chapters.length} 个章节里抽 {size} 道
              </span>
            </div>
          </Card>

          <Card>
            <CardHeader title="试卷说明" subtitle="建议按真实考试节奏做" icon={<Award size={16} />} />
            <div className="space-y-2 px-4 pb-4 text-[0.78rem] leading-relaxed text-fg-muted sm:px-5">
              <p>· 每题判分规则和刷题页一致：全部用例通过才算过。</p>
              <p>· 得分 = 通过题数 / 总题数 × 100，逐题记录用时。</p>
              <p>· 中途刷新不会丢卷，回来还能接着做；交卷后才有报告。</p>
              <p>· 错题加权会明显偏向你没通过的题，适合考前突击。</p>
              <div className="mt-3 rounded-lg border border-line bg-ink-900/60 px-3 py-2 text-[0.7rem] text-fg-dim">
                当前题库：{questions.length} 道，已通过 {questions.filter((q) => q.last === "pass").length} 道
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  /* ------------------------------------------------------------ 答题页 */
  if (screen === "running") {
    const answeredCount = answered;
    const unchecked = paper.size - answeredCount;
    return (
      <div className="animate-rise">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={restart} icon={<ChevronLeft size={14} />}>
              放弃本卷
            </Button>
            <span className="text-sm font-semibold">模拟组卷 · {paper.size} 道</span>
            <Badge tone="brand">
              已答 {answeredCount}/{paper.size}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {paper.minutes > 0 ? (
              <span
                className={cls(
                  "flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs tabular-nums",
                  remainingMs < 60_000
                    ? "border-bad-500/40 bg-bad-500/10 text-bad-400"
                    : remainingMs < 5 * 60_000
                      ? "border-warn-400/40 bg-warn-400/10 text-warn-400"
                      : "border-line text-fg-muted",
                )}
              >
                <Timer size={13} />
                {Math.max(0, Math.floor(remainingMs / 1000 / 60))}:
                {String(Math.max(0, Math.floor(remainingMs / 1000) % 60)).padStart(2, "0")}
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded-lg border border-line px-2.5 py-1.5 text-xs text-fg-muted">
                <Clock size={13} /> 不限时 · 已用 {fmtDuration(usedMs)}
              </span>
            )}
            <Button size="sm" onClick={() => setConfirmOpen(true)} icon={<Send size={13} />}>
              交卷
            </Button>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          {paper.items.map((item, i) => (
            <button
              key={item.qid}
              type="button"
              onClick={() => goto(i)}
              className={cls(
                "grid size-8 place-items-center rounded-lg border text-[0.72rem] font-semibold tabular-nums transition-colors",
                i === index
                  ? "border-brand-400 bg-brand-500/25 text-brand-200"
                  : item.status === "pass"
                    ? "border-ok-500/40 bg-ok-500/15 text-ok-400"
                    : item.status === "fail"
                      ? "border-bad-500/40 bg-bad-500/15 text-bad-400"
                      : "border-line text-fg-dim hover:text-fg",
              )}
              title={questions.find((q) => q.id === item.qid)?.title}
            >
              {i + 1}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-1.5 text-[0.66rem] text-fg-dim">
            <CheckCircle2 size={11} className="text-ok-400" /> 通过
            <XCircle size={11} className="ml-1.5 text-bad-400" /> 未通过
          </div>
        </div>

        {currentQuestion ? (
          <div className="grid gap-3 xl:grid-cols-[1fr_1.15fr]">
            <Card className="px-4 py-4 sm:px-5">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[0.7rem] text-fg-dim">
                  第 {index + 1} / {paper.size} 题
                </span>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => goto(index - 1)} disabled={index === 0}>
                    <ChevronLeft size={16} />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => goto(index + 1)} disabled={index >= paper.size - 1}>
                    <ChevronRight size={16} />
                  </Button>
                </div>
              </div>
              <QuestionBody question={currentQuestion} chapters={chapters} />
            </Card>

            <div className="min-w-0 space-y-3">
              <Card className="overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
                  <div className="flex items-center gap-1.5 text-[0.7rem] text-fg-dim">
                    <span className="font-mono text-fg-muted">main.py</span>
                    {currentItem?.status === "pass" ? <Badge tone="ok">已通过</Badge> : null}
                    {currentItem?.status === "fail" ? <Badge tone="bad">未通过</Badge> : null}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        updatePaper((prev) => ({
                          ...prev,
                          items: prev.items.map((item, i) =>
                            i === index ? { ...item, code: STARTER_CODE } : item,
                          ),
                        }));
                        toast.info("已重置本题代码");
                      }}
                      disabled={judging}
                      icon={<RotateCcw size={13} />}
                    >
                      重置
                    </Button>
                    <Button size="sm" onClick={onJudge} loading={judging} disabled={judging} icon={<Play size={13} />}>
                      判题
                    </Button>
                  </div>
                </div>
                <div className="p-2">
                  <CodeEditor
                    value={currentItem?.code ?? ""}
                    onChange={(next) => {
                      codeDraft.current[currentItem?.qid ?? ""] = next;
                      updatePaper((prev) => ({
                        ...prev,
                        items: prev.items.map((item, i) => (i === index ? { ...item, code: next } : item)),
                      }));
                    }}
                    onRun={onJudge}
                    height="clamp(260px, 40vh, 520px)"
                  />
                </div>
              </Card>

              {judging ? (
                <Card className="flex items-center gap-2 px-4 py-3 text-xs text-fg-muted">
                  <Spinner size={14} /> 判题中…
                </Card>
              ) : null}

              {review ? (
                <Card className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge tone={review.status === "passed" ? "ok" : "bad"}>
                      {review.status === "passed" ? "全部用例通过" : "还有用例没过"}
                    </Badge>
                    <span className="text-fg-muted">
                      {review.results?.filter((r) => r.status === "pass").length ?? 0}/{review.total} 用例 ·{" "}
                      {fmtDuration(review.duration_ms)}
                    </span>
                  </div>
                  <div className="mt-2 space-y-1">
                    {(review.results ?? []).map((item) => (
                      <div key={item.index} className="flex items-center gap-2 text-[0.7rem]">
                        {item.status === "pass" ? (
                          <CheckCircle2 size={12} className="text-ok-400" />
                        ) : (
                          <XCircle size={12} className="text-bad-400" />
                        )}
                        <span className="text-fg-dim">用例 {item.index + 1}</span>
                        <span className="text-fg-muted">
                          {item.status === "pass" ? "通过" : item.error ? item.error.split("\n")[0] : "输出不符"}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              ) : null}

              <div className="flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => goto(index - 1)} disabled={index === 0}>
                  上一题
                </Button>
                {index >= paper.size - 1 ? (
                  <Button size="sm" onClick={() => setConfirmOpen(true)} icon={<Send size={13} />}>
                    交卷
                  </Button>
                ) : (
                  <Button variant="soft" size="sm" onClick={() => goto(index + 1)}>
                    下一题
                  </Button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <Card className="px-4 py-10 text-center text-sm text-fg-dim">题目还在载入…</Card>
        )}

        <Modal
          open={confirmOpen}
          onClose={() => setConfirmOpen(false)}
          title="确认交卷？"
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setConfirmOpen(false)}>
                再检查一下
              </Button>
              <Button size="sm" onClick={() => submitPaper(false)}>
                确认交卷
              </Button>
            </>
          }
        >
          <div className="space-y-2 text-sm text-fg-muted">
            <p>
              已作答 <span className="font-semibold text-fg">{answeredCount}</span> / {paper.size} 题，
              通过 <span className="font-semibold text-ok-400">{passed}</span> 题。
            </p>
            {unchecked > 0 ? (
              <p className="flex items-start gap-1.5 rounded-lg border border-warn-400/40 bg-warn-400/10 px-2.5 py-2 text-xs text-warn-400">
                <TriangleAlert size={13} className="mt-0.5 shrink-0" />
                还有 {unchecked} 题没判过，这些题会按未通过计入成绩。
              </p>
            ) : (
              <p className="text-xs text-fg-dim">所有题目都判过了。</p>
            )}
          </div>
        </Modal>
      </div>
    );
  }

  /* ------------------------------------------------------------ 报告页 */
  const wrongItems = paper.items.map((item, i) => ({ item, i })).filter(({ item }) => item.status !== "pass");
  return (
    <div className="animate-rise">
      <PageTitle
        title="交卷报告"
        subtitle={`用时 ${fmtDuration(usedMs)}${paper.minutes > 0 ? ` · 限时 ${paper.minutes} 分钟` : ""}`}
        right={
          <>
            <Button variant="ghost" size="sm" onClick={restart} icon={<RotateCcw size={14} />}>
              再来一套
            </Button>
            {wrongItems.length > 0 ? (
              <Button size="sm" onClick={() => navigate("/book")} icon={<FileText size={14} />}>
                去错题本
              </Button>
            ) : null}
          </>
        }
      />

      <div className="grid items-start gap-3 lg:grid-cols-[1fr_1.3fr]">
        <Card className="flex flex-col items-center justify-center px-5 py-8">
          <p className="text-xs text-fg-dim">得分</p>
          <p
            className={cls(
              "mt-1 text-5xl font-semibold tabular-nums",
              score >= 80 ? "text-ok-400" : score >= 60 ? "text-warn-400" : "text-bad-400",
            )}
          >
            {score}
          </p>
          <p className="mt-1 text-xs text-fg-dim">
            通过 {passed} / {paper.size} 题
          </p>
          <ProgressBar value={passed} max={paper.size || 1} tone={score >= 80 ? "ok" : score >= 60 ? "warn" : "brand"} className="mt-4" />
          <div className="mt-4 grid w-full grid-cols-3 gap-2 text-center">
            {[
              { label: "通过", value: passed, tone: "text-ok-400" },
              { label: "未通过", value: paper.items.filter((i) => i.status === "fail").length, tone: "text-bad-400" },
              { label: "未作答", value: paper.items.filter((i) => i.status === "todo").length, tone: "text-fg-dim" },
            ].map((cell) => (
              <div key={cell.label} className="rounded-lg border border-line bg-ink-900/50 py-2">
                <p className={cls("text-base font-semibold tabular-nums", cell.tone)}>{cell.value}</p>
                <p className="text-[0.62rem] text-fg-dim">{cell.label}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-center text-[0.66rem] leading-relaxed text-fg-dim">
            策略：{STRATEGY_OPTIONS.find((s) => s.value === paper.strategy)?.label}
            <br />
            范围：{paper.chapters.length >= chapters.length ? "全部章节" : paper.chapters.map((id) => chapters.find((c) => c.id === id)?.short ?? id).join(" / ")}
          </p>
        </Card>

        <Card>
          <CardHeader title="逐题明细" subtitle="点任意一题回到原题继续练" icon={<Award size={16} />} />
          <div className="max-h-[60vh] overflow-y-auto px-2 pb-2">
            <ul className="divide-y divide-line-soft">
              {paper.items.map((item, i) => {
                const q = questions.find((x) => x.id === item.qid);
                return (
                  <li key={item.qid}>
                    <Link
                      to={`/practice/${encodeURIComponent(item.qid)}`}
                      className="flex items-center gap-2 px-2 py-2 transition-colors hover:bg-ink-800/50"
                    >
                      <span className="w-5 shrink-0 text-center text-[0.7rem] tabular-nums text-fg-dim">{i + 1}</span>
                      {item.status === "pass" ? (
                        <CheckCircle2 size={14} className="shrink-0 text-ok-400" />
                      ) : item.status === "fail" ? (
                        <XCircle size={14} className="shrink-0 text-bad-400" />
                      ) : (
                        <Clock size={14} className="shrink-0 text-fg-dim" />
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1.5">
                          {q ? (
                            <span
                              className="font-mono text-[0.66rem]"
                              style={{ color: chapterColor(chapters, q.chapter_id) }}
                            >
                              {questionCode(q)}
                            </span>
                          ) : null}
                          <span className="truncate text-[0.8rem] text-fg-muted">{q?.title ?? item.qid}</span>
                        </span>
                      </span>
                      <span className="shrink-0 text-[0.66rem] tabular-nums text-fg-dim">
                        {item.status === "todo" ? "未作答" : `${item.casesPassed}/${item.casesTotal} 用例`}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        </Card>
      </div>

      <div className="mt-3 flex justify-center">
        <Button variant="soft" onClick={() => navigate("/practice")} icon={<ChevronRight size={14} />}>
          回到刷题
        </Button>
      </div>
    </div>
  );
}
