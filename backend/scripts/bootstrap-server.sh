#!/usr/bin/env bash
# 一键把刷题系统跑起来（服务器上以 root 运行）
#
# 用法：
#   cd /srv/quiz/backend
#   sudo bash scripts/bootstrap-server.sh
#
# 它只做五件事，**不碰** nginx / 宝塔面板（那些在宝塔界面里点）：
#   1. 检查 Python ≥ 3.10
#   2. 内存不足 3G 且没 swap 时，加一个 2G 的 /swapfile（1G 机器必需）
#   3. 建 .venv 并装 requirements.txt
#   4. 生成 .env（已存在则跳过，按内存自动调判题并发）
#   5. 注册并启动 systemd 服务 quiz.service（只监听 127.0.0.1:8000）
#
# 重复执行是安全的：swap、用户、venv、.env 都有「已存在就跳过」的判断。

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$(cd "$APP_DIR/.." && pwd)/web"
SERVICE_USER="quizrun"
SERVICE_NAME="quiz"
PORT=8000

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "${EUID:-0}" -eq 0 ]] || die "请用 root 运行：sudo bash $0"
[[ -f "$APP_DIR/requirements.txt" ]] || die "找不到 $APP_DIR/requirements.txt，脚本要放在 backend/scripts/ 下"
[[ -f "$WEB_DIR/index.html" ]] || die "找不到网页版前端 $WEB_DIR/index.html"

# ---------------------------------------------------------------- 1. Python
PY=""
for cand in python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" >/dev/null 2>&1 \
       && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$cand"
        break
    fi
done

if [[ -z "$PY" ]]; then
    die "没有 Python 3.10+。
  Ubuntu/Debian:   apt update && apt install -y python3 python3-venv python3-pip
  Alibaba Cloud Linux / CentOS:  dnf install -y python3.11 python3.11-pip"
fi
say "Python: $("$PY" --version 2>&1)（$PY）"

# ---------------------------------------------------------------- 2. swap
MEM_MB=$(awk '/^MemTotal:/{printf "%d", $2/1024}' /proc/meminfo)
SWAP_MB=$(awk '/^SwapTotal:/{printf "%d", $2/1024}' /proc/meminfo)

if [[ "$MEM_MB" -lt 3072 && "$SWAP_MB" -lt 1024 && ! -f /swapfile ]]; then
    say "物理内存 ${MEM_MB}MB，创建 2G /swapfile"
    fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    say "swap 已启用：$(free -h | awk '/Swap/{print $2}')"
else
    say "内存 ${MEM_MB}MB / swap ${SWAP_MB}MB，跳过 swap"
fi

# ---------------------------------------------------------------- 3. 运行用户
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    say "创建系统用户 $SERVICE_USER（不登录、只用来跑服务）"
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# ---------------------------------------------------------------- 4. venv
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    say "创建虚拟环境 .venv"
    "$PY" -m venv "$APP_DIR/.venv" \
        || die "创建 venv 失败：Ubuntu 请先 apt install -y python3-venv"
fi
say "安装依赖（首次约 1–2 分钟）"
"$APP_DIR/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# ---------------------------------------------------------------- 5. .env
ENV_FILE="$APP_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    say "生成 .env（按 ${MEM_MB}MB 内存选判题参数）"
    SECRET=$("$PY" -c 'import secrets; print(secrets.token_hex(32))')
    WORKERS=2; MEM_LIMIT=256; STEPS=800
    if [[ "$MEM_MB" -lt 2048 ]]; then
        WORKERS=1; MEM_LIMIT=128; STEPS=400
        warn "内存 < 2G：判题并发设为 1、单进程上限 128MB（想放开就升配后改 .env）"
    fi
    cat > "$ENV_FILE" <<EOF
QUIZ_ENV=prod
QUIZ_DEBUG=false
QUIZ_JWT_SECRET=$SECRET
QUIZ_DATABASE_URL=sqlite:///$APP_DIR/data/app.db
QUIZ_WEB_DIR=$WEB_DIR
QUIZ_JUDGE_WORKERS=$WORKERS
QUIZ_JUDGE_MEMORY_MB=$MEM_LIMIT
QUIZ_JUDGE_TIMEOUT=6
QUIZ_TRACE_MAX_STEPS=$STEPS
QUIZ_TRACE_TIMEOUT=5
QUIZ_REGISTER_CODE=
QUIZ_RATE_LIMIT_PER_MINUTE=120
QUIZ_RATE_LIMIT_AUTH_PER_MINUTE=10
QUIZ_SEED_ON_START=true
QUIZ_BEIAN=
EOF
    chmod 600 "$ENV_FILE"
else
    warn ".env 已存在，跳过（要改参数就编辑 $ENV_FILE）"
fi

mkdir -p "$APP_DIR/data"
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/data"
chmod 750 "$APP_DIR/data"

# ---------------------------------------------------------------- 6. systemd
say "注册 systemd 服务 $SERVICE_NAME"
cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Python Quiz System (FastAPI)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
# workers 必须是 1：判题是进程内线程池，多开会重复消费队列 + 抢写 SQLite
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=full
ReadWritePaths=$APP_DIR/data

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
systemctl restart "$SERVICE_NAME"

sleep 3
if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    say "后端已启动 ✅  http://127.0.0.1:$PORT/healthz 正常"
else
    warn "后端没起来，看日志：journalctl -u $SERVICE_NAME -n 50 --no-pager"
fi

# ---------------------------------------------------------------- 7. 下一步
cat <<TIP

────────────────────────────────────────────────────────────
后端已经在 127.0.0.1:$PORT 上跑起来了。还差对外访问这一步：

【A. 宝塔面板点几下】
  1. 软件商店 → 安装 Nginx（1G 内存够用，别装 MySQL/PHP）
  2. 网站 → 添加站点，域名先填你的公网 IP（如 47.108.140.52）
  3. 站点设置 → 反向代理 → 目标 URL 填 http://127.0.0.1:$PORT
  4. 保存后访问 http://47.108.140.52/ 应该看到登录浮层

【B. 阿里云安全组放行】
  80/tcp  0.0.0.0/0
  443/tcp 0.0.0.0/0
  8888/tcp 只填你自己的 IP（面板不要对全网开）

【C. 备案通过后】
  1. 域名加 A 记录指向这台机器
  2. 宝塔 → 站点 → SSL → Let's Encrypt 一键申请
  3. 编辑 .env 填 QUIZ_BEIAN=你的备案号，然后 systemctl restart $SERVICE_NAME
     （页面左下角会自动出现备案号并链接到工信部）

常用命令：
  systemctl status $SERVICE_NAME        # 看状态
  journalctl -u $SERVICE_NAME -f        # 看日志
  systemctl restart $SERVICE_NAME       # 改完 .env 重启
────────────────────────────────────────────────────────────
TIP
