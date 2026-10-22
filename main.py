# -*- coding: utf-8 -*-
"""程序入口：Python 字符串刷题系统。

直接运行：  python main.py
打包 exe：  python build.py
"""

import os
import sys
import traceback


def _enable_dpi_awareness():
    """让高分屏下的文字不发虚。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _write_crash_log(text):
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "PyQuizState")
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "error.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n" + "-" * 70 + "\n")
    except OSError:
        pass


def main():
    _enable_dpi_awareness()
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    from ui import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        detail = traceback.format_exc()
        _write_crash_log(detail)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "程序启动失败",
                "启动时出现异常，详细信息已写入：\n"
                "%LOCALAPPDATA%\\PyQuizState\\error.log\n\n" + detail[-1500:],
            )
            root.destroy()
        except Exception:
            pass
        sys.exit(1)
