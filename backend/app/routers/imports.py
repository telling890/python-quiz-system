# -*- coding: utf-8 -*-
"""导入桌面版进度：`POST /api/v1/import/state`。

桌面版把进度存在 `state.json`，服务端存在数据库。这个接口负责把老用户的
`state.json` 灌进来，规则是**合并而不是覆盖**：

- 作答次数 / 通过 / 失败取两边的**最大值**，重复导入不会把次数翻倍；
- `last` 和 `code` 以作答次数更多的一边为准（相等时保留服务端已有的）；
- 收藏取并集；
- 片段按名字对齐，同名的保留 `updated` 更新的那份；
- 自由编程草稿只在服务端还空着时填入，绝不覆盖用户在网页上新写的草稿；
- `exams`（组卷历史）没有对应表，跳过并如实报告条数。

这样「导错了」「导两次」都不会把进度弄坏，是幂等的。
"""

from fastapi import APIRouter, Body, Depends

from ..db import get_db
from ..errors import ApiError, ok
from ..models import FreeDraft, Question, Record, Snippet, now_iso
from ..security import current_user

router = APIRouter(prefix="/import", tags=["import"])

MAX_RECORDS = 2000
MAX_SNIPPETS = 500
MAX_CODE = 20000
MAX_ATTEMPTS = 1_000_000


def _as_int(value, default=0):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(MAX_ATTEMPTS, number))


def _as_text(value, limit=MAX_CODE):
    if value is None:
        return ""
    return str(value)[:limit]


def _state_of(payload):
    """同时接受 `{"state": {...}}` 和直接把 state.json 当请求体。"""
    if not isinstance(payload, dict):
        raise ApiError(400, "invalid_state", "请求体必须是 JSON 对象")
    inner = payload.get("state")
    return inner if isinstance(inner, dict) else payload


@router.post("/state")
def import_state(payload: dict = Body(...), user=Depends(current_user),
                 db=Depends(get_db)):
    state = _state_of(payload)
    questions = state.get("questions")
    if questions is None:
        questions = {}
    if not isinstance(questions, dict):
        raise ApiError(400, "invalid_state", "state.json 里的 questions 应该是一个对象")
    if len(questions) > MAX_RECORDS:
        raise ApiError(413, "state_too_large",
                       "一次最多导入 {} 条记录".format(MAX_RECORDS))

    known = {row[0] for row in db.query(Question.id).all()}
    existing = {record.question_id: record for record in
                db.query(Record).filter(Record.user_id == user.id).all()}

    created = merged = skipped = 0
    for raw_qid, item in questions.items():
        qid = _as_text(raw_qid, 24)
        if qid not in known or not isinstance(item, dict):
            skipped += 1
            continue

        attempts = _as_int(item.get("attempts"))
        passes = min(_as_int(item.get("passes")), attempts) if attempts else 0
        fails = min(_as_int(item.get("fails")), attempts) if attempts else 0
        imported_last = _as_text(item.get("last"), 8)
        imported_code = _as_text(item.get("code"))

        record = existing.get(qid)
        if record is None:
            record = Record(user_id=user.id, question_id=qid, attempts=0, passes=0,
                            fails=0, last="", code="", favorite=False)
            db.add(record)
            existing[qid] = record
            created += 1
        else:
            merged += 1

        before = record.attempts
        record.attempts = max(record.attempts, attempts)
        record.passes = max(record.passes, passes)
        record.fails = max(record.fails, fails)
        record.favorite = bool(record.favorite or item.get("favorite"))

        # 谁次数多听谁的；次数相同保留服务端已有的（导入不会倒退）
        if attempts > before:
            if imported_last:
                record.last = imported_last
            if imported_code:
                record.code = imported_code
        elif not record.last and imported_last:
            record.last = imported_last

        updated = _as_text(item.get("updated"), 32)
        if updated and (not record.updated or updated > record.updated):
            record.updated = updated

    snippets = state.get("snippets") or []
    snippet_count = 0
    if isinstance(snippets, list):
        for item in snippets[:MAX_SNIPPETS]:
            if not isinstance(item, dict):
                continue
            name = _as_text(item.get("name"), 80).strip()
            if not name:
                continue
            code = _as_text(item.get("code"))
            updated = _as_text(item.get("updated"), 32)
            row = (db.query(Snippet)
                   .filter(Snippet.user_id == user.id, Snippet.name == name)
                   .one_or_none())
            if row is None:
                db.add(Snippet(user_id=user.id, name=name, code=code,
                               updated=updated or now_iso()))
                snippet_count += 1
            elif updated and updated > (row.updated or ""):
                row.code = code
                row.updated = updated
                snippet_count += 1

    free_filled = False
    free = state.get("free") or {}
    if isinstance(free, dict) and (_as_text(free.get("code")) or _as_text(free.get("stdin"))):
        draft = db.get(FreeDraft, user.id)
        if draft is None:
            db.add(FreeDraft(user_id=user.id, code=_as_text(free.get("code")),
                             stdin=_as_text(free.get("stdin")), updated=now_iso()))
            free_filled = True
        elif not draft.code and not draft.stdin:
            draft.code = _as_text(free.get("code"))
            draft.stdin = _as_text(free.get("stdin"))
            draft.updated = now_iso()
            free_filled = True

    db.commit()

    exams = state.get("exams") or []
    return ok({
        "records": {"created": created, "merged": merged, "skipped": skipped},
        "snippets": snippet_count,
        "free": free_filled,
        "ignored": {"exams": len(exams) if isinstance(exams, list) else 0},
    })
