# -*- coding: utf-8 -*-
"""认证接口：注册、登录、当前用户。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError

from ..config import get_settings
from ..db import get_db
from ..errors import ApiError, ok
from ..models import User
from ..schemas import LoginIn, RegisterIn
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_payload(user):
    settings = get_settings()
    return {
        "token": create_token(user.id, user.username),
        "expires_in": settings.token_ttl_minutes * 60,
        "user": {"id": user.id, "username": user.username, "created_at": user.created_at},
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db=Depends(get_db)):
    expected = (get_settings().register_code or "").strip()
    if expected and (payload.code or "").strip() != expected:
        raise ApiError(status.HTTP_403_FORBIDDEN, "invalid_invite_code",
                       "邀请码不对，找管理员要一个")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(status.HTTP_409_CONFLICT, "username_taken", "用户名已被占用")
    db.refresh(user)
    return ok(_token_payload(user))


@router.post("/login")
def login(payload: LoginIn, db=Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    # 用户不存在和密码错误给同一个提示，避免被用来枚举用户名
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "invalid_credentials",
                       "用户名或密码错误")
    if not user.is_active:
        raise ApiError(status.HTTP_403_FORBIDDEN, "account_disabled", "账号已被停用")
    return ok(_token_payload(user))


@router.get("/me")
def me(user=Depends(current_user)):
    return ok({"id": user.id, "username": user.username, "created_at": user.created_at})
