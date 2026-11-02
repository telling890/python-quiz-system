# -*- coding: utf-8 -*-
"""可复用的「执行过程」面板：代码当前行高亮 + 变量快照 + 已输出 + 时间轴。

刷题页与自由编程页共用这一套界面，区别只在头部按钮（刷题页多一个「用参考答案演示」）。
面板自己负责异步追踪（工作线程 + after 轮询），宿主只需调用 run()。
"""

import queue
import threading

import tkinter as tk
from tkinter import ttk

import theme as T
import tracer
from widgets import RoundButton, TraceScrubber


class TracePane(tk.Frame):
    """执行过程面板。

    actions   头部右侧的按钮列表 [(文字, 回调, "accent"/"ghost"), ...]，
              列表首项排在最右边
    on_status 可选回调 (text, color)，宿主用它更新自己的状态栏
    hint      没有追踪结果时显示的提示语
    """

    def __init__(self, master, fonts, actions=None, on_status=None,
                 hint="点「跟踪当前代码」开始逐行走一遍", height=9):
        super().__init__(master, bg=T.CARD_HI)
        self.fonts = fonts
        self._on_status = on_status
        self._hint = hint
        self._actions = list(actions or [])
        self._trace = None
        self._trace_index = 0
        self._trace_syncing = False
        self._play_job = None
        self._running = False
        self._queue = queue.Queue()
        self._build(height)
        self._poll()

    # ------------------------------------------------------------ 构建
    def _build(self, height):
        f = self.fonts
        head = tk.Frame(self, bg=T.CARD_HI)
        head.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(head, text="逐行看代码怎么跑：当前行、变量、已经打印的内容",
                 bg=T.CARD_HI, fg=T.MUTED, font=f["tiny"]).pack(side="left")

        body = tk.Frame(self, bg=T.CARD_HI)
        body.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        src_box = tk.Frame(body, bg=T.CARD, highlightbackground=T.BORDER,
                           highlightthickness=1)
        src_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        src_box.grid_rowconfigure(0, weight=1)
        src_box.grid_columnconfigure(1, weight=1)
        self.tr_ln = tk.Text(src_box, width=4, height=height, bg=T.GUTTER, fg=T.MUTED,
                             font=f["mono_s"], relief="flat", bd=0, highlightthickness=0,
                             wrap="none", padx=6, pady=8, cursor="arrow", takefocus=0,
                             spacing1=1, spacing3=1)
        self.tr_ln.grid(row=0, column=0, sticky="ns")
        self.tr_src = tk.Text(src_box, bg=T.CARD, fg=T.TEXT_DIM, font=f["mono_s"],
                              height=height, relief="flat", bd=0, highlightthickness=0,
                              wrap="none", padx=10, pady=8, cursor="arrow", takefocus=0,
                              spacing1=1, spacing3=1)
        self.tr_src.grid(row=0, column=1, sticky="nsew")
        sb = ttk.Scrollbar(src_box, orient="vertical", style="Dark.Vertical.TScrollbar")
        sb.grid(row=0, column=2, sticky="ns")
        sb.configure(command=lambda *a: (self.tr_src.yview(*a),
                                         self.tr_ln.yview_moveto(self.tr_src.yview()[0])))
        self.tr_src.configure(yscrollcommand=lambda first, last: (
            sb.set(first, last), self.tr_ln.yview_moveto(first)))
        self.tr_src.tag_configure("cur", background="#17395f")
        self.tr_src.tag_raise("cur")
        self.tr_ln.tag_configure("cur", foreground=T.ACCENT_HI, background="#17395f")
        for w in (self.tr_ln, self.tr_src):
            w.bind("<MouseWheel>", self._on_wheel)

        side = tk.Frame(body, bg=T.CARD_HI)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(1, weight=1)
        side.grid_rowconfigure(3, weight=1)
        tk.Label(side, text="变量", bg=T.CARD_HI, fg=T.MUTED,
                 font=f["tiny"]).grid(row=0, column=0, sticky="w")
        self.tr_vars = tk.Text(side, height=4, bg=T.CARD, fg=T.TEXT_DIM, font=f["mono_s"],
                               relief="flat", bd=0, highlightthickness=1,
                               highlightbackground=T.BORDER, wrap="none", padx=10, pady=6,
                               cursor="arrow", takefocus=0)
        self.tr_vars.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        tk.Label(side, text="已输出", bg=T.CARD_HI, fg=T.MUTED,
                 font=f["tiny"]).grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.tr_out = tk.Text(side, height=3, bg=T.CARD, fg=T.TEXT_DIM, font=f["mono_s"],
                              relief="flat", bd=0, highlightthickness=1,
                              highlightbackground=T.BORDER, wrap="none", padx=10, pady=6,
                              cursor="arrow", takefocus=0)
        self.tr_out.grid(row=3, column=0, sticky="nsew", pady=(2, 0))
        self.tr_vars.tag_configure("name", foreground="#9cdcfe")
        self.tr_vars.tag_configure("val", foreground=T.GREEN)
        self.tr_vars.tag_configure("dim", foreground=T.MUTED)
        self.tr_out.tag_configure("val", foreground=T.GREEN)
        self.tr_out.tag_configure("dim", foreground=T.MUTED)
        for w in (self.tr_vars, self.tr_out, self.tr_ln, self.tr_src):
            w.configure(state="disabled")

        ctl = tk.Frame(self, bg=T.CARD_HI)
        ctl.pack(fill="x", padx=12, pady=(8, 10))
        ctl.grid_columnconfigure(0, weight=1)
        btns = tk.Frame(ctl, bg=T.CARD_HI)
        btns.grid(row=0, column=0, sticky="w")
        self.tr_prev = RoundButton(btns, "◀ 上一步", command=lambda: self.trace_step(-1),
                                   bg=T.CARD, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                                   font=f["tiny"], padx=12, pady=5)
        self.tr_prev.pack(side="left")
        self.tr_next = RoundButton(btns, "下一步 ▶", command=lambda: self.trace_step(1),
                                   bg=T.CARD, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                                   font=f["tiny"], padx=12, pady=5)
        self.tr_next.pack(side="left", padx=(6, 0))
        self.tr_play = RoundButton(btns, "▶ 自动播放", command=self.toggle_trace_play,
                                   bg=T.CARD_HI, fg=T.ACCENT_HI, hover=T.BORDER_HI,
                                   font=f["tiny"], padx=12, pady=5)
        self.tr_play.pack(side="left", padx=(6, 0))
        self.tr_pos = tk.Label(ctl, text=self._hint, bg=T.CARD_HI, fg=T.MUTED,
                               font=f["tiny"])
        self.tr_pos.grid(row=0, column=1, sticky="e")
        self.tr_scale = TraceScrubber(ctl, command=self._on_scale)
        self.tr_scale.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        # 头部按钮最后放，保证压在标题右侧
        for text, command, style in reversed(self._actions):
            if style == "accent":
                RoundButton(head, text, command=command, bg=T.ACCENT, fg="#ffffff",
                            hover=T.ACCENT_HI, font=f["tiny"], padx=14,
                            pady=5).pack(side="right", padx=(0, 8))
            else:
                RoundButton(head, text, command=command, bg=T.CARD, fg=T.TEXT_DIM,
                            hover=T.BORDER_HI, font=f["tiny"], padx=12,
                            pady=5).pack(side="right")

    # ------------------------------------------------------------ 对外接口
    def run(self, code, stdin_text="", what="当前代码"):
        """异步追踪一段代码；完成后自动展示第一步。"""
        if self._running:
            return False
        if not (code or "").strip():
            self.set_note("先写点代码再单步执行吧", T.YELLOW)
            return False
        self._stop_play()
        self._running = True
        self.tr_pos.configure(text="正在跟踪「{}」…".format(what), fg=T.MUTED)
        self._notify("正在跟踪执行…", T.MUTED)

        def job():
            result = tracer.trace_code(code, stdin_text)
            self._queue.put((code, what, result))

        threading.Thread(target=job, daemon=True).start()
        return True

    def _poll(self):
        """主线程轮询工作线程的结果：Tk 只能在主线程里改控件。"""
        try:
            while True:
                code, what, result = self._queue.get_nowait()
                self._finish(code, what, result)
        except queue.Empty:
            pass
        try:
            self.after(80, self._poll)
        except tk.TclError:
            pass

    def load(self, code, result, what="当前代码"):
        """直接装载一份已有的追踪结果（tests / 截图脚本用）。"""
        self._finish(code, what, result)

    def reset(self):
        """清空面板（换题时调用）。"""
        self._stop_play()
        self._trace = None
        self._trace_index = 0
        for w in (self.tr_ln, self.tr_src):
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.configure(state="disabled")
        self.set_note(self._hint, T.MUTED)
        self._render_vars(None)
        self._render_out("")
        self.tr_scale.set_range(0)
        self._sync_scale(0)

    def set_note(self, text, color=T.MUTED):
        self.tr_pos.configure(text=text, fg=color)

    @property
    def steps(self):
        return ((self._trace or {}).get("result", {}) or {}).get("steps") or []

    # ------------------------------------------------------------ 内部：渲染
    def _finish(self, code, what, result):
        self._running = False
        self._trace = {"code": code, "what": what, "result": result}
        self._trace_index = 0
        steps = result["steps"]
        self._render_code(code)

        note = tracer.describe(result)
        if not steps:
            self.set_note(note or "这段代码没有可执行的语句", T.YELLOW)
            self._notify(note or "没有记录到执行过程", T.YELLOW)
            self._render_vars(None)
            self._render_out("")
            self.tr_scale.set_range(0)
            self._sync_scale(0)
            return

        self.tr_scale.set_range(max(0, len(steps) - 1))
        self._sync_scale(0)
        self.render_step()
        if note:
            self._notify(note, T.YELLOW)
        else:
            self._notify("跟踪完成：{} 步 · 可拖动时间轴回看".format(len(steps)), T.GREEN)

    def _render_code(self, code):
        lines = (code or "").replace("\t", "    ").split("\n")
        numbers = "\n".join("{:>3}".format(i) for i in range(1, len(lines) + 1))
        for w, text in ((self.tr_ln, numbers), (self.tr_src, "\n".join(lines))):
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.insert("1.0", text)
            w.configure(state="disabled")

    def render_step(self):
        steps = self.steps
        if not steps:
            return
        self._trace_index = max(0, min(self._trace_index, len(steps) - 1))
        idx = self._trace_index
        step = steps[idx]

        for w in (self.tr_src, self.tr_ln):
            w.tag_remove("cur", "1.0", "end")
        line = max(1, int(step.get("line") or 1))
        start, end = "%d.0" % line, "%d.end" % line
        self.tr_src.tag_add("cur", start, end)
        self.tr_ln.tag_add("cur", start, end)
        for w in (self.tr_src, self.tr_ln):
            try:
                w.see(start)
            except tk.TclError:
                pass
        self.tr_ln.yview_moveto(self.tr_src.yview()[0])

        self._render_vars(step)
        self._render_out(step.get("out", ""))

        title = tracer.step_title(step)
        if idx == 0 and step.get("event") == "call":
            title = "开始执行 · " + title
        self.set_note("第 {} / {} 步 · {}".format(idx + 1, len(steps), title), T.TEXT_DIM)
        self._sync_scale(idx)

    def _render_vars(self, step):
        t = self.tr_vars
        t.configure(state="normal")
        t.delete("1.0", "end")
        if step and step.get("vars"):
            for name, value in step["vars"]:
                t.insert("end", name, "name")
                t.insert("end", " = ", "dim")
                t.insert("end", value + "\n", "val")
            if step.get("hidden"):
                t.insert("end", "… 另有 {} 个变量未显示\n".format(step["hidden"]), "dim")
        else:
            t.insert("end", "（这一步还没有变量）\n", "dim")
        t.configure(state="disabled")

    def _render_out(self, text):
        t = self.tr_out
        t.configure(state="normal")
        t.delete("1.0", "end")
        if text:
            t.insert("end", text, "val")
        else:
            t.insert("end", "（还没有输出）\n", "dim")
        t.configure(state="disabled")
        t.see("end")

    def _notify(self, text, color):
        if self._on_status:
            self._on_status(text, color)

    # ------------------------------------------------------------ 内部：交互
    def _on_wheel(self, event):
        delta = getattr(event, "delta", 0)
        if not delta:
            delta = 120 if getattr(event, "num", 0) == 4 else -120
        self.tr_src.yview_scroll(int(-delta / 120), "units")
        self.tr_ln.yview_moveto(self.tr_src.yview()[0])
        return "break"

    def trace_step(self, delta):
        if not self.steps:
            self.set_note("先点「跟踪当前代码」或「用参考答案演示」", T.YELLOW)
            return
        self._stop_play()
        self._trace_index += delta
        self.render_step()

    def toggle_trace_play(self):
        if self._play_job is not None:
            self._stop_play()
            return
        if not self.steps:
            self.set_note("先点「跟踪当前代码」再播放", T.YELLOW)
            return
        if self._trace_index >= len(self.steps) - 1:
            self._trace_index = 0
            self.render_step()
        self.tr_play.configure_text("⏸ 暂停")
        self._play_job = self.after(420, self._play_once)

    def _play_once(self):
        self._play_job = None
        if not self.steps or self._trace_index >= len(self.steps) - 1:
            self._stop_play()
            return
        self._trace_index += 1
        self.render_step()
        self._play_job = self.after(420, self._play_once)

    def _stop_play(self):
        if self._play_job is not None:
            try:
                self.after_cancel(self._play_job)
            except Exception:
                pass
            self._play_job = None
        try:
            self.tr_play.configure_text("▶ 自动播放")
        except (tk.TclError, AttributeError):
            pass

    def _on_scale(self, value):
        if self._trace_syncing:
            return
        if not self.steps:
            return
        try:
            idx = int(round(float(value)))
        except (TypeError, ValueError):
            return
        self._stop_play()
        self._trace_index = max(0, min(idx, len(self.steps) - 1))
        self.render_step()

    def _sync_scale(self, idx):
        self._trace_syncing = True
        try:
            self.tr_scale.set_value(idx)
        except (tk.TclError, AttributeError):
            pass
        finally:
            self._trace_syncing = False
