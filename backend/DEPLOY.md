# 上线部署手册 · 单机版（香港 / 海外节点）

> 目标：把这套刷题系统**长期**挂在公网上，同学用浏览器就能刷，进度按账号各存各的。
> 场景前提：**不想备案** → 服务器选香港或海外节点（备案只针对中国大陆节点）。

- 组成：`caddy`（公网 80/443，**自动签 HTTPS**）+ `api`（FastAPI，只在 Docker 内网）+ 可选 `worker`（独立判题进程）
- 数据：SQLite 单文件在 `/data` 卷里，备份就是拷一个文件
- 判题：每次提交都在**独立子进程**里跑，超时 kill、POSIX 下有内存/CPU/写盘上限

```
浏览器 ──HTTPS──> caddy ──> api:8000 ──subprocess──> 学习者代码
                                    │
                                    └─ /data/app.db
```

---

## 0. 先选机器

| 配置 | 能扛多少 | 价格参考 | 说明 |
|---|---|---|---|
| **2 核 2G**（推荐起步） | 同时 20–30 人在线刷题 | 香港轻量 ¥288–500/年 | 只跑 `api + caddy`，`QUIZ_JUDGE_WORKERS=2` |
| 2 核 4G | 50 人左右 | ¥600–900/年 | 再加 `worker` 容器 |
| Oracle 永久免费 ARM（4 核 24G） | 上百人 | 0 元 | 注册玄学、实例可能被回收，务必开自动备份 |

**关键**：判题吃的是 CPU 和内存，不是带宽。2G 内存里要留 ~512MB 给两个判题子进程、
~300MB 给 uvicorn 和 SQLite，所以**别买 1 核 1G**（会被 OOM 杀掉）。

系统选 **Ubuntu 22.04 / 24.04**（Docker 官方支持最好）。

---

## 1. 装 Docker

```bash
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

国内机器拉镜像慢的话配个加速（香港/海外机器通常不需要）：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{ "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"] }
JSON
sudo systemctl restart docker
```

---

## 2. 拉代码

```bash
sudo mkdir -p /srv && cd /srv
git clone https://github.com/telling890/python-quiz-system.git quiz
cd quiz
```

> 不 clone 也行，`rsync` 上传整个目录即可，但**必须包含** `backend/` 和 `web/`
> —— 镜像要同时打包后端和网页版前端（`backend/Dockerfile` 用的是仓库根作为构建上下文）。

---

## 3. 配置

```bash
cd /srv/quiz/backend
cp .env.example .env
nano .env
```

必须改的三处：

1. **`QUIZ_JWT_SECRET`** —— 不换等于谁都能伪造令牌：
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **`QUIZ_ENV=prod`**（`.env.example` 默认是 `dev`）。
3. **`QUIZ_REGISTER_CODE`** —— 填一个只有你们班知道的邀请码。
   不填的话，网址一旦被转发出去，就会有人注册进来白嫖你的 CPU 跑代码。

按机器内存调判题并发（**内存要先够**）：

```bash
# 2G 机器
QUIZ_JUDGE_WORKERS=2
# 4G 机器
QUIZ_JUDGE_WORKERS=4
```

---

## 4. 起服务

### 4.1 快速路径：一键脚本（1G / 宝塔机器推荐）

机器上已经有宝塔面板、又只有 1G 内存时，**别用 Docker**（Docker + Caddy 白吃 150–250MB），
直接用脚本跑 systemd 服务：

```bash
cd /srv/quiz/backend
sudo bash scripts/bootstrap-server.sh
```

脚本会自动：检查 Python ≥3.10 → 内存 <3G 时加 2G swap → 建 `.venv` 装依赖 →
按内存生成 `.env`（1G 机器判题并发自动降到 1、单进程 128MB）→ 注册 `quiz.service`
并启动（只监听 `127.0.0.1:8000`）。重复执行安全，`.env` 已存在就跳过。

它**不碰** nginx：对外访问在宝塔里加个反向代理指向 `http://127.0.0.1:8000` 就行。

### 4.2 Docker 路径（2G 以上）

```bash
cd /srv/quiz/backend

# 2G 机器别开 worker 容器（两个 1g 的容器会打架）
docker compose up -d --build api caddy

# 4G 以上再考虑把判题拆出去
# docker compose up -d --build api worker caddy
```

第一次要装依赖，2–4 分钟。检查：

