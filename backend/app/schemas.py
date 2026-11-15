# -*- coding: utf-8 -*-
"""请求 / 响应模型（Pydantic v2）。"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------- 认证
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    # 邀请码：服务端配了 QUIZ_REGISTER_CODE 才校验，没配就留空
    code: str = Field(default="", max_length=64)

    @field_validator("username")
    @classmethod
    def _name_ok(cls, value):
        value = value.strip()
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线和连字符")
        return value


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    created_at: str


class TokenOut(BaseModel):
    token: str
    expires_in: int
    user: UserOut


# ---------------------------------------------------------------- 题库
class CaseModel(BaseModel):
    stdin: str = ""
    expect: str = ""
    raw: bool = False


class QuestionOut(BaseModel):
    id: str
    chapter_id: str
    chapter: str
    no: int
    title: str
    topic: str
    level: int
    desc: str
    hint: str
    ref: str = ""
    explain: str = ""
    source: str = ""
    cases: List[CaseModel] = Field(default_factory=list)
    # 当前用户的学习状态
    last: str = ""
    attempts: int = 0
    favorite: bool = False
    code: str = ""


class ChapterOut(BaseModel):
    id: str
    name: str
    short: str
    count: int


class StatsOut(BaseModel):
    total: int = 0
    solved: int = 0
    tried: int = 0
    favorite: int = 0
    attempts: int = 0
    passes: int = 0
    rate: int = 0


class BankOut(BaseModel):
    questions: List[QuestionOut]
    chapters: List[ChapterOut]
    stats: StatsOut


# ---------------------------------------------------------------- 提交
class SubmissionIn(BaseModel):
    qid: Optional[str] = Field(default=None, max_length=24)
    code: str = Field(min_length=1, max_length=20000)
    stdin: str = Field(default="", max_length=20000)


class SubmissionOut(BaseModel):
    id: str
    qid: str = ""
    status: str
    result: dict = Field(default_factory=dict)
    error: str = ""
    created_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0


class FreeRunIn(BaseModel):
    code: str = Field(min_length=1, max_length=20000)
    stdin: str = Field(default="", max_length=20000)


# ---------------------------------------------------------------- 片段 / 草稿
class SnippetIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(default="", max_length=50000)


class SnippetOut(BaseModel):
    name: str
    code: str
    updated: str


class FreeIn(BaseModel):
    code: str = ""
    stdin: str = ""


class FreeOut(BaseModel):
    code: str
    stdin: str
    updated: str


class RecordOut(BaseModel):
    qid: str
    attempts: int
    passes: int
    fails: int
    last: str
    favorite: bool
    updated: str


class ProgressOut(BaseModel):
    stats: StatsOut
    records: List[RecordOut]


class FavoriteIn(BaseModel):
    favorite: bool = True
