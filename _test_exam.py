# -*- coding: utf-8 -*-
"""组卷系统自检：随机性、覆盖面、过滤、评分、限时。"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import exam
from qbank import QUESTIONS, CHAPTERS


def main():
    ok = []

    # 1. 全量组卷：数量、去重
    paper = exam.generate_paper(QUESTIONS, 10, seed=1)
    assert len(paper) == 10, len(paper)
    ids = [q["id"] for q in paper]
    assert len(set(ids)) == 10, "出现重复题目"
    ok.append("全量组卷 10 题、无重复")

    # 2. 章节均衡：5 章抽 5 题，应每章一题
    paper5 = exam.generate_paper(QUESTIONS, len(CHAPTERS), seed=7)
    chapters = set(q["chapter"] for q in paper5)
    assert chapters == set(c["name"] for c in CHAPTERS), chapters
    ok.append("抽 {} 题覆盖全部 {} 章".format(len(CHAPTERS), len(CHAPTERS)))

    # 3. 章节过滤
    only = ["第5章 字符串"]
    paper_ch = exam.generate_paper(QUESTIONS, 5, chapters=only, seed=2)
    assert all(q["chapter"] == "第5章 字符串" for q in paper_ch)
    ok.append("章节过滤只出第5章题目")

    # 4. 难度过滤
    paper_lv = exam.generate_paper(QUESTIONS, 5, levels={3}, seed=3)
    assert all(q["level"] == 3 for q in paper_lv)
    ok.append("难度过滤只出挑战题")

    # 5. 题量不足要报错
    try:
        exam.generate_paper(QUESTIONS, 9999)
        raise AssertionError("题量不足时应当报错")
    except exam.NotEnoughQuestions:
        ok.append("题量不足时抛出 NotEnoughQuestions")

    # 6. 随机性：不同种子结果不同
    a = [q["id"] for q in exam.generate_paper(QUESTIONS, 8, seed=11)]
    b = [q["id"] for q in exam.generate_paper(QUESTIONS, 8, seed=12)]
    assert a != b, "不同种子应得到不同卷子"
    ok.append("不同随机种子得到不同试卷")

    # 7. 同种子可复现
    c = [q["id"] for q in exam.generate_paper(QUESTIONS, 8, seed=11)]
    assert a == c, "同种子应可复现"
    ok.append("同一种子结果可复现")

    # 8. 评分
    paper_s = exam.generate_paper(QUESTIONS, 4, seed=5)
    st = exam.start_exam(paper_s, minutes=0, now=1000)
    exam.record_result(st, paper_s[0]["id"], True, seconds=12)
    exam.record_result(st, paper_s[1]["id"], False, seconds=8)
    exam.record_result(st, paper_s[1]["id"], True, seconds=20)
    summary = exam.summarize(st, now=1060)
    assert summary["passed"] == 2, summary["passed"]
    assert summary["score"] == 50, summary["score"]
    assert summary["seconds"] == 60, summary["seconds"]
    assert summary["rows"][2]["status"] == "skip", summary["rows"][2]
    assert summary["rows"][1]["attempts"] == 2, summary["rows"][1]
    ok.append("评分：2/4 通过 = 50 分，未作答记为 skip")

    # 9. 限时
    st2 = exam.start_exam(paper_s, minutes=2, now=1000)
    assert exam.remaining_seconds(st2, now=1000) == 120
    assert exam.remaining_seconds(st2, now=1120) == 0
    assert exam.remaining_seconds(st2, now=2000) == 0
    assert exam.format_clock(120) == "02:00"
    assert exam.format_clock(-1) == "不限时"
    ok.append("限时倒计时与超时归零")

    # 10. 分布统计
    bal = exam.balance_report(paper5)
    assert sum(bal["chapters"].values()) == len(paper5)
    assert sum(bal["levels"].values()) == len(paper5)
    ok.append("章节/难度分布统计正确")

    print("组卷系统自检通过（{} 项）：".format(len(ok)))
    for line in ok:
        print("  ✓", line)


if __name__ == "__main__":
    main()
