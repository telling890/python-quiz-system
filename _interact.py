# -*- coding: utf-8 -*-
"""交互冒烟测试：不启动主循环，直接调用界面逻辑，检查各功能路径不报错。"""

import os
import sys
import time
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from main import _enable_dpi_awareness
_enable_dpi_awareness()

import tkinter.messagebox as mb
mb.askyesno = lambda *a, **k: True

from ui import App
from store import Store

TEST_STATE = os.path.join(HERE, "tmp_run", "state_test.json")


def pump(app, n=3):
    for _ in range(n):
        app.update_idletasks()
        app.update()


def wait_run(app, timeout=30):
    t0 = time.time()
    while app.practice._running and time.time() - t0 < timeout:
        app.update()
        time.sleep(0.05)
    pump(app)


def main():
    if os.path.exists(TEST_STATE):
        os.remove(TEST_STATE)
    app = App()
    app.store = Store(TEST_STATE)
    app.practice.store = app.store
    app.home.app = app
    pump(app)

    checks = []

    # 1. 空错题本
    app.start("wrong")
    pump(app)
    assert not app.practice.seq, "空错题本应没有题目"
    checks.append("空错题本 -> 空状态页")

    # 2. 顺序刷题 + 判题失败
    app.start("order")
    pump(app)
    q = app.practice.current()
    app.practice.editor.set_code("print('wrong answer')\n")
    app.practice.run_tests()
    wait_run(app)
    rec = app.store.record(q["id"])
    assert rec["attempts"] == 1 and rec["last"] == "fail", rec
    checks.append("判题失败 -> 记录 attempts=1 last=fail")

    # 3. 错题本应出现 1 题
    app.start("wrong")
    pump(app)
    assert len(app.practice.seq) == 1, app.practice.seq
    checks.append("错题本 -> 收集到 1 题")

    # 4. 参考答案通过
    q = app.practice.current()
    app.practice.editor.set_code(q["ref"])
    app.practice.run_tests()
    wait_run(app)
    assert app.store.record(q["id"])["last"] == "pass"
    checks.append("参考答案 -> 通过并从错题本移除")

    # 5. 收藏 + 收藏夹
    app.practice.toggle_fav()
    pump(app)
    assert app.store.is_favorite(q["id"])
    app.start("fav")
    pump(app)
    assert len(app.practice.seq) == 1
    checks.append("收藏 -> 收藏夹 1 题")

    # 6. 随机抽题
    app.start("random")
    pump(app)
    assert len(app.practice.seq) == len(app.questions)
    checks.append("随机抽题 -> 20 题")

    # 7. 手动运行
    app.practice.editor.set_code("x = input()\nprint('hi', x)\n")
    app.practice.stdin_text.delete("1.0", "end")
    app.practice.stdin_text.insert("1.0", "world\n")
    app.practice.manual_run()
    wait_run(app)
    out = app.practice.result.get("1.0", "end")
    assert "hi world" in out, out
    checks.append("手动运行 -> 输出正确")

    # 8. 提示 / 答案 / 载入答案
    app.practice.toggle_hint()
    assert app.practice._hint_visible
    app.practice.toggle_hint()
    app.practice.show_answer()
    app.practice.load_answer_code()
    pump(app)
    checks.append("提示/答案/载入答案 -> 正常")

    # 9. 边界：第一题按上一题、最后一题按下一题
    app.practice.load(app.practice.seq, 0, "边界")
    app.practice.prev_q()
    pump(app)
    app.practice.load(app.practice.seq, len(app.practice.seq) - 1, "边界")
    app.practice.next_q()
    pump(app)
    checks.append("首尾切题 -> 不越界")

    # 10. 统计页 + 重置
    app.show("stats")
    pump(app)
    app.stats.refresh()
    pump(app)
    assert app.stats.tiles["solved"].cget("text").startswith("1")
    checks.append("统计页 -> 数字正确")

    app.stats.reset_all()
    pump(app)
    assert app.store.stats(app.questions)["attempts"] == 0
    checks.append("重置进度 -> 清空")

    # 11. 组卷考试：组卷 -> 作答 -> 交卷
    import exam as examlib
    app.show("exam")
    pump(app)
    assert "可用" in app.exam_setup.avail_label.cget("text")
    paper = examlib.generate_paper(app.questions, 5)
    app.start_exam(paper, 5, meta={"chapters": [], "levels": [1, 2, 3], "limit": 5})
    pump(app)
    assert app.practice.exam is not None, "应当进入考试模式"
    assert not app.practice.answer_btn._enabled, "考试中不能看答案"
    for q in paper[:3]:
        app.practice.exam["results"][q["id"]] = {"status": "pass", "attempts": 1, "seconds": 0}
    app.practice.submit_exam()
    pump(app)
    assert app.result.tiles["score"].cget("text") == "60 分", app.result.tiles["score"].cget("text")
    assert len(app.store.data.get("exams", [])) >= 1
    checks.append("组卷考试 -> 5 题、交卷 60 分、记录已保存")

    # 12. 搜索
    app.start("order")
    pump(app)
    app.practice.search_var.set("回文")
    app.practice.do_search()
    pump(app)
    assert app.practice.seq, "搜索没有结果"
    assert all("回文" in (q["title"] + q["desc"] + q["topic"] + q["id"]) for q in app.practice.seq)
    checks.append("搜索「回文」-> 命中 {} 题".format(len(app.practice.seq)))

    # 13. 导出学习报告
    import tempfile
    from tkinter import filedialog
    out = os.path.join(tempfile.gettempdir(), "dsh_report_check.csv")
    if os.path.exists(out):
        os.remove(out)
    filedialog.asksaveasfilename = lambda **kw: out
    app.show("stats")
    pump(app)
    app.stats.export_report()
    pump(app)
    assert os.path.exists(out), "没有生成 CSV"
    with open(out, encoding="utf-8-sig") as f:
        text = f.read()
    assert "学习报告" in text and "逐题明细" in text and "组卷记录" in text
    os.remove(out)
    checks.append("导出学习报告 -> CSV 生成且含汇总/组卷/明细")

    # 14. 自定义题库导入（写 state -> reload qbank -> 出现自定义章节）
    import json, importlib
    import qbank as qbanklib
    demo = [{
        "id": "C-99", "title": "导入自检测试题", "desc": "输出 ok",
        "ref": "print('ok')", "cases": [{"stdin": "", "expect": "ok"}],
    }]
    norm = [qbanklib.normalize_question(x, i) for i, x in enumerate(demo)]
    good = [q for q in norm if q]
    assert len(good) == 1
    folder = os.path.dirname(qbanklib.CUSTOM_FILE)
    os.makedirs(folder, exist_ok=True)
    with open(qbanklib.CUSTOM_FILE, "w", encoding="utf-8") as f:
        json.dump(good, f, ensure_ascii=False)
    importlib.reload(qbanklib)
    ids = [c["id"] for c in qbanklib.CHAPTERS]
    assert "custom" in ids, "重新加载后没有自定义章节"
    assert any(q["id"] == "C-99" for q in qbanklib.QUESTIONS)
    os.remove(qbanklib.CUSTOM_FILE)
    importlib.reload(qbanklib)
    checks.append("自定义题库导入 -> 出现自定义章节，删除后恢复")

    # 15. 主页刷新
    app.show("home")
    pump(app)
    assert app.home.stat_values["solved"].cget("text").startswith("0")
    checks.append("主页刷新 -> 正常")

    app.destroy()
    if os.path.exists(TEST_STATE):
        os.remove(TEST_STATE)

    print("交互测试全部通过：")
    for c in checks:
        print("  ✓", c)


if __name__ == "__main__":
    main()