```bash
docker compose ps                     # api / caddy 都是 running (healthy)
docker compose logs --tail 20 api     # 看到 "判题 worker 已启动"
curl -s https://pyquit.fun/healthz    # 经 caddy，返回 {"ok":true,...}
```

浏览器打开 `http://你的服务器IP/`，验收四项：

1. 出现深色登录浮层（`web/auth.js` 注入的），点「注册并登录」建第一个账号
2. 主页四个统计卡片、章节进度正常
3. 随便点一题，写 `print(1)` 运行 → 判题结果有红绿反馈
4. 点「单步执行」→ 时间轴能拖、变量能看到

**四项都过 = 部署成功。**

---

## 5. 日常运维

```bash
docker compose logs -f api        # 应用日志（每条请求一行）
docker compose logs -f caddy      # 访问日志 + 证书状态
```

升级：

```bash
cd /srv/quiz && git pull
cd backend && docker compose up -d --build
```

数据库在 volume 里，重建镜像不会丢。

备份（强烈建议加 cron）：

```bash
chmod +x backup.sh
./backup.sh                       # 先手动试一次
crontab -e
# 每天 3:07，保留 14 天
7 3 * * * /srv/quiz/backend/backup.sh >> /var/log/quiz-backup.log 2>&1
```

恢复：

```bash
gunzip -c backups/app-20260101-030700.db.gz > /tmp/restore.db
docker compose cp /tmp/restore.db api:/data/app.db
docker compose restart api
```

> 备份只有几 MB，**顺手 rsync 到另一台机器或对象存储**才算真安全。

---

## 6. 域名与 HTTPS（你的情况：pyquit.fun 已买好）

**先澄清一个常见误解：不备案 ≠ 不能用域名。** 备案只约束大陆节点；服务器在香港/海外，
域名买来直接解析就能用，不需要任何审批。

`pyquit.fun` 目前的实际状态（已核实）：

- 注册商 / DNS：阿里云（NS 是 `dns23.hichina.com` / `dns24.hichina.com`）
- A 记录：**还没配**，所以现在访问域名是不通的
- 证书：**还没有**，等 Caddy 起来自动签

### 6.1 加解析（阿里云控制台，2 分钟）

阿里云 → 域名 → `pyquit.fun` → **解析设置** → 添加记录：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---|---|---|---|
| A | `@` | 你的服务器公网 IP | 600（10 分钟） |
| A | `www` | 同一个 IP（**可选**，见下方注意） | 600 |

> ⚠️ `www` 先别急着加进 `Caddyfile`：Caddy 会给站点块里所有名字**一起签一张证书**，
> www 的解析没生效时整张证书都会失败，站点直接打不开。等 `ping www.pyquit.fun`
> 能通之后，再把 `Caddyfile` 第一行的 `pyquit.fun {` 改成 `pyquit.fun, www.pyquit.fun {`。

验证（在你自己的电脑上）：

```bash
nslookup pyquit.fun        # 要返回你的服务器 IP
nslookup www.pyquit.fun
```

> 解析生效通常 1–10 分钟。**先等它通了再做下一步**，否则 Caddy 申请证书会失败，
> 而 Let's Encrypt 对失败次数有频率限制（每小时 5 次），反复重试会被临时封。

### 6.2 放行端口（两处都要改）

- **阿里云安全组**：入方向允许 TCP **80**、**443**（还有 22 给 SSH）
- **机器防火墙**：`sudo ufw allow 80,443/tcp`（如果开了 ufw）

80 必须开：Let's Encrypt 的 HTTP-01 验证要访问它。

### 6.3 起服务（Caddy 自动签证书）

`docker-compose.yml` 默认已经是 Caddy，域名写在 `Caddyfile` 里：

```caddyfile
pyquit.fun, www.pyquit.fun {
	encode zstd gzip
	reverse_proxy api:8000
	...
}
```

所以只要：

```bash
cd /srv/quiz/backend
docker compose up -d --build api caddy
docker compose logs -f caddy | grep -iE "certificate|obtained|error"
```

看到 `certificate obtained successfully` 就成了。Caddy 会自己续期，不用配 cron。

### 6.4 验收

```bash
curl -I https://pyquit.fun          # 期望 200，且有 strict-transport-security 头
curl -s https://pyquit.fun/healthz  # {"ok":true,...}
```

