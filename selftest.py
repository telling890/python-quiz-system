# -*- coding: utf-8 -*-
"""题库自检：跑一遍所有参考答案，确保每题都能通过自己的测试用例。

用法： python selftest.py
全部通过时退出码为 0，否则为 1（打包前会先跑这个）。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from qbank import QUESTIONS
from judge import run_case


def main():
    bad = 0
    total_cases = 0
    for q in QUESTIONS:
        problems = []
        for i, case in enumerate(q["cases"], 1):
            total_cases += 1
            r = run_case(q["ref"], case)
            if r["status"] != "pass":
                detail = "、" .join(
                    [
                        "用例{} {}".format(i, r["status"]),
                        "期望={}".format(case["expect"]),
                        "实际={}".format(r["actual"]),
                        "错误={}".format(r["error"]),
                    ]
                )
                problems.append(detail)
        if problems:
            bad += 1
            print("[FAIL] {} {}".format(q["id"], q["title"]))
            for p in problems:
                print("       " + p)
        else:
            print("[ OK ] {} {} ({} 个用例)".format(q["id"], q["title"], len(q["cases"])))

    print("-" * 64)
    print("题目 {} 道，测试用例 {} 个，失败 {} 道".format(len(QUESTIONS), total_cases, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
