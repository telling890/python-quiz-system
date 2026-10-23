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

    # 11. 加权抽样：高权重题的占比应接近其权重占比
    import random
    bucket = [{"id": "heavy"}] + [{"id": "n%d" % i} for i in range(9)]
    weights = {"heavy": 18.0}
    for i in range(9):
        weights["n%d" % i] = 1.0
    rng = random.Random(2024)
    picked_heavy = 0
    trials = 60
    for _ in range(trials):
        items = list(bucket)
        got = exam._weighted_pop(rng, items, weights)
        if got["id"] == "heavy":
            picked_heavy += 1
        assert len(items) == len(bucket) - 1, "抽走一题后列表长度应减 1"
    assert picked_heavy >= 30, "高权重题被抽中次数偏低：{}/{}".format(picked_heavy, trials)
    assert picked_heavy > trials / 3.0, "加权后命中率应显著高于等概率（1/10）"
    ok.append("加权抽样：权重 18:1 的题被抽中 {}/{} 次".format(picked_heavy, trials))

    # 12. weights=None 与不传权重等价（结果可复现）
    a2 = [q["id"] for q in exam.generate_paper(QUESTIONS, 6, seed=99, weights=None)]
    b2 = [q["id"] for q in exam.generate_paper(QUESTIONS, 6, seed=99)]
    assert a2 == b2, "weights=None 应与不传权重等价"
    ok.append("weights=None 与默认等概率组卷结果一致")

    print("组卷系统自检通过（{} 项）：".format(len(ok)))
    for line in ok:
        print("  ✓", line)


if __name__ == "__main__":
    main()
