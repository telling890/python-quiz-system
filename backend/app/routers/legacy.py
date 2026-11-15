# -*- coding: utf-8 -*-
"""网页版旧接口兼容层：`/api/*`（无版本号）。

背景
----
`web/index.html` 是给桌面版 `webserver.py` 写的，它按「一人一台机器、一份
state.json」的假设调用 `/api/run`、`/api/bank` 这些接口。要把它直接放到公网上
（多用户、每人独立进度），又不重写整个前端，最省事也最不容易出错的做法是：
**把这套旧接口原样实现一遍，底下换成 FastAPI 的数据库模型**。

因此这个文件的三条铁律：

1. 响应的 JSON 形状必须和 `webserver.py` 一模一样（含 `ok`/`error` 是**字符串**，
   前端 `api()` 会直接把 `data.error` 塞进 `new Error(...)`）。
2. 所有接口都要求登录（Bearer 令牌），进度/草稿/片段按 user_id 隔离。
3. 判题逻辑不另写一份，直接复用 `judge_worker` 的模块级函数，
   保证「同步判题」和「异步队列判题」结果一致。

未来前端改成调 `/api/v1/*` 之后，这个文件可以整体删掉。
"""

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from ..db import get_db
from ..judge.executor import run_python, run_trace
from ..judge.worker import judge_question
from ..models import FreeDraft, Question, Record, Snippet, now_iso
from ..security import current_user
from ..serializers import question_dict, stats_dict

router = APIRouter(prefix="/api", tags=["web-legacy"])

MAX_CODE = 20000
MAX_NAME = 80


def _fail(message, status_code=400):
    """旧接口的错误格式：error 是给人看的字符串，不是对象。"""
    return JSONResponse(status_code=status_code, content={"ok": False, "error": message})


def _payload(data):
    return data if isinstance(data, dict) else {}


def _bank_payload(db, user):
    questions = db.query(Question).order_by(Question.sort_order).all()
    records = {r.question_id: r for r in
               db.query(Record).filter(Record.user_id == user.id).all()}

    chapters = []
    seen = {}
    for question in questions:
        if question.chapter_id not in seen:
            seen[question.chapter_id] = {"id": question.chapter_id, "name": question.chapter,
                                         "short": question.chapter_short, "count": 0}
            chapters.append(seen[question.chapter_id])
        seen[question.chapter_id]["count"] += 1

    return {
        "questions": [question_dict(q, records.get(q.id)) for q in questions],
        "chapters": chapters,
        "stats": stats_dict(records.values(), len(questions)),
    }


def _stats_of(db, user):
    records = db.query(Record).filter(Record.user_id == user.id).all()
    return stats_dict(records, db.query(Question).count())


def _bump_record(db, user, qid, passed, code):
    """记一次作答：与 JudgeService._update_record 保持同样的口径。"""
    record = (db.query(Record)
              .filter(Record.user_id == user.id, Record.question_id == qid).one_or_none())
    if record is None:
        # SQLAlchemy 的 default 是 flush 才生效的，构造时显式给初值
        record = Record(user_id=user.id, question_id=qid, attempts=0, passes=0,
                        fails=0, last="", code="", favorite=False)
        db.add(record)
    record.attempts += 1
    if passed:
        record.passes += 1
        record.last = "pass"
    else:
        record.fails += 1
        record.last = "fail"
    record.code = code
    record.updated = now_iso()
    db.commit()
    return record


def _snippets_of(db, user):
    rows = (db.query(Snippet).filter(Snippet.user_id == user.id)
            .order_by(Snippet.updated.desc()).all())
    return [{"name": row.name, "code": row.code, "updated": row.updated} for row in rows]


def describe_trace(trace):
    """把追踪结果总结成一句话（与桌面版 tracer.describe 一致）。"""
    steps = trace.get("steps") or []
    if trace.get("error"):
        return trace["error"]
    if trace.get("timeout"):
        return "执行超时，追踪在第 {} 步被打断（检查循环条件）".format(len(steps))
    if trace.get("truncated"):
        return "记录到前 {} 步就停了（循环太长，或者写成了死循环）".format(len(steps))
    return ""


# ---------------------------------------------------------------- 读接口
@router.get("/bank")
def get_bank(user=Depends(current_user), db=Depends(get_db)):
    return _bank_payload(db, user)


