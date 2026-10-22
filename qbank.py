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

CHAPTERS = [
    {"id": "ch3", "name": "第3章 程序控制结构", "short": "第3章", "questions": _CH3},
    {"id": "ch4", "name": "第4章 序列", "short": "第4章", "questions": _CH4},
    {"id": "ch5", "name": "第5章 字符串", "short": "第5章", "questions": _CH5},
    {"id": "extra", "name": "拓展练习", "short": "拓展", "questions": _EXTRA},
    {"id": "algo", "name": "进阶算法", "short": "算法", "questions": _ALGO},
]
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
