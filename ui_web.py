# -*- coding: utf-8 -*-
"""网页版入口页：一键启动本地 Web 服务，用浏览器/手机连上来刷同一份题库。

和桌面版是同一个进程、同一个 state.json：
浏览器里判过的题、存过的片段，桌面端立刻就能看到，反之亦然。
"""

import os
import webbrowser

import tkinter as tk
from tkinter import ttk

import theme as T
import webserver
from widgets import RoundButton

PORTS = (8765, 8766, 8767, 8768)


class WebView(tk.Frame):
    """启动 / 停止网页版服务，并显示访问地址。"""

    def __init__(self, master, app):
        super().__init__(master, bg=T.BG)
        self.app = app
        self.fonts = app.fonts
        self.server = None
        self.url = ""
        self._build()

    # ------------------------------------------------------------ 构建
    def _build(self):
        f = self.fonts
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=40, pady=(30, 6))
        tk.Label(head, text="网页版", bg=T.BG, fg=T.TEXT, font=f["h2"]).pack(side="left")
        tk.Label(head, text="  浏览器 / 手机打开就能刷题、自由编程，进度和桌面版共用一份",
                 bg=T.BG, fg=T.MUTED, font=f["small"]).pack(side="left", pady=(6, 0))

        card = tk.Frame(self, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        card.pack(fill="x", padx=40, pady=(14, 0))
        inner = tk.Frame(card, bg=T.CARD)
        inner.pack(fill="x", padx=22, pady=18)

        row = tk.Frame(inner, bg=T.CARD)
        row.pack(fill="x")
        self.state_label = tk.Label(row, text="未启动", bg=T.CARD, fg=T.MUTED,
                                    font=f["h3"])
        self.state_label.pack(side="left")
        self.lan_var = tk.BooleanVar(value=False)
        self.lan_check = tk.Checkbutton(row, text="允许局域网访问（手机 / 机房其他电脑）",
                                        variable=self.lan_var, command=self._on_lan,
                                        bg=T.CARD, fg=T.TEXT_DIM, font=f["small"],
                                        activebackground=T.CARD, activeforeground=T.TEXT,
                                        selectcolor=T.CARD_HI, bd=0, highlightthickness=0)
        self.lan_check.pack(side="right")
        self.stop_btn = RoundButton(row, "停止服务", command=self.stop, bg=T.CARD_HI,
                                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["small"],
                                    padx=14, pady=7)
        self.stop_btn.pack(side="right", padx=(0, 10))
        self.start_btn = RoundButton(row, "启动网页版", command=self.start, bg=T.ACCENT,
                                     fg="#ffffff", font=f["button"], padx=20, pady=9)
        self.start_btn.pack(side="right", padx=(0, 10))

        self.url_var = tk.StringVar(value="")
        url_row = tk.Frame(inner, bg=T.CARD)
        url_row.pack(fill="x", pady=(14, 0))
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var, state="readonly",
                                  bg=T.CARD_HI, fg=T.ACCENT_HI, relief="flat",
                                  font=(f["mono_s"][0], 11), readonlybackground=T.CARD_HI,
                                  highlightthickness=1, highlightbackground=T.BORDER)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self.copy_btn = RoundButton(url_row, "复制地址", command=self.copy_url, bg=T.CARD_HI,
                                    fg=T.TEXT_DIM, hover=T.BORDER_HI, font=f["small"],
                                    padx=14, pady=7)
        self.copy_btn.pack(side="left")
        self.open_btn = RoundButton(url_row, "在浏览器打开", command=self.open_browser,
                                    bg=T.CARD_HI, fg=T.TEXT, hover=T.BORDER_HI,
                                    font=f["small"], padx=14, pady=7)
        self.open_btn.pack(side="left", padx=(8, 0))

        self.tip = tk.Label(inner, text="启动后默认只监听 127.0.0.1，只有本机能访问。",
                            bg=T.CARD, fg=T.MUTED, font=f["tiny"], anchor="w",
                            justify="left")
        self.tip.pack(fill="x", pady=(12, 0))

        # ---- 说明
        info = tk.Frame(self, bg=T.BG)
        info.pack(fill="both", expand=True, padx=40, pady=(18, 20))
        for title, body, color in [
            ("一、怎么用",
             "1. 点「启动网页版」，地址栏里会出现 http://127.0.0.1:8765/\n"
             "2. 点「在浏览器打开」，或者自己把地址粘到浏览器里\n"
             "3. 想用手机刷：勾上「允许局域网访问」，手机连同一个 Wi-Fi，"
             "用卡片里那串带 ?k= 的地址打开", T.TEXT_DIM),
            ("二、和桌面版的关系",
             "同一个程序、同一份 state.json：网页里判过的题、保存的片段、"
             "自由编程的草稿，桌面端立刻能看到，反过来也一样。\n"
             "网页关掉即可退出，桌面端不受影响。", T.TEXT_DIM),
            ("三、安全说明",
             "网页版会执行你写的代码，所以默认只对本机开放。\n"
             "勾选局域网后地址会带上一个随机口令，没口令的请求一律拒绝——"
             "但请不要把带口令的地址发到公共群里。", T.YELLOW),
        ]:
            box = tk.Frame(info, bg=T.BG)
            box.pack(fill="x", pady=(0, 10))
            tk.Label(box, text=title, bg=T.BG, fg=T.ACCENT, font=f["small"],
                     anchor="w").pack(fill="x")
            tk.Label(box, text=body, bg=T.BG, fg=color, font=f["small"], anchor="w",
                     justify="left").pack(fill="x", pady=(2, 0))

    # ------------------------------------------------------------ 服务控制
    def start(self):
        if self.server is not None:
            self.app.toast("网页版已经在运行了")
            return
        lan = bool(self.lan_var.get())
        last_error = None
        for port in PORTS:
            try:
                self.server = webserver.start(self.app.store, port=port, lan=lan)
                break
            except OSError as exc:
                last_error = exc
                self.server = None
        if self.server is None:
            self.state_label.configure(text="启动失败", fg=T.RED)
            self.tip.configure(text="端口 {} 都被占用了：{}".format(
                "、".join(str(p) for p in PORTS), last_error), fg=T.RED)
            return

        self.url = self.server.url
        self.url_var.set(self.url)
        self.state_label.configure(text="运行中", fg=T.GREEN)
        self.start_btn.set_enabled(False)
        self.lan_check.configure(state="disabled")
        self.url_entry.configure(state="normal")
        self.url_entry.selection_range(0, "end")
        if lan:
            self.tip.configure(
                text="局域网模式：手机连同一个 Wi-Fi，打开上面这串地址（带 ?k= 口令，别外传）。",
                fg=T.YELLOW)
        else:
            self.tip.configure(text="只监听本机（127.0.0.1），其他电脑访问不到。",
                               fg=T.MUTED)
        self.app.toast("网页版已启动：" + self.url)

    def stop(self):
        if self.server is None:
            self.app.toast("网页版还没启动")
            return
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass
        self.server = None
        self.url = ""
        self.url_var.set("")
        self.state_label.configure(text="已停止", fg=T.MUTED)
        self.start_btn.set_enabled(True)
        self.lan_check.configure(state="normal")
        self.tip.configure(text="已停止服务。随时可以再启动。", fg=T.MUTED)
        self.app.toast("网页版已停止")

    def _on_lan(self):
        if self.server is not None:
            self.app.toast("切换访问范围需要先停止服务")
            self.lan_var.set(not self.lan_var.get())

    def copy_url(self):
        if not self.url:
            self.app.toast("先启动网页版")
            return
        self.clipboard_clear()
        self.clipboard_append(self.url)
        self.app.toast("地址已复制")

    def open_browser(self):
        if not self.url:
            self.app.toast("先启动网页版")
            return
        try:
            webbrowser.open(self.url)
        except Exception:
            self.app.toast("打开浏览器失败，可以手动粘贴地址")

    # ------------------------------------------------------------ 生命周期
    def refresh(self):
        """切回本页时同步状态（服务可能还在后台跑）。"""
        if self.server is not None:
            self.state_label.configure(text="运行中", fg=T.GREEN)
            self.url_var.set(self.url)
