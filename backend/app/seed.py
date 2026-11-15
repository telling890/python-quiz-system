# -*- coding: utf-8 -*-
"""启动时把题库写进数据库（表为空才写，重启不会重复）。"""

import json
from pathlib import Path

from .db import SessionLocal
from .models import Question

DATA_FILE = Path(__file__).with_name("data") / "questions.json"


def load_seed():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        return payload.get("questions") or []
    return payload


def seed_questions():
    rows = load_seed()
    if not rows:
        return 0
    with SessionLocal() as db:
        if db.query(Question).count() > 0:
            return 0
        for index, raw in enumerate(rows):
            db.add(Question(
                id=raw["id"],
                chapter_id=raw.get("chapter_id", ""),
                chapter=raw.get("chapter", ""),
                chapter_short=raw.get("chapter_short", ""),
                no=int(raw.get("no") or 0),
                title=raw.get("title", ""),
                topic=raw.get("topic", ""),
                level=int(raw.get("level") or 1),
                desc=raw.get("desc", ""),
                hint=raw.get("hint", ""),
                ref=raw.get("ref", ""),
                explain=raw.get("explain", ""),
                source=raw.get("source", ""),
                cases_json=json.dumps(raw.get("cases") or [], ensure_ascii=False),
                sort_order=index,
            ))
        db.commit()
    return len(rows)
