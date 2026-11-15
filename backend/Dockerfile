# ---------------------------------------------------------------------------
# 新前端（React 18 + Vite + TypeScript + Tailwind）：先构建，再把产物拷进镜像
# 构建上下文是仓库根：
#   cd backend && docker compose build
# 或在仓库根：docker build -f backend/Dockerfile -t python-quiz .
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /web
# 先只拷依赖清单，源码变了也能复用这一层缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# 产物在 /web/dist，由下面运行阶段拷到 /app/frontend/dist
RUN npm run build


FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# 老网页版前端：服务端在 "/" 上把它发出去（并注入登录脚本 web/auth.js）
COPY web ./web
# 新前端（React SPA）：服务端挂在 "/app"，SPA 路由回退到 index.html
COPY --from=frontend /web/dist ./frontend/dist

# 非 root 运行；判题会执行用户代码，权限越小越好
RUN useradd --create-home --uid 10001 quiz \
    && mkdir -p /data /tmp/judge \
    && chown -R quiz:quiz /data /tmp/judge /app
USER quiz

ENV QUIZ_DATABASE_URL=sqlite:////data/app.db \
    QUIZ_JUDGE_TMP=/tmp/judge \
    QUIZ_WEB_DIR=/app/web \
    QUIZ_FRONTEND_DIR=/app/frontend/dist \
    QUIZ_SEED_ON_START=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).status == 200 else 1)"

# 注意：判题线程跟着进程走，默认单进程；workers 必须是 1
# （多进程会重复消费同一份提交队列，且多个进程抢写同一个 SQLite）。
# 要横向扩容就多开副本（提交走数据库认领，不会重复判）。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--workers", "1"]
