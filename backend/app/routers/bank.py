# -*- coding: utf-8 -*-
"""题库与进度接口：题目列表、单题详情、学习记录、收藏。"""

from fastapi import APIRouter, Depends, status

from ..db import get_db
from ..errors import ApiError, ok
from ..models import Question, Record
from ..schemas import FavoriteIn
from ..security import current_user
from ..serializers import question_dict, record_dict, stats_dict

router = APIRouter(tags=["bank"])


def _records_of(db, user_id):
    return db.query(Record).filter(Record.user_id == user_id).all()


@router.get("/bank")
def bank(user=Depends(current_user), db=Depends(get_db)):
    """一次把题库 + 当前用户的进度发给前端（本地开发够用，数据量大时改分页）。"""
    questions = db.query(Question).order_by(Question.sort_order).all()
    records = {r.question_id: r for r in _records_of(db, user.id)}

    chapters = []
    seen = {}
    for q in questions:
        if q.chapter_id not in seen:
            seen[q.chapter_id] = {"id": q.chapter_id, "name": q.chapter,
                                  "short": q.chapter_short, "count": 0}
            chapters.append(seen[q.chapter_id])
        seen[q.chapter_id]["count"] += 1

    items = [question_dict(q, records.get(q.id)) for q in questions]
    return ok({"questions": items, "chapters": chapters,
               "stats": stats_dict(records.values(), len(questions))})


@router.get("/questions/{qid}")
def get_question(qid: str, user=Depends(current_user), db=Depends(get_db)):
    question = db.get(Question, qid)
    if question is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "question_not_found", "没有这道题：" + qid)
    record = db.query(Record).filter(Record.user_id == user.id,
                                     Record.question_id == qid).one_or_none()
    return ok(question_dict(question, record))


@router.get("/progress")
def progress(user=Depends(current_user), db=Depends(get_db)):
    total = db.query(Question).count()
    records = _records_of(db, user.id)
    return ok({"stats": stats_dict(records, total),
               "records": [record_dict(r) for r in records]})


@router.post("/progress/{qid}/favorite")
def favorite(qid: str, payload: FavoriteIn, user=Depends(current_user), db=Depends(get_db)):
    question = db.get(Question, qid)
    if question is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "question_not_found", "没有这道题：" + qid)
    record = db.query(Record).filter(Record.user_id == user.id,
                                     Record.question_id == qid).one_or_none()
    if record is None:
        record = Record(user_id=user.id, question_id=qid)
        db.add(record)
    record.favorite = bool(payload.favorite)
    db.commit()
    return ok({"qid": qid, "favorite": record.favorite})
