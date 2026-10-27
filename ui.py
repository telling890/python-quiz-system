# -*- coding: utf-8 -*-
"""主界面：侧边导航 + 主页 / 刷题页 / 学习统计。"""

import io
import os
import queue
import threading

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import theme as T
from widgets import (RoundButton, Pill, NavItem, ProgressBar, ScrollFrame,
                       CodeEditor, PieChart, LineChart)
import exam as examlib
from ui_exam import ExamSetupView, ExamResultView
from qbank import QUESTIONS, CHAPTERS
from store import Store
from judge import run_case, run_code

TEMPLATE = """# 在这里写你的代码
# 读入数据用 input()，输出结果用 print()

"""


def _short(text, limit=90):
    if not text:
        return "（无）"
    s = " / ".join([ln for ln in text.split("\n") if ln != ""]) or "（空行）"
    if len(s) > limit:
        s = s[:limit] + "…"
    return s


def _indent(text, prefix="      "):
    if not text:
        return prefix + "（无输出）"
    return "\n".join(prefix + ln for ln in text.split("\n"))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg=T.BG)
        self.title("Python 程序设计刷题系统")

        # 按屏幕 DPI 放大窗口与间距：高分屏下文字清晰且不挤
        try:
            dpi = float(self.winfo_fpixels("1i"))
        except tk.TclError:
            dpi = 96.0
        self.scale = T.set_scale(dpi / 96.0)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        win_w = min(T.S(1320), sw - T.S(40))
        win_h = min(T.S(860), sh - T.S(80))
        self.geometry("%dx%d+%d+%d" % (win_w, win_h, T.S(24), T.S(16)))
        self.minsize(min(T.S(1080), win_w, sw - T.S(60)), min(T.S(720), win_h, sh - T.S(120)))

        fam = T.pick_font(["Microsoft YaHei UI", "Microsoft YaHei", "SimHei"], self)
        mono = T.pick_font(["Consolas", "Cascadia Mono", "Courier New"], self)
        self.fonts = {
            "h1": (fam, 26, "bold"),
            "h2": (fam, 18, "bold"),
            "h3": (fam, 13, "bold"),
            "body": (fam, 11),
            "small": (fam, 10),
            "tiny": (fam, 9),
            "button": (fam, 11, "bold"),
            "mono": (mono, 11),
            "mono_s": (mono, 9),
        }

        self.store = Store()
        self._save_warned = False
        self.store.on_save_error = self._on_save_error
        self.store.on_save_ok = self._on_save_ok
        self.questions = QUESTIONS
        self.chapters = CHAPTERS
        self.session_chapter = None
        self.qmap = dict((q["id"], q) for q in QUESTIONS)

        self._init_style()
        self._build_layout()

        self.bind_all("<F5>", lambda e: self.practice.run_tests())
        self.bind_all("<Control-Return>", lambda e: self.practice.run_tests())
        self.bind_all("<Alt-Right>", lambda e: self.practice.next_q())
        self.bind_all("<Alt-Left>", lambda e: self.practice.prev_q())
        self.bind_all("<Control-f>", lambda e: self._focus_search())

        self.refresh_global()
        self.show("home")

    # ------------------------------------------------------------ 样式
    def _init_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TNotebook", background=T.BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        st.configure("TNotebook.Tab", background=T.CARD, foreground=T.MUTED,
                     lightcolor=T.CARD, darkcolor=T.CARD, bordercolor=T.BORDER,
                     padding=(T.S(16), T.S(8)), borderwidth=1, font=self.fonts["small"])
        st.map("TNotebook.Tab",
               background=[("selected", T.CARD_HI)],
               lightcolor=[("selected", T.CARD_HI)],
               darkcolor=[("selected", T.CARD_HI)],
               bordercolor=[("selected", T.CARD_HI)],
               foreground=[("selected", T.TEXT)],
               expand=[("selected", (0, 0, 0, 0))])
        st.configure("Dark.Vertical.TScrollbar", gripcount=0,
                     background=T.CARD_HI, darkcolor=T.CARD_HI, lightcolor=T.CARD_HI,
                     troughcolor=T.CARD, bordercolor=T.CARD, arrowcolor=T.MUTED,
                     width=T.S(11), arrowsize=T.S(11))
        st.map("Dark.Vertical.TScrollbar",
               background=[("active", T.BORDER_HI)],
               arrowcolor=[("active", T.TEXT)])

    def import_bank(self):
        """导入 JSON 格式的自定义题库，写入 state 目录，重启后并入「自定义题库」章节。"""
        import json as _json

        path = filedialog.askopenfilename(
            title="选择题库文件（JSON）",
            filetypes=[("JSON 题库", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = _json.load(f)
        except Exception as e:
            messagebox.showerror("导入失败", "文件不是合法的 JSON：\n{}".format(e))
            return

        items = data.get("questions") if isinstance(data, dict) else data
        if not isinstance(items, list):
            messagebox.showerror("导入失败", "JSON 顶层应该是题目数组，或带 questions 字段的对象。")
            return

        import qbank as qbanklib
        good = []
        for i, raw in enumerate(items):
            q = qbanklib.normalize_question(raw, i)
            if q:
                good.append(q)
        if not good:
            messagebox.showerror(
                "导入失败",
                "没有可用的题目。每道题至少要有 title / desc / ref / cases 四个字段。")
            return

        # 校验参考答案：跑一遍用例，提示有多少题答案对不上
        bad = []
        for q in good:
            ok = True
            for case in q["cases"]:
                result = run_case(q["ref"], case)
                if result.get("status") != "pass":
                    ok = False
                    break
            if not ok:
                bad.append(q["id"])

        folder = os.path.dirname(qbanklib.CUSTOM_FILE)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        try:
            with open(qbanklib.CUSTOM_FILE, "w", encoding="utf-8") as f:
                _json.dump(good, f, ensure_ascii=False, indent=1)
        except Exception as e:
            messagebox.showerror("导入失败", "写入文件时出错：\n{}".format(e))
            return

        msg = "已导入 {} 道题（共 {} 条，{} 条格式不完整被跳过）。\n\n".format(
            len(good), len(items), len(items) - len(good))
        if bad:
            msg += "注意：有 {} 道题的参考答案没通过自己的用例（{}），\n讲课时可能需要先改一下。\n\n".format(
                len(bad), "、".join(bad[:5]) + ("…" if len(bad) > 5 else ""))
        msg += "题库会在重启程序后出现在「自定义题库」章节里。\n现在重启吗？"

        if messagebox.askyesno("导入成功", msg):
            self._restart()

    def _restart(self):
        """重启程序（打包版直接重新拉起 exe，源码模式用当前解释器再跑一遍）。"""
        import subprocess
        import sys
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable])
            else:
                subprocess.Popen([sys.executable] + sys.argv)
        except Exception as e:
            messagebox.showerror("重启失败", "请手动关闭程序再重新打开。\n{}".format(e))
            return
        self.destroy()

    # ------------------------------------------------------------ 进度保存
    def _on_save_error(self, message):
        """进度写盘失败：侧栏常驻红字提醒，并在第一次失败时弹窗说明。"""
        if getattr(self, "save_warning", None) is not None:
            self.save_warning.configure(text="⚠ 进度未保存\n点击查看原因")
            self.save_warning.pack(fill="x", pady=(0, 6), before=self.progress_label)
        self._log_save_error(message)
        if not self._save_warned:
            self._save_warned = True
            try:
                messagebox.showwarning(
                    "进度没能保存",
                    "刚才的学习记录没有写入磁盘。\n\n{}\n\n"
                    "常见原因：安全软件拦截、目录只读、磁盘空间不足。\n"
                    "在修复之前，关闭程序后本次进度会丢失。\n\n"
                    "侧栏会一直显示「⚠ 进度未保存」，点它可再看原因。".format(message))
            except tk.TclError:
                pass

    def _on_save_ok(self):
        """之前失败过、这次写成功了：撤掉告警并提示。"""
        if getattr(self, "save_warning", None) is not None:
            self.save_warning.pack_forget()
            self.save_warning.configure(text="")
        self._save_warned = False
        self.toast("进度已恢复保存")

    def show_save_error(self):
        """点侧栏告警时看详细原因与处理办法。"""
        message = self.store.last_error or "（没有更多信息）"
        messagebox.showerror(
            "进度未能保存",
            "保存路径：\n{}\n\n原因：\n{}\n\n"
            "可以这样处理：\n"
            "· 把进度文件换个位置：设置环境变量 PYQUIZ_STATE_DIR 指向可写目录\n"
            "· 检查安全软件是否拦截了写文件，或给该目录加白名单\n"
            "· 确认磁盘还有剩余空间".format(self.store.path, message))

    def _log_save_error(self, message):
        """把失败原因追加到 error.log，方便事后排查。"""
        import time
        try:
            folder = os.path.dirname(self.store.path) or "."
            if not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            with io.open(os.path.join(folder, "error.log"), "a", encoding="utf-8") as f:
                f.write("[{}] 进度保存失败：{}\n".format(
                    time.strftime("%Y-%m-%d %H:%M:%S"), message))
        except (OSError, ValueError):
            pass

    def _focus_search(self):
        """Ctrl+F：跳到搜索框。"""
        if self.session_mode != "practice":
            self.start("order")
        self.practice.search_entry.focus_set()
        self.practice.search_entry.select_range(0, "end")

    # ------------------------------------------------------------ 布局
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=T.SIDEBAR, width=T.S(212))
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self._build_sidebar()

        self.container = tk.Frame(self, bg=T.BG)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.views = {}
        self.home = HomeView(self.container, self)
        self.practice = PracticeView(self.container, self)
        self.stats = StatsView(self.container, self)
        self.exam_setup = ExamSetupView(self.container, self)
        self.result = ExamResultView(self.container, self)
        for v in (self.home, self.practice, self.stats, self.exam_setup, self.result):
            v.grid(row=0, column=0, sticky="nsew")

        self.toast_label = tk.Label(self, text="", bg=T.CARD_HI, fg=T.TEXT,
                              font=self.fonts["small"], padx=16, pady=8)
        self._toast_job = None

    def _build_sidebar(self):
        brand = tk.Frame(self.sidebar, bg=T.SIDEBAR)
        brand.pack(fill="x", padx=18, pady=(26, 6))
        tk.Label(brand, text="PY", bg=T.ACCENT, fg="#ffffff",
                 font=self.fonts["h3"], padx=8, pady=2).pack(side="left")
        tk.Label(brand, text="  Python 刷题", bg=T.SIDEBAR, fg=T.TEXT,
                 font=self.fonts["h3"]).pack(side="left")

        tk.Label(self.sidebar, text="教材实验题库 · {} 题".format(len(self.questions)), bg=T.SIDEBAR, fg=T.MUTED,
                 font=self.fonts["tiny"]).pack(anchor="w", padx=20, pady=(0, 22))

        self.nav = {}
        items = [
            ("home", "◆", "主页"),
            ("order", "▶", "顺序刷题"),
            ("random", "↻", "随机抽题"),
            ("exam", "◎", "模拟组卷"),
            ("wrong", "!", "错题本"),
            ("fav", "★", "收藏夹"),
            ("stats", "%", "学习统计"),
        ]
        for key, icon, label in items:
            item = NavItem(self.sidebar, icon, label,
                           command=(lambda k=key: self.on_nav(k)),
                           font=self.fonts["body"], font_bold=self.fonts["h3"])
            item.pack(fill="x", padx=8, pady=1)
            self.nav[key] = item

        bottom = tk.Frame(self.sidebar, bg=T.SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        self.save_warning = tk.Label(bottom, text="", bg=T.SIDEBAR, fg=T.RED,
                                     font=self.fonts["tiny"], anchor="w",
                                     cursor="hand2", justify="left")
        self.save_warning.bind("<Button-1>", lambda e: self.show_save_error())
        self.progress_label = tk.Label(bottom, text="已通过 0 / 20", bg=T.SIDEBAR,
                                       fg=T.MUTED, font=self.fonts["tiny"], anchor="w")
        self.progress_label.pack(fill="x", pady=(0, 8))
        self.progress_bar = ProgressBar(bottom, width=T.S(170), height=T.S(6),
                                        bg=T.CARD_HI, fg=T.GREEN)
        self.progress_bar.pack(fill="x")
        tk.Label(bottom, text="F5 运行 · Alt+←/→ 切题", bg=T.SIDEBAR, fg="#5d6579",
                 font=self.fonts["tiny"], anchor="w").pack(fill="x", pady=(14, 0))

    # ------------------------------------------------------------ 通用
    def on_nav(self, key):
        if key == "home":
            self.show("home")
        elif key == "stats":
            self.show("stats")
        elif key == "exam":
            self.show("exam")
        elif key == "order":
            self.start("order")
        elif key == "random":
            self.start("random")
        elif key == "wrong":
            self.start("wrong")
        elif key == "fav":
            self.start("fav")

    def show(self, name):
        self.views = {"home": self.home, "practice": self.practice,
                      "stats": self.stats, "exam": self.exam_setup,
                      "result": self.result}
        view = self.views[name]
        view.tkraise()
        if name == "home":
            self.home.refresh()
        elif name == "stats":
            self.stats.refresh()
        elif name == "exam":
            self.exam_setup.refresh()
        active = "practice" if name == "practice" else name
        if name == "result":
            active = "exam"
        for k, item in self.nav.items():
            item.set_active(k == self._active_nav_key(active))

    def _active_nav_key(self, mode):
        return {"order": "order", "random": "random", "wrong": "wrong",
                "fav": "fav", "home": "home", "stats": "stats",
                "exam": "exam"}.get(mode, "order")

    def start_exam(self, paper, minutes, meta=None):
        """开始一次组卷考试。"""
        self.session_mode = "exam"
        self.session_chapter = None
        self.practice.start_exam_session(paper, minutes, meta or {})
        self.show("practice")
        for k, item in self.nav.items():
            item.set_active(k == "exam")

    def finish_exam(self, summary, meta=None):
        """交卷：保存记录并展示成绩报告。"""
        self.store.record_exam(summary, meta or {})
        self.result.load(summary, meta or {})
        self.show("result")
        self.refresh_global()

    def _pool(self, chapter=None):
        """按章节取题；chapter 为 None 表示全部。"""
        if chapter:
            for c in self.chapters:
                if c["id"] == chapter:
                    return list(c["questions"])
            return list(self.questions)
        return list(self.questions)

    def start(self, mode, chapter=None):
        if mode == "order":
            seq = self._pool(chapter)
            title = "顺序刷题"
            for c in self.chapters:
                if c["id"] == chapter:
                    title = c["name"]
                    break
            index = 0
            # 从第一道没通过的题开始，全部通过则从头再来
            for i, q in enumerate(seq):
                if not self.store.is_solved(q["id"]):
                    index = i
                    break
        elif mode == "random":
            import random
            seq = self._pool(chapter)
            random.shuffle(seq)
            title = "随机抽题"
            index = 0
        elif mode == "wrong":
            seq = self.store.wrongs(self.questions)
            title = "错题本"
            index = 0
        else:
            seq = self.store.favorites(self.questions)
            title = "收藏夹"
            index = 0

        self.session_mode = mode
        self.session_chapter = chapter
        self.practice.load(seq, index, title, chapter=chapter)
        self.show("practice")
        for k, item in self.nav.items():
            item.set_active(k == mode)

    def open_question(self, qid):
        seq = list(self.questions)
        ids = [q["id"] for q in seq]
        index = ids.index(qid) if qid in ids else 0
        self.session_mode = "order"
        self.session_chapter = None
        self.practice.load(seq, index, "顺序刷题", chapter=None)
        self.show("practice")
        for k, item in self.nav.items():
            item.set_active(k == "order")

    def refresh_global(self):
        stats = self.store.stats(self.questions)
        self.progress_label.configure(
            text="已通过 {} / {}".format(stats["solved"], stats["total"]))
        self.progress_bar.set(stats["solved"] / float(stats["total"] or 1))
        self.nav["wrong"].set_badge(str(len(self.store.wrongs(self.questions))))
        self.nav["fav"].set_badge(str(len(self.store.favorites(self.questions))))
        if self.home.winfo_exists():
            self.home.refresh()
        if self.stats.winfo_exists():
            self.stats.refresh()

    def toast(self, text):
        self.toast_label.configure(text=text)
        self.toast_label.place(relx=0.5, rely=0.94, anchor="center")
        self.toast_label.lift()
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(1800, self.toast_label.place_forget)


# ---------------------------------------------------------------- 主页
class HomeView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.fonts = app.fonts
        f = app.fonts

        wrap = tk.Frame(self, bg=T.BG)
        wrap.pack(fill="both", expand=True, padx=44, pady=(38, 24))

        tk.Label(wrap, text="Python 程序设计刷题系统", bg=T.BG, fg=T.TEXT,
                 font=f["h1"]).pack(anchor="w")
        self.subtitle = tk.Label(wrap, text="", bg=T.BG, fg=T.MUTED, font=f["body"])
        self.subtitle.pack(anchor="w", pady=(6, 26))

        cards = tk.Frame(wrap, bg=T.BG)
        cards.pack(fill="x")
        self.stat_values = {}
        specs = [
            ("solved", "已通过", T.GREEN),
            ("tried", "已练习", T.ACCENT),
            ("rate", "通过率", T.YELLOW),
            ("wrong", "待复习", T.RED),
        ]
        for i, (key, label, color) in enumerate(specs):
            card = tk.Frame(cards, bg=T.CARD, highlightbackground=T.BORDER,
                            highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            cards.grid_columnconfigure(i, weight=1)
            inner = tk.Frame(card, bg=T.CARD)
            inner.pack(fill="both", expand=True, padx=20, pady=16)
            value = tk.Label(inner, text="0", bg=T.CARD, fg=color, font=(f["h1"][0], 24, "bold"))
            value.pack(anchor="w")
            tk.Label(inner, text=label, bg=T.CARD, fg=T.MUTED,
                     font=f["tiny"]).pack(anchor="w", pady=(2, 0))
            self.stat_values[key] = value

        actions = tk.Frame(wrap, bg=T.BG)
        actions.pack(fill="x", pady=(26, 30))
        RoundButton(actions, "开始顺序刷题", command=lambda: self.app.start("order"),
                    bg=T.ACCENT, fg="#ffffff", font=f["button"], padx=22, pady=11).pack(side="left")
        RoundButton(actions, "随机抽一题", command=lambda: self.app.start("random"),
                    bg=T.CARD_HI, fg=T.TEXT, hover=T.BORDER_HI, font=f["button"],
                    padx=20, pady=11).pack(side="left", padx=10)
        RoundButton(actions, "继续上次", command=self._continue,
                    bg=T.CARD_HI, fg=T.TEXT, hover=T.BORDER_HI, font=f["button"],
                    padx=20, pady=11).pack(side="left")
        RoundButton(actions, "导入题库", command=self.app.import_bank,
                    bg=T.CARD_HI, fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["small"],
                    padx=16, pady=11).pack(side="left", padx=(10, 0))

        cols = tk.Frame(wrap, bg=T.BG)
        cols.pack(fill="both", expand=True)
        cols.grid_columnconfigure(0, weight=1, uniform="col")
        cols.grid_columnconfigure(1, weight=1, uniform="col")
        cols.grid_rowconfigure(0, weight=1)

        left = tk.Frame(cols, bg=T.BG)
        left.grid(row=0, column=0, sticky="nsew")

        guide = tk.Frame(left, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        guide.pack(fill="both", expand=True)
        gi = tk.Frame(guide, bg=T.CARD)
        gi.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(gi, text="怎么刷", bg=T.CARD, fg=T.TEXT, font=f["h3"]).pack(anchor="w")
        lines = [
            "1. 读题 → 在代码区写出程序（读入用 input()，输出用 print()）。",
            "2. 按 F5 或点「运行测试」，程序会用题目自带的测试用例逐条比对输出。",
            "3. 通过后自动记为「已通过」；没通过会留在错题本里，随时回来重做。",
            "4. 想不出来时点「查看答案」，参考答案和易错点解析都在里面。",
        ]
        for ln in lines:
            tk.Label(gi, text=ln, bg=T.CARD, fg=T.TEXT_DIM, font=f["body"],
                     justify="left").pack(anchor="w", pady=3)
        tk.Label(gi, text="快捷键", bg=T.CARD, fg=T.TEXT, font=f["h3"]).pack(anchor="w", pady=(18, 2))
        tk.Label(gi, text="F5 / Ctrl+Enter 运行测试      Alt+←/→ 上下题",
                 bg=T.CARD, fg=T.MUTED, font=f["small"]).pack(anchor="w")
        tk.Label(gi, text="易错提醒", bg=T.CARD, fg=T.TEXT,
                 font=f["h3"]).pack(anchor="w", pady=(22, 2))
        for tip in [
            "· 先判断字段个数再取下标，别让 IndexError 打断循环。",
            "· 判题忽略行尾空格与空行，但字符顺序、大小写必须一致。",
            "· while True 里记得改变退出条件，否则会判定为超时。",
        ]:
            tk.Label(gi, text=tip, bg=T.CARD, fg=T.MUTED, font=f["small"],
                     justify="left").pack(anchor="w", pady=2)

        prog_card = tk.Frame(left, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        prog_card.pack(fill="x", pady=(14, 0))
        pb = tk.Frame(prog_card, bg=T.CARD)
        pb.pack(fill="x", padx=24, pady=18)
        pb_head = tk.Frame(pb, bg=T.CARD)
        pb_head.pack(fill="x")
        tk.Label(pb_head, text="学习进度", bg=T.CARD, fg=T.TEXT,
                 font=f["h3"]).pack(side="left")
        self.prog_text = tk.Label(pb_head, text="", bg=T.CARD, fg=T.MUTED, font=f["small"])
        self.prog_text.pack(side="right")
        self.prog_bar = ProgressBar(pb, width=T.S(360), height=T.S(8),
                                    bg=T.CARD_HI, fg=T.GREEN)
        self.prog_bar.pack(fill="x", pady=(12, 0))
        self.next_hint = tk.Label(pb, text="", bg=T.CARD, fg=T.ACCENT,
                                  font=f["small"], cursor="hand2")
        self.next_hint.pack(anchor="w", pady=(12, 0))
        self.next_hint.bind("<Button-1>", lambda e: self._next_unsolved())

        overview = tk.Frame(cols, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        overview.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        oi = tk.Frame(overview, bg=T.CARD)
        oi.pack(fill="both", expand=True, padx=24, pady=20)
        head = tk.Frame(oi, bg=T.CARD)
        head.pack(fill="x")
        tk.Label(head, text="章节进度", bg=T.CARD, fg=T.TEXT, font=f["h3"]).pack(side="left")
        tk.Label(head, text="点章节即可开刷", bg=T.CARD, fg=T.MUTED,
                 font=f["tiny"]).pack(side="right")
        self.overview_body = tk.Frame(oi, bg=T.CARD)
        self.overview_body.pack(fill="both", expand=True, pady=(14, 0))

    def _continue(self):
        last = self.app.store.data.get("last_qid")
        if last and last in self.app.qmap:
            self.app.open_question(last)
        else:
            self.app.start("order")

    def _next_unsolved(self):
        for q in self.app.questions:
            if not self.app.store.is_solved(q["id"]):
                self.app.open_question(q["id"])
                return
        self.app.start("order")

    def _pending(self):
        for q in self.app.questions:
            if not self.app.store.is_solved(q["id"]):
                return q
        return None

    def _build_overview(self):
        body = self.overview_body
        for w in body.winfo_children():
            w.destroy()
        store = self.app.store
        f = self.fonts

        for c in self.app.chapters:
            qs = c["questions"]
            total = len(qs)
            solved = sum(1 for q in qs if store.is_solved(q["id"]))
            card = tk.Frame(body, bg=T.CARD, cursor="hand2")
            card.pack(fill="x", pady=(0, T.S(14)))
            head = tk.Frame(card, bg=T.CARD)
            head.pack(fill="x")
            name = tk.Label(head, text=c["name"], bg=T.CARD, fg=T.TEXT, font=f["h3"])
            name.pack(side="left")
            count = tk.Label(head, text="{} / {} 题".format(solved, total),
                             bg=T.CARD, fg=T.MUTED, font=f["small"])
            count.pack(side="right")
            bar = ProgressBar(card, width=T.S(200), height=T.S(7), bg=T.CARD_HI, fg=T.GREEN)
            bar.pack(fill="x", pady=(T.S(8), 0))
            bar.set(solved / float(total or 1))

            chap_id = c["id"]
            for w in (card, head, name, count, bar):
                w.bind("<Button-1>", lambda e, x=chap_id: self.app.start("order", x))
                w.bind("<Enter>", lambda e, g=(card, head, name, count): self._paint(g, T.CARD_HI))
                w.bind("<Leave>", lambda e, g=(card, head, name, count): self._paint(g, T.CARD))

    @staticmethod
    def _paint(widgets, color):
        for w in widgets:
            w.configure(bg=color)

    def refresh(self):
        stats = self.app.store.stats(self.app.questions)
        self.subtitle.configure(text="{} 个章节 · {} 道实验题 · 边写边判 · 错题自动收集".format(
            len(self.app.chapters), len(self.app.questions)))
        self.stat_values["solved"].configure(text="{} / {}".format(stats["solved"], stats["total"]))
        self.stat_values["tried"].configure(text=str(stats["tried"]))
        self.stat_values["rate"].configure(text="{}%".format(stats["rate"]))
        self.stat_values["wrong"].configure(
            text=str(len(self.app.store.wrongs(self.app.questions))))
        self._build_overview()

        total = stats["total"] or 1
        self.prog_bar.set(stats["solved"] / float(total))
        self.prog_text.configure(text="已通过 {} / {} 题，还有 {} 题没做".format(
            stats["solved"], stats["total"], max(0, stats["total"] - stats["solved"])))
        pending = self._pending()
        if pending:
            self.next_hint.configure(text="下一步 → {} {}".format(pending["id"], pending["title"]))
        else:
            self.next_hint.configure(text="全部通过！可以随机抽题复习，或看看别人的写法。")


# ---------------------------------------------------------------- 刷题页
class PracticeView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.store = app.store
        self.fonts = app.fonts
        self.seq = []
        self.pos = 0
        self.session_title = "顺序刷题"
        self.chapter_id = None
        self.exam = None
        self.exam_meta = {}
        self._timer_job = None
        self._running = False
        self._queue = queue.Queue()
        self._hint_visible = False
        self._build()
        self._poll()

    # ------------------------------------------------------------ 构建
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        f = self.fonts

        self.empty = tk.Frame(self, bg=T.BG)
        self.empty.grid(row=0, column=0, sticky="nsew")
        box = tk.Frame(self.empty, bg=T.BG)
        box.place(relx=0.5, rely=0.42, anchor="center")
        self.empty_title = tk.Label(box, text="这里还没有题", bg=T.BG, fg=T.TEXT, font=f["h2"])
        self.empty_title.pack()
        self.empty_sub = tk.Label(box, text="先去刷几道题，错题会自动出现在这里。",
                                  bg=T.BG, fg=T.MUTED, font=f["body"])
        self.empty_sub.pack(pady=(8, 16))
        RoundButton(box, "去顺序刷题", command=lambda: self.app.start("order"),
                    bg=T.ACCENT, fg="#ffffff", font=f["button"], padx=18, pady=10).pack()

        self.body = tk.Frame(self, bg=T.BG)
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(3, weight=1)

        # ---- 头部
        head = tk.Frame(self.body, bg=T.BG)
        head.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 10))
        head.grid_columnconfigure(0, weight=1)

        crumb_bar = tk.Frame(head, bg=T.BG)
        crumb_bar.grid(row=0, column=0, sticky="w")
        self.chap_buttons = {}
        specs = [(u"全部", None)] + [(c["short"], c["id"]) for c in self.app.chapters]
        for text, cid in specs:
            btn = RoundButton(crumb_bar, text,
                              command=lambda x=cid: self.app.start("order", x),
                              bg=T.CARD, fg=T.MUTED, hover=T.CARD_HI,
                              font=f["tiny"], padx=11, pady=5)
            btn.pack(side="left", padx=(0, T.S(6)))
            self.chap_buttons[cid] = btn
        self.crumb = tk.Label(crumb_bar, text="", bg=T.BG, fg=T.MUTED,
                              font=f["tiny"], anchor="w")
        self.crumb.pack(side="left", padx=(T.S(10), 0))

        # 搜索框：回车按题号 / 标题 / 考点 / 题干过滤
        search_box = tk.Frame(crumb_bar, bg=T.CARD, highlightbackground=T.BORDER,
                              highlightthickness=1)
        search_box.pack(side="right", padx=(T.S(10), 0))
        tk.Label(search_box, text="⌕", bg=T.CARD, fg=T.MUTED,
                 font=f["small"]).pack(side="left", padx=(T.S(8), 0))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_box, textvariable=self.search_var,
                                     width=16, bg=T.CARD, fg=T.TEXT, relief="flat",
                                     insertbackground=T.TEXT, font=f["tiny"],
                                     highlightthickness=0, bd=0)
        self.search_entry.pack(side="left", padx=(T.S(4), T.S(8)), pady=T.S(4))
        self.search_entry.bind("<Return>", lambda e: self.do_search())
        self.search_entry.bind("<Escape>", lambda e: self.search_var.set(""))
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.configure(bg=T.CARD_HI))
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.configure(bg=T.CARD))

        self.title_label = tk.Label(head, text="", bg=T.BG, fg=T.TEXT, font=f["h2"],
                                    anchor="w", justify="left")
        self.title_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ---- 考试状态条（仅考试模式下显示）
        self.exam_bar = tk.Frame(head, bg=T.CARD_HI, highlightbackground=T.ACCENT,
                                 highlightthickness=1)
        self.exam_clock = tk.Label(self.exam_bar, text="", bg=T.CARD_HI, fg=T.ACCENT,
                                   font=f["small"])
        self.exam_clock.pack(side="left", padx=(14, 10), pady=6)
        self.exam_progress = tk.Label(self.exam_bar, text="", bg=T.CARD_HI, fg=T.TEXT_DIM,
                                      font=f["small"])
        self.exam_progress.pack(side="left")
        self.submit_btn = RoundButton(self.exam_bar, "交卷", command=self.submit_exam,
                                      bg=T.ACCENT, fg="#ffffff", font=f["small"],
                                      padx=16, pady=6)
        self.submit_btn.pack(side="right", padx=10, pady=4)

        badges = tk.Frame(head, bg=T.BG)
        badges.grid(row=1, column=1, sticky="e")
        self.level_pill = Pill(badges, "入门", fg=T.GREEN, bg=T.CARD, font=f["tiny"])
        self.level_pill.pack(side="left", padx=(0, 8))
        self.topic_pill = Pill(badges, "", fg=T.MUTED, bg=T.CARD, font=f["tiny"])
        self.topic_pill.pack(side="left", padx=(0, 8))
        self.fav_btn = RoundButton(badges, "☆ 收藏", command=self.toggle_fav,
                                   bg=T.CARD, fg=T.TEXT_DIM, hover=T.CARD_HI,
                                   font=f["small"], padx=12, pady=7)
        self.fav_btn.pack(side="left")

        # ---- 题目卡片
        card = tk.Frame(self.body, bg=T.CARD, highlightbackground=T.BORDER,
                        highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew", padx=30)
        card.grid_columnconfigure(0, weight=1)
        inner = tk.Frame(card, bg=T.CARD)
        inner.grid(row=0, column=0, sticky="ew", padx=20, pady=14)
        inner.grid_columnconfigure(0, weight=1)

        top = tk.Frame(inner, bg=T.CARD)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        tk.Label(top, text="题目描述", bg=T.CARD, fg=T.MUTED, font=f["tiny"]).grid(row=0, column=0, sticky="w")
        self.hint_btn = RoundButton(top, "显示提示", command=self.toggle_hint,
                                    bg=T.CARD_HI, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                                    font=f["tiny"], padx=12, pady=5)
        self.hint_btn.grid(row=0, column=1, sticky="e")

        self.desc_label = tk.Label(inner, text="", bg=T.CARD, fg=T.TEXT_DIM,
                                   font=f["body"], justify="left", anchor="w")
        self.desc_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        inner.bind("<Configure>", self._on_inner_config)

        self.hint_label = tk.Label(inner, text="", bg=T.CARD, fg=T.YELLOW,
                                   font=f["small"], justify="left", anchor="w")

        # ---- 编辑器工具条
        bar = tk.Frame(self.body, bg=T.BG)
        bar.grid(row=2, column=0, sticky="ew", padx=30, pady=(16, 6))
        bar.grid_columnconfigure(0, weight=1)
        tk.Label(bar, text="代码编辑区", bg=T.BG, fg=T.MUTED, font=f["tiny"]).grid(row=0, column=0, sticky="w")
        self.status_label = tk.Label(bar, text="", bg=T.BG, fg=T.MUTED, font=f["small"])
        self.status_label.grid(row=0, column=1, sticky="e", padx=(0, 12))
        self.reset_btn = RoundButton(bar, "重置", command=self.reset_code, bg=T.CARD_HI,
                                     fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["tiny"],
                                     padx=12, pady=5)
        self.reset_btn.grid(row=0, column=2, sticky="e")

        # ---- 代码编辑器
        self.editor = CodeEditor(self.body, font=f["mono"], font_small=f["tiny"])
        self.editor.grid(row=3, column=0, sticky="nsew", padx=30)

        # ---- 下方标签页
        self.nb = ttk.Notebook(self.body)
        self.nb.grid(row=4, column=0, sticky="ew", padx=30, pady=(12, 0))

        stdin_tab = tk.Frame(self.nb, bg=T.CARD_HI)
        self.nb.add(stdin_tab, text="  标准输入  ")
        stdin_head = tk.Frame(stdin_tab, bg=T.CARD_HI)
        stdin_head.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(stdin_head, text="手动运行用的输入数据（不影响判题）",
                 bg=T.CARD_HI, fg=T.MUTED, font=f["tiny"]).pack(side="left")
        RoundButton(stdin_head, "手动运行", command=self.manual_run, bg=T.CARD,
                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["tiny"],
                    padx=12, pady=5).pack(side="right")
        self.stdin_text = tk.Text(stdin_tab, height=4, bg=T.CARD_HI, fg=T.TEXT_DIM,
                                  insertbackground=T.ACCENT, font=f["mono_s"], relief="flat",
                                  bd=0, highlightthickness=0, padx=12, pady=6, wrap="none")
        self.stdin_text.pack(fill="both", expand=True)

        res_tab = tk.Frame(self.nb, bg=T.CARD_HI)
        self.nb.add(res_tab, text="  判题结果  ")
        self.result = tk.Text(res_tab, height=9, bg=T.CARD_HI, fg=T.TEXT_DIM,
                              font=f["small"], relief="flat", bd=0, highlightthickness=0,
                              padx=14, pady=8, wrap="word", cursor="arrow")
        rsb = ttk.Scrollbar(res_tab, orient="vertical", command=self.result.yview,
                            style="Dark.Vertical.TScrollbar")
        self.result.configure(yscrollcommand=rsb.set)
        self.result.pack(side="left", fill="both", expand=True)
        rsb.pack(side="right", fill="y")
        self.result.configure(state="disabled")
        self.result.tag_configure("ok", foreground=T.GREEN)
        self.result.tag_configure("bad", foreground=T.RED)
        self.result.tag_configure("dim", foreground=T.MUTED)
        self.result.tag_configure("code", foreground="#9cdcfe",
                                  font=(f["mono_s"][0], 9))
        self.result.tag_configure("tip", foreground=T.YELLOW)
        self.result.tag_configure("big", foreground=T.GREEN,
                                  font=(f["h3"][0], 12, "bold"))

        ans_tab = tk.Frame(self.nb, bg=T.CARD_HI)
        self.nb.add(ans_tab, text="  参考答案  ")
        ans_head = tk.Frame(ans_tab, bg=T.CARD_HI)
        ans_head.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(ans_head, text="先自己写，卡住了再看", bg=T.CARD_HI, fg=T.MUTED,
                 font=f["tiny"]).pack(side="left")
        RoundButton(ans_head, "载入到编辑器", command=self.load_answer_code, bg=T.CARD,
                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["tiny"],
                    padx=12, pady=5).pack(side="right")
        self.answer = tk.Text(ans_tab, height=9, bg=T.CARD_HI, fg=T.TEXT_DIM,
                              font=f["mono_s"], relief="flat", bd=0, highlightthickness=0,
                              padx=14, pady=8, wrap="word", cursor="arrow")
        asb = ttk.Scrollbar(ans_tab, orient="vertical", command=self.answer.yview,
                            style="Dark.Vertical.TScrollbar")
        self.answer.configure(yscrollcommand=asb.set)
        self.answer.pack(side="left", fill="both", expand=True)
        asb.pack(side="right", fill="y")
        self.answer.configure(state="disabled")
        self.answer.tag_configure("head", foreground=T.ACCENT,
                                  font=(f["h3"][0], 10, "bold"))
        self.answer.tag_configure("code", foreground="#cfe6ff",
                                  font=(f["mono_s"][0], 9))
        self.answer.tag_configure("text", foreground=T.TEXT_DIM)
        self.answer.tag_configure("dim", foreground=T.MUTED)

        # ---- 底部按钮
        bottom = tk.Frame(self.body, bg=T.BG)
        bottom.grid(row=5, column=0, sticky="ew", padx=30, pady=(12, 18))
        bottom.grid_columnconfigure(2, weight=1)
        self.prev_btn = RoundButton(bottom, "← 上一题", command=self.prev_q, bg=T.CARD_HI,
                                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["small"],
                                    padx=14, pady=8)
        self.prev_btn.grid(row=0, column=0)
        self.next_btn = RoundButton(bottom, "下一题 →", command=self.next_q, bg=T.CARD_HI,
                                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["small"],
                                    padx=14, pady=8)
        self.next_btn.grid(row=0, column=1, padx=(8, 0))

        self.answer_btn = RoundButton(bottom, "查看参考答案", command=self.show_answer,
                                      bg=T.CARD_HI, fg=T.TEXT_DIM, hover=T.BORDER_HI,
                                      font=f["small"], padx=16, pady=8)
        self.answer_btn.grid(row=0, column=3)

        self.run_btn = RoundButton(bottom, "运行测试  (F5)", command=self.run_tests,
                                   bg=T.ACCENT, fg="#ffffff", font=f["button"],
                                   padx=22, pady=9)
        self.run_btn.grid(row=0, column=4, padx=(10, 0))

    def _on_inner_config(self, event):
        width = max(320, event.width - 40)
        self.desc_label.configure(wraplength=width)
        self.hint_label.configure(wraplength=width)

    # ------------------------------------------------------------ 数据加载
    def current(self):
        if not self.seq:
            return None
        self.pos = max(0, min(self.pos, len(self.seq) - 1))
        return self.seq[self.pos]

    def load(self, seq, index=0, title="顺序刷题", chapter=None):
        self._stop_exam(clear=True)
        self.seq = list(seq)
        self.pos = max(0, min(index, len(self.seq) - 1)) if self.seq else 0
        self.session_title = title
        self.chapter_id = chapter
        self._refresh_chapter_pills()
        if not self.seq:
            self._show_empty(title)
            return
        self.empty.grid_remove()
        self.body.grid()
        self._load_question()

    # ------------------------------------------------------------ 考试模式
    def start_exam_session(self, paper, minutes, meta=None):
        self._stop_exam(clear=True)
        self.exam = examlib.start_exam(paper, minutes)
        self.exam_meta = dict(meta or {})
        self.seq = list(paper)
        self.pos = 0
        self.session_title = "模拟考试"
        self.chapter_id = None
        self._refresh_chapter_pills()
        for btn in self.chap_buttons.values():
            btn.set_enabled(False)
        self.empty.grid_remove()
        self.body.grid()
        self.exam_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.exam_clock.configure(fg=T.ACCENT)
        self._load_question()
        self._tick()

    def _stop_exam(self, clear=False):
        if self._timer_job:
            try:
                self.after_cancel(self._timer_job)
            except Exception:
                pass
            self._timer_job = None
        if getattr(self, "exam_bar", None) is not None and self.exam_bar.winfo_ismapped():
            self.exam_bar.grid_remove()
        if clear:
            self.exam = None
            self.exam_meta = {}
            if hasattr(self, "chap_buttons"):
                for btn in self.chap_buttons.values():
                    btn.set_enabled(True)

    def _tick(self):
        self._timer_job = None
        if not self.exam:
            return
        remaining = examlib.remaining_seconds(self.exam)
        passed = sum(1 for r in self.exam["results"].values() if r["status"] == "pass")
        total = len(self.exam["paper"])
        if remaining < 0:
            self.exam_clock.configure(text="不限时", fg=T.ACCENT)
        else:
            self.exam_clock.configure(text="剩余 " + examlib.format_clock(remaining))
            if remaining <= 60:
                self.exam_clock.configure(fg=T.RED)
            elif remaining <= 300:
                self.exam_clock.configure(fg=T.YELLOW)
            else:
                self.exam_clock.configure(fg=T.ACCENT)
        self.exam_progress.configure(text="已通过 {} / {}".format(passed, total))
        if remaining == 0:
            self.app.toast("时间到，自动交卷")
            self.submit_exam(auto=True)
            return
        self._timer_job = self.after(1000, self._tick)

    def submit_exam(self, auto=False):
        if not self.exam or self.exam.get("submitted"):
            return
        self.exam["submitted"] = True
        summary = examlib.summarize(self.exam)
        meta = dict(self.exam_meta)
        meta["balance"] = examlib.balance_report(self.exam["paper"])
        meta["auto"] = bool(auto)
        self._stop_exam(clear=True)
        self.app.finish_exam(summary, meta)

    def _refresh_chapter_pills(self):
        for cid, btn in self.chap_buttons.items():
            if cid == getattr(self, "chapter_id", None):
                btn.set_colors(T.ACCENT, "#ffffff", hover=T.ACCENT_HI)
            else:
                btn.set_colors(T.CARD, T.MUTED, hover=T.CARD_HI)

    def _show_empty(self, title):
        self.body.grid_remove()
        self.empty.grid()
        if title == "错题本":
            self.empty_title.configure(text="暂时没有错题")
            self.empty_sub.configure(text="做错或未通过的题会自动收进这里。先去刷几道吧。")
        elif title == "收藏夹":
            self.empty_title.configure(text="收藏夹是空的")
            self.empty_sub.configure(text="在题目右上角点「☆ 收藏」，把想复习的题攒起来。")
        else:
            self.empty_title.configure(text="这里还没有题")
            self.empty_sub.configure(text="先去顺序刷题吧。")

    def _save_current_code(self):
        q = self.current()
        if q:
            self.store.save_code(q["id"], self.editor.get_code())

    def _load_question(self):
        q = self.current()
        if not q:
            return
        self._hint_visible = False
        self.hint_label.grid_remove()
        self.hint_btn.configure_text("显示提示")
        self.desc_label.configure(text=q["desc"])
        self.hint_label.configure(text="提示 · " + q["hint"])
        self.title_label.configure(text="{} {}".format(q["id"], q["title"]))
        self.crumb.configure(text="{} · 第 {} / {} 题".format(
            self.session_title, self.pos + 1, len(self.seq)))
        self.level_pill.update_style(
            text=T.LEVEL_NAMES.get(q["level"], "入门"),
            fg=T.LEVEL_COLORS.get(q["level"], T.GREEN), bg=T.CARD)
        self.topic_pill.update_style(text=q["topic"])
        self._refresh_fav()

        saved = self.store.get_code(q["id"])
        self.editor.set_code(saved if saved.strip() else TEMPLATE)
        self.store.mark_seen(q["id"])
        self.store.data["last_qid"] = q["id"]
        self.store.save()

        self.stdin_text.delete("1.0", "end")
        if q["cases"]:
            self.stdin_text.insert("1.0", q["cases"][0]["stdin"])

        self.status_label.configure(text="")
        self._clear_results("还没运行。写好代码后按 F5 或点「运行测试」。")
        self._build_answer(q)
        self.nb.select(0)
        self.prev_btn.set_enabled(self.pos > 0)
        self.next_btn.set_enabled(self.pos < len(self.seq) - 1)
        # 考试模式下不允许看参考答案
        in_exam = self.exam is not None
        self.answer_btn.set_enabled(not in_exam)
        if in_exam:
            self.answer_btn.configure_text("考试中不可看答案")
        else:
            self.answer_btn.configure_text("查看参考答案")
        self.editor.focus_editor()

    def _refresh_fav(self):
        q = self.current()
        if not q:
            return
        if self.store.is_favorite(q["id"]):
            self.fav_btn.configure_text("★ 已收藏")
        else:
            self.fav_btn.configure_text("☆ 收藏")

    def do_search(self):
        """按关键词在当前题库里找题，找到就进入一个新的「搜索结果」序列。"""
        text = (self.search_var.get() or "").strip()
        if not text:
            self.app.toast("输入题号、关键词或考点再回车")
            return
        low = text.lower()
        hits = []
        for q in self.app.questions:
            blob = "{} {} {} {}".format(q["id"], q["title"], q["topic"], q["desc"]).lower()
            if low in blob:
                hits.append(q)
        if not hits:
            self.app.toast("没有找到包含「{}」的题目".format(text))
            return
        self.app.session_mode = "search"
        self.load(hits, 0, "搜索：{}".format(text))
        self.app.toast("找到 {} 道题".format(len(hits)))

    def toggle_fav(self):
        q = self.current()
        if not q:
            return
        now = self.store.toggle_favorite(q["id"])
        self._refresh_fav()
        self.app.toast("已加入收藏" if now else "已取消收藏")
        self.app.refresh_global()

    def toggle_hint(self):
        if self._hint_visible:
            self.hint_label.grid_remove()
            self.hint_btn.configure_text("显示提示")
        else:
            self.hint_label.grid(row=2, column=0, sticky="ew", pady=(10, 0))
            self.hint_btn.configure_text("收起提示")
        self._hint_visible = not self._hint_visible

    def reset_code(self):
        if messagebox.askyesno("重置代码", "要用初始模板替换当前代码吗？"):
            self.editor.set_code(TEMPLATE)

    def prev_q(self):
        if self.pos > 0:
            self._save_current_code()
            self.pos -= 1
            self._load_question()

    def next_q(self):
        if self.pos < len(self.seq) - 1:
            self._save_current_code()
            self.pos += 1
            self._load_question()

    # ------------------------------------------------------------ 运行判题
    def run_tests(self):
        if self._running or not self.seq:
            return
        q = self.current()
        code = self.editor.get_code()
        if not code.strip():
            self.app.toast("先写点代码再运行吧")
            return
        self._save_current_code()
        self._running = True
        self.run_btn.set_enabled(False)
        self.run_btn.configure_text("判题中…")
        self.status_label.configure(text="正在运行…", fg=T.MUTED)
        self._clear_results("正在运行测试用例…")

        def job():
            results = []
            all_ok = True
            for case in q["cases"]:
                item = run_case(code, case)
                results.append(item)
                if item["status"] != "pass":
                    all_ok = False
                    break
            self._queue.put(("judge", q, code, results, all_ok))

        threading.Thread(target=job, daemon=True).start()

    def manual_run(self):
        if self._running or not self.seq:
            return
        code = self.editor.get_code()
        if not code.strip():
            self.app.toast("先写点代码再运行吧")
            return
        stdin_data = self.stdin_text.get("1.0", "end-1c")
        self._running = True
        self.run_btn.set_enabled(False)
        self.status_label.configure(text="正在运行…", fg=T.MUTED)

        def job():
            run = run_code(code, stdin_data)
            self._queue.put(("manual", None, code, run, None))

        threading.Thread(target=job, daemon=True).start()

    def _poll(self):
        try:
            while True:
                msg = self._queue.get_nowait()
                if msg[0] == "judge":
                    self._finish_judge(*msg[1:])
                else:
                    self._finish_manual(*msg[1:])
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish_judge(self, q, code, results, all_ok):
        self._running = False
        self.run_btn.set_enabled(True)
        self.run_btn.configure_text("运行测试  (F5)")
        self.store.record_attempt(q["id"], all_ok, code)
        if self.exam is not None:
            examlib.record_result(self.exam, q["id"], all_ok)
            self._tick()
        self._render_results(q, results, all_ok)
        self.nb.select(1)
        if all_ok:
            self.status_label.configure(text="✓ 全部用例通过", fg=T.GREEN)
        else:
            self.status_label.configure(text="还有用例没通过", fg=T.RED)
        self.app.refresh_global()

    def _finish_manual(self, _q, code, run, _extra):
        self._running = False
        self.run_btn.set_enabled(True)
        self.run_btn.configure_text("运行测试  (F5)")
        self.status_label.configure(text="手动运行完成", fg=T.MUTED)
        self.nb.select(1)
        t = self._reset_result()
        t.insert("end", "手动运行（不判分）\n\n", "dim")
        if run["timeout"]:
            t.insert("end", "运行超时（可能写了死循环）\n", "bad")
        elif run["error"]:
            t.insert("end", "运行出错：\n", "bad")
            t.insert("end", _indent(run["error"]) + "\n", "code")
        else:
            t.insert("end", "程序输出：\n", "dim")
            t.insert("end", _indent(run["output"]) + "\n", "code")
        t.configure(state="disabled")

    def _reset_result(self):
        t = self.result
        t.configure(state="normal")
        t.delete("1.0", "end")
        return t

    def _clear_results(self, text):
        t = self._reset_result()
        t.insert("end", text + "\n", "dim")
        t.configure(state="disabled")

    def _render_results(self, q, results, all_ok):
        t = self._reset_result()
        total = len(q["cases"])
        if all_ok:
            t.insert("end", "✓ 全部 {} 个用例通过\n".format(total), "big")
            t.insert("end", "\n可以点「下一题」继续，或看看参考答案里的其他写法。\n", "dim")
            t.configure(state="disabled")
            return

        t.insert("end", "共 {} 个测试用例，逐条比对输出：\n\n".format(total), "dim")
        for i, r in enumerate(results, 1):
            if r["status"] == "pass":
                t.insert("end", "✓ 用例 {}  通过\n".format(i), "ok")
                t.insert("end", "    输入：{}\n\n".format(_short(r["stdin"])), "dim")
                continue

            label = {"fail": "输出不同", "error": "运行出错", "timeout": "运行超时"}.get(
                r["status"], "未通过")
            t.insert("end", "✗ 用例 {}  {}\n".format(i, label), "bad")
            t.insert("end", "    输入：{}\n".format(_short(r["stdin"])), "dim")

            if r["status"] == "fail":
                t.insert("end", "    期望输出：\n", "dim")
                t.insert("end", _indent(r["expect"]) + "\n", "code")
                t.insert("end", "    实际输出：\n", "dim")
                t.insert("end", _indent(r["actual"]) + "\n", "code")
                diff = r.get("first_diff")
                if diff:
                    t.insert("end", "    第 {} 行对不上：期望「{}」，实际「{}」\n".format(
                        diff["line"],
                        diff["expect"] if diff["expect"] is not None else "（缺失）",
                        diff["actual"] if diff["actual"] is not None else "（缺失）"), "tip")
                t.insert("end", "    提示：判题会忽略行尾空格与空行，但字符、顺序、大小写要一致。\n", "tip")
            elif r["status"] == "error":
                t.insert("end", "    报错信息：\n", "dim")
                t.insert("end", _indent(r["error"]) + "\n", "code")
                if "EOFError" in (r["error"] or ""):
                    t.insert("end", "    提示：input() 要读的行数比用例给的多，检查循环的退出条件。\n", "tip")
                elif "NameError" in (r["error"] or ""):
                    t.insert("end", "    提示：变量名拼错或没定义，注意大小写。\n", "tip")
                elif "IndentationError" in (r["error"] or "") or "SyntaxError" in (r["error"] or ""):
                    t.insert("end", "    提示：缩进或语法有误，Python 用 4 个空格缩进。\n", "tip")
                elif "TypeError" in (r["error"] or ""):
                    t.insert("end", "    提示：类型不匹配，检查是否把字符串和数字混用。\n", "tip")
            else:
                t.insert("end", "    提示：很可能写了死循环（while 条件没有改变），或 input 一直等数据。\n", "tip")

            if len(results) < total:
                t.insert("end", "\n    后面的 {} 个用例没有执行（前面的用例未通过）。\n".format(
                    total - len(results)), "dim")
            t.insert("end", "\n")
        t.configure(state="disabled")

    # ------------------------------------------------------------ 参考答案
    def _build_answer(self, q):
        a = self.answer
        a.configure(state="normal")
        a.delete("1.0", "end")
        if q.get("source"):
            a.insert("end", "题目来源：" + q["source"] + "\n\n", "dim")
        a.insert("end", "参考答案\n", "head")
        a.insert("end", q["ref"].rstrip() + "\n\n", "code")
        a.insert("end", "解析与易错点\n", "head")
        a.insert("end", q["explain"].rstrip() + "\n", "text")
        a.configure(state="disabled")

    def show_answer(self):
        if not self.seq:
            return
        if self.exam is not None:
            self.app.toast("模拟考试中不能查看参考答案")
            return
        self.nb.select(2)

    def load_answer_code(self):
        q = self.current()
        if not q:
            return
        if self.exam is not None:
            self.app.toast("模拟考试中不能载入参考答案")
            return
        if messagebox.askyesno("载入参考答案", "会用参考答案覆盖编辑区里的代码，继续吗？"):
            self.editor.set_code(q["ref"])
            self.nb.select(0)


# ---------------------------------------------------------------- 统计页
class StatsView(tk.Frame):
    # 表头与数据行共用同一组列宽，保证逐列对齐
    COLUMNS = [(u"章节", 8), (u"题号", 6), (u"题目", 28), (u"考点", 32), (u"难度", 6),
               (u"尝试", 5), (u"状态", 8), (u"最近练习", 17)]

    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.fonts = app.fonts
        self._build()

    def _build(self):
        f = self.fonts
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=40, pady=(34, 8))
        tk.Label(head, text="学习统计", bg=T.BG, fg=T.TEXT, font=self.fonts["h2"]).pack(side="left")
        RoundButton(head, "重置全部进度", command=self.reset_all, bg=T.CARD_HI,
                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=self.fonts["small"],
                    padx=14, pady=8).pack(side="right")
        RoundButton(head, "导出学习报告", command=self.export_report, bg=T.CARD_HI,
                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=self.fonts["small"],
                    padx=14, pady=8).pack(side="right")

        self.summary = tk.Frame(self, bg=T.BG)
        self.summary.pack(fill="x", padx=40, pady=(6, 18))
        self.tiles = {}
        for i, (key, label, color) in enumerate([
            ("solved", "已通过", T.GREEN),
            ("tried", "已练习", T.ACCENT),
            ("rate", "通过率", T.YELLOW),
            ("attempts", "总提交次数", T.PURPLE),
        ]):
            card = tk.Frame(self.summary, bg=T.CARD, highlightbackground=T.BORDER,
                            highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            self.summary.grid_columnconfigure(i, weight=1)
            inner = tk.Frame(card, bg=T.CARD)
            inner.pack(fill="both", expand=True, padx=18, pady=14)
            v = tk.Label(inner, text="0", bg=T.CARD, fg=color, font=(f["h2"][0], 20, "bold"))
            v.pack(anchor="w")
            tk.Label(inner, text=label, bg=T.CARD, fg=T.MUTED, font=f["tiny"]).pack(anchor="w")
            self.tiles[key] = v

        charts = tk.Frame(self, bg=T.BG)
        charts.pack(fill="x", padx=40, pady=(0, 12))
        charts.grid_columnconfigure(0, weight=1, uniform="chart")
        charts.grid_columnconfigure(1, weight=1, uniform="chart")
        self.status_chart = self._chart_card(charts, 0, "学习状态分布")
        self.chapter_chart = self._chart_card(charts, 1, "各章已通过")

        trend_card = tk.Frame(self, bg=T.CARD, highlightbackground=T.BORDER,
                              highlightthickness=1)
        trend_card.pack(fill="x", padx=40, pady=(0, 12))
        trend_inner = tk.Frame(trend_card, bg=T.CARD)
        trend_inner.pack(fill="x", padx=18, pady=10)
        tip = tk.Frame(trend_inner, bg=T.CARD)
        tip.pack(fill="x")
        tk.Label(tip, text="历次组卷得分", bg=T.CARD, fg=T.TEXT,
                 font=self.fonts["h3"]).pack(side="left")
        self.trend_hint = tk.Label(tip, text="", bg=T.CARD, fg=T.MUTED,
                                   font=self.fonts["tiny"])
        self.trend_hint.pack(side="right")
        self.trend = LineChart(trend_inner, width=1100, height=132, bg=T.CARD,
                               font=self.fonts["h3"], small_font=self.fonts["tiny"])
        self.trend.pack(fill="x", pady=(6, 0))

        cols = tk.Frame(self, bg=T.BG)
        cols.pack(fill="x", padx=40)
        for text, width in self.COLUMNS:
            tk.Label(cols, text=text, bg=T.BG, fg=T.MUTED, font=f["small"],
                     width=width, anchor="w").pack(side="left", padx=(0, 6))
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x", padx=40, pady=(6, 4))

        self.scroll = ScrollFrame(self, bg=T.BG)
        self.scroll.pack(fill="both", expand=True, padx=40, pady=(0, 16))
        self.rows_body = self.scroll.body

    def _chart_card(self, parent, col, title):
        card = tk.Frame(parent, bg=T.CARD, highlightbackground=T.BORDER,
                        highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 12, 0))
        inner = tk.Frame(card, bg=T.CARD)
        inner.pack(fill="both", expand=True, padx=18, pady=12)
        top = tk.Frame(inner, bg=T.CARD)
        top.pack(fill="x")
        tk.Label(top, text=title, bg=T.CARD, fg=T.TEXT,
                 font=self.fonts["h3"]).pack(side="left")
        hint = tk.Label(top, text="", bg=T.CARD, fg=T.MUTED, font=self.fonts["tiny"])
        hint.pack(side="right")
        body = tk.Frame(inner, bg=T.CARD)
        body.pack(fill="x", pady=(8, 0))
        pie = PieChart(body, size=T.S(128), bg=T.CARD, font=self.fonts["h3"],
                       small_font=self.fonts["tiny"])
        pie.pack(side="left")
        legend = tk.Frame(body, bg=T.CARD)
        legend.pack(side="left", fill="x", expand=True, padx=(T.S(16), 0))
        return {"pie": pie, "legend": legend, "hint": hint}

    def _set_chart(self, chart, data):
        for w in chart["legend"].winfo_children():
            w.destroy()
        chart["pie"].set_data(data)
        total = sum(v for _l, v, _c in data)
        chart["hint"].configure(text="共 {} 题".format(total) if total else "还没有数据")
        for label, value, color in data:
            if value <= 0:
                continue
            row = tk.Frame(chart["legend"], bg=T.CARD)
            row.pack(fill="x", pady=T.S(3))
            sw = tk.Frame(row, bg=color, width=T.S(10), height=T.S(10))
            sw.pack(side="left")
            sw.pack_propagate(False)
            tk.Label(row, text=label, bg=T.CARD, fg=T.TEXT_DIM, font=self.fonts["small"],
                     anchor="w").pack(side="left", padx=(T.S(8), 0))
            pct = int(round(value * 100.0 / total)) if total else 0
            tk.Label(row, text="{} · {}%".format(value, pct), bg=T.CARD, fg=T.MUTED,
                     font=self.fonts["tiny"]).pack(side="right")

    def _refresh_charts(self):
        store = self.app.store
        qs = self.app.questions
        solved = wrong = seen = rest = 0
        for q in qs:
            rec = store.record(q["id"])
            if rec.get("last") == "pass":
                solved += 1
            elif rec.get("attempts", 0) > 0:
                wrong += 1
            elif rec.get("seen", 0) > 0:
                seen += 1
            else:
                rest += 1
        self._set_chart(self.status_chart, [
            ("已通过", solved, T.GREEN),
            ("需复习", wrong, T.RED),
            ("已看题", seen, T.YELLOW),
            ("未开始", rest, T.MUTED),
        ])

        palette = [T.ACCENT, T.GREEN, T.YELLOW, T.PURPLE, T.CYAN, T.RED]
        chapter_data = []
        for i, c in enumerate(self.app.chapters):
            n = sum(1 for q in c["questions"] if store.is_solved(q["id"]))
            chapter_data.append((c["short"], n, palette[i % len(palette)]))
        self._set_chart(self.chapter_chart, chapter_data)

        history = list(reversed(store.exam_history(10)))
        points = [(str(i + 1), int(h.get("score", 0))) for i, h in enumerate(history)]
        self.trend.set_data(points)
        if history:
            scores = [int(h.get("score", 0)) for h in history]
            avg = int(round(sum(scores) / float(len(scores))))
            self.trend_hint.configure(text="最近 {} 次 · 平均 {} 分 · 最高 {} 分".format(
                len(scores), avg, max(scores)))
        else:
            self.trend_hint.configure(text="还没有组卷记录")

    def export_report(self):
        """把学习情况导出成 CSV（UTF-8 BOM，Excel 双击可直接打开）。"""
        import csv
        import time
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            title="导出学习报告", defaultextension=".csv",
            initialfile="学习报告-{}.csv".format(time.strftime("%Y%m%d")),
            filetypes=[("CSV 文件（Excel 可打开）", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return

        store = self.app.store
        qs = self.app.questions
        stats = store.stats(qs)

        rows = []
        rows.append(["学习报告", "Python 程序设计刷题系统"])
        rows.append(["导出时间", time.strftime("%Y-%m-%d %H:%M")])
        rows.append(["题目总数", stats["total"]])
        rows.append(["已通过", stats["solved"]])
        rows.append(["已练习", stats["tried"]])
        rows.append(["通过率", "{}%".format(stats["rate"])])
        rows.append(["总提交次数", stats["attempts"]])
        rows.append([])

        rows.append(["各章进度"])
        rows.append(["章节", "题数", "已通过", "通过率"])
        for c in self.app.chapters:
            total = len(c["questions"])
            done = sum(1 for q in c["questions"] if store.is_solved(q["id"]))
            rate = int(round(done * 100.0 / total)) if total else 0
            rows.append([c["name"], total, done, "{}%".format(rate)])
        rows.append([])

        history = store.exam_history(20)
        if history:
            rows.append(["组卷记录"])
            rows.append(["时间", "得分", "通过题数", "总题数", "用时(秒)"])
            for h in history:
                rows.append([h.get("finished_at", ""), h.get("score", 0),
                             h.get("passed", 0), h.get("total", 0),
                             h.get("seconds", 0)])
            rows.append([])

        rows.append(["逐题明细"])
        rows.append(["章节", "题号", "题目", "考点", "难度", "用例数",
                     "尝试次数", "是否通过", "最近练习"])
        for q in qs:
            rec = store.record(q["id"])
            passed = "是" if rec.get("last") == "pass" else "否"
            rows.append([
                q["chapter"], q["id"], q["title"], q["topic"],
                T.LEVEL_NAMES.get(q["level"], "入门"), len(q["cases"]),
                rec.get("attempts", 0), passed, rec.get("updated", "") or "-",
            ])

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows(rows)
        except Exception as e:
            messagebox.showerror("导出失败", "写入文件时出错：\n{}".format(e))
            return
        self.app.toast("已导出到 {}".format(os.path.basename(path)))

    def refresh(self):
        store = self.app.store
        qs = self.app.questions
        stats = store.stats(qs)
        self.tiles["solved"].configure(text="{} / {}".format(stats["solved"], stats["total"]))
        self.tiles["tried"].configure(text=str(stats["tried"]))
        self.tiles["rate"].configure(text="{}%".format(stats["rate"]))
        self.tiles["attempts"].configure(text=str(stats["attempts"]))
        self._refresh_charts()

        for child in self.rows_body.winfo_children():
            child.destroy()

        f = self.fonts
        for i, q in enumerate(qs):
            rec = store.record(q["id"])
            last = rec.get("last", "")
            if last == "pass":
                status, color = "已通过", T.GREEN
            elif rec.get("attempts", 0) > 0:
                status, color = "需复习", T.RED
            elif rec.get("seen", 0) > 0:
                status, color = "已看题", T.YELLOW
            else:
                status, color = "未开始", T.MUTED

            row = tk.Frame(self.rows_body, bg=T.BG, cursor="hand2")
            row.pack(fill="x", pady=1)
            labels = []
            widths = [w for _t, w in self.COLUMNS]
            short = q.get("chapter", "").split(" ")[0]
            labels.append(self._cell(row, short, widths[0], T.ACCENT, f["small"]))
            labels.append(self._cell(row, q["id"], widths[1], T.MUTED, f["small"]))
            labels.append(self._cell(row, q["title"], widths[2], T.TEXT, f["small"]))
            labels.append(self._cell(row, q["topic"], widths[3], T.MUTED, f["small"]))
            labels.append(self._cell(row, T.LEVEL_NAMES.get(q["level"], ""), widths[4],
                                     T.LEVEL_COLORS.get(q["level"], T.MUTED), f["small"]))
            labels.append(self._cell(row, str(rec.get("attempts", 0)), widths[5], T.MUTED, f["small"]))
            labels.append(self._cell(row, status, widths[6], color, f["small"]))
            updated = rec.get("updated", "")
            labels.append(self._cell(row, updated[5:16] if updated else "—",
                                     widths[7], T.MUTED, f["small"]))
            qid = q["id"]
            for w in [row] + labels:
                w.bind("<Button-1>", lambda e, x=qid: self.app.open_question(x))
                w.bind("<Enter>", lambda e, r=row, ls=labels: self._hover(r, ls, True))
                w.bind("<Leave>", lambda e, r=row, ls=labels: self._hover(r, ls, False))

    def _cell(self, parent, text, width, fg, font):
        lab = tk.Label(parent, text=text, bg=T.BG, fg=fg, font=font, width=width,
                       anchor="w", justify="left")
        lab.pack(side="left", padx=(0, 6))
        return lab

    def _hover(self, row, labels, on):
        color = T.CARD if on else T.BG
        row.configure(bg=color)
        for l in labels:
            l.configure(bg=color)

    def reset_all(self):
        if messagebox.askyesno("重置进度", "确定清空所有练习记录、收藏和代码吗？此操作不可撤销。"):
            self.app.store.reset()
            self.app.refresh_global()
            self.app.toast("进度已清空")
