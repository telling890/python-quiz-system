# -*- coding: utf-8 -*-
"""自绘控件：圆角按钮、导航项、进度条、代码编辑器、滚动容器。"""

import re

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import theme as T


# ---------------------------------------------------------------- 基础绘制
def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """在 Canvas 上画圆角矩形（用平滑多边形近似）。"""
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kw)


class RoundButton(tk.Canvas):
    """圆角按钮：Canvas 自绘，支持悬停与禁用。"""

    def __init__(self, master, text, command=None, bg=T.ACCENT, fg="#ffffff",
                 hover=None, font=None, padx=18, pady=8, radius=9,
                 outline="", width=None, height=None):
        self._bg = master.cget("bg") if "bg" in master.keys() else T.BG
        self._font = font or (T.__dict__.get("FONT", ("Microsoft YaHei UI", 11)))
        self._f = tkfont.Font(font=self._font)
        self._tw = self._f.measure(text)
        self._th = self._f.metrics("linespace")
        padx = T.S(padx)
        pady = T.S(pady)
        w = width or self._tw + padx * 2
        h = height or self._th + pady * 2
        super().__init__(master, width=w, height=h, bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = text
        self._command = command
        self._base = bg
        self._hover = hover or _lighten(bg, 0.12)
        self._fg = fg
        self._radius = radius
        self._outline = outline
        self._enabled = True
        self._cw, self._ch = w, h
        self._draw(self._base)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, fill):
        self.delete("all")
        rounded_rect(self, 1, 1, self._cw - 1, self._ch - 1, self._radius,
                     fill=fill, outline=self._outline)
        self.create_text(self._cw / 2.0, self._ch / 2.0, text=self._text,
                         fill=self._fg if self._enabled else T.MUTED,
                         font=self._font)

    def configure_text(self, text):
        self._text = text
        f = tkfont.Font(font=self._font)
        self._cw = max(self._cw, f.measure(text) + 36)
        self.configure(width=self._cw)
        self._draw(self._base if self._enabled else self._base)

    def set_enabled(self, flag):
        self._enabled = bool(flag)
        self.configure(cursor="hand2" if flag else "arrow")
        self._draw(self._base if flag else T.CARD_HI)

    def set_colors(self, bg, fg=None, hover=None):
        """切换配色（用于章节切换按钮的选中态）。"""
        self._base = bg
        self._hover = hover or _lighten(bg, 0.12)
        if fg is not None:
            self._fg = fg
        self._draw(self._base if self._enabled else T.CARD_HI)

    def _on_enter(self, _e):
        if self._enabled:
            self._draw(self._hover)

    def _on_leave(self, _e):
        self._draw(self._base if self._enabled else T.CARD_HI)

    def _on_press(self, _e):
        if self._enabled:
            self._draw(_darken(self._base, 0.12))

    def _on_release(self, _e):
        if not self._enabled:
            return
        self._draw(self._hover)
        if self._command:
            self._command()


def _hex_to_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)


def _lighten(c, amount):
    r, g, b = _hex_to_rgb(c)
    return _rgb_to_hex((r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount))


def _darken(c, amount):
    r, g, b = _hex_to_rgb(c)
    return _rgb_to_hex((r * (1 - amount), g * (1 - amount), b * (1 - amount)))


class Pill(tk.Label):
    """小徽章：难度、考点、状态。"""

    def __init__(self, master, text, fg=T.TEXT, bg=T.CARD_HI, font=None, padx=9, pady=2):
        super().__init__(master, text=text, fg=fg, bg=bg, font=font,
                         padx=T.S(padx), pady=T.S(pady))

    def update_style(self, text=None, fg=None, bg=None):
        if text is not None:
            self.configure(text=text)
        if fg is not None:
            self.configure(fg=fg)
        if bg is not None:
            self.configure(bg=bg)


class NavItem(tk.Frame):
    """左侧导航项，带高亮竖条。"""

    def __init__(self, master, icon, label, command, font=None, font_bold=None):
        super().__init__(master, bg=T.SIDEBAR, cursor="hand2")
        self._command = command
        self._active = False
        self._bar = tk.Frame(self, bg=T.SIDEBAR, width=3)
        self._bar.pack(side="left", fill="y")
        body = tk.Frame(self, bg=T.SIDEBAR)
        body.pack(side="left", fill="both", expand=True)
        self._icon = tk.Label(body, text=icon, bg=T.SIDEBAR, fg=T.MUTED,
                              font=font, width=2)
        self._icon.pack(side="left", padx=(10, 2), pady=9)
        self._label = tk.Label(body, text=label, bg=T.SIDEBAR, fg=T.TEXT_DIM,
                               font=font, anchor="w")
        self._label.pack(side="left", fill="x", expand=True, pady=9)
        self._badge = tk.Label(body, text="", bg=T.SIDEBAR, fg=T.MUTED, font=font)
        self._badge.pack(side="right", padx=(0, 12))
        self._font = font
        self._font_bold = font_bold or font
        for w in (self, self._icon, self._label, self._bar, body, self._badge):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)

    def _click(self, _e):
        self._command()

    def _enter(self, _e):
        if not self._active:
            for w in (self, self._label, self._icon, self._bar, self._badge):
                w.configure(bg=T.SIDEBAR_HI)

    def _leave(self, _e):
        if not self._active:
            for w in (self, self._label, self._icon, self._bar, self._badge):
                w.configure(bg=T.SIDEBAR)

    def set_badge(self, text):
        self._badge.configure(text=text)

    def set_active(self, flag):
        self._active = bool(flag)
        bg = T.SIDEBAR_HI if flag else T.SIDEBAR
        fg = T.TEXT if flag else T.TEXT_DIM
        for w in (self, self._label, self._icon, self._bar):
            w.configure(bg=bg)
        self._badge.configure(bg=bg)
        self._bar.configure(bg=T.ACCENT if flag else bg)
        self._label.configure(fg=fg, font=self._font_bold if flag else self._font)
        self._icon.configure(fg=T.ACCENT if flag else T.MUTED)


