import { useState } from "react";
import { BookOpen, Check, ChevronDown, Copy, Lightbulb, ListTree, Star } from "lucide-react";
import type { Chapter, Question } from "../lib/types";
import { chapterColor, levelMeta, questionCode, statusMeta } from "../lib/format";
import { Badge, Button, cls } from "./ui";

function Disclosure({
  icon,
  title,
  children,
  defaultOpen = false,
  tone = "neutral",
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  tone?: "neutral" | "brand";
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-ink-900/50">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition-colors hover:bg-ink-800/60"
        aria-expanded={open}
      >
        <span className={cls("flex items-center gap-1.5 text-xs font-semibold", tone === "brand" ? "text-brand-300" : "text-fg-muted")}>
          {icon}
          {title}
        </span>
        <ChevronDown size={14} className={cls("text-fg-dim transition-transform", open && "rotate-180")} />
      </button>
      {open ? <div className="animate-fade-in border-t border-line px-3 py-2.5">{children}</div> : null}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        } catch {
          /* 非 https 下剪贴板不可用，忽略 */
        }
      }}
      className="flex items-center gap-1 rounded-md border border-line px-1.5 py-1 text-[0.66rem] text-fg-dim transition-colors hover:text-fg"
    >
      {done ? <Check size={11} className="text-ok-400" /> : <Copy size={11} />}
      {done ? "已复制" : "复制"}
    </button>
  );
}

export default function QuestionBody({
  question,
  chapters,
  favoriteSlot,
}: {
  question: Question;
  chapters: Chapter[];
  favoriteSlot?: React.ReactNode;
}) {
  const level = levelMeta(question.level);
  const status = statusMeta(question.last);
  const tone = chapterColor(chapters, question.chapter_id);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span
          className="rounded-md px-1.5 py-0.5 font-mono text-[0.7rem] font-semibold"
          style={{ background: `${tone}22`, color: tone }}
        >
          {questionCode(question)}
        </span>
        <span className="text-[0.7rem] text-fg-dim">{question.chapter}</span>
        <Badge tone={level.tone}>{level.label}</Badge>
        <Badge tone={status.tone}>{status.label}</Badge>
        {question.topic ? <Badge tone="neutral">{question.topic}</Badge> : null}
        <span className="ml-auto flex items-center gap-1.5">
          {question.attempts > 0 ? (
            <span className="text-[0.68rem] tabular-nums text-fg-dim">作答 {question.attempts} 次</span>
          ) : null}
          {favoriteSlot}
        </span>
      </div>

      <h2 className="text-lg font-semibold leading-snug tracking-tight text-fg">{question.title}</h2>

      <p className="whitespace-pre-wrap text-[0.86rem] leading-relaxed text-fg-muted">{question.desc}</p>

      {question.cases.length > 0 ? (
        <Disclosure icon={<ListTree size={13} />} title={`测试用例（${question.cases.length} 条）`} defaultOpen>
          <div className="space-y-1.5">
            {question.cases.map((item, index) => (
              <div key={index} className="grid gap-1.5 rounded-lg bg-ink-950/50 p-2 sm:grid-cols-2">
                <div>
                  <p className="mb-0.5 text-[0.64rem] font-semibold text-fg-dim">输入</p>
                  <pre className="whitespace-pre-wrap break-all font-mono text-[0.74rem] text-fg-muted">
                    {item.stdin || "（无输入）"}
                  </pre>
                </div>
                <div>
                  <p className="mb-0.5 text-[0.64rem] font-semibold text-fg-dim">期望输出</p>
                  <pre className="whitespace-pre-wrap break-all font-mono text-[0.74rem] text-ok-400">
                    {item.expect || "（无输出）"}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </Disclosure>
      ) : null}

      {question.hint ? (
        <Disclosure icon={<Lightbulb size={13} />} title="提示" tone="brand">
          <p className="whitespace-pre-wrap text-[0.82rem] leading-relaxed text-fg-muted">{question.hint}</p>
        </Disclosure>
      ) : null}

      {question.ref ? (
        <Disclosure icon={<BookOpen size={13} />} title="参考答案">
          <div className="space-y-1.5">
            <div className="flex justify-end">
              <CopyButton text={question.ref} />
            </div>
            <pre className="max-h-64 overflow-auto rounded-lg border border-line bg-ink-950/70 px-3 py-2 font-mono text-[0.76rem] leading-relaxed text-fg-muted">
              {question.ref}
            </pre>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                void navigator.clipboard?.writeText(question.ref);
              }}
            >
              复制到编辑器（先清空再粘贴）
            </Button>
          </div>
        </Disclosure>
      ) : null}

      {question.explain ? (
        <Disclosure icon={<Star size={13} />} title="题解">
          <p className="whitespace-pre-wrap text-[0.82rem] leading-relaxed text-fg-muted">{question.explain}</p>
        </Disclosure>
      ) : null}

      {question.source ? <p className="text-[0.68rem] text-fg-dim">来源：{question.source}</p> : null}
    </div>
  );
}
