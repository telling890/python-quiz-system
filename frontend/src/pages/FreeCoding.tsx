import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bug,
  FileCode2,
  Play,
  Save,
  Terminal,
  Trash2,
  Upload,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { RunResult, Snippet, Trace } from "../lib/types";
import { Button, Card, CardHeader, EmptyState, Modal, Spinner, useToast } from "../components/ui";
import { PageTitle } from "../components/Layout";
import CodeEditor from "../components/CodeEditor";
import { RunResultView } from "../components/JudgeResult";
import TraceViewer from "../components/TraceViewer";
import { FREE_STARTER, fmtDateTime } from "../lib/format";

export default function FreeCoding() {
  const toast = useToast();
  const [code, setCode] = useState(FREE_STARTER);
  const [stdin, setStdin] = useState("小明\n");
  const [run, setRun] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState<"idle" | "run" | "trace" | "save">("idle");
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [loadingSnippets, setLoadingSnippets] = useState(true);
  const [snippetName, setSnippetName] = useState("");
  const [savedAt, setSavedAt] = useState("");
  const [trace, setTrace] = useState<Trace | null>(null);
  const [traceSummary, setTraceSummary] = useState("");
  const [traceOpen, setTraceOpen] = useState(false);
  const dirtyRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  const loadSnippets = useCallback(async () => {
    setLoadingSnippets(true);
    try {
      const res = await api.snippets();
      setSnippets(res.snippets);
    } catch {
      toast.bad("片段列表加载失败");
    } finally {
      setLoadingSnippets(false);
    }
  }, [toast]);

  useEffect(() => {
    let alive = true;
    api
      .freeDraft()
      .then((draft) => {
        if (!alive) return;
        if (draft.code) {
          setCode(draft.code);
          setSavedAt(draft.updated);
        }
        if (draft.stdin) setStdin(draft.stdin);
      })
      .catch(() => {
        /* 首次使用没有草稿，忽略 */
      });
    void loadSnippets();
    return () => {
      alive = false;
    };
  }, [loadSnippets]);

  // 停止输入 1.5 秒后自动保存草稿
  useEffect(() => {
    if (!dirtyRef.current) return;
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      void saveDraft(true);
    }, 1500);
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, stdin]);

  const saveDraft = async (silent = false) => {
    setBusy((b) => (b === "idle" ? "save" : b));
    try {
      const res = await api.saveFreeDraft(code, stdin);
      dirtyRef.current = false;
      setSavedAt(res.updated);
      if (!silent) toast.ok("草稿已保存");
    } catch (err) {
      if (!silent) toast.bad(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setBusy("idle");
    }
  };

  const onRun = async () => {
    if (busy !== "idle") return;
    if (!code.trim()) {
      toast.warn("代码是空的");
      return;
    }
    setBusy("run");
    try {
      const res = await api.runFree(code, stdin);
      setRun(res.run);
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "运行失败");
    } finally {
      setBusy("idle");
    }
  };

  const onTrace = async () => {
    if (busy !== "idle") return;
    setBusy("trace");
    try {
      const res = await api.trace(code, stdin);
      setTrace(res.trace);
      setTraceSummary(res.summary);
      setTraceOpen(true);
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "追踪失败");
    } finally {
      setBusy("idle");
    }
  };

  const saveSnippet = async () => {
    const name = snippetName.trim();
    if (!name) {
      toast.warn("给片段起个名字");
      return;
    }
    try {
      const res = await api.saveSnippet(name, code);
      toast.ok(res.created ? `已新建片段「${name}」` : `已更新片段「${name}」`);
      setSnippetName("");
      await loadSnippets();
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "保存片段失败");
    }
  };

  const removeSnippet = async (name: string) => {
    try {
      await api.deleteSnippet(name);
      setSnippets((prev) => prev.filter((s) => s.name !== name));
      toast.ok(`已删除「${name}」`);
    } catch (err) {
      toast.bad(err instanceof ApiError ? err.message : "删除失败");
    }
  };

  const stats = useMemo(
    () => ({
      lines: code.split("\n").length,
      chars: code.length,
    }),
    [code],
  );

  return (
    <div className="animate-rise">
      <PageTitle
        title="自由编程"
        subtitle="随手写点 Python，立即运行；支持单步追踪和片段保存。草稿会自动同步到账号。"
        right={
          <>
            <span className="hidden items-center gap-1 text-[0.68rem] text-fg-dim sm:flex">
              {savedAt ? `已保存 ${fmtDateTime(savedAt)}` : "还没保存过"}
            </span>
            <Button variant="ghost" size="sm" onClick={() => void saveDraft()} loading={busy === "save"} icon={<Save size={14} />}>
              保存草稿
            </Button>
          </>
        }
      />

      <div className="grid gap-3 xl:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-3">
          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
              <div className="flex items-center gap-1.5 text-[0.7rem] text-fg-dim">
                <Terminal size={13} />
                <span className="font-mono text-fg-muted">scratch.py</span>
                <span className="text-fg-dim/50">·</span>
                <span>
                  {stats.lines} 行 / {stats.chars} 字符
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <Button variant="ghost" size="sm" onClick={onTrace} loading={busy === "trace"} disabled={busy !== "idle"} icon={<Bug size={13} />}>
                  单步追踪
                </Button>
                <Button size="sm" onClick={onRun} loading={busy === "run"} disabled={busy !== "idle"} icon={<Play size={13} />}>
                  运行
                </Button>
              </div>
            </div>
            <div className="p-2">
              <CodeEditor
                value={code}
                onChange={(next) => {
                  dirtyRef.current = true;
                  setCode(next);
                }}
                onRun={onRun}
                onSave={() => void saveDraft()}
                height="clamp(320px, 52vh, 680px)"
                placeholder="# 想写什么都可以…"
              />
            </div>
          </Card>

          <div className="grid gap-3 lg:grid-cols-2">
            <Card className="overflow-hidden">
              <CardHeader title="标准输入 stdin" subtitle="作为 input() 的输入" icon={<Upload size={15} />} />
              <div className="px-3 pb-3">
                <textarea
                  className="input min-h-28 resize-y font-mono text-[0.78rem] leading-relaxed"
                  value={stdin}
                  onChange={(e) => {
                    dirtyRef.current = true;
                    setStdin(e.target.value);
                  }}
                  placeholder="每行一条输入…"
                  spellCheck={false}
                />
              </div>
            </Card>

            <Card className="overflow-hidden">
              <CardHeader title="运行结果" subtitle="标准输出与报错" icon={<FileCode2 size={15} />} />
              <div className="px-3 pb-3">
                {run ? (
                  <RunResultView run={run} />
                ) : (
                  <p className="rounded-lg border border-dashed border-line px-3 py-8 text-center text-xs text-fg-dim">
                    按 Ctrl+Enter 或点「运行」看输出
                  </p>
                )}
              </div>
            </Card>
          </div>
        </div>

        {/* 片段侧栏 */}
        <Card className="h-fit">
          <CardHeader
            title="我的片段"
            subtitle={`${snippets.length} 个`}
            icon={<FileCode2 size={15} />}
            right={
              <Button variant="ghost" size="sm" onClick={() => void loadSnippets()} loading={loadingSnippets}>
                刷新
              </Button>
            }
          />
          <div className="px-3 pb-3">
            <div className="flex gap-1.5">
              <input
                className="input py-1.5 text-xs"
                placeholder="片段名字"
                value={snippetName}
                onChange={(e) => setSnippetName(e.target.value)}
                maxLength={80}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void saveSnippet();
                }}
              />
              <Button size="sm" onClick={() => void saveSnippet()} icon={<Save size={13} />}>
                保存
              </Button>
            </div>

            <div className="mt-2 max-h-[52vh] space-y-1.5 overflow-y-auto">
              {loadingSnippets ? (
                <div className="flex justify-center py-6">
                  <Spinner />
                </div>
              ) : snippets.length === 0 ? (
                <EmptyState icon={<FileCode2 size={18} />} title="还没有片段" hint="把常用代码存成片段，下次一点就回来。" />
              ) : (
                snippets.map((item) => (
                  <div
                    key={item.name}
                    className="group flex items-center gap-1.5 rounded-lg border border-line bg-ink-900/50 px-2 py-1.5"
                  >
                    <button
                      type="button"
                      onClick={() => {
                        dirtyRef.current = true;
                        setCode(item.code);
                        toast.info(`已载入「${item.name}」`);
                      }}
                      className="min-w-0 flex-1 text-left"
                    >
                      <span className="block truncate text-[0.78rem] text-fg-muted group-hover:text-fg">{item.name}</span>
                      <span className="block text-[0.62rem] text-fg-dim">{fmtDateTime(item.updated)}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void removeSnippet(item.name)}
                      className="rounded p-1 text-fg-dim opacity-0 transition-opacity hover:text-bad-400 group-hover:opacity-100"
                      title="删除片段"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
            <div className="mt-3 space-y-1 rounded-lg border border-line bg-ink-900/40 px-2.5 py-2 text-[0.66rem] leading-relaxed text-fg-dim">
              <p>· 运行上限：6 秒 / 单次输出 4 万字符</p>
              <p>· 练习环境不允许 os.system、subprocess、ctypes 等</p>
              <p>· 草稿随账号同步，换设备也在</p>
            </div>
          </div>
        </Card>
      </div>

      <Modal open={traceOpen} onClose={() => setTraceOpen(false)} title="执行过程单步追踪" width="max-w-5xl">
        {trace ? <TraceViewer code={code} trace={trace} summary={traceSummary} /> : null}
      </Modal>
    </div>
  );
}
