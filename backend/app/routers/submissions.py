# -*- coding: utf-8 -*-
"""判题接口：提交进队列（异步）、查结果、自由编程即时运行。"""

from fastapi import APIRouter, Depends, Query, status

from ..db import get_db
from ..errors import ApiError, ok
from ..judge.executor import run_python
from ..judge.worker import get_service
from ..models import Question, Submission
from ..schemas import FreeRunIn, SubmissionIn
from ..security import current_user
from ..serializers import submission_dict

router = APIRouter(tags=["judge"])


@router.post("/submissions", status_code=status.HTTP_202_ACCEPTED)
def create_submission(payload: SubmissionIn, user=Depends(current_user), db=Depends(get_db)):
    """返回 202 + 提交 id，判题在后台 worker 里跑，前端轮询结果。"""
    qid = (payload.qid or "").strip()
    if qid:
        if db.get(Question, qid) is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "question_not_found",
                           "没有这道题：" + qid)
    submission = Submission(user_id=user.id, question_id=qid,
                            code=payload.code, stdin=payload.stdin)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    get_service().enqueue(submission.id)
    return ok(submission_dict(submission))


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: str, user=Depends(current_user), db=Depends(get_db)):
    submission = db.get(Submission, submission_id)
    if submission is None or submission.user_id != user.id:
        # 别人的提交也按「不存在」处理，不泄露 id 是否有效
        raise ApiError(status.HTTP_404_NOT_FOUND, "submission_not_found", "没有这次提交")
    return ok(submission_dict(submission))


@router.get("/submissions")
def list_submissions(limit: int = Query(default=20, ge=1, le=100),
                     user=Depends(current_user), db=Depends(get_db)):
    rows = (db.query(Submission)
            .filter(Submission.user_id == user.id)
            .order_by(Submission.created_at.desc())
            .limit(limit).all())
    return ok({"items": [submission_dict(s) for s in rows], "limit": limit})


@router.post("/run")
def run_free(payload: FreeRunIn, user=Depends(current_user)):
    """自由编程：同步跑一次，直接返回输出（不走队列，方便边写边看）。"""
    run = run_python(payload.code, payload.stdin)
    return ok({"mode": "free", "run": run})
