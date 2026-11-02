# -*- coding: utf-8 -*-
"""数据位置卡片：截图 + 冒烟（导出进度 / 导入进度 / 打开文件夹按钮存在）。"""

import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

os.environ["PYQUIZ_STATE_DIR"] = tempfile.mkdtemp(prefix="pyquiz-data-")
WORK = tempfile.mkdtemp(prefix="pyquiz-backup-")

from PIL import ImageGrab

from main import _enable_dpi_awareness

OUT = os.path.join(HERE, "shots")


def shot(app, name):
    app.update_idletasks()
    app.update()
    time.sleep(0.4)
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(
        os.path.join(OUT, name))
    print("saved", name)


def main():
    _enable_dpi_awareness()
    import ui
    from ui import App

    app = App()
    app.attributes("-topmost", True)
    app.update()

    # 造一点进度，让统计页有内容
    for qid in ("3-01", "3-02", "4-01"):
        app.store.record_attempt(qid, True, "print(1)")
    app.refresh_global()
    app.show("stats")
    app.update()

    label = app.stats.data_label.cget("text")
    print("data label:", label)
    assert app.store.path in label, label
    shot(app, "19_data.png")

    # 导出进度：把弹窗换成固定路径
    target = os.path.join(WORK, "backup.json")
    ui.filedialog.asksaveasfilename = lambda **kw: target
    app.stats.export_progress()
    app.update()
    assert os.path.isfile(target), "导出没生成文件"

    # 改脏数据 → 导入恢复
    app.store.record_attempt("3-03", True, "print(2)")
    assert app.store.is_solved("3-03")
    ui.filedialog.askopenfilename = lambda **kw: target
    ui.messagebox.askyesno = lambda *a, **k: True
    app.stats.import_progress()
    app.update()
    assert not app.store.is_solved("3-03"), "导入后没有覆盖成备份内容"
    assert app.store.is_solved("3-01"), "导入后进度丢了"
    print("export/import ok")

    app.destroy()
    print("DONE")


if __name__ == "__main__":
    main()