class ProgressBar(tk.Canvas):
    def __init__(self, master, width=180, height=6, bg=T.CARD_HI, fg=T.ACCENT):
        super().__init__(master, width=width, height=height, bg=master.cget("bg"),
                         highlightthickness=0, bd=0)
        self._cw, self._ch = width, height
        self._track, self._fill = bg, fg
        self._value = 0.0
        self.bind("<Configure>", self._on_config)
        self._draw()

    def _on_config(self, e):
        self._cw, self._ch = e.width, e.height
        self._draw()

    def _draw(self):
        self.delete("all")
        r = self._ch / 2.0
        rounded_rect(self, 0, 0, self._cw, self._ch, r, fill=self._track, outline="")
        fw = max(0, int(self._cw * self._value))
        if fw > 1:
            rounded_rect(self, 0, 0, fw, self._ch, min(r, fw / 2.0), fill=self._fill, outline="")

    def set(self, value):
        self._value = max(0.0, min(1.0, float(value)))
        self._draw()


class ScrollFrame(tk.Frame):
    """可滚动容器：往 .body 里放内容。"""

    def __init__(self, master, bg=T.BG):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical",
                                 style="Dark.Vertical.TScrollbar",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _on_body(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def _bind_wheel(self, on):
        if on:
            self.canvas.bind_all("<MouseWheel>", self._wheel)
        else:
            self.canvas.unbind_all("<MouseWheel>")

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")


class PieChart(tk.Canvas):
    """饼图：用 create_arc 画扇形，中间显示总数，右侧配图例。

    set_data([(标签, 数值, 颜色), ...])，数值为 0 的项自动跳过；
    全部为 0 时显示「暂无数据」，避免画出空饼。
    """

    def __init__(self, master, size=150, bg=T.CARD, font=None, small_font=None):
        super().__init__(master, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0)
        self._size = size
        self._bg = bg
        self._font = font
        self._small = small_font or font
        self._data = []

    def set_data(self, data):
        self._data = [(label, value, color) for label, value, color in data if value > 0]
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        pad = 6
        box = (pad, pad, s - pad, s - pad)
        total = sum(v for _l, v, _c in self._data)

        if total <= 0:
            self.create_oval(box, outline=T.BORDER_HI, width=2, dash=(4, 4))
            self.create_text(s / 2, s / 2, text="暂无数据", fill=T.MUTED,
                             font=self._small)
            return

        start = 90.0
        for label, value, color in self._data:
            extent = -360.0 * value / total
            self.create_arc(box, start=start, extent=extent, fill=color,
                            outline=self._bg, width=2)
            start += extent

        # 中线圆环 + 总数，做成环形图更清爽
        inner = s * 0.30
        self.create_oval(s / 2 - inner, s / 2 - inner, s / 2 + inner, s / 2 + inner,
                         fill=self._bg, outline=self._bg)
        self.create_text(s / 2, s / 2 - 8, text=str(total), fill=T.TEXT,
                         font=self._font)
        self.create_text(s / 2, s / 2 + 12, text="总计", fill=T.MUTED,
                         font=self._small)


# ---------------------------------------------------------------- 代码编辑器
_TOKEN = re.compile(
    r"(?P<comment>#[^\n]*)"
    r"|(?P<string>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')"
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<keyword>\b(?:and|as|assert|break|class|continue|def|del|elif|else|except|"
    r"finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|"
    r"return|try|while|with|yield)\b)"
    r"|(?P<builtin>\b(?:abs|all|any|bin|bool|chr|dict|divmod|enumerate|filter|float|"
    r"format|frozenset|hex|input|int|isinstance|len|list|map|max|min|oct|open|ord|"
    r"pow|print|range|reversed|round|set|sorted|str|sum|tuple|type|zip)\b)"
)

_TAG_STYLE = {
    "comment": {"foreground": "#6b7280"},
    "string": {"foreground": "#98c379"},
    "number": {"foreground": "#d19a66"},
    "keyword": {"foreground": "#c678dd"},
    "builtin": {"foreground": "#61afef"},
}


class CodeEditor(tk.Frame):
    """带行号、语法高亮、自动缩进的代码编辑区。"""

    def __init__(self, master, font=None, font_small=None):
        super().__init__(master, bg=T.CARD, highlightthickness=1,
                         highlightbackground=T.BORDER, highlightcolor=T.BORDER_HI)
        self._font = font
        self._font_small = font_small
        self.gutter = tk.Canvas(self, width=T.S(46), bg=T.GUTTER, highlightthickness=0, bd=0)
        self.gutter.pack(side="left", fill="y")
        holder = tk.Frame(self, bg=T.CARD)
        holder.pack(side="left", fill="both", expand=True)
        self.sb = ttk.Scrollbar(holder, orient="vertical", style="Dark.Vertical.TScrollbar")
        self.sb.pack(side="right", fill="y")

        self.text = tk.Text(
            holder, bg=T.CARD, fg=T.TEXT, insertbackground=T.ACCENT,
            insertwidth=2, selectbackground="#2d4a80", selectforeground="#ffffff",
            font=font, relief="flat", bd=0, highlightthickness=0, undo=True,
            wrap="none", padx=T.S(14), pady=T.S(10), spacing1=1, spacing3=1, tabs=("4c",),
        )
        self.text.pack(side="left", fill="both", expand=True)
        self.text.configure(yscrollcommand=self._on_yscroll)
        self.sb.configure(command=self.text.yview)

        for tag, style in _TAG_STYLE.items():
            self.text.tag_configure(tag, **style)
        self.text.tag_configure("current", background="#191e2a")
        self.text.tag_raise("current")
        self.text.tag_raise("sel")

        self.text.bind("<KeyRelease>", self._on_change)
        self.text.bind("<ButtonRelease-1>", self._on_change)
        self.text.bind("<Tab>", self._on_tab)
        self.text.bind("<Return>", self._on_return)
        self.text.bind("<BackSpace>", self._on_backspace)
        self.text.bind("<<Paste>>", lambda e: self.after(10, self._on_change))
        self.text.bind("<Configure>", lambda e: self._redraw_gutter())

        self._highlight()
        self._redraw_gutter()

    # ---------------------------------------------------------- 对外接口
    def get_code(self):
        return self.text.get("1.0", "end-1c")

    def set_code(self, code):
        self.text.delete("1.0", "end")
        if code:
            self.text.insert("1.0", code)
        self.text.edit_reset()
        self.text.mark_set("insert", "1.0")
        self._highlight()
        self._redraw_gutter()

    def focus_editor(self):
        self.text.focus_set()

    # ---------------------------------------------------------- 内部逻辑
    def _on_yscroll(self, first, last):
        self.sb.set(first, last)
        self._redraw_gutter()

    def _on_change(self, _e=None):
        self._highlight()
        self._redraw_gutter()

    def _on_tab(self, _e):
        self.text.insert("insert", "    ")
        self._on_change()
        return "break"

    def _on_return(self, _e):
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r"[ \t]*", line).group(0)
        stripped = line.strip()
        extra = "    " if stripped.endswith(":") else ""
        self.text.insert("insert", "\n" + indent + extra)
        self._on_change()
        self.text.see("insert")
        return "break"

    def _on_backspace(self, _e):
        # 在 4 空格缩进处按退格，一次删掉整级缩进
        line = self.text.get("insert linestart", "insert")
        if line.strip() == "" and len(line) >= 4 and line.endswith("    "):
            self.text.delete("insert-4c", "insert")
            self._on_change()
            return "break"
        return None

    def _highlight(self):
        self.text.tag_remove("comment", "1.0", "end")
        self.text.tag_remove("string", "1.0", "end")
        self.text.tag_remove("number", "1.0", "end")
        self.text.tag_remove("keyword", "1.0", "end")
        self.text.tag_remove("builtin", "1.0", "end")
        content = self.text.get("1.0", "end-1c")
        if not content:
            return
        for lineno, line in enumerate(content.split("\n"), 1):
            for m in _TOKEN.finditer(line):
                tag = m.lastgroup
                if not tag:
                    continue
                start = "%d.%d" % (lineno, m.start())
                end = "%d.%d" % (lineno, m.end())
                self.text.tag_add(tag, start, end)

    def _redraw_gutter(self):
        self.gutter.delete("all")
        try:
            index = self.text.index("@0,0")
        except tk.TclError:
            return
        lasth = int(self.gutter.winfo_height()) or 400
        while True:
            info = self.text.dlineinfo(index)
            if info is None:
                break
            y = info[1]
            if y > lasth:
                break
            num = str(index).split(".")[0]
            self.gutter.create_text(T.S(34), y + 1, anchor="ne", text=num,
                                    fill=T.MUTED, font=self._font_small)
            index = self.text.index("%s+1line" % index)
        # 当前行底色
        self.text.tag_remove("current", "1.0", "end")
        try:
            cur = self.text.index("insert")
            self.text.tag_add("current", "%s linestart" % cur, "%s lineend+1c" % cur)
            self.text.tag_lower("current")
        except tk.TclError:
            pass
