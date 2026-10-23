# -*- coding: utf-8 -*-
"""题库汇总：按教材章节组织。

  第3章 程序控制结构  bank_ch3.py
  第4章 序列          bank_ch4.py
  第5章 字符串        bank_ch5.py

每道题的结构：
  id       题号（如 5-03，前缀是章节）
  chapter  所属章节名
  no       教材中的题号
  title    题名
  topic    考点标签
  level    难度 1 入门 / 2 进阶 / 3 挑战
  desc     题目描述（含输入、输出约定）
  hint     方法提示
  ref      参考答案（必须能通过全部测试用例）
  cases    测试用例 [{"stdin": "...", "expect": "..."}]
  explain  解析与易错点
"""

import json
import os

from bank_ch5 import QUESTIONS as _CH5
from bank_extra import QUESTIONS as _EXTRA
from bank_algo import QUESTIONS as _ALGO

try:
    from bank_ch3 import QUESTIONS as _CH3
except ImportError:  # 还没转录完的章节允许缺省
    _CH3 = []
try:
    from bank_ch4 import QUESTIONS as _CH4
except ImportError:
    _CH4 = []

CUSTOM_FILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "PyQuizState", "custom_bank.json")
CUSTOM_NAME = "自定义题库"
CUSTOM_SHORT = "自定义"


def normalize_question(raw, index=0):
    """把导入的一条题目补齐成程序内部结构；缺关键字段返回 None。"""
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    desc = str(raw.get("desc") or "").strip()
    ref = raw.get("ref") or raw.get("answer") or ""
    if not (title and desc and ref):
        return None

    cases = []
    for c in (raw.get("cases") or []):
        if isinstance(c, dict):
            stdin = c.get("stdin", "")
            expect = c.get("expect", c.get("stdout", ""))
            item = {"stdin": stdin, "expect": expect}
            if c.get("raw"):
                item["raw"] = True
            cases.append(item)
    if not cases:
        return None

    try:
        level = int(raw.get("level", 1))
    except (TypeError, ValueError):
        level = 1
    level = min(3, max(1, level))

    return {
        "id": str(raw.get("id") or "C-{:02d}".format(index + 1)),
        "chapter": CUSTOM_NAME,
        "no": index + 1,
        "title": title,
        "topic": str(raw.get("topic") or "自定义"),
        "level": level,
        "desc": desc,
        "hint": str(raw.get("hint") or "先想清楚输入输出格式，再动手写。"),
        "ref": str(ref),
        "cases": cases,
        "explain": str(raw.get("explain") or ""),
        "source": str(raw.get("source") or "用户导入"),
    }


def load_custom(path=None):
    """读取自定义题库，返回题目列表（文件不存在或格式不对时返回空列表）。"""
    path = path or CUSTOM_FILE
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (IOError, ValueError):
        return []

    if isinstance(data, dict):
        data = data.get("questions") or []
    if not isinstance(data, list):
        return []

    questions = []
    for i, raw in enumerate(data):
        q = normalize_question(raw, i)
        if q:
            questions.append(q)
    return questions


CHAPTERS = [
    {"id": "ch3", "name": "第3章 程序控制结构", "short": "第3章", "questions": _CH3},
    {"id": "ch4", "name": "第4章 序列", "short": "第4章", "questions": _CH4},
    {"id": "ch5", "name": "第5章 字符串", "short": "第5章", "questions": _CH5},
    {"id": "extra", "name": "拓展练习", "short": "拓展", "questions": _EXTRA},
    {"id": "algo", "name": "进阶算法", "short": "算法", "questions": _ALGO},
]
_CUSTOM = load_custom()
if _CUSTOM:
    CHAPTERS.append({"id": "custom", "name": CUSTOM_NAME,
                     "short": CUSTOM_SHORT, "questions": _CUSTOM})

CHAPTERS = [c for c in CHAPTERS if c["questions"]]

QUESTIONS = []
for _c in CHAPTERS:
    QUESTIONS.extend(_c["questions"])


def get_questions():
    return QUESTIONS


def get_chapters():
    return CHAPTERS


def chapter_of(qid, questions=None):
    questions = questions or QUESTIONS
    for q in questions:
        if q["id"] == qid:
            return q.get("chapter", "")
    return ""
