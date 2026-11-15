# -*- coding: utf-8 -*-
"""统一响应格式与错误约定。

成功：{"ok": true, "data": ...}
失败：{"ok": false, "error": {"code": "...", "message": "..."}}
所有接口都遵守这一条，前端只需要写一次解包逻辑。
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def ok(data=None):
    return {"ok": True, "data": data}


class ApiError(Exception):
    """业务错误：带上机器可读的 code，方便前端分支处理。"""

    def __init__(self, status_code, code, message):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code, code, message, request=None):
    body = {"ok": False, "error": {"code": code, "message": message}}
    if request is not None:
        rid = getattr(request.state, "request_id", "")
        if rid:
            body["error"]["request_id"] = rid
    return JSONResponse(status_code=status_code, content=body)


async def api_error_handler(request: Request, exc: ApiError):
    return error_response(exc.status_code, exc.code, exc.message, request)


async def http_error_handler(request: Request, exc: HTTPException):
    code = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
            405: "method_not_allowed", 409: "conflict", 413: "payload_too_large",
            415: "unsupported_media_type", 422: "validation_error",
            429: "rate_limited"}.get(exc.status_code, "http_error")
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code,
                            content={"ok": False, "error": dict(detail)})
    return error_response(exc.status_code, code, str(detail), request)


async def validation_error_handler(request: Request, exc):
    errors = exc.errors() if hasattr(exc, "errors") else []
    first = errors[0] if errors else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    message = "{}: {}".format(loc or "请求体", first.get("msg", "参数不合法"))
    return error_response(422, "validation_error", message, request)


async def unhandled_error_handler(request: Request, exc: Exception):
    from .config import get_settings

    message = "服务端内部错误"
    if get_settings().debug:
        message = "{}: {}".format(type(exc).__name__, exc)
    return error_response(500, "internal_error", message, request)
