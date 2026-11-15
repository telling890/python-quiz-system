# -*- coding: utf-8 -*-
"""不依赖 HTTP 的单元测试：密码、JWT、输出比对、限流。"""

import time

import pytest

from app.errors import ApiError
from app.judge.compare import first_diff, normalize_lines
from app.ratelimit import SlidingWindow
from app.security import (create_token, decode_token, hash_password, verify_password)


# ---------------------------------------------------------------- 密码
def test_password_roundtrip():
    stored = hash_password("secret-pass-123", iterations=1000)
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("secret-pass-123", stored) is True
    assert verify_password("wrong-pass-123", stored) is False


def test_password_salted():
    a = hash_password("same-password", iterations=1000)
    b = hash_password("same-password", iterations=1000)
    assert a != b


def test_password_bad_hash():
    assert verify_password("x", "garbage") is False
    assert verify_password("x", "") is False


# ---------------------------------------------------------------- JWT
def test_token_roundtrip():
    token = create_token(7, "alice")
    payload = decode_token(token)
    assert payload["sub"] == "7"
    assert payload["name"] == "alice"


def test_token_expired():
    token = create_token(7, "alice", ttl_minutes=-1)
    with pytest.raises(ValueError):
        decode_token(token)


def test_token_tampered():
    token = create_token(7, "alice")
    head, body, sig = token.split(".")
    with pytest.raises(ValueError):
        decode_token(head + "." + body + "." + ("A" * len(sig)))


# ---------------------------------------------------------------- 比对
def test_normalize_lines_default():
    assert normalize_lines("a  b\r\n\r\n  c  \n") == ["a b", "c"]


def test_normalize_lines_keep_indent():
    assert normalize_lines("  a\n    b\n\n", keep_indent=True) == ["  a", "    b"]


def test_first_diff_reports_line():
    diff = first_diff(["1", "2", "3"], ["1", "2", "9"])
    assert diff == {"line": 3, "expect": "3", "actual": "9"}


def test_first_diff_missing_line():
    assert first_diff(["1", "2"], ["1"])["line"] == 2
    assert first_diff(["1"], ["1", "2"])["line"] == 2


# ---------------------------------------------------------------- 限流
def test_rate_limit_window():
    window = SlidingWindow(limit=3, window=60)
    assert [window.allow() for _ in range(3)] == [True, True, True]
    assert window.allow() is False


def test_rate_limit_recovers():
    window = SlidingWindow(limit=2, window=0.2)
    assert window.allow() and window.allow()
    assert window.allow() is False
    time.sleep(0.25)
    assert window.allow() is True
