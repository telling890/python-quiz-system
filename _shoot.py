# -*- coding: utf-8 -*-
"""展示截图：在干净进度下模拟一次完整刷题，抓图到 shots/。"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

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


def wait_run(app, timeout=30):
    t0 = time.time()
    while app.practice._running and time.time() - t0 < timeout:
        app.update()
        time.sleep(0.05)
    app.update()


BUGGY_Q01 = '''n = int(input())
if n % 2 == 0 or n % 3 == 0:
    print("Yes")
else:
    print("No")
'''


def main():
    _enable_dpi_awareness()
    from ui import App

    app = App()
    app.attributes("-topmost", True)
    app.update()
    print("scale =", app.scale, "size =", app.winfo_width(), "x", app.winfo_height())

    app.show("home")
    shot(app, "01_home.png")

    # 第一题：先交一个有小 bug 的版本
    app.start("order")
    app.update()
    app.practice.editor.set_code(BUGGY_Q01)
    app.practice.run_tests()
    wait_run(app)
    shot(app, "02_practice_fail.png")

    # 换成参考答案，全部用例通过
    q = app.practice.current()
    app.practice.editor.set_code(q["ref"])
    app.practice.run_tests()
    wait_run(app)
    shot(app, "03_practice_pass.png")

    # 提示展开
    app.practice.toggle_hint()
    shot(app, "04_hint.png")

    # 下一题：答案页
    app.practice.next_q()
    app.update()
    app.practice.show_answer()
    shot(app, "05_answer.png")

    # 再通过一题，让统计有内容
    q = app.practice.current()
    app.practice.editor.set_code(q["ref"])
    app.practice.run_tests()
    wait_run(app)
    app.practice.next_q()
    app.update()
    shot(app, "06_next_question.png")

    # 造一批分布数据，让统计页的饼图有内容
    for c in app.chapters:
        qs = c["questions"]
        n = len(qs)
        for q in qs[:max(1, n // 4)]:
            rec = app.store.record(q["id"])
            rec["last"] = "pass"
            rec["passes"] = rec.get("passes", 0) + 1
            rec["attempts"] = max(1, rec.get("attempts", 0))
            rec["updated"] = "2026-10-21 14:0{}".format(q["no"] % 10)
        for q in qs[n // 4:n // 4 + 2]:
            rec = app.store.record(q["id"])
            rec["last"] = "fail"
            rec["fails"] = rec.get("fails", 0) + 1
            rec["attempts"] = max(1, rec.get("attempts", 0))
            rec["updated"] = "2026-10-21 14:1{}".format(q["no"] % 10)
        for q in qs[n // 4 + 2:n // 4 + 4]:
            app.store.record(q["id"])["seen"] = 1
    app.store.save()
    app.refresh_global()

    app.show("stats")
    shot(app, "07_stats.png")

    # 错题本（制造一道错题）
    app.practice.load(app.questions, 4, "顺序刷题")
    app.practice.editor.set_code("print('oops')\n")
    app.practice.run_tests()
    wait_run(app)
    app.start("wrong")
    app.update()
    shot(app, "08_wrong_book.png")

    app.destroy()
    print("DONE")


if __name__ == "__main__":
    main()
