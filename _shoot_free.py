# -*- coding: utf-8 -*-
"""自由编程页的截图 + 冒烟测试：运行、单步执行、片段保存/载入/删除、草稿自动保存。"""

import os
import sys
import time
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

os.environ["PYQUIZ_STATE_DIR"] = tempfile.mkdtemp(prefix="pyquiz-free-")

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
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(
        os.path.join(OUT, name))
    print("saved", name)


def wait_run(app, view, timeout=30):
    t0 = time.time()
    while view._running and time.time() - t0 < timeout:
        app.update()
        time.sleep(0.05)
    app.update()


def wait_trace(app, pane, timeout=30):
    t0 = time.time()
    while pane._running and time.time() - t0 < timeout:
        app.update()
        time.sleep(0.05)
    app.update()


DEMO = '''# 自由编程：素数与因数拆解都能自己玩
def prime_factors(n):
    factors, d = [], 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors

for n in (97, 360, 1024):
    print(n, "->", prime_factors(n))
'''


def main():
    _enable_dpi_awareness()
    import ui as uimod
    from ui import App

    # 冒烟测试不能弹模态框：确认框一律当「是」
    uimod.messagebox.askyesno = lambda *a, **k: True

    app = App()
    app.attributes("-topmost", True)
    app.update()

    app.show("free")
    app.update()
    view = app.free

    # 1. 首次进入装载模板草稿
    assert "自由编程" in view.editor.get_code(), "首次进入没有装载草稿"
    assert view.editor.get_code().strip(), "草稿为空"

    # 2. 运行模板
    view.run()
    wait_run(app, view)
    out = view.result.get("1.0", "end-1c")
    assert "的平方是" in out, out
    print("run ok:", out.splitlines()[2] if len(out.splitlines()) > 2 else out)

    # 3. 自己的代码 + 标准输入
    view.editor.set_code(DEMO)
    view.run()
    wait_run(app, view)
    out = view.result.get("1.0", "end-1c")
    assert "97 -> [97]" in out and "360 -> [2, 2, 2, 3, 3, 5]" in out, out
    print("demo ok")

    # 4. 单步执行：函数内部也要能看到变量
    view.trace()
    wait_trace(app, view.trace_pane)
    steps = view.trace_pane.steps
    assert steps, "单步执行没有记录到步骤"
    pane = view.trace_pane
    pane._trace_index = len(steps) // 2
    pane.render_step()
    app.update()
    shot(app, "16_free.png")

    # 5. 保存片段 → 列表出现 → 载入 → 删除
    view.store.save_snippet("质因数拆解", DEMO)
    view.refresh_snippets()
    app.update()
    names = [it["name"] for it in view.store.snippets()]
    assert "质因数拆解" in names, names
    view.editor.set_code("print('临时替换')\n")
    view.load_snippet([it for it in view.store.snippets() if it["name"] == "质因数拆解"][0])
    assert "prime_factors" in view.editor.get_code(), "载入片段失败"
    assert view.store.delete_snippet("质因数拆解") is True
    view.refresh_snippets()
    assert not view.store.snippets(), view.store.snippets()

    # 6. 草稿自动保存：改代码后立刻保存，再读回来
    view.editor.set_code("# 草稿落盘测试\nprint(1 + 1)\n")
    view.stdin_text.delete("1.0", "end")
    view.stdin_text.insert("1.0", "42\n")
    view._save_now()
    free = view.store.free_state()
    assert "# 草稿落盘测试" in free["code"], free["code"]
    assert free["stdin"].strip() == "42", free["stdin"]

    # 7. 报错与超时都要有明确提示
    view.editor.set_code("print(1 / 0)\n")
    view.run()
    wait_run(app, view)
    assert "运行出错" in view.result.get("1.0", "end-1c")

    # 8. 超时提示
    view.editor.set_code("while True:\n    pass\n")
    view.run()
    wait_run(app, view, timeout=30)
    assert "运行超时" in view.result.get("1.0", "end-1c"), view.result.get("1.0", "end-1c")
    print("error/timeout ok")

    # 9. F5 / F6 在自由编程页要路由到本页
    app.current_view = "free"
    view.editor.set_code("print('f5 路由')\n")
    app._run_active()
    wait_run(app, view)
    assert "f5 路由" in view.result.get("1.0", "end-1c")

    app.destroy()
    print("DONE")


if __name__ == "__main__":
    main()
