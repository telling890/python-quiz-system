# -*- coding: utf-8 -*-
"""配置：全部走环境变量（前缀 QUIZ_），本地开发有安全默认值，生产必须覆盖。"""

import os
import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUIZ_", env_file=".env", extra="ignore")

    app_name: str = "Python Quiz API"
    env: str = "dev"
    debug: bool = False

    # 数据库：默认 SQLite（单文件、零运维）；生产用 QUIZ_DATABASE_URL=postgresql+psycopg://...
    database_url: str = "sqlite:///" + (DATA_DIR / "app.db").as_posix()

    # 认证
    jwt_secret: str = "dev-secret-change-me-please"
    token_ttl_minutes: int = 60 * 24 * 7          # 7 天
    password_iterations: int = 200_000

    # 判题
    judge_timeout: float = 6.0
    judge_memory_mb: int = 256
    judge_output_limit: int = 40_000
    judge_workers: int = 2
    judge_tmp: str = os.path.join(tempfile.gettempdir(), "quiz-judge")

    # 单步执行（追踪）
    trace_timeout: float = 5.0
    trace_max_steps: int = 800

    # 网页版静态文件目录（仓库根的 web/）；Docker 里用 QUIZ_WEB_DIR=/srv/web 覆盖
    web_dir: str = str(BASE_DIR.parent.parent / "web")

    # 新前端（React + Vite）构建产物目录；挂载在 /app。没构建过就当没有，不影响老页面
    frontend_dir: str = str(BASE_DIR.parent.parent / "frontend" / "dist")

    # 注册开关：留空 = 任何人都能注册；填了就要求带邀请码（公开站点建议填）
    register_code: str = ""

    # ICP 备案号：备案通过后填进来（如「蜀ICP备2026000001号-1」），
    # 服务端会把它渲染到页面左下角——法律要求必须展示并链接到工信部。
    beian: str = ""

    # 接口
    cors_origins: str = ""                          # 逗号分隔，如 https://quiz.example.com
    rate_limit_per_minute: int = 120                # 普通接口，每 IP
    rate_limit_auth_per_minute: int = 10            # 登录/注册，每 IP
    seed_on_start: bool = True

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self):
        return self.database_url.startswith("sqlite")

    @property
    def is_dev(self):
        return self.env.lower() in ("dev", "development", "local", "test")


@lru_cache
def get_settings():
    return Settings()
