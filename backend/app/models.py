# -*- coding: utf-8 -*-
"""数据模型：用户、题目、学习记录、提交、代码片段、自由编程草稿。"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, ForeignKey, Integer, String, Text, UniqueConstraint,
                        Index)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String(24), index=True, default="")
    chapter: Mapped[str] = mapped_column(String(64), default="")
    chapter_short: Mapped[str] = mapped_column(String(24), default="")
    no: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200), default="")
    topic: Mapped[str] = mapped_column(String(120), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    desc: Mapped[str] = mapped_column(Text, default="")
    hint: Mapped[str] = mapped_column(Text, default="")
    ref: Mapped[str] = mapped_column(Text, default="")
    explain: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(120), default="")
    cases_json: Mapped[str] = mapped_column(Text, default="[]")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Record(Base):
    """某个用户在某道题上的学习记录（每人一份，天然多用户隔离）。"""

    __tablename__ = "records"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_record_user_q"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"),
                                             index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    passes: Mapped[int] = mapped_column(Integer, default=0)
    fails: Mapped[int] = mapped_column(Integer, default=0)
    last: Mapped[str] = mapped_column(String(8), default="")
    code: Mapped[str] = mapped_column(Text, default="")
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    updated: Mapped[str] = mapped_column(String(32), default="")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(24), default="", index=True)
    code: Mapped[str] = mapped_column(Text)
    stdin: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso, index=True)
    finished_at: Mapped[str] = mapped_column(String(32), default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class Snippet(Base):
    __tablename__ = "snippets"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_snippet_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(Text, default="")
    updated: Mapped[str] = mapped_column(String(32), default=now_iso)


class FreeDraft(Base):
    """自由编程页的草稿，每人一份。"""

    __tablename__ = "free_drafts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                         primary_key=True)
    code: Mapped[str] = mapped_column(Text, default="")
    stdin: Mapped[str] = mapped_column(Text, default="")
    updated: Mapped[str] = mapped_column(String(32), default=now_iso)