@router.get("/free")
def get_free(user=Depends(current_user), db=Depends(get_db)):
    row = db.get(FreeDraft, user.id)
    if row is None:
        return {"code": "", "stdin": "", "updated": ""}
    return {"code": row.code, "stdin": row.stdin, "updated": row.updated}


@router.get("/snippets")
def get_snippets(user=Depends(current_user), db=Depends(get_db)):
    return {"snippets": _snippets_of(db, user)}


# ---------------------------------------------------------------- 判题
@router.post("/run")
def post_run(data: dict = Body(default={}), user=Depends(current_user), db=Depends(get_db)):
    data = _payload(data)
    code = str(data.get("code") or "")
    qid = str(data.get("qid") or "").strip()
    stdin_text = str(data.get("stdin") or "")

    if not code.strip():
        return _fail("代码是空的")
    if len(code) > MAX_CODE:
        return _fail("代码太长了（上限 {} 字符）".format(MAX_CODE), 413)

    if qid:
        question = db.get(Question, qid)
        if question is None:
            return _fail("没有这道题：{}".format(qid), 404)
        return {"ok": True, "mode": "judge", "judge": judge_question(code, question)}

    # 自由编程：没有题目就当场跑一遍，把输出给浏览器。
    # 这里直接调 run_python（而不是 run_free_code）：网页版期望的形状是
    # {ok, mode:"free", run:{output, error, ...}}，run_free_code 会再包一层
    # status/passed，形状就对不上了。
    return {"ok": True, "mode": "free", "run": run_python(code, stdin_text)}


@router.post("/trace")
def post_trace(data: dict = Body(default={}), user=Depends(current_user)):
    data = _payload(data)
    code = str(data.get("code") or "")
    if not code.strip():
        return _fail("代码是空的")
    if len(code) > MAX_CODE:
        return _fail("代码太长了（上限 {} 字符）".format(MAX_CODE), 413)

    trace = run_trace(code, str(data.get("stdin") or ""))
    return {"ok": True, "trace": trace, "summary": describe_trace(trace)}


# ---------------------------------------------------------------- 写接口
@router.post("/attempt")
def post_attempt(data: dict = Body(default={}), user=Depends(current_user),
                 db=Depends(get_db)):
    data = _payload(data)
    qid = str(data.get("qid") or "").strip()
    if not qid:
        return _fail("缺少题目编号")
    if db.get(Question, qid) is None:
        return _fail("没有这道题：{}".format(qid), 404)

    record = _bump_record(db, user, qid, bool(data.get("passed")),
                          str(data.get("code") or "")[:MAX_CODE])
    stats = _stats_of(db, user)
    return {"ok": True, "stats": stats,
            "record": {"last": record.last, "attempts": record.attempts}}


@router.post("/free")
def post_free(data: dict = Body(default={}), user=Depends(current_user),
              db=Depends(get_db)):
    data = _payload(data)
    row = db.get(FreeDraft, user.id)
    if row is None:
        row = FreeDraft(user_id=user.id)
        db.add(row)
    row.code = str(data.get("code") or "")[:MAX_CODE]
    row.stdin = str(data.get("stdin") or "")[:MAX_CODE]
    row.updated = now_iso()
    db.commit()
    return {"ok": True, "saved": True}


@router.post("/snippet")
def post_snippet(data: dict = Body(default={}), user=Depends(current_user),
                 db=Depends(get_db)):
    data = _payload(data)
    name = str(data.get("name") or "").strip()

    if data.get("delete"):
        if not name:
            return _fail("缺少片段名字")
        row = (db.query(Snippet)
               .filter(Snippet.user_id == user.id, Snippet.name == name).one_or_none())
        if row is None:
            return {"ok": True, "removed": False}
        db.delete(row)
        db.commit()
        return {"ok": True, "removed": True}

    if not name:
        return _fail("片段名字不能为空")
    if len(name) > MAX_NAME:
        return _fail("片段名字太长了（上限 {} 字符）".format(MAX_NAME))
    code = str(data.get("code") or "")[:MAX_CODE]

    row = (db.query(Snippet)
           .filter(Snippet.user_id == user.id, Snippet.name == name).one_or_none())
    created = row is None
    if created:
        row = Snippet(user_id=user.id, name=name, code=code, updated=now_iso())
        db.add(row)
    else:
        row.code = code
        row.updated = now_iso()
    db.commit()
    return {"ok": True, "created": created, "snippets": _snippets_of(db, user)}
