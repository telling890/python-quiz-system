# -*- coding: utf-8 -*-
"""判题：输出归一化与用例比对（逻辑与桌面版 judge.py 一致，便于迁移对照）。"""

import re


def normalize_lines(text, keep_indent=False):
    """统一换行、压缩空白、去掉空行；keep_indent 用于图形类题目。"""
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for line in text.split("\n"):
        if keep_indent:
            line = line.rstrip()
            if line.strip():
                out.append(line)
        else:
            line = re.sub(r"[ \t\u3000]+", " ", line).strip()
            if line:
                out.append(line)
    return out


def first_diff(expect_lines, actual_lines):
    total = max(len(expect_lines), len(actual_lines))
    for i in range(total):
        e = expect_lines[i] if i < len(expect_lines) else None
        a = actual_lines[i] if i < len(actual_lines) else None
        if e != a:
            return {"line": i + 1, "expect": e, "actual": a}
    return None
