# -*- coding: utf-8 -*-
"""从桌面版的 qbank.py 导出题库 JSON，供后端启动时灌库。

用法（在 quiz_app 目录下）：
    py -3.10 backend/scripts/export_bank.py
产物：backend/app/data/questions.json
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QUIZ_ROOT = os.path.dirname(os.path.dirname(HERE))       # quiz_app/
OUT = os.path.join(os.path.dirname(HERE), "app", "data", "questions.json")

sys.path.insert(0, QUIZ_ROOT)
sys.path.insert(0, os.path.join(QUIZ_ROOT, "backend"))

import qbank  # noqa: E402 - 必须在 sys.path 设好之后导入


def main():
    rows = []
    for chapter in qbank.CHAPTERS:
        for q in chapter["questions"]:
            rows.append({
                "id": q["id"],
                "chapter_id": chapter["id"],
                "chapter": chapter["name"],
                "chapter_short": chapter["short"],
                "no": q.get("no", 0),
                "title": q["title"],
                "topic": q.get("topic", ""),
                "level": q.get("level", 1),
                "desc": q.get("desc", ""),
                "hint": q.get("hint", ""),
                "ref": q.get("ref", ""),
                "explain": q.get("explain", ""),
                "source": q.get("source", ""),
                "cases": q.get("cases", []),
            })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"chapters": [{"id": c["id"], "name": c["name"], "short": c["short"],
                                 "count": len(c["questions"])} for c in qbank.CHAPTERS],
                   "questions": rows}, f, ensure_ascii=False, indent=1)
    print("导出 {} 道题 -> {}".format(len(rows), OUT))


if __name__ == "__main__":
    main()
