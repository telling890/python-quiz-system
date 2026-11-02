# -*- coding: utf-8 -*-
"""自由编程页：不看题库，自己写代码、自己运行、自己单步看执行过程。

和刷题页的区别只有一个——这里没有题目和测试用例，代码全靠自己定，
所以输出要自己看，草稿与代码片段会存进 state.json。
"""

import os
import queue
import threading
import time

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

import theme as T
from judge import run_code
from widgets import CodeEditor, RoundButton, ScrollFrame
from ui_trace import TracePane

TEMPLATE = '''# 自由编程：想写什么就写什么，写完按 F5 运行
# 这里没有题目也没有测试用例，输出对不对全靠自己判断

for i in range(1, 6):
    print(i, "的平方是", i * i)
'''


class FreeView(tk.Frame):
    """自由编程 / 草稿本。"""

    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.store = app.store
        self.fonts = app.fonts
        self._queue = queue.Queue()
        self._running = False
        self._save_job = None
        self._loaded = False
        self._build()
        self._poll()

    # ------------------------------------------------------------ 构建
    def _build(self):
        f = self.fonts
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = tk.Frame(self, bg=T.BG)
        head.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 8))
        head.grid_columnconfigure(0, weight=1)
        tk.Label(head, text="自由编程", bg=T.BG, fg=T.TEXT,
                 font=f["h2"]).grid(row=0, column=0, sticky="w")
        tk.Label(head, text="不看题库，写自己想写的代码；卡住了就单步执行看它怎么跑",
                 bg=T.BG, fg=T.MUTED, font=f["small"]).grid(row=1, column=0, sticky="w", pady=(2, 0))

        acts = tk.Frame(head, bg=T.BG)
        acts.grid(row=0, column=1, rowspan=2, sticky="e")
        RoundButton(acts, "清空", command=self.clear, bg=T.CARD_HI, fg=T.TEXT_DIM,
                    hover=T.BORDER_HI, font=f["small"], padx=14, pady=8).pack(side="right")
        RoundButton(acts, "导出 .py", command=self.export_py, bg=T.CARD_HI, fg=T.TEXT_DIM,
                    hover=T.BORDER_HI, font=f["small"], padx=14, pady=8).pack(side="right", padx=(0, 8))
        RoundButton(acts, "保存片段", command=self.save_snippet, bg=T.CARD_HI, fg=T.TEXT_DIM,
                    hover=T.BORDER_HI, font=f["small"], padx=14, pady=8).pack(side="right", padx=(0, 8))

        body = tk.Frame(self, bg=T.BG)
        body.grid(row=1, column=0, sticky="nsew", padx=30)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        bar = tk.Frame(body, bg=T.BG)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        bar.grid_columnconfigure(0, weight=1)
        tk.Label(bar, text="代码草稿（自动保存）", bg=T.BG, fg=T.MUTED,
                 font=f["tiny"]).grid(row=0, column=0, sticky="w")
        self.status = tk.Label(bar, text="F5 运行 · F6 单步执行 · Tab 缩进 4 格",
                               bg=T.BG, fg=T.MUTED, font=f["small"])
        self.status.grid(row=0, column=1, sticky="e")

        self.editor = CodeEditor(body, font=f["mono"], font_small=f["tiny"])
        self.editor.grid(row=1, column=0, sticky="nsew")
        self.editor.text.bind("<KeyRelease>", lambda e: self._schedule_save(), add="+")
        self.editor.text.bind("<<Paste>>", lambda e: self._schedule_save(), add="+")

        # ---- 右侧：我的片段
        side = tk.Frame(body, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        side.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(12, 0))
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(1, weight=1)
        tk.Label(side, text="我的片段", bg=T.CARD, fg=T.TEXT_DIM,
                 font=f["small"]).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.snip_count = tk.Label(side, text="", bg=T.CARD, fg=T.MUTED, font=f["tiny"])
        self.snip_count.grid(row=0, column=0, sticky="e", padx=12, pady=(10, 4))
        self.snip_list = ScrollFrame(side, bg=T.CARD)
        self.snip_list.canvas.configure(width=T.S(210))
        self.snip_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        tk.Label(side, text="点名字载入，✕ 删除", bg=T.CARD, fg=T.MUTED,
                 font=f["tiny"]).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

        # ---- 下方标签页
        self.nb = ttk.Notebook(body)
        self.nb.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        stdin_tab = tk.Frame(self.nb, bg=T.CARD_HI)
        self.nb.add(stdin_tab, text="  标准输入  ")
        tk.Label(stdin_tab, text="程序里用 input() 读的数据，一行一条", bg=T.CARD_HI,
                 fg=T.MUTED, font=f["tiny"]).pack(anchor="w", padx=12, pady=(8, 0))
        self.stdin_text = tk.Text(stdin_tab, height=4, bg=T.CARD_HI, fg=T.TEXT_DIM,
                                  insertbackground=T.ACCENT, font=f["mono_s"],
                                  relief="flat", bd=0, highlightthickness=0,
                                  padx=12, pady=6, wrap="none")
        self.stdin_text.pack(fill="both", expand=True)
        self.stdin_text.bind("<KeyRelease>", lambda e: self._schedule_save(), add="+")

        out_tab = tk.Frame(self.nb, bg=T.CARD_HI)
        self.nb.add(out_tab, text="  运行结果  ")
        self.result = tk.Text(out_tab, height=9, bg=T.CARD_HI, fg=T.TEXT_DIM,
                              font=f["small"], relief="flat", bd=0, highlightthickness=0,
                              padx=14, pady=8, wrap="word", cursor="arrow")
        rsb = ttk.Scrollbar(out_tab, orient="vertical", command=self.result.yview,
                            style="Dark.Vertical.TScrollbar")
        self.result.configure(yscrollcommand=rsb.set)
        self.result.pack(side="left", fill="both", expand=True)
        rsb.pack(side="right", fill="y")
        self.result.configure(state="disabled")
        self.result.tag_configure("ok", foreground=T.GREEN)
        self.result.tag_configure("bad", foreground=T.RED)
        self.result.tag_configure("dim", foreground=T.MUTED)
        self.result.tag_configure("code", foreground="#cfe6ff", font=(f["mono_s"][0], 9))
        self.result.tag_configure("tip", foreground=T.YELLOW)
        self.result.tag_configure("big", foreground=T.GREEN, font=(f["h3"][0], 12, "bold"))

        trace_tab = tk.Frame(self.nb, bg=T.CARD_HI)
        self.nb.add(trace_tab, text="  执行过程  ")
        self.trace_pane = TracePane(trace_tab, f, on_status=self._set_status,
                                    hint="点「单步执行」(F6) 开始逐行走一遍")
        self.trace_pane.pack(fill="both", expand=True)

        # ---- 底部
        bottom = tk.Frame(self, bg=T.BG)
        bottom.grid(row=2, column=0, sticky="ew", padx=30, pady=(12, 18))
        bottom.grid_columnconfigure(0, weight=1)
        tk.Label(bottom, text="输出在「运行结果」，逐步变量在「执行过程」",
                 bg=T.BG, fg=T.MUTED, font=f["tiny"]).grid(row=0, column=0, sticky="w")
        self.trace_btn = RoundButton(bottom, "单步执行  (F6)", command=self.trace,
                                     bg=T.CARD_HI, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                                     font=f["small"], padx=16, pady=8)
        self.trace_btn.grid(row=0, column=1, padx=(0, 10))
        self.run_btn = RoundButton(bottom, "运行  (F5)", command=self.run,
                                   bg=T.ACCENT, fg="#ffffff", font=f["button"],
                                   padx=22, pady=9)
        self.run_btn.grid(row=0, column=2)

    # ------------------------------------------------------------ 数据
    def refresh(self):
        """首次显示时装载草稿；之后每次回到本页刷新片段列表。"""
        if not self._loaded:
            self._loaded = True
            free = self.store.free_state()
            self.editor.set_code(free.get("code") or TEMPLATE)
            self.stdin_text.delete("1.0", "end")
            if free.get("stdin"):
                self.stdin_text.insert("1.0", free["stdin"])
            self._clear_result("还没运行。写好代码后按 F5。")
        self.refresh_snippets()

    def _stdin(self):
        return self.stdin_text.get("1.0", "end-1c")

    def _schedule_save(self):
        if self._save_job is not None:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                pass
        self._save_job = self.after(1200, self._save_now)

    def _save_now(self):
        self._save_job = None
        free = self.store.free_state()
        code = self.editor.get_code()
        stdin_text = self._stdin() if hasattr(self, "stdin_text") else ""
        if free.get("code") == code and free.get("stdin") == stdin_text:
            return
        if self.store.save_free(code, stdin_text):
            self.status.configure(text="草稿已保存 " + time.strftime("%H:%M:%S"), fg=T.GREEN)

    def _set_status(self, text, color=T.MUTED):
        self.status.configure(text=text, fg=color)

    # ------------------------------------------------------------ 片段
    def refresh_snippets(self):
        for w in self.snip_list.body.winfo_children():
            w.destroy()
        items = self.store.snippets()
        self.snip_count.configure(text="{} 个".format(len(items)) if items else "")
        if not items:
            tk.Label(self.snip_list.body, text="还没有片段\n写完一段就点「保存片段」",
                     bg=T.CARD, fg=T.MUTED, font=self.fonts["tiny"],
                     justify="left").pack(anchor="w", padx=10, pady=10)
            return
        for it in items[:40]:
            row = tk.Frame(self.snip_list.body, bg=T.CARD)
            row.pack(fill="x", padx=4, pady=1)
            name = tk.Label(row, text=it.get("name", ""), bg=T.CARD, fg=T.TEXT_DIM,
                            font=self.fonts["tiny"], anchor="w", cursor="hand2")
            name.pack(side="left", fill="x", expand=True, padx=(6, 0))
            del_btn = tk.Label(row, text="✕", bg=T.CARD, fg=T.MUTED,
                               font=self.fonts["tiny"], cursor="hand2")
            del_btn.pack(side="right", padx=(4, 6))
            for w in (row, name):
                w.bind("<Button-1>", lambda e, i=it: self.load_snippet(i))
                w.bind("<Enter>", lambda e, r=row, n=name: self._hover(r, n, True))
                w.bind("<Leave>", lambda e, r=row, n=name: self._hover(r, n, False))
            del_btn.bind("<Button-1>", lambda e, n=it.get("name", ""): self.delete_snippet(n))

    def _hover(self, row, name, on):
        color = T.CARD_HI if on else T.CARD
        row.configure(bg=color)
        name.configure(bg=color, fg=T.TEXT if on else T.TEXT_DIM)

    def load_snippet(self, item):
        code = item.get("code", "")
        current = self.editor.get_code()
        if current.strip() and current != TEMPLATE:
            if not messagebox.askyesno("载入片段",
                                       "会用片段「{}」替换当前代码，继续吗？".format(
                                           item.get("name", "")), parent=self):
                return
        self._save_now()
        self.editor.set_code(code)
        self._save_now()
        self._clear_result("已载入片段「{}」，按 F5 运行。".format(item.get("name", "")))
        self.nb.select(1)
        self.app.toast("已载入片段：{}".format(item.get("name", "")))

    def save_snippet(self):
        code = self.editor.get_code()
        if not code.strip():
            self.app.toast("先写点代码再保存")
            return
        name = simpledialog.askstring("保存片段", "给这段代码起个名字：",
                                      parent=self, initialvalue="片段 {}".format(
                                          time.strftime("%m-%d %H:%M")))
        if not name:
            return
        created = self.store.save_snippet(name, code)
        if created is None:
            self.app.toast("名字不能为空")
            return
        self.refresh_snippets()
        self.app.toast("{}：{}".format("已保存" if created else "已更新", name.strip()))

    def delete_snippet(self, name):
        if not name:
            return
        if not messagebox.askyesno("删除片段", "确定删除片段「{}」吗？".format(name), parent=self):
            return
        if self.store.delete_snippet(name):
            self.refresh_snippets()
            self.app.toast("已删除片段：{}".format(name))

    def export_py(self):
        code = self.editor.get_code()
        if not code.strip():
            self.app.toast("还没有代码可导出")
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="导出 Python 文件", defaultextension=".py",
            initialfile="my_code.py",
            filetypes=[("Python 文件", "*.py"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code)
        except OSError as exc:
            messagebox.showerror("导出失败", "写入文件失败：{}".format(exc), parent=self)
            return
        self.app.toast("已导出到 " + os.path.basename(path))

    def clear(self):
        if not messagebox.askyesno("清空代码", "确定清空编辑区吗？（草稿会被覆盖）", parent=self):
            return
        self.editor.set_code("")
        self._save_now()
        self._clear_result("编辑区已清空。")
        self.nb.select(1)

    # ------------------------------------------------------------ 运行
    def run(self):
        if self._running:
            return
        code = self.editor.get_code()
        if not code.strip():
            self.app.toast("先写点代码再运行")
            return
        self._save_now()
        self._running = True
        self.run_btn.set_enabled(False)
        self.run_btn.configure_text("运行中…")
        self.status.configure(text="正在运行…", fg=T.MUTED)
        self.nb.select(1)
        stdin_data = self._stdin()
        started = time.time()

        def job():
            run = run_code(code, stdin_data)
            self._queue.put((run, time.time() - started))

        threading.Thread(target=job, daemon=True).start()

    def trace(self):
        self.nb.select(2)
        if not self.trace_pane.run(self.editor.get_code(), self._stdin(), "当前代码"):
            self.app.toast("先写点代码再单步执行吧")

    def _poll(self):
        try:
            while True:
                run, elapsed = self._queue.get_nowait()
                self._finish_run(run, elapsed)
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish_run(self, run, elapsed):
        self._running = False
        self.run_btn.set_enabled(True)
        self.run_btn.configure_text("运行  (F5)")
        cost = "用时 {:.2f} 秒".format(elapsed)

        t = self.result
        t.configure(state="normal")
        t.delete("1.0", "end")
        if run["timeout"]:
            self.status.configure(text="运行超时 · " + cost, fg=T.RED)
            t.insert("end", "运行超时（6 秒上限）\n", "big")
            t.insert("end", "很可能写了死循环，或者 input() 一直在等数据。\n"
                            "可以点「单步执行」逐行走一遍，看是在哪一步开始出不来的。\n", "tip")
        elif run["error"]:
            self.status.configure(text="运行出错 · " + cost, fg=T.RED)
            t.insert("end", "运行出错\n\n", "big")
            t.insert("end", run["error"] + "\n", "code")
            t.insert("end", "\n提示：报错只说明最后一步失败了，"
                            "切到「执行过程」逐行走一遍往往能直接看到变量是怎么变坏的。\n", "tip")
        else:
            self.status.configure(text="运行完成 · " + cost, fg=T.GREEN)
            t.insert("end", "程序输出（{}）\n\n".format(cost), "dim")
            t.insert("end", run["output"] if run["output"] else "（没有任何输出）\n", "code")
            if run["truncated"]:
                t.insert("end", "\n输出太长，只保留了前一部分。\n", "tip")
        t.configure(state="disabled")

    def _clear_result(self, text):
        t = self.result
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("end", text + "\n", "dim")
        t.configure(state="disabled")
