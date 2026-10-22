# -*- coding: utf-8 -*-
"""组卷考试的界面：组卷配置页（ExamSetupView）与成绩报告页（ExamResultView）。

追加在 ui.py 末尾，由 App 持有。
"""

import tkinter as tk

import theme as T
import exam as examlib
from widgets import RoundButton, ProgressBar, ScrollFrame


class ExamSetupView(tk.Frame):
    """组卷配置：题量、章节范围、难度、限时。"""

    COUNTS = [5, 10, 20, 30]
    LIMITS = [(0, "不限时"), (10, "10 分钟"), (20, "20 分钟"), (30, "30 分钟")]
    LEVELS = [(0, "不限"), (1, "入门"), (2, "进阶"), (3, "挑战")]

    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.fonts = app.fonts
        self.count = 10
        self.limit = 20
        self.level = 0
        self.chapters = set(c["name"] for c in app.chapters)
        self.count_btns = {}
        self.limit_btns = {}
        self.level_btns = {}
        self.chapter_btns = {}
        self._build()

    # ------------------------------------------------------------ 构建
    def _build(self):
        f = self.fonts
        wrap = tk.Frame(self, bg=T.BG)
        wrap.pack(fill="both", expand=True, padx=44, pady=(34, 20))

        tk.Label(wrap, text="模拟组卷", bg=T.BG, fg=T.TEXT, font=f["h1"]).pack(anchor="w")
        tk.Label(wrap, text="选择范围后随机抽题，限时作答，交卷后给出得分与逐题明细",
                 bg=T.BG, fg=T.MUTED, font=f["body"]).pack(anchor="w", pady=(6, 22))

        card = tk.Frame(wrap, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        card.pack(fill="x")
        body = tk.Frame(card, bg=T.CARD)
        body.pack(fill="x", padx=26, pady=20)

        self.count_btns = self._row(body, "题目数量",
                                    [(c, "{} 题".format(c)) for c in self.COUNTS],
                                    self.count, self._set_count, f)
        self.chapter_btns = self._row_multi(body, "章节范围", f)
        self.level_btns = self._row(body, "难度",
                                    [(lv, name) for lv, name in self.LEVELS],
                                    self.level, self._set_level, f)
        self.limit_btns = self._row(body, "限时",
                                    [(v, name) for v, name in self.LIMITS],
                                    self.limit, self._set_limit, f)

        bottom = tk.Frame(wrap, bg=T.BG)
        bottom.pack(fill="x", pady=(22, 0))
        self.avail_label = tk.Label(bottom, text="", bg=T.BG, fg=T.MUTED, font=f["small"])
        self.avail_label.pack(side="left")
        RoundButton(bottom, "随机组卷并开始", command=self._start,
                    bg=T.ACCENT, fg="#ffffff", font=f["button"],
                    padx=24, pady=12).pack(side="right")

        # 历史成绩
        hist = tk.Frame(wrap, bg=T.BG)
        hist.pack(fill="both", expand=True, pady=(26, 0))
        head = tk.Frame(hist, bg=T.BG)
        head.pack(fill="x")
        tk.Label(head, text="最近成绩", bg=T.BG, fg=T.TEXT, font=f["h3"]).pack(side="left")
        self.hist_note = tk.Label(head, text="", bg=T.BG, fg=T.MUTED, font=f["tiny"])
        self.hist_note.pack(side="right")

        self.scroll = ScrollFrame(hist, bg=T.BG)
        self.scroll.pack(fill="both", expand=True, pady=(8, 0))
        self.hist_body = self.scroll.body

    def _row(self, parent, title, options, current, on_select, f):
        row = tk.Frame(parent, bg=T.CARD)
        row.pack(fill="x", pady=(0, T.S(12)))
        tk.Label(row, text=title, bg=T.CARD, fg=T.MUTED, font=f["small"],
                 width=8, anchor="w").pack(side="left")
        btns = {}
        for value, text in options:
            btn = RoundButton(row, text, command=lambda v=value: on_select(v),
                              bg=T.CARD_HI, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                              font=f["small"], padx=14, pady=7)
            btn.pack(side="left", padx=(0, T.S(8)))
            btns[value] = btn
        return btns

    def _row_multi(self, parent, title, f):
        row = tk.Frame(parent, bg=T.CARD)
        row.pack(fill="x", pady=(0, T.S(12)))
        tk.Label(row, text=title, bg=T.CARD, fg=T.MUTED, font=f["small"],
                 width=8, anchor="w").pack(side="left")
        btns = {}
        for c in self.app.chapters:
            btn = RoundButton(row, c["short"], command=lambda n=c["name"]: self._toggle_chapter(n),
                              bg=T.CARD_HI, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                              font=f["tiny"], padx=12, pady=7)
            btn.pack(side="left", padx=(0, T.S(8)))
            btns[c["name"]] = btn
        return btns

    # ------------------------------------------------------------ 交互
    def _set_count(self, value):
        self.count = value
        self._paint()

    def _set_level(self, value):
        self.level = value
        self._paint()

    def _set_limit(self, value):
        self.limit = value
        self._paint()

    def _toggle_chapter(self, name):
        if name in self.chapters:
            if len(self.chapters) == 1:
                self.app.toast("至少要选一个章节")
                return
            self.chapters.discard(name)
        else:
            self.chapters.add(name)
        self._paint()

    def _paint(self):
        for value, btn in self.count_btns.items():
            self._mark(btn, value == self.count)
        for value, btn in self.level_btns.items():
            self._mark(btn, value == self.level)
        for value, btn in self.limit_btns.items():
            self._mark(btn, value == self.limit)
        for name, btn in self.chapter_btns.items():
            self._mark(btn, name in self.chapters)
        self._update_available()

    @staticmethod
    def _mark(btn, active):
        if active:
            btn.set_colors(T.ACCENT, "#ffffff", hover=T.ACCENT_HI)
        else:
            btn.set_colors(T.CARD_HI, T.TEXT_DIM, hover=T.BORDER_HI)

    def _pool(self):
        levels = {self.level} if self.level else None
        return examlib.filter_pool(self.app.questions, self.chapters, levels)

    def _update_available(self):
        pool = self._pool()
        self.avail_label.configure(
            text="当前范围可用 {} 题（题库共 {} 题）".format(len(pool), len(self.app.questions)))

    # ------------------------------------------------------------ 开始
    def _start(self):
        levels = {self.level} if self.level else None
        try:
            paper = examlib.generate_paper(self.app.questions, self.count,
                                           chapters=self.chapters, levels=levels)
        except examlib.NotEnoughQuestions as e:
            self.app.toast(str(e))
            return
        meta = {
            "chapters": sorted(self.chapters),
            "levels": sorted(levels) if levels else [1, 2, 3],
            "limit": self.limit,
        }
        self.app.start_exam(paper, self.limit, meta=meta)

    # ------------------------------------------------------------ 刷新
    def refresh(self):
        self._paint()
        for w in self.hist_body.winfo_children():
            w.destroy()
        history = self.app.store.exam_history(10)
        if not history:
            self.hist_note.configure(text="还没有考试记录")
            tk.Label(self.hist_body, text="组一套卷子试试：选择题量后点右下角「随机组卷并开始」。",
                     bg=T.BG, fg=T.MUTED, font=self.fonts["small"]).pack(anchor="w", pady=6)
            return
        self.hist_note.configure(text="共 {} 次".format(len(history)))
        f = self.fonts
        for rec in history:
            row = tk.Frame(self.hist_body, bg=T.BG)
            row.pack(fill="x", pady=1)
            score = rec.get("score", 0)
            color = T.GREEN if score >= 80 else (T.YELLOW if score >= 60 else T.RED)
            tk.Label(row, text=rec.get("finished_at", "")[5:16], bg=T.BG, fg=T.MUTED,
                     font=f["small"], width=13, anchor="w").pack(side="left")
            tk.Label(row, text="{} 分".format(score), bg=T.BG, fg=color,
                     font=f["small"], width=7, anchor="w").pack(side="left")
            tk.Label(row, text="通过 {}/{}".format(rec.get("passed", 0), rec.get("total", 0)),
                     bg=T.BG, fg=T.TEXT_DIM, font=f["small"], width=12, anchor="w").pack(side="left")
            tk.Label(row, text="用时 " + examlib.format_clock(rec.get("seconds", 0)),
                     bg=T.BG, fg=T.MUTED, font=f["small"]).pack(side="left")


class ExamResultView(tk.Frame):
    """交卷后的成绩报告。"""

    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.fonts = app.fonts
        self.summary = None
        self.meta = {}
        self._build()

    def _build(self):
        f = self.fonts
        wrap = tk.Frame(self, bg=T.BG)
        wrap.pack(fill="both", expand=True, padx=44, pady=(34, 20))

        tk.Label(wrap, text="交卷报告", bg=T.BG, fg=T.TEXT, font=f["h1"]).pack(anchor="w")
        tk.Label(wrap, text="下面是本次组卷的得分与逐题情况，错题已自动进入错题本",
                 bg=T.BG, fg=T.MUTED, font=f["body"]).pack(anchor="w", pady=(6, 20))

        cards = tk.Frame(wrap, bg=T.BG)
        cards.pack(fill="x")
        self.tiles = {}
        specs = [("score", "得分", T.ACCENT), ("passed", "通过题数", T.GREEN),
                 ("used", "用时", T.YELLOW), ("rank", "评价", T.RED)]
        for i, (key, label, color) in enumerate(specs):
            card = tk.Frame(cards, bg=T.CARD, highlightbackground=T.BORDER,
                            highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            cards.grid_columnconfigure(i, weight=1)
            inner = tk.Frame(card, bg=T.CARD)
            inner.pack(fill="both", expand=True, padx=18, pady=14)
            value = tk.Label(inner, text="-", bg=T.CARD, fg=color,
                             font=(f["h1"][0], 22, "bold"))
            value.pack(anchor="w")
            tk.Label(inner, text=label, bg=T.CARD, fg=T.MUTED, font=f["tiny"]).pack(anchor="w")
            self.tiles[key] = value

        self.detail_bar = tk.Frame(wrap, bg=T.BG)
        self.detail_bar.pack(fill="x", pady=(24, 6))
        tk.Label(self.detail_bar, text="逐题明细", bg=T.BG, fg=T.TEXT,
                 font=f["h3"]).pack(side="left")
        self.meta_label = tk.Label(self.detail_bar, text="", bg=T.BG, fg=T.MUTED,
                                   font=f["tiny"])
        self.meta_label.pack(side="right")

        self.scroll = ScrollFrame(wrap, bg=T.BG)
        self.scroll.pack(fill="both", expand=True)
        self.rows_body = self.scroll.body

        actions = tk.Frame(wrap, bg=T.BG)
        actions.pack(fill="x", pady=(16, 0))
        RoundButton(actions, "再来一套", command=lambda: self.app.show("exam"),
                    bg=T.ACCENT, fg="#ffffff", font=f["button"],
                    padx=22, pady=11).pack(side="left")
        RoundButton(actions, "去错题本", command=lambda: self.app.start("wrong"),
                    bg=T.CARD_HI, fg=T.TEXT, hover=T.BORDER_HI, font=f["button"],
                    padx=20, pady=11).pack(side="left", padx=10)
        RoundButton(actions, "返回主页", command=lambda: self.app.show("home"),
                    bg=T.CARD_HI, fg=T.TEXT, hover=T.BORDER_HI, font=f["button"],
                    padx=20, pady=11).pack(side="left")

    def load(self, summary, meta=None):
        self.summary = summary
        self.meta = dict(meta or {})
        score = summary.get("score", 0)
        color = T.GREEN if score >= 80 else (T.YELLOW if score >= 60 else T.RED)
        self.tiles["score"].configure(text="{} 分".format(score), fg=color)
        self.tiles["passed"].configure(
            text="{}/{}".format(summary.get("passed", 0), summary.get("total", 0)))
        self.tiles["used"].configure(text=examlib.format_clock(summary.get("seconds", 0)))
        if score >= 90:
            rank = "优秀"
        elif score >= 80:
            rank = "良好"
        elif score >= 60:
            rank = "及格"
        else:
            rank = "需加强"
        self.tiles["rank"].configure(text=rank, fg=color)

        bal = self.meta.get("balance") or {}
        chapters = bal.get("chapters") or {}
        parts = ["{} {}".format(k.split(" ")[0], v) for k, v in chapters.items()]
        self.meta_label.configure(text="章节分布：" + "、".join(parts))

        for w in self.rows_body.winfo_children():
            w.destroy()
        f = self.fonts
        for i, row in enumerate(summary.get("rows", []), 1):
            line = tk.Frame(self.rows_body, bg=T.BG)
            line.pack(fill="x", pady=1)
            status = row["status"]
            if status == "pass":
                mark, color = "✓", T.GREEN
            elif status == "fail":
                mark, color = "✗", T.RED
            else:
                mark, color = "—", T.MUTED
            tk.Label(line, text=mark, bg=T.BG, fg=color, font=f["small"],
                     width=3, anchor="w").pack(side="left")
            tk.Label(line, text=row["id"], bg=T.BG, fg=T.MUTED, font=f["small"],
                     width=7, anchor="w").pack(side="left")
            tk.Label(line, text=row["title"], bg=T.BG, fg=T.TEXT, font=f["small"],
                     width=30, anchor="w").pack(side="left")
            tk.Label(line, text=row["chapter"].split(" ")[0], bg=T.BG, fg=T.MUTED,
                     font=f["tiny"], width=8, anchor="w").pack(side="left")
            tk.Label(line, text="尝试 {} 次".format(row["attempts"]), bg=T.BG, fg=T.MUTED,
                     font=f["tiny"], width=10, anchor="w").pack(side="left")
            text = {"pass": "通过", "fail": "未通过", "skip": "未作答"}[status]
            tk.Label(line, text=text, bg=T.BG, fg=color, font=f["tiny"]).pack(side="left")