浏览器打开 `https://pyquit.fun/`：地址栏有锁、能注册登录、能判题 → 完成。

顺便把 `http://pyquit.fun` 也点一下，应该自动 301 跳到 https。

### 6.5 备用路线：坚持用 nginx

Caddy 的短板是**没有内置按 IP 限流**（`limit_req` 是 nginx 有的）。
如果你更看重这一条，可以把 compose 里的 `caddy` 注释掉、换成注释里的 `nginx`，然后：

```bash
sudo apt install -y certbot
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d pyquit.fun -d www.pyquit.fun
```

再在 `nginx.conf` 里补一个 443 的 server 块指向
`/etc/letsencrypt/live/pyquit.fun/fullchain.pem`，续期交给 `certbot renew` 的 systemd timer。
**注意：应用本身已有按 IP 的滑窗限流**，所以 nginx 这层限流属于加分项，不是必需。

### 6.6 两个要记住的事

1. **实名认证**：阿里云注册的域名必须完成实名认证，否则会被 `serverHold` 停解析。
   控制台里看到「已实名」就行；没实名的话 .fun 也可能解析不了。
2. **续费价**：`.fun` 这类新顶级域首年便宜、**续费通常一两百一年**，
   比 `.com` 的续费贵不少。现在就把续费价看清楚，开自动续费，或者趁有多年优惠直接买 3 年。

---

## 7. 安全清单（判题 = 执行陌生人的代码，逐条对照）

| 项 | 现状 | 为什么 |
|---|---|---|
| 非 root 运行 | ✅ `USER quiz` | 逃出沙箱也拿不到 root |
| 禁止提权 | ✅ `no-new-privileges` + `cap_drop: ALL` | 第二道锁 |
| 根文件系统只读 | ✅ `read_only: true` + `tmpfs /tmp` | 改不了镜像里的代码 |
| 端口收敛 | ✅ 只有 caddy 暴露 80/443 | api 只在 Docker 内网 |
| 判题资源上限 | ✅ `QUIZ_JUDGE_TIMEOUT` / `MEMORY_MB` / `pids_limit` | 一个死循环拖不垮全站 |
| 邀请码 | 需自己配 `QUIZ_REGISTER_CODE` | 防陌生人注册跑代码 |
| 限流 | ✅ 应用内滑窗（`QUIZ_RATE_LIMIT_*`） | 防刷、防爆破；要 nginx 那层再换代理 |
| JWT 密钥 | 需自己换 `QUIZ_JWT_SECRET` | 否则可伪造任意用户 |
| 备份 | 需自己配 cron | SQLite 单文件，删了就没了 |
| HTTPS | ✅ Caddy 自动签发 + 强制跳转 | 密码不能明文过网 |

**已知边界（不假装做到）**：沙箱是「rlimit + 子进程 + 非 root」，**没有网络隔离和文件系统隔离**，
学习者代码理论上仍能访问外网。要彻底关死，下一步是把判题容器化
（一次性容器 + `--network=none` + 只挂临时目录），`judge/worker.py` 的注释里预留了方向。

---

## 8. 容量参考（2 核 2G，worker=2）

| 指标 | 数值 |
|---|---|
| 同时在线浏览 | 30–50 人没问题（静态页面 + 轻量接口） |
| 同时判题 | 2 个并发，其余排队 |
| 单次判题 | 每用例约 60–150ms，通常 1–4 个用例 |
| 磁盘 | 139 题 + 记录，一年也就几十 MB |

想加并发就调 `QUIZ_JUDGE_WORKERS`，但要同时放大 `docker-compose.yml` 里的
`mem_limit`，而且**先确认物理内存够**（每 worker 峰值 256MB）。

---

## 9. 故障排查

