# -*- coding: utf-8 -*-
"""新前端（React SPA）在 /app 上的挂载行为。

只测两个函数级行为，不启服务：
1. 构建产物存在时，/app 及其子路径都返回 index.html（前端路由靠它）；
2. 构建产物不存在时整块跳过，后端其余接口不受影响。
"""

import os
import sys

from fastapi import FastAPI

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import get_settings          # noqa: E402
from app.main import _mount_frontend         # noqa: E402


def _make_dist(root):
    dist = root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><body><div id=root>spa</div></body></html>", encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("console.log('hi')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    return dist


def test_mount_frontend_serves_spa(tmp_path):
    dist = _make_dist(tmp_path)
    settings = get_settings()
    original = settings.frontend_dir
    settings.frontend_dir = str(dist)
    try:
        app = FastAPI()
        assert _mount_frontend(app, settings) is True

        routes = {getattr(route, "path", ""): route for route in app.routes}
        assert "/app/{path:path}" in routes, routes.keys()

        endpoint = routes["/app/{path:path}"].endpoint
        # 根路径、前端路由（/app/practice/3-01）都要吐 index.html
        for path in ("", "practice/3-01", "book"):
            response = endpoint(path)
            assert response.status_code == 200
            assert "spa" in open(response.path, encoding="utf-8").read()

        # 静态资源按文件返回
        asset = endpoint("assets/index-abc123.js")
        assert asset.status_code == 200
        assert asset.path.endswith("index-abc123.js")

        # 想用 ../ 跳出目录的，一律退回 index.html（不泄露仓库文件）
        escape = endpoint("../requirements.txt")
        assert escape.path.endswith("index.html")
    finally:
        settings.frontend_dir = original


def test_mount_frontend_absent_is_harmless(tmp_path):
    settings = get_settings()
    original = settings.frontend_dir
    settings.frontend_dir = str(tmp_path / "nowhere")
    try:
        app = FastAPI()
        assert _mount_frontend(app, settings) is False
        paths = {getattr(route, "path", "") for route in app.routes}
        assert "/app/{path:path}" not in paths
    finally:
        settings.frontend_dir = original


def test_root_redirects_to_spa_when_built(tmp_path):
    """构建过前端时，打开服务器地址（/）应该直接进新界面，而不是旧页面。"""
    dist = _make_dist(tmp_path)
    settings = get_settings()
    original = settings.frontend_dir
    settings.frontend_dir = str(dist)
    try:
        from app.main import create_app

        app = create_app()
        routes = {getattr(route, "path", ""): route for route in app.routes}
        response = routes["/"].endpoint()
        assert response.status_code == 307
        assert response.headers["location"] == "/app/"
        # 旧页面挪到 /legacy，还能打开（auth.js 仍在根上）
        legacy_routes = {getattr(route, "path", "") for route in app.routes}
        assert "/legacy" in legacy_routes
        assert "/auth.js" in legacy_routes
    finally:
        settings.frontend_dir = original
