# -*- coding: utf-8 -*-
"""FastAPI 应用入口：装配路由、中间件、异常处理与生命周期。

启动：
    py -3.10 -m uvicorn app.main:app --reload --port 8000
或：
    py -3.10 -m app.main
"""

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import get_settings
from .db import init_db
from .errors import (ApiError, api_error_handler, error_response, http_error_handler,
                     unhandled_error_handler, validation_error_handler)
from .judge.worker import get_service
from .ratelimit import check
from .routers import auth, bank, imports, legacy, snippets, submissions

logger = logging.getLogger("quiz.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.is_dev and settings.jwt_secret.startswith("dev-secret"):
        logger.warning("生产环境请设置 QUIZ_JWT_SECRET，当前用的是开发默认密钥")
    init_db(seed=settings.seed_on_start)
    service = get_service()
    service.start()
    logger.info("判题 worker 已启动：%s 个线程", service.workers)
    try:
        yield
    finally:
        service.stop()
        logger.info("判题 worker 已停止")


def render_index(source, beian="", frontend_url=""):
    """把登录脚本（以及可选的 ICP 备案号 / 新版入口）注入 index.html。

    抽成独立函数只为了能单测：注入一旦坏了，站点会「能打开但登录不了」，
    比直接 500 难查得多。三个注入都是幂等的，重复调用不会注入两次。
    """
    text = source
    if "/auth.js" not in text:
        tag = '<script src="/auth.js"></script>'
        text = (text.replace("</head>", tag + "</head>", 1)
                if "</head>" in text else tag + text)

    frontend_url = (frontend_url or "").strip()
    if frontend_url and 'id="pyquiz-frontend-link"' not in text:
        pill = (
            '<a id="pyquiz-frontend-link" href="' + escape(frontend_url) + '"'
            ' style="position:fixed;right:10px;top:10px;z-index:9000;'
            "font:12px/1.4 -apple-system,'Segoe UI','Microsoft YaHei',sans-serif;"
            "color:#c7d2fe;text-decoration:none;background:rgba(79,70,229,.9);"
            'padding:5px 10px;border-radius:8px;border:1px solid #6366f1">试试新版界面 →</a>'
        )
        text = (text.replace("</body>", pill + "</body>", 1)
                if "</body>" in text else text + pill)

    beian = (beian or "").strip()
    if beian and 'id="pyquiz-beian"' not in text:
        badge = (
            '<a id="pyquiz-beian" href="https://beian.miit.gov.cn/" target="_blank"'
            ' rel="noopener noreferrer" style="position:fixed;left:10px;bottom:8px;'
            "z-index:9000;font:12px/1.4 -apple-system,'Segoe UI','Microsoft YaHei',sans-serif;"
            "color:#8b93a3;text-decoration:none;background:rgba(21,24,31,.85);"
            'padding:4px 8px;border-radius:8px;border:1px solid #2a2f3a">'
            + escape(beian) + "</a>"
        )
        text = (text.replace("</body>", badge + "</body>", 1)
                if "</body>" in text else text + badge)
    return text


def _mount_web(app, settings):
    """把仓库根的老网页版（web/）挂到 /legacy，/auth.js 仍留在根上。

    为什么要注入而不是改 index.html：同一个文件桌面版（webserver.py）也在用，
    桌面版是单人本机、没有账号体系，不能背上来一个登录浮层。

    为什么不再占用 `/`：`/` 现在让给新前端（构建过就跳 /app/，没构建就退回这里），
    这样「打开服务器地址」永远看到的是能用的界面，而不是一份 797 行的旧页面。

    返回 True 表示挂上了；没有静态目录时返回 False，调用方退回 JSON 首页。
    """
    web_dir = Path(settings.web_dir)
    index = web_dir / "index.html"
    if not index.is_file():
        logger.warning("没有找到网页版目录（%s），只提供 API", web_dir)
        return False

    def render_legacy():
        # 构建过新前端就在旧页面右上角挂一个入口；没构建就不显示，免得点进 404
        frontend_url = "/app/" if app.state.frontend_ready else ""
        html = index.read_text(encoding="utf-8")
        return HTMLResponse(render_index(html, settings.beian, frontend_url),
                            headers={"Cache-Control": "no-store"})

    @app.get("/legacy", include_in_schema=False, response_class=HTMLResponse)
    @app.get("/legacy/", include_in_schema=False, response_class=HTMLResponse)
    def web_index():
        return render_legacy()

    @app.get("/auth.js", include_in_schema=False)
    def web_auth_js():
        path = web_dir / "auth.js"
        if not path.is_file():
            raise HTTPException(404, "没有 auth.js")
        return FileResponse(str(path), media_type="application/javascript",
                            headers={"Cache-Control": "no-store"})

    app.state.render_legacy = render_legacy
    return True


def _mount_frontend(app, settings):
    """把新前端（frontend/ 构建产物）挂到 /app，老网页版仍然留在 /。

    - /app/assets/* 交给 StaticFiles：文件名带 hash，可以长缓存
    - /app 与 /app/<任意前端路由> 都返回 index.html，剩下的交给前端路由
      （vite base = /app/，BrowserRouter basename = /app）
    - 目录不存在（没跑过 npm run build）就整块跳过，不影响后端与老页面

    返回 True 表示挂上了。
    """
    root = Path(settings.frontend_dir).expanduser()
    index = root / "index.html"
    if not index.is_file():
        logger.info("没有找到前端构建产物（%s），/app 不可用：先 cd frontend && npm run build", root)
        return False

    root_resolved = root.resolve()
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/app/assets", StaticFiles(directory=str(assets)), name="frontend-assets")

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{path:path}", include_in_schema=False)
    def frontend(path: str = ""):
        if path:
            candidate = (root_resolved / path).resolve()
            try:
                inside = os.path.commonpath([str(root_resolved), str(candidate)]) == str(root_resolved)
            except ValueError:                       # 不同盘符
                inside = False
            if inside and candidate.is_file():
                return FileResponse(str(candidate))
        return FileResponse(str(index), media_type="text/html",
                            headers={"Cache-Control": "no-store"})

    logger.info("新前端已挂载：/app -> %s", root_resolved)
    return True


def create_app():
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Python 刷题系统的后端：账号、题库、进度、异步判题、代码片段。\n\n"
                    "**响应格式**：成功 `{ok: true, data: ...}`，失败 "
                    "`{ok: false, error: {code, message}}`。",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ------------------------------------------------------------ 中间件
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            max_age=600,
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = uuid.uuid4().hex[:12]
        request.state.request_id = rid

        if request.method != "OPTIONS":
            group = "auth" if request.url.path.startswith("/api/v1/auth") else "api"
            client = request.client.host if request.client else "unknown"
            allowed, retry_after = check(group, client)
            if not allowed:
                response = error_response(429, "rate_limited", "请求太频繁，请稍后再试", request)
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-Request-ID"] = rid
                return response

        started = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - started) * 1000

        response.headers["X-Request-ID"] = rid
        response.headers["X-Process-Time-Ms"] = "{:.1f}".format(elapsed)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        logger.info("%s %s %s %.1fms", request.method, request.url.path,
                    response.status_code, elapsed)
        return response

    # ------------------------------------------------------------ 异常
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    # ------------------------------------------------------------ 路由
    for router in (auth.router, bank.router, submissions.router, snippets.router,
                   imports.router):
        app.include_router(router, prefix="/api/v1")
    # 网页版旧接口 /api/*（web/index.html 用的那一套，已按用户隔离）
    app.include_router(legacy.router)

    # ------------------------------------------------------------ 网页版
    # 先挂新前端，老页面才知道要不要往右上角放「试试新版」入口
    app.state.frontend_ready = False
    has_frontend = _mount_frontend(app, settings)
    app.state.frontend_ready = has_frontend
    has_web = _mount_web(app, settings)

    # ------------------------------------------------------------ 首页
    @app.get("/", include_in_schema=False)
    def root():
        """打开服务器地址时给一份能用的界面。

        - 构建过新前端 → 307 跳到 /app/（首页就是 React 版）
        - 没构建（比如只跑了后端）→ 退回老网页版 /legacy 的内容
        - 两个都没有 → 返回一份 JSON 元信息，至少不是 404
        """
        if has_frontend:
            return RedirectResponse("/app/", status_code=307)
        if has_web:
            return app.state.render_legacy()
        return {"ok": True,
                "data": {"name": settings.app_name, "version": __version__,
                         "docs": "/docs", "health": "/healthz"}}

    # ------------------------------------------------------------ 运维
    @app.get("/healthz", tags=["ops"], summary="健康检查")
    def healthz():
        from sqlalchemy import text
        from .db import engine

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:                 # noqa: BLE001
            return JSONResponse(status_code=503,
                                content={"ok": False,
                                         "error": {"code": "db_unavailable",
                                                   "message": str(exc)}})
        return {"ok": True,
                "data": {"status": "ok", "version": __version__,
                         "judge_workers": get_service().workers,
                         "frontend": has_frontend, "legacy": has_web}}

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    s = get_settings()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=s.debug)
