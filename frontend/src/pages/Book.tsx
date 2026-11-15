import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookMarked, ChevronRight, Download, Search, Star, XCircle } from "lucide-react";
import { useBank } from "../lib/bank";
import { Badge, Button, Card, EmptyState, Segmented } from "../components/ui";
import { PageTitle } from "../components/Layout";
import {
  chapterColor,
  downloadText,
  levelMeta,
  questionCode,
  toCsv,
} from "../lib/format";
import { api } from "../lib/api";
import { useToast } from "../components/ui";
import type { ProgressRecord } from "../lib/types";

type Tab = "fail" | "favorite" | "todo";

const TABS: Array<{ value: Tab; label: string }> = [
  { value: "fail", label: "错题本" },
  { value: "favorite", label: "收藏夹" },
  { value: "todo", label: "没通过" },
];

export default function Book() {
  const { questions, chapters, stats, loading } = useBank();
  const [tab, setTab] = useState<Tab>("fail");
  const [keyword, setKeyword] = useState("");
  const [exporting, setExporting] = useState(false);
  const toast = useToast();

  const items = useMemo(() => {
    const text = keyword.trim().toLowerCase();
    return questions
      .filter((q) => {
        if (tab === "fail") return q.last === "fail";
        if (tab === "favorite") return q.favorite;
        return q.last !== "pass";
      })
      .filter((q) =>
        text
          ? q.title.toLowerCase().includes(text) ||
            q.topic.toLowerCase().includes(text) ||
            questionCode(q).includes(text) ||
            q.chapter.includes(text)
          : true,
      );
  }, [questions, tab, keyword]);

  const counts = useMemo(
    () => ({
      fail: questions.filter((q) => q.last === "fail").length,
      favorite: questions.filter((q) => q.favorite).length,
      todo: questions.filter((q) => q.last !== "pass").length,
    }),
    [questions],
  );

  const exportCsv = async () => {
    setExporting(true);
    try {
      const progress = await api.progress();
      const byId = new Map<string, ProgressRecord>(progress.records.map((r) => [r.qid, r]));
      const rows: Array<Array<string | number>> = [
        ["题号", "章节", "标题", "知识点", "难度", "状态", "作答次数", "通过次数", "收藏", "最后作答"],
      ];
      for (const q of questions) {
        const record = byId.get(q.id);
        rows.push([
          questionCode(q),
          q.chapter,
          q.title,
          q.topic,
          levelMeta(q.level).label,
          q.last === "pass" ? "已通过" : q.last === "fail" ? "未通过" : "未尝试",
          record?.attempts ?? 0,
          record?.passes ?? 0,
          q.favorite ? "是" : "否",
          record?.updated ?? "",
        ]);
      }
      const stamp = new Date().toISOString().slice(0, 10);
      downloadText(`刷题成绩-${stamp}.csv`, toCsv(rows), "text/csv;charset=utf-8");
      toast.ok("已导出 CSV，可直接用 Excel 打开");
    } catch {
      toast.bad("导出失败，检查网络或登录状态");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="animate-rise">
      <PageTitle
        title="题本"
        subtitle="错题、收藏和没通过的题都在这儿，复习从这里进。"
        right={
          <Button variant="ghost" size="sm" onClick={exportCsv} loading={exporting} icon={<Download size={14} />}>
            导出成绩 CSV
          </Button>
        }
      />

      <Card className="px-3 py-3 sm:px-4">
        <div className="mb-3 grid gap-2 sm:grid-cols-3">
          {[
            { label: "没通过的题", value: counts.fail, hint: "判题失败自动进这儿", tone: "text-bad-400", icon: XCircle },
            { label: "收藏的题", value: counts.favorite, hint: "随手攒的重点题", tone: "text-warn-400", icon: Star },
            { label: "还没通过", value: counts.todo, hint: `全库 ${stats.total} 道`, tone: "text-brand-300", icon: BookMarked },
          ].map((tile) => (
            <div key={tile.label} className="flex items-center gap-2.5 rounded-lg border border-line bg-ink-900/50 px-3 py-2">
              <tile.icon size={15} className={tile.tone} />
              <div>
                <p className="text-[0.66rem] text-fg-dim">{tile.label}</p>
                <p className={`text-sm font-semibold tabular-nums ${tile.tone}`}>{tile.value}</p>
              </div>
              <p className="ml-auto hidden text-[0.62rem] text-fg-dim sm:block">{tile.hint}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Segmented
            value={tab}
            onChange={setTab}
            options={TABS.map((item) => ({ ...item, count: counts[item.value] }))}
          />
          <div className="relative w-full sm:w-64">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-dim" />
            <input
              className="input py-1.5 pl-8 text-xs"
              placeholder="在这个题本里搜…"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-3">
          {loading ? (
            <p className="py-10 text-center text-xs text-fg-dim">正在载入…</p>
          ) : items.length === 0 ? (
            <EmptyState
              icon={<BookMarked size={20} />}
              title={tab === "fail" ? "错题本是空的 🎉" : tab === "favorite" ? "还没有收藏" : "全部通过，太强了"}
              hint={
                tab === "fail"
                  ? "判题没通过的题会自动进这里。"
                  : tab === "favorite"
                    ? "刷题时点题目右上角的收藏，就会出现在这里。"
                    : `题库共 ${stats.total} 道，你已通过 ${stats.solved} 道。`
              }
              action={
                <Link to="/practice">
                  <Button size="sm">去刷题</Button>
                </Link>
              }
            />
          ) : (
            <ul className="divide-y divide-line-soft">
              {items.map((q) => {
                const level = levelMeta(q.level);
                return (
                  <li key={q.id}>
                    <Link
                      to={`/practice/${encodeURIComponent(q.id)}`}
                      className="group flex items-center gap-3 px-2 py-2.5 transition-colors hover:bg-ink-800/50"
                    >
                      <span
                        className="w-12 shrink-0 rounded-md px-1 py-0.5 text-center font-mono text-[0.68rem] font-semibold"
                        style={{
                          background: `${chapterColor(chapters, q.chapter_id)}1f`,
                          color: chapterColor(chapters, q.chapter_id),
                        }}
                      >
                        {questionCode(q)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1.5">
                          <span className="truncate text-[0.85rem] font-medium text-fg">
                            {q.title}
                          </span>
                          {q.favorite ? <Star size={11} className="shrink-0 fill-warn-400 text-warn-400" /> : null}
                        </span>
                        <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[0.66rem] text-fg-dim">
                          <span className="truncate">{q.chapter}</span>
                          {q.topic ? <span>· {q.topic}</span> : null}
                          {q.attempts > 0 ? <span>· 作答 {q.attempts} 次</span> : null}
                        </span>
                      </span>
                      <span className="hidden shrink-0 items-center gap-1.5 sm:flex">
                        {q.last === "fail" ? (
                          <Badge tone="bad">
                            <XCircle size={10} /> 未通过
                          </Badge>
                        ) : q.last === "pass" ? (
                          <Badge tone="ok">已通过</Badge>
                        ) : (
                          <Badge tone="neutral">未尝试</Badge>
                        )}
                        <Badge tone={level.tone}>{level.label}</Badge>
                      </span>
                      <ChevronRight size={14} className="shrink-0 text-fg-dim/50" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </Card>
    </div>
  );
}
