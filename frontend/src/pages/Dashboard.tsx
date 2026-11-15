import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BookMarked,
  CheckCircle2,
  Clock3,
  Flame,
  ListChecks,
  PlayCircle,
  Star,
  Target,
  Terminal,
  TrendingUp,
} from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useBank } from "../lib/bank";
import type { Submission } from "../lib/types";
import { BarRow } from "../components/Charts";
import { Badge, Button, Card, CardHeader, ProgressBar } from "../components/ui";
import { PageTitle } from "../components/Layout";
import { chapterColor, pct, questionCode, timeAgo } from "../lib/format";

function StatTile({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone: string;
}) {
  return (
    <div className="panel-flat flex items-center gap-3 px-3.5 py-3">
      <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${tone}`}>{icon}</span>
      <div className="min-w-0">
        <p className="text-[0.68rem] text-fg-dim">{label}</p>
        <p className="text-lg font-semibold leading-tight tabular-nums">{value}</p>
        {hint ? <p className="truncate text-[0.64rem] text-fg-dim">{hint}</p> : null}
      </div>
    </div>
  );
}

const STATUS_STYLE: Record<string, { label: string; tone: "ok" | "bad" | "warn" | "neutral" }> = {
  passed: { label: "通过", tone: "ok" },
  failed: { label: "未通过", tone: "bad" },
  timeout: { label: "超时", tone: "warn" },
  error: { label: "报错", tone: "bad" },
  queued: { label: "排队中", tone: "neutral" },
  running: { label: "判题中", tone: "neutral" },
};

export default function Dashboard() {
  const { user } = useAuth();
  const { questions, chapters, stats, loading } = useBank();
  const navigate = useNavigate();
  const [recent, setRecent] = useState<Submission[]>([]);

  useEffect(() => {
    let alive = true;
    api
      .submissions(8)
      .then((res) => {
        if (alive) setRecent(res.items);
      })
      .catch(() => {
        /* 最近提交拿不到不影响主页 */
      });
    return () => {
      alive = false;
    };
  }, []);

  const chapterRows = useMemo(
    () =>
      chapters.map((chapter) => {
        const items = questions.filter((q) => q.chapter_id === chapter.id);
        const solved = items.filter((q) => q.last === "pass").length;
        return { chapter, solved, total: items.length };
      }),
    [chapters, questions],
  );

  const nextQuestion = useMemo(() => {
    const failed = questions.find((q) => q.last === "fail");
    if (failed) return failed;
    const untouched = questions.find((q) => q.attempts === 0);
    return untouched ?? questions[0];
  }, [questions]);

  const wrongCount = questions.filter((q) => q.last === "fail").length;
  const solvedPct = pct(stats.solved, stats.total);

  return (
    <div className="animate-rise">
      <PageTitle
        title={
          <span className="flex flex-wrap items-center gap-2">
            你好，{user?.username}
            <span className="text-base">👋</span>
          </span>
        }
        subtitle={loading ? "正在载入题库与进度…" : `已通过 ${stats.solved} 道，还剩 ${stats.total - stats.solved} 道；错题 ${wrongCount} 道。`}
        right={
          <Button onClick={() => navigate("/practice")} icon={<PlayCircle size={15} />}>
            继续刷题
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">
        <StatTile
          icon={<Target size={17} />}
          label="题库总量"
          value={stats.total}
          hint="第 3～5 章 + 拓展 + 算法"
          tone="bg-brand-500/15 text-brand-300"
        />
        <StatTile
          icon={<CheckCircle2 size={17} />}
          label="已通过"
          value={`${stats.solved}`}
          hint={`覆盖率 ${solvedPct}%`}
          tone="bg-ok-500/15 text-ok-400"
        />
        <StatTile
          icon={<Flame size={17} />}
          label="累计作答"
          value={stats.attempts}
          hint={`通过率 ${stats.rate}%`}
          tone="bg-warn-400/15 text-warn-400"
        />
        <StatTile
          icon={<Star size={17} />}
          label="收藏题目"
          value={stats.favorite}
          hint="随时回看"
          tone="bg-aqua-400/15 text-aqua-400"
        />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1.5fr_1fr]">
        {/* 继续练习 */}
        <Card className="overflow-hidden">
          <CardHeader title="接着上次继续" subtitle="优先推错题，其次推没做过的" icon={<PlayCircle size={16} />} />
          <div className="px-4 pb-4 sm:px-5">
            {nextQuestion ? (
              <div className="rounded-xl border border-line bg-ink-900/60 p-3.5">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className="rounded-md px-1.5 py-0.5 font-mono text-[0.7rem] font-semibold"
                    style={{
                      background: `${chapterColor(chapters, nextQuestion.chapter_id)}22`,
                      color: chapterColor(chapters, nextQuestion.chapter_id),
                    }}
                  >
                    {questionCode(nextQuestion)}
                  </span>
                  <span className="text-[0.7rem] text-fg-dim">{nextQuestion.chapter}</span>
                  {nextQuestion.last === "fail" ? <Badge tone="bad">上次没过</Badge> : null}
                  {nextQuestion.topic ? <Badge tone="neutral">{nextQuestion.topic}</Badge> : null}
                </div>
                <h3 className="mt-2 text-base font-semibold leading-snug">{nextQuestion.title}</h3>
                <p className="mt-1 line-clamp-2 text-[0.8rem] leading-relaxed text-fg-dim">{nextQuestion.desc}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Button
                    size="sm"
                    onClick={() => navigate(`/practice/${encodeURIComponent(nextQuestion.id)}`)}
                    icon={<ArrowRight size={14} />}
                  >
                    打开这题
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => navigate("/exam")} icon={<ListChecks size={14} />}>
                    先来一套组卷
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-fg-dim">题库还没加载好。</p>
            )}

            <div className="mt-3 flex items-center gap-3 rounded-xl border border-line bg-ink-900/40 px-3 py-2.5">
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 flex items-baseline justify-between text-[0.7rem]">
                  <span className="text-fg-muted">整体进度</span>
                  <span className="tabular-nums text-fg-dim">
                    {stats.solved}/{stats.total} · {solvedPct}%
                  </span>
                </div>
                <ProgressBar value={stats.solved} max={stats.total || 1} tone="ok" />
              </div>
            </div>
          </div>
        </Card>

        {/* 章节进度 */}
        <Card>
          <CardHeader
            title="章节进度"
            subtitle="点一下直接跳到该章"
            icon={<TrendingUp size={16} />}
            right={
              <Link to="/stats" className="text-[0.7rem] text-brand-300 hover:underline">
                详细统计
              </Link>
            }
          />
          <div className="space-y-2 px-4 pb-4 sm:px-5">
            {chapterRows.map(({ chapter, solved, total }) => (
              <BarRow
                key={chapter.id}
                label={chapter.name}
                value={solved}
                max={total}
                tone={chapterColor(chapters, chapter.id)}
                onClick={() => navigate(`/practice?chapter=${encodeURIComponent(chapter.id)}`)}
              />
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1.5fr_1fr]">
        {/* 最近提交 */}
        <Card>
          <CardHeader title="最近提交" subtitle="判题记录按时间倒序" icon={<Clock3 size={16} />} />
          <div className="px-2 pb-2">
            {recent.length === 0 ? (
              <p className="px-3 py-6 text-center text-xs text-fg-dim">还没有提交记录，去刷第一题吧。</p>
            ) : (
              <ul className="divide-y divide-line-soft">
                {recent.map((item) => {
                  const style = STATUS_STYLE[item.status] ?? STATUS_STYLE.queued;
                  const question = questions.find((q) => q.id === item.qid);
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => (item.qid ? navigate(`/practice/${encodeURIComponent(item.qid)}`) : undefined)}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-ink-800/50"
                      >
                        <Badge tone={style.tone}>{style.label}</Badge>
                        <span className="min-w-0 flex-1 truncate text-[0.8rem] text-fg-muted">
                          {question ? `${questionCode(question)} ${question.title}` : item.qid || "自由编程"}
                        </span>
                        <span className="shrink-0 text-[0.68rem] tabular-nums text-fg-dim">
                          {item.result?.total ? `${item.result.total} 用例` : ""}
                        </span>
                        <span className="w-16 shrink-0 text-right text-[0.66rem] text-fg-dim">
                          {timeAgo(item.created_at)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Card>

        {/* 快捷入口 */}
        <Card>
          <CardHeader title="快捷入口" subtitle="常用的四件事" icon={<Flame size={16} />} />
          <div className="grid grid-cols-2 gap-2 px-4 pb-4 sm:px-5">
            {[
              { to: "/book", label: "错题本", desc: `${wrongCount} 道待复习`, icon: BookMarked },
              { to: "/free", label: "自由编程", desc: "随手写点代码", icon: Terminal },
              { to: "/exam", label: "模拟组卷", desc: "按错题加权出卷", icon: ListChecks },
              { to: "/stats", label: "学习统计", desc: "通过率与趋势", icon: TrendingUp },
            ].map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="group rounded-xl border border-line bg-ink-900/50 px-3 py-3 transition-colors hover:border-brand-500/40 hover:bg-ink-800/60"
              >
                <item.icon size={16} className="text-brand-300" />
                <p className="mt-2 text-[0.82rem] font-semibold text-fg">{item.label}</p>
                <p className="text-[0.66rem] text-fg-dim">{item.desc}</p>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
