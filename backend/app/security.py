# -*- coding: utf-8 -*-
"""认证：PBKDF2 密码哈希 + 手写 HS256 JWT（不引入 pyjwt 之类依赖）。

为什么要手写 JWT：这个项目的主张是「能跑在裸 Python 上」，
HS256 只有十几行，用标准库 hmac/hashlib 实现反而比多装一个包更透明。
"""

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException, status

from .config import get_settings

_HASH_NAME = "sha256"


# ---------------------------------------------------------------- 编码工具
def _b64e(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text):
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


# ---------------------------------------------------------------- 密码
def hash_password(password, iterations=None):
    """返回 pbkdf2_sha256$迭代次数$盐$摘要。"""
    iterations = iterations or get_settings().password_iterations
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, iterations)
    return "pbkdf2_{}${}${}${}".format(_HASH_NAME, iterations, _b64e(salt), _b64e(digest))


def verify_password(password, stored):
    try:
        algo, iterations, salt_b64, digest_b64 = stored.split("$")
        if not algo.startswith("pbkdf2_"):
            return False
        salt = _b64d(salt_b64)
        expected = _b64d(digest_b64)
        actual = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# ---------------------------------------------------------------- JWT
def _sign(message):
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).digest()


def create_token(user_id, username, ttl_minutes=None):
    ttl = (ttl_minutes or get_settings().token_ttl_minutes) * 60
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(user_id), "name": username, "iat": now, "exp": now + ttl}
    body = _b64e(json.dumps(header, separators=(",", ":")).encode()) + "." + \
        _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return body + "." + _b64e(_sign(body.encode("ascii")))


def decode_token(token):
    """校验签名与过期时间，返回 payload；无效时抛 ValueError。"""
    try:
        head_b64, body_b64, sig_b64 = token.split(".")
        expected = _sign((head_b64 + "." + body_b64).encode("ascii"))
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            raise ValueError("签名不对")
        payload = json.loads(_b64d(body_b64))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise ValueError("令牌无效")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("令牌已过期")
    return payload


# ---------------------------------------------------------------- 依赖
def _bearer(authorization):
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def current_user(authorization: str = Header(default="")):
    from .db import SessionLocal
    from .models import User

    token = _bearer(authorization)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少 Bearer 令牌",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "令牌无效或已过期",
                            headers={"WWW-Authenticate": "Bearer"})

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已停用")
        db.expunge(user)
    return user
