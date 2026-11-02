# -*- coding: utf-8 -*-
"""执行过程演示截图：抓 shots/13_trace.png 与 shots/14_trace_limit.png，
同时兼作单步执行功能的界面冒烟测试（换题清空、按钮、时间轴、死循环提示）。
"""

import os
import sys
import time
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# 截图用干净的临时进度目录，别碰真实的 %LOCALAPPDATA%\PyQuizState
os.environ["PYQUIZ_STATE_DIR"] = tempfile.mkdtemp(prefix="pyquiz-shot-")

from PIL import ImageGrab

from main import _enable_dpi_awareness

OUT = os.path.join(HERE, "shots")
if not os.path.isdir(OUT):
    os.makedirs(OUT)


def shot(app, name):
    app.update_idletasks()
    app.update()
    time.sleep(0.4)
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    path = os.path.join(OUT, name)
    img.save(path)
    print("saved", path, img.size)


def wait_trace(app, timeout=30):
    t0 = time.time()
    while app.practice._running and time.time() - t0 < timeout:
        app.update()
        time.sleep(0.05)
    app.update()


def pick_demo(questions, tracer):
    """挑一道「有循环、步数适中、中途会打印」的题，演示效果最好。"""
    for q in questions:
        stdin = q["cases"][0].get("stdin", "") if q["cases"] else ""
        r = tracer.trace_code(q["ref"], stdin)
        steps = r["steps"]
        if r["error"] or r["truncated"] or r["timeout"]:
            continue
        if not (25 <= len(steps) <= 70):
            continue
        mid = steps[len(steps) // 2]
        if mid.get("out"):
            return q
    return None


def main():
    _enable_dpi_awareness()
    from ui import App
    import tracer

    app = App()
    app.attributes("-topmost", True)
    app.update()

    # 选一道适合演示的题，把参考答案放进编辑器，让上下两个面板讲同一个故事
    q = pick_demo(app.questions, tracer)
    assert q is not None, "没有找到适合演示的题"
    idx = app.questions.index(q)
    app.start("order")
    app.update()
    app.practice.load(app.questions, idx, "顺序刷题")
    app.update()
    app.practice.editor.set_code(q["ref"])
    app.update()

    app.practice.trace_current()
    wait_trace(app)
    steps = app.practice._trace["result"]["steps"]
    assert steps, "没有记录到执行过程"
    app.practice._trace_index = len(steps) // 2
    app.practice._render_trace_step()
    app.update()
    print("demo question:", q["id"], q["title"], "steps:", len(steps))
    shot(app, "13_trace.png")

    # 冒烟：上一步 / 下一步 / 自动播放开关 / 拖时间轴
    app.practice.trace_step(-1)
    app.practice.trace_step(1)
    app.practice.toggle_trace_play()
    assert app.practice._play_job is not None, "自动播放没有启动"
    app.practice.toggle_trace_play()
    assert app.practice._play_job is None, "自动播放没有停下"
    app.practice.tr_scale.set_range(len(steps) - 1)
    app.practice.tr_scale._on_pointer(type("E", (), {"x": 10 ** 6})())
    app.update()
    assert app.practice._trace_index == len(steps) - 1, app.practice._trace_index

    # 换题后轨迹应被清空
    app.practice.next_q()
    app.update()
    assert app.practice._trace is None, "换题后执行过程没有清空"
    assert app.practice.tr_src.get("1.0", "end-1c").strip() == "", "换题后代码视图没清空"

    # 死循环：给出提示、不卡界面、不拖垮判题
    app.practice.editor.set_code("while True:\n    pass\n")
    app.practice.trace_current()
    wait_trace(app)
    print("loop note:", app.practice.status_label.cget("text"))
    assert "步就停了" in app.practice.status_label.cget("text"), \
        app.practice.status_label.cget("text")
    shot(app, "14_trace_limit.png")

    app.destroy()
    print("DONE")


if __name__ == "__main__":
    main()
