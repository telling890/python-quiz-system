# -*- coding: utf-8 -*-
"""组卷相关界面截图：组卷页、考试中、交卷报告。"""

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
    img.save(os.path.join(OUT, name))
    print("saved", name, img.size)


def main():
    _enable_dpi_awareness()
    from ui import App
    import exam as examlib

    app = App()
    app.attributes("-topmost", True)
    app.update()

    paper = examlib.generate_paper(app.questions, 8, seed=2026)
    app.start_exam(paper, 20, meta={"chapters": ["全部"], "levels": [1, 2, 3], "limit": 20})
    app.update()
    # 模拟作答：通过 5 题、未通过 1 题、2 题未作答；把开始时间往前挪 8 分 12 秒
    app.practice.exam["started"] -= 492
    app.practice.exam["deadline"] -= 492
    for q in paper[:5]:
        app.practice.exam["results"][q["id"]] = {"status": "pass", "attempts": 1, "seconds": 40}
    app.practice.exam["results"][paper[5]["id"]] = {"status": "fail", "attempts": 2, "seconds": 55}
    app.practice._tick()
    app.practice._load_question()
    app.update()
    shot(app, "10_exam_running.png")

    app.practice.submit_exam()
    app.update()
    shot(app, "11_exam_result.png")

    app.show("exam")
    app.update()
    shot(app, "09_exam_setup.png")

    app.destroy()
    print("DONE")


if __name__ == "__main__":
    main()