| 现象 | 处理 |
|---|---|
| `api` 一直 restarting | `docker compose logs api`；最常见是 `.env` 里 `QUIZ_JWT_SECRET` 没填 |
| 打开首页 404 | 多半是还在用`nginx.conf` 的旧版本（`location /` 曾是 `return 404`）；本仓库已改成反代到 api，用 Caddy 则不会出现 |
| 502 Bad Gateway | api 没起来或还 unhealthy：`docker compose exec caddy wget -qO- http://api:8000/healthz` |
| 证书签不下来 | 80 端口没放行 / A 记录还没生效 / 反复重试被 Let's Encrypt 限流（等 1 小时）。先 `nslookup pyquit.fun` 确认解析到你机器 |
| 登录后立刻被踢回登录页 | 反代没传 `X-Forwarded-Proto`；确认用的是本仓库的 `Caddyfile` / `nginx.conf` |
| 判题总是「运行超时」 | 机器太慢或 `QUIZ_JUDGE_TIMEOUT` 太小；也可能内存不足被 OOM，`dmesg \| tail` 确认 |
| 单步执行很慢 | 正常：开追踪会把执行放慢 5–10 倍，所以上限设了 800 步 |
| 提交后一直 queued | 判题线程没起来：日志里应有「判题 worker 已启动」；只起了 worker 容器而没起 api 也会这样 |

---

## 10. 大陆节点备案（服务器在国内才需要）

香港/海外节点**不用**备案；一旦服务器是阿里云/腾讯云的大陆节点（如成都、青岛、北京），
域名必须 ICP 备案，否则云厂商会阻断该域名的 80/443 —— 表现是「IP 能开、域名打不开」。

### 10.1 三个前置条件（缺一不可）

| 条件 | 怎么确认 |
|---|---|
| 域名可备案后缀 | 在备案系统里输入域名，**提示"该后缀不支持备案"就是不能备**（`.fun` 这类新顶级域要特别确认） |
| 域名已实名 | 阿里云 → 域名 → 基本信息，实名状态「已实名」且与备案主体一致 |
| 服务器包年包月且剩余 ≥ 3 个月 | 按量付费、剩余不足 3 个月都不行；还要先申请**备案服务号**（每台包年包月 ECS 可申请若干个） |

### 10.2 个人备案：网站名称怎么写

这是最容易被打回的一项。个人备案**不能**出现"教育、培训、学院、题库、在线课程、XX网/XX门户"等
需要前置审批或容易被判定为经营性内容的词。

- ❌ `Python 刷题系统`、`XX在线题库`、`XX教育`
- ✅ `个人技术学习笔记`、`学习记录`、`XX的技术博客`

首页标题如果写着"刷题系统"，审核时也可能被追问，建议备案期间把 `web/index.html` 的
`<title>` 改中性一点，过了再改回来。

### 10.3 流程与时间

1. 阿里云 → 备案 → 新增备案 → 选备案服务号
2. 填主体（身份证、手机、邮箱、住址）+ 网站信息（名称、域名、服务内容选「其他/个人空间」）
3. 上传证件 + **App 人脸核验**
4. 阿里云初审 1–2 天 → 管局审核 **7–20 天**
5. 通过后：域名加 A 记录 → 配 HTTPS → **在 `.env` 里填 `QUIZ_BEIAN=你的备案号`** 并重启，
   页面左下角会自动出现备案号并链接到 `beian.miit.gov.cn`（法律要求，不能省）

### 10.4 备案期间怎么办

- 先用 `http://服务器IP/` 跑起来（IP 访问不受备案限制），功能自测、答辩演示都够用
- **域名先别解析**：解析了也打不开，还可能被扫描到并提示
- 备案通过前**不要**折腾证书：证书能签，但 80/443 被拦，签了也用不了

### 10.5 首页标题顺带提醒

`.fun` / `.icu` / `.xyz` 这类后缀的备案支持情况会变，买域名前先在备案系统里验一遍再付款，
比事后换域名便宜得多。

---

## 11. 成本小结

| 项 | 年成本 |
|---|---|
| 香港轻量 2 核 2G | ¥288–500 |
| 域名（可选） | ¥10–60 |
| HTTPS 证书 | 0（Let's Encrypt 自动续） |
| **合计** | **约 ¥300–560/年，或 0（Oracle 免费 ARM）** |

---

## 附：本机（Windows）先跑一遍

上线前确认代码没问题：

```powershell
cd quiz_app\backend
py -3.10 -m pip install -r requirements.txt -r requirements-dev.txt
py -3.10 -m pytest -q                       # 全量测试，含判题与单步执行
py -3.10 -m uvicorn app.main:app --port 8000
# 浏览器打开 http://127.0.0.1:8000/
```

> 桌面版 `python main.py` 里的「网页版」走的是 `webserver.py`，那条路**没有账号体系**
> （单人本机用），和本文档部署的服务端不是一套。两者共用同一个 `web/index.html`，
> 服务端只是多注入了 `auth.js`。
