# -*- coding: utf-8 -*-
"""把 ORM 对象转成接口里的 dict（集中一处，避免每个路由各写一遍）。"""

import json


def question_dict(question, record=None):
    cases = []
    try:
        cases = json.loads(question.cases_json or "[]")
    except ValueError:
        cases = []
    return {
        "id": question.id,
        "chapter_id": question.chapter_id,
        "chapter": question.chapter,
        "no": question.no,
        "title": question.title,
        "topic": question.topic,
        "level": question.level,
        "desc": question.desc,
        "hint": question.hint,
        "ref": question.ref,
        "explain": question.explain,
        "source": question.source,
        "cases": cases,
        "last": record.last if record else "",
        "attempts": record.attempts if record else 0,
        "favorite": bool(record.favorite) if record else False,
        "code": record.code if record else "",
    }


def stats_dict(records, total):
    solved = sum(1 for r in records if r.last == "pass")
    tried = sum(1 for r in records if r.attempts > 0)
    favorite = sum(1 for r in records if r.favorite)
    attempts = sum(r.attempts for r in records)
    passes = sum(r.passes for r in records)
    return {
        "total": total,
        "solved": solved,
        "tried": tried,
        "favorite": favorite,
        "attempts": attempts,
        "passes": passes,
        "rate": int(round(passes * 100.0 / attempts)) if attempts else 0,
    }


def submission_dict(submission):
    try:
        result = json.loads(submission.result_json or "{}")
    except ValueError:
        result = {}
    return {
        "id": submission.id,
        "qid": submission.question_id,
        "status": submission.status,
        "result": result,
        "error": submission.error,
        "created_at": submission.created_at,
        "finished_at": submission.finished_at,
        "duration_ms": submission.duration_ms,
    }


def record_dict(record):
    return {
        "qid": record.question_id,
        "attempts": record.attempts,
        "passes": record.passes,
        "fails": record.fails,
        "last": record.last,
        "favorite": bool(record.favorite),
        "updated": record.updated,
    }
