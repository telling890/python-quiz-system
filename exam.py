# -*- coding: utf-8 -*-
"""组卷与评分：纯逻辑，不依赖界面，方便单独测试。

组卷策略：
1. 先按「章节 + 难度」过滤出可用题库；
2. 按章节轮转抽题（每轮从各章剩余题目里随机取一题），保证章节覆盖均衡；
3. 支持按权重抽题：错得多、没掌握的题权重更高（权重由调用方按学习记录计算）；
4. 最后打乱题序，避免同章题目扎堆。

评分：每题通过得 1 分，总分按百分制折算；同时记录用时与逐题结果。
"""

import random
import time


class NotEnoughQuestions(Exception):
    """可用题目不足，无法组卷。"""


def filter_pool(questions, chapters=None, levels=None):
    """按章节名集合与难度集合过滤题目。chapters/levels 为 None 表示不限。"""
    pool = []
    for q in questions:
        if chapters and q.get("chapter") not in chapters:
            continue
        if levels and q.get("level") not in levels:
            continue
        pool.append(q)
    return pool


def _weighted_pop(rng, bucket, weights):
    """按权重从 bucket 里取一题（权重缺失按 1 计），取走后从列表删除。"""
    if not weights:
        return bucket.pop()
    total = 0.0
    for q in bucket:
        total += max(0.01, float(weights.get(q.get("id"), 1.0)))
    if total <= 0:
        return bucket.pop()
    r = rng.uniform(0.0, total)
    acc = 0.0
    for i, q in enumerate(bucket):
        acc += max(0.01, float(weights.get(q.get("id"), 1.0)))
        if r <= acc:
            return bucket.pop(i)
    return bucket.pop()


def generate_paper(questions, count, chapters=None, levels=None, seed=None, weights=None):
    """随机组卷，返回题目列表（长度 = count，且不重复）。

    chapters: 章节名集合（如 {"第3章 程序控制结构", "进阶算法"}），None 表示全部
    levels:   难度集合（{1,2,3}），None 表示不限
    seed:     随机种子，测试时传固定值可复现
    weights:  题目权重 {qid: 数值}，越大越容易被抽到；None 表示等概率（章节均衡）
    """
    if count <= 0:
        raise NotEnoughQuestions("题目数量必须大于 0")

    pool = filter_pool(questions, chapters, levels)
    if len(pool) < count:
        raise NotEnoughQuestions(
            "符合条件的题目只有 {} 道，不够出 {} 道".format(len(pool), count))

    rng = random.Random(seed)

    # 按章节分组，组内打乱
    groups = {}
    for q in pool:
        groups.setdefault(q.get("chapter", ""), []).append(q)
    for items in groups.values():
        rng.shuffle(items)

    # 轮转抽题：每轮各章出一题，直到凑够数量
    chapter_names = list(groups.keys())
    rng.shuffle(chapter_names)

    picked = []
    while len(picked) < count:
        progressed = False
        for name in chapter_names:
            if len(picked) >= count:
                break
            bucket = groups[name]
            if bucket:
                picked.append(_weighted_pop(rng, bucket, weights))
                progressed = True
        if not progressed:
            break

    if len(picked) < count:
        raise NotEnoughQuestions("可用题目不足")

    rng.shuffle(picked)
    return picked


def start_exam(paper, minutes=0, now=None):
    """构造一次考试的运行时状态。minutes=0 表示不限时。"""
    now = now if now is not None else time.time()
    return {
        "paper": list(paper),
        "started": now,
        "limit": int(minutes or 0),
        "deadline": now + int(minutes) * 60 if minutes else 0,
        "results": {},          # qid -> {"status": "pass"/"fail", "attempts": n, "seconds": s}
        "submitted": False,
    }


def record_result(exam, qid, passed, seconds=None):
    """记录某题的判题结果（同一题多次提交以最后一次为准，attempts 累加）。"""
    item = exam["results"].setdefault(qid, {"status": "fail", "attempts": 0, "seconds": 0})
    item["attempts"] += 1
    item["status"] = "pass" if passed else "fail"
    if seconds:
        item["seconds"] = int(seconds)
    return item


def remaining_seconds(exam, now=None):
    """剩余秒数；不限时返回 -1。"""
    if not exam.get("deadline"):
        return -1
    now = now if now is not None else time.time()
    return max(0, int(exam["deadline"] - now))


def summarize(exam, now=None):
    """交卷统计：得分、通过数、用时、逐题明细。"""
    now = now if now is not None else time.time()
    paper = exam["paper"]
    total = len(paper)
    passed = 0
    rows = []
    for q in paper:
        r = exam["results"].get(q["id"])
        ok = bool(r and r["status"] == "pass")
        if ok:
            passed += 1
        rows.append({
            "id": q["id"],
            "title": q["title"],
            "chapter": q.get("chapter", ""),
            "level": q.get("level", 1),
            "status": "pass" if ok else ("fail" if r else "skip"),
            "attempts": r["attempts"] if r else 0,
            "seconds": r["seconds"] if r else 0,
        })

    score = int(round(passed * 100.0 / total)) if total else 0
    return {
        "total": total,
        "passed": passed,
        "score": score,
        "seconds": int(now - exam["started"]),
        "rows": rows,
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
    }


def format_clock(seconds):
    """秒数格式化成 mm:ss。"""
    if seconds < 0:
        return "不限时"
    m, s = divmod(int(seconds), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return "{}:{:02d}:{:02d}".format(h, m, s)
    return "{:02d}:{:02d}".format(m, s)


def balance_report(paper):
    """统计一套卷子的章节 / 难度分布，用于界面提示与文档。"""
    by_chapter = {}
    by_level = {}
    for q in paper:
        by_chapter[q.get("chapter", "")] = by_chapter.get(q.get("chapter", ""), 0) + 1
        by_level[q.get("level", 1)] = by_level.get(q.get("level", 1), 0) + 1
    return {"chapters": by_chapter, "levels": by_level}
