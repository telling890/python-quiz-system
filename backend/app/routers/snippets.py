# -*- coding: utf-8 -*-
"""代码片段与自由编程草稿（按用户隔离）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError

from ..db import get_db
from ..errors import ApiError, ok
from ..models import FreeDraft, Snippet, now_iso
from ..schemas import FreeIn, SnippetIn
from ..security import current_user

router = APIRouter(tags=["snippets"])


@router.get("/snippets")
def list_snippets(user=Depends(current_user), db=Depends(get_db)):
    rows = (db.query(Snippet).filter(Snippet.user_id == user.id)
            .order_by(Snippet.updated.desc()).all())
    return ok({"snippets": [{"name": s.name, "code": s.code, "updated": s.updated}
                            for s in rows]})


@router.post("/snippets")
def save_snippet(payload: SnippetIn, user=Depends(current_user), db=Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise ApiError(400, "invalid_name", "片段名字不能为空")
    row = (db.query(Snippet)
           .filter(Snippet.user_id == user.id, Snippet.name == name).one_or_none())
    created = row is None
    if created:
        row = Snippet(user_id=user.id, name=name, code=payload.code, updated=now_iso())
        db.add(row)
    else:
        row.code = payload.code
        row.updated = now_iso()
    try:
        db.commit()
    except IntegrityError:                      # 并发同名，退化成更新
        db.rollback()
        row = db.query(Snippet).filter(Snippet.user_id == user.id,
                                       Snippet.name == name).one()
        row.code = payload.code
        row.updated = now_iso()
        db.commit()
        created = False
    return ok({"created": created, "name": name})


@router.delete("/snippets/{name}")
def delete_snippet(name: str, user=Depends(current_user), db=Depends(get_db)):
    row = (db.query(Snippet)
           .filter(Snippet.user_id == user.id, Snippet.name == name).one_or_none())
    if row is None:
        raise ApiError(404, "snippet_not_found", "没有这个片段：" + name)
    db.delete(row)
    db.commit()
    return ok({"removed": True, "name": name})


@router.get("/free")
def get_free(user=Depends(current_user), db=Depends(get_db)):
    row = db.get(FreeDraft, user.id)
    if row is None:
        return ok({"code": "", "stdin": "", "updated": ""})
    return ok({"code": row.code, "stdin": row.stdin, "updated": row.updated})


@router.put("/free")
def save_free(payload: FreeIn, user=Depends(current_user), db=Depends(get_db)):
    row = db.get(FreeDraft, user.id)
    if row is None:
        row = FreeDraft(user_id=user.id)
        db.add(row)
    row.code = payload.code
    row.stdin = payload.stdin
    row.updated = now_iso()
    db.commit()
    return ok({"saved": True, "updated": row.updated})
