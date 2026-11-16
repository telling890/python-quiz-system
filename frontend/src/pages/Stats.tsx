import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, BarChart3, BookOpen, Download, PieChart, Target, TrendingUp } from "lucide-react";
import { api } from "../lib/api";
import { useBank } from "../lib/bank";
import type { ProgressRecord, Submission } from "../lib/types";
import { BarRow, Donut, Legend, Trend } from "../components/Charts";
import { Badge, Button, Card, CardHeader, Spinner } from "../components/ui";
import { PageTitle } from "../components/Layout";
import {
  chapterColor,
  dayKey,
  downloadText,
  levelMeta,
  pct,
  questionCode,
  toCsv,
} from "../lib/format";
import { useToast } from "../components/ui";

const COLOR = {
  ok: "var(--color-ok-400)",
  bad: "var(--color-bad-400)",
  idle: "var(--color-ink-600)",
  brand: "var(--color-brand-400)",
  aqua: "var(--color-aqua-400)",
};

export default function StatsPage() {
  const { questions, chapters, stats } = useBank();
  const [records, setRecords] = useState<ProgressRecord[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    let alive = true;
    Promise.all([api.progress(), api.submissions(50)])
      .then(([progress, subs]) => {
        if (!alive) return;
        setRecords(progress.records);
        setSubmissions(subs.items);
      })
      .catch(() => {
        if (alive) toast.bad("统计数据加载失败");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [toast]);

  const recordMap = useMemo(() => new Map(records.map((r) => [r.qid, r])), [records]);

  const slices = useMemo(() => {
    const failed = questions.filter((q) => q.last === "fail").length;
    const solved = questions.filter((q) => q.last === "pass").length;
    const idle = Math.max(questions.length - failed - solved, 0);
    return [
      { label: "已通过", value: solved, color: COLOR.ok },
      { label: "没通过", value: failed, color: COLOR.bad },
      { label: "没做过", value: idle, color: COLOR.idle },
    ];
  }, [questions]);

  const chapterRows = useMemo(
    () =>
      chapters.map((chapter) => {
        const items = questions.filter((q) => q.chapter_id === chapter.id);
        return {
          chapter,
          solved: items.filter((q) => q.last === "pass").length,
          tried: items.filter((q) => q.attempts > 0).length,
          total: items.length,
        };
      }),
    [chapters, questions],
  );

  const levelRows = useMemo(() => {
    const groups = new Map<number, { solved: number; total: number }>();
    for (const q of questions) {
      const g = groups.get(q.level) ?? { solved: 0, total: 0 };
      g.total += 1;
      if (q.last === "pass") g.solved += 1;
      groups.set(q.level, g);
    }
    return [...groups.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([level, g]) => ({ level, ...g, meta: levelMeta(level) }));
  }, [questions]);

  const activity = useMemo(() => {
    const days: Array<{ label: string; value: number }> = [];
    const now = new Date();
    for (let i = 6; i >= 0; i -= 1) {
      const date = new Date(now);
      date.setDate(now.getDate() - i);
      const key = `${date.getMonth() + 1}/${String(date.getDate()).padStart(2, "0")}`;
      days.push({ label: key, value: 0 });
    }
    const index = new Map(days.map((d, i) => [d.label, i]));
    for (const sub of submissions) {
      const key = dayKey(sub.created_at);
      const at = index.get(key);
      if (at !== undefined) days[at].value += 1;
    }
    return days;
  }, [submissions]);

  const statusRows = useMemo(() => {
    const counts: Record<string, number> = { passed: 0, failed: 0, timeout: 0, error: 0 };
    for (const sub of submissions) {
      if (sub.status in counts) counts[sub.status] += 1;
    }
    return [
      { label: "通过", value: counts.passed, color: COLOR.ok },
      { label: "未通过", value: counts.failed, color: COLOR.bad },
      { label: "超时", value: counts.timeout, color: "#fbbf24" },
      { label: "运行报错", value: counts.error, color: "#a78bfa" },
    ];
  }, [submissions]);

  const wrongCount = useMemo(() => questions.filter((q) => q.last === "fail").length, [questions]);

  const hardest = useMemo(
    () =>
      questions
        .map((q) => ({ q, record: recordMap.get(q.id) }))
        .filter((entry) => (entry.record?.fails ?? 0) > 0)
        .sort((a, b) => (b.record?.fails ?? 0) - (a.record?.fails ?? 0))
        .slice(0, 6),
    [questions, recordMap],
  );

  const exportCsv = () => {
    const rows: Array<Array<string | number>> = [
      ["题号", "章节", "标题", "知识点", "难度", "状态", "作答", "通过", "失败", "收藏", "最后作答"],
    ];
    for (const q of questions) {
      const record = recordMap.get(q.id);
      rows.push([
        questionCode(q),
        q.chapter,
        q.title,
        q.topic,
        levelMeta(q.level).label,
        q.last === "pass" ? "已通过" : q.last === "fail" ? "未通过" : "未尝试",
        record?.attempts ?? 0,
        record?.passes ?? 0,
        record?.fails ?? 0,
        q.favorite ? "是" : "否",
        record?.updated ?? "",
      ]);
    }
    downloadText(`刷题统计-${new Date().toISOString().slice(0, 10)}.csv`, toCsv(rows), "text/csv;charset=utf-8");
    toast.ok("统计已导出");
  };

  const solvedPct = pct(stats.solved, stats.total);

  return (
    <div className="animate-rise">
      <PageTitle
        title="学习统计"
        subtitle="覆盖率、章节掌握度、提交分布，都从服务端实时算。"
        right={
          <>
            <Button variant="ghost" size="sm" onClick={exportCsv} icon={<Download size={14} />}>
              导出 CSV
            </Button>
            <Link to="/book">
              <Button variant="soft" size="sm" icon={<BookOpen size={14} />}>
                去复习错题
              </Button>
            </Link>
          </>
        }
      />

      <div className="grid items-start gap-3 lg:grid-cols-[1fr_1.35fr]">
        <Card className="px-4 py-4 sm:px-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[0.95rem] font-semibold">整体掌握</h2>
            <Badge tone="brand">共 {stats.total} 道</Badge>
          </div>
          <div className="mt-3 flex flex-col items-center gap-4 sm:flex-row sm:items-center">
            <Donut slices={slices} centerValue={`${solvedPct}%`} centerLabel="覆盖率" size={152} thickness={15} />
            <div className="w-full">
              <Legend slices={slices} />
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {[
              { label: "累计作答", value: stats.attempts, suffix: "次" },
              { label: "累计通过", value: stats.passes, suffix: "次" },
              { label: "按次通过率", value: `${stats.rate}%`, suffix: "" },
              { label: "待攻克错题", value: wrongCount, suffix: "道" },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border border-line bg-ink-900/50 px-2.5 py-2">
                <p className="text-[0.64rem] text-fg-dim">{item.label}</p>
                <p className="text-sm font-semibold tabular-nums">
                  {item.value}
                  <span className="ml-0.5 text-[0.66rem] font-normal text-fg-dim">{item.suffix}</span>
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="章节掌握度" subtitle="已通过 / 该章总题数" icon={<BarChart3 size={16} />} />
          <div className="space-y-2.5 px-4 pb-4 sm:px-5">
            {chapterRows.map(({ chapter, solved, tried, total }) => (
              <div key={chapter.id}>
                <BarRow
                  label={chapter.name}
                  value={solved}
                  max={total}
                  tone={chapterColor(chapters, chapter.id)}
                />
                <p className="mt-0.5 pl-1.5 text-[0.62rem] text-fg-dim">
                  练过 {tried} 道 · 通过率 {pct(solved, total)}%
                </p>
              </div>
            ))}
            <div className="pt-1">
              <p className="mb-2 text-[0.68rem] font-semibold text-fg-dim">按难度</p>
              {levelRows.map((row) => (
                <BarRow
                  key={row.level}
                  label={`${row.meta.dots} ${row.meta.label}`}
                  value={row.solved}
                  max={row.total}
                  tone={row.meta.tone === "ok" ? COLOR.ok : row.meta.tone === "warn" ? "#fbbf24" : COLOR.bad}
                />
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader title="最近 7 天提交" subtitle="每天判了多少次" icon={<Activity size={16} />} />
          <div className="px-4 pb-4 sm:px-5">
            <Trend points={activity} color={COLOR.brand} formatValue={(v) => `${v} 次`} />
          </div>
        </Card>

        <Card>
          <CardHeader title="提交结果分布" subtitle={`最近 ${submissions.length} 次判题`} icon={<PieChart size={16} />} />
          <div className="px-4 pb-4 sm:px-5">
            {submissions.length === 0 ? (
              <p className="py-10 text-center text-xs text-fg-dim">还没有判题记录</p>
            ) : (
              <div className="space-y-2.5">
                {statusRows.map((row) => (
                  <div key={row.label}>
                    <div className="mb-1 flex items-baseline justify-between text-xs">
                      <span className="text-fg-muted">{row.label}</span>
                      <span className="tabular-nums text-fg-dim">
                        {row.value} · {pct(row.value, submissions.length)}%
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
                      <div
                        className="h-full rounded-full transition-[width] duration-500"
                        style={{ width: `${pct(row.value, submissions.length)}%`, background: row.color }}
                      />
                    </div>
                  </div>
                ))}
                <p className="pt-1 text-[0.66rem] text-fg-dim">
                  判题worker 会顺带记录进度，所以这里和错题本数量会对得上。
                </p>
              </div>
            )}
          </div>
        </Card>
      </div>

      <Card className="mt-3">
        <CardHeader
          title="最需要复习的题"
          subtitle="按失败次数排序"
          icon={<Target size={16} />}
          right={
            <Link to="/book" className="text-[0.7rem] text-brand-300 hover:underline">
              打开错题本
            </Link>
          }
        />
        <div className="px-2 pb-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : hardest.length === 0 ? (
            <p className="px-3 py-8 text-center text-xs text-fg-dim">还没有失败记录，保持住 💪</p>
          ) : (
            <ul className="divide-y divide-line-soft">
              {hardest.map(({ q, record }) => (
                <li key={q.id}>
                  <Link
                    to={`/practice/${encodeURIComponent(q.id)}`}
                    className="flex items-center gap-2 px-2 py-2 transition-colors hover:bg-ink-800/50"
                  >
                    <span
                      className="w-12 shrink-0 rounded-md px-1 py-0.5 text-center font-mono text-[0.66rem]"
                      style={{ background: `${chapterColor(chapters, q.chapter_id)}1f`, color: chapterColor(chapters, q.chapter_id) }}
                    >
                      {questionCode(q)}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[0.82rem] text-fg-muted">{q.title}</span>
                    <span className="shrink-0 text-[0.66rem] tabular-nums text-fg-dim">
                      失败 {record?.fails ?? 0} / 作答 {record?.attempts ?? 0}
                    </span>
                    <TrendingUp size={13} className="shrink-0 text-fg-dim/60" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>
    </div>
  );
}
