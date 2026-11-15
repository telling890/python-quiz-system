# Python 刷题系统 · 后端服务

把原来的「单机工具」升级成**多用户 Web 服务**：账号登录、每人独立的进度、异步判题、
代码片段、限流与健康检查。前端（桌面版 / 网页版）通过 HTTP 调用它。

原来的 `webserver.py` 是单进程 `http.server` + 一个 `state.json`，只够一台电脑自己用；
这里换成了正经的服务端结构，但刻意**没有引入重框架之外的东西**：

| 关注点 | 方案 | 为什么 |
|---|---|---|
| Web 框架 | FastAPI 0.116 | 自带 OpenAPI 文档、Pydantic 校验、依赖注入 |
| 数据库 | SQLAlchemy 2.0 + SQLite（可换 PostgreSQL） | 换库只改一个环境变量 |
| 认证 | 手写 HS256 JWT + PBKDF2 密码哈希 | 少两个依赖，逻辑透明，20 万次迭代够用 |
| 判题 | **独立子进程** + 超时 kill + 输出上限 + POSIX rlimit | 学习者代码拿不到本项目的模块，炸不到 API |
| 队列 | 数据库认领（`UPDATE ... WHERE status='queued'`） | 多进程 / API+worker 分容器都不会重复判题 |
| 部署 | Docker + Compose + Caddy | 一条命令起来，权限收窄，HTTPS 自动签发 |

---

## 一、目录结构

```
backend/
├── app/
│   ├── main.py               # FastAPI 入口：路由、中间件、异常、生命周期
│   ├── config.py             # 配置（QUIZ_* 环境变量）
│   ├── db.py                 # 引擎 / 会话 / 建表 / WAL
│   ├── models.py             # User Question Record Submission Snippet FreeDraft
│   ├── schemas.py            # Pydantic 请求响应模型
│   ├── security.py           # PBKDF2 密码 + HS256 JWT + current_user 依赖
│   ├── errors.py             # 统一 {ok, data} / {ok, error} 信封
│   ├── ratelimit.py          # 进程内滑动窗口限流
│   ├── serializers.py        # ORM → dict
│   ├── seed.py               # 启动灌题库
│   ├── data/questions.json   # 从桌面版 qbank.py 导出的 139 道题
│   ├── judge/
│   │   ├── compare.py        # 输出归一化与首行差异（与桌面版一致）
│   │   ├── child_runner.py   # 子进程里执行学习者代码
│   │   ├── trace_runner.py   # 子进程里做「单步执行」追踪（同样隔离）
│   │   ├── executor.py       # 起子进程、计时、杀进程树、读结果
│   │   ├── worker.py         # 线程池 + 数据库认领
│   │   └── worker_entry.py   # 独立 worker 进程入口
│   └── routers/              # auth / bank / submissions / snippets / legacy / imports
├── scripts/
│   ├── export_bank.py        # 从 qbank.py 重新导出题库
│   └── import_state.py       # 把桌面版 state.json 导进服务端（命令行）
├── tests/                    # 67 个测试（接口集成 + 旧网页版接口 + 单步执行 + 进度导入 + 前端挂载）
├── Dockerfile                # 多阶段构建：先构建 frontend/，再把 web/ 与 frontend/dist 一起打进镜像
├── docker-compose.yml        # api + worker + caddy
├── Caddyfile                 # 反代 + 自动 HTTPS（域名写在这里：pyquit.fun）
├── nginx.conf                # 备选：需要 limit_req 按 IP 限流时替换 Caddy
├── DEPLOY.md                 # 上线部署手册（香港/海外节点、HTTPS、备份、排查）
├── backup.sh                 # SQLite 在线备份（可挂 cron）
└── requirements.txt
```

> `routers/legacy.py` 是给 `web/index.html` 用的兼容层（`/api/*`，无版本号）：
> 让原来的网页版一行不改就跑在多用户后端上。前端彻底切到 `/api/v1` 之后可以整体删掉。

---

## 二、快速开始

```powershell
cd quiz_app\backend
py -3.10 -m pip install -r requirements.txt

# 开发模式（自动重载）
py -3.10 -m uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 就是完整的交互式 API 文档。
数据库默认落在 `backend/app/data/app.db`，首次启动自动建表并灌入 139 道题。

> 注意：本机 `python` 是 3.8，FastAPI 这套跑在 **3.10** 上，命令里写的是 `py -3.10`。

跑测试：

```powershell
py -3.10 -m pip install -r requirements-dev.txt
py -3.10 -m pytest -q
```

测试会起一个真实 uvicorn（随机端口）、真发 HTTP、真跑子进程判题，覆盖：
注册登录、重复用户名、错误密码、401/422 错误格式、题库结构、判题通过/失败/超时/报错、
**沙箱里 import 不到项目模块**、多用户隔离、片段增删改查、草稿、限流窗口、
旧网页版 `/api/*` 兼容层的字段形状、单步执行的步数/变量/超时/危险调用拦截、
以及 `state.json` 导入的幂等性与「不覆盖新进度」。

---

## 三、接口一览

统一前缀 `/api/v1`，统一信封：

```json
{"ok": true,  "data": { ... }}
{"ok": false, "error": {"code": "validation_error", "message": "password: ..."}}
```

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/healthz` | 否 | 健康检查（含数据库连通性） |
| POST | `/api/v1/auth/register` | 否 | 注册，返回 token（201） |
| POST | `/api/v1/auth/login` | 否 | 登录，返回 token |
| GET | `/api/v1/auth/me` | 是 | 当前用户 |
| GET | `/api/v1/bank` | 是 | 题库 + 章节 + 当前用户统计 |
| GET | `/api/v1/questions/{qid}` | 是 | 单题详情（含用例与我的记录） |
| GET | `/api/v1/progress` | 是 | 统计 + 学习记录 |
| POST | `/api/v1/progress/{qid}/favorite` | 是 | 收藏 / 取消收藏 |
| POST | `/api/v1/submissions` | 是 | 提交判题，**202** 返回 id |
| GET | `/api/v1/submissions/{id}` | 是 | 轮询判题结果 |
| GET | `/api/v1/submissions?limit=20` | 是 | 最近提交 |
| POST | `/api/v1/run` | 是 | 自由编程，同步返回输出 |
| GET/POST | `/api/v1/snippets` | 是 | 代码片段列表 / 新增或覆盖 |
| DELETE | `/api/v1/snippets/{name}` | 是 | 删除片段（中文名需 URL 编码） |
| GET/PUT | `/api/v1/free` | 是 | 自由编程草稿 |
| POST | `/api/v1/import/state` | 是 | 导入桌面版 `state.json`（幂等合并） |
| GET | `/` | 否 | 网页版前端（服务端在这里注入 `auth.js`） |
| GET | `/auth.js` | 否 | 登录浮层 + 令牌注入脚本 |

认证方式：请求头 `Authorization: Bearer <token>`，token 默认 7 天有效。

### 网页版兼容接口（`/api/*`，无版本号）

`web/index.html` 原本对接的是桌面版 `webserver.py`，这里把那一套**原样实现**了一遍，
响应形状完全一致（**注意**：旧接口错误里的 `error` 是字符串，不是对象），全部要求登录：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/bank` | 题库 + 章节 + 我的进度（字段与 `webserver.py` 一致） |
| GET / POST | `/api/free` | 自由编程草稿：读取 / 保存 |
| GET | `/api/snippets` | 我的全部片段 |
| POST | `/api/snippet` | 保存片段；带 `{name, delete:true}` 则删除 |
| POST | `/api/run` | 带 `qid` → 逐用例判题；不带 → 自由运行 |
| POST | `/api/trace` | 单步执行：把代码逐行走一遍并返回每一步 |
| POST | `/api/attempt` | 记一次作答，返回最新统计与本题记录 |

### 一条完整链路

```powershell
$base = "http://127.0.0.1:8000"

# 1. 注册
$r = Invoke-RestMethod "$base/api/v1/auth/register" -Method Post -ContentType application/json `
     -Body '{"username":"alice","password":"secret-pass-123"}'
$h = @{ Authorization = "Bearer " + $r.data.token }

# 2. 看题库
$bank = Invoke-RestMethod "$base/api/v1/bank" -Headers $h
$bank.data.stats
$bank.data.questions[0].id

# 3. 判题（异步）
$s = Invoke-RestMethod "$base/api/v1/submissions" -Method Post -Headers $h -ContentType application/json `
     -Body '{"qid":"3-01","code":"print(1+1)"}'
Start-Sleep 2
Invoke-RestMethod "$base/api/v1/submissions/$($s.data.id)" -Headers $h
```

---

## 四、判题是怎么隔离的

这是这次重构最关键的一点。桌面版 `judge.py` 在主进程里 `exec`，学生代码可以
`import qbank` 直接读答案、`open("../data/state.json","w")` 改自己进度、`while True` 卡死界面。
现在每一次「跑代码」都是：

1. 新建临时工作目录，写入 `main.py` / `stdin.txt`；
2. 用 `python -I -B -S child_runner.py <workdir>` 起**独立进程**（隔离模式、不加载 site-packages、不写 pyc、不读用户环境变量）；
3. 父进程 `wait(timeout)`，超时立刻 `taskkill /T /F`（Windows）或 `killpg`（POSIX）杀**整棵进程树**；
4. 子进程只把 `{output, error, truncated}` 写进 `result.json`，父进程截断到 4 万字符；
5. POSIX（Docker/Linux）下额外加 `RLIMIT_AS`（内存）、`RLIMIT_CPU`（CPU）、`RLIMIT_FSIZE`（写盘）上限；
6. 工作目录跑完全部用例后 `rmtree`。

因此：

- `import qbank` 会 `ModuleNotFoundError`（测试里专门验证了这一点）；
- `while True: pass` 会在 `QUIZ_JUDGE_TIMEOUT` 秒后被 kill，状态记为 `timeout`；
- 无限打印只会让输出被截断，不会把 API 进程内存吃光；
- 内存炸弹在 Linux/Docker 下被 rlimit 挡住，**Windows 本机没有 rlimit**，靠 Docker 的
  `mem_limit` 兜底 —— 这一点是已知限制，没有假装做到。

真实生产建议再套一层：把判题容器换成 `nsjail`/`gVisor`/Firecracker，或每判一题起一个一次性的
受限容器。本项目给出的是「够用且明显安全于原来」的版本。

---

## 五、配置

全部用 `QUIZ_` 前缀的环境变量（或 `backend/.env`，参考 `.env.example`）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `QUIZ_ENV` | `dev` | `prod` 时检查默认 JWT 密钥 |
| `QUIZ_DATABASE_URL` | `sqlite:///.../backend/app/data/app.db` | 换 PostgreSQL 填 `postgresql+psycopg://...` |
| `QUIZ_JWT_SECRET` | 开发默认值 | **生产必须改**，`openssl rand -hex 32` |
| `QUIZ_TOKEN_TTL_MINUTES` | `10080` | token 有效期（7 天） |
| `QUIZ_JUDGE_TIMEOUT` | `6` | 单用例超时秒数 |
| `QUIZ_JUDGE_MEMORY_MB` | `256` | POSIX 下的内存上限 |
| `QUIZ_JUDGE_WORKERS` | `2` | 判题线程数 |
| `QUIZ_TRACE_TIMEOUT` | `5` | 单步执行的超时秒数 |
| `QUIZ_TRACE_MAX_STEPS` | `800` | 单步执行最多录多少步 |
| `QUIZ_REGISTER_CODE` | 空 | 注册邀请码；留空 = 任何人可注册 |
| `QUIZ_WEB_DIR` | `仓库根/web` | 网页版静态目录（Docker 里是 `/app/web`） |
| `QUIZ_RATE_LIMIT_PER_MINUTE` | `120` | 普通接口，每 IP |
| `QUIZ_RATE_LIMIT_AUTH_PER_MINUTE` | `10` | 登录/注册，每 IP |
| `QUIZ_CORS_ORIGINS` | 空 | 前端单独部署时填地址，逗号分隔 |
| `QUIZ_SEED_ON_START` | `true` | 空库时灌题库 |

---

## 六、部署

完整流程（选机器 → 装 Docker → 配置 → 起服务 → 域名/HTTPS → 备份 → 排查）见
[`DEPLOY.md`](DEPLOY.md)，这里只列组成：

```powershell
cd quiz_app\backend
cp .env.example .env                          # 改 QUIZ_JWT_SECRET / QUIZ_ENV / QUIZ_REGISTER_CODE
docker compose up -d --build api caddy       # 2G 机器；4G 以上再加 worker
```

- `api`：正式进程，同时也是网页版的宿主（`/` 跳新前端 `/app`，旧页面在 `/legacy`）；非 root、只读根文件系统、`cap_drop: ALL`、`pids_limit`、`mem_limit`；
- `worker`：独立判题容器（`python -m app.judge.worker_entry`），和 API 共用数据库。**2G 机器别开**（两个 1g 容器会打架）；
- `caddy`：反代 `/`、`/auth.js` 和 `/api/*`，**自动申请并续期 HTTPS 证书**（域名写在 `Caddyfile`，当前是 `pyquit.fun`）。
  想用 nginx 的 `limit_req` 按 IP 限流，就把 compose 里的 `caddy` 换成注释中的 `nginx`，按 `DEPLOY.md` 6.5 补证书。

扩容：

- 多开 `api` 副本即可，提交靠数据库认领，不会重复判；
- 判题压力大就多开 `worker`；再加就把 `judge/worker.py` 的认领换成 Redis/RQ/Celery —— 接口层不用动。

**限流目前是进程内的**，多副本时每份各自计数；要全局精确限流，把 `ratelimit.py` 换成 Redis 版。

---

## 七、和桌面版的关系

- 题库：`scripts/export_bank.py` 从 `qbank.py` 导出 JSON 灌库，桌面版改了题就重新导出一次：
  ```powershell
  cd quiz_app
  py -3.10 backend/scripts/export_bank.py
  ```
- 进度：桌面版仍读写本地 `state.json`，服务端读写数据库；要搬家就用导入接口
  `POST /api/v1/import/state`（幂等合并，重复导入不会把次数翻倍）：

  ```powershell
  py -3.10 backend/scripts/import_state.py `
      --base http://127.0.0.1:8000 --user alice --password secret-pass-123
  ```

  `--file` 指定进度文件（默认 `quiz_app/data/state.json`），`--dry-run` 先看条数不发送。
  合并规则：作答次数取两边最大值，`last`/`code` 听次数多的一边（相等时保留服务端的），
  收藏取并集，片段同名的保留 `updated` 更新的，草稿只在服务端为空时填入；
  `exams`（组卷历史）没有对应表，跳过并报告条数。
- 旧网页版 `web/index.html` 调的是 `/api/*` 且不带 token，本来和新接口不兼容。
  现在由 `routers/legacy.py` 原样兼容，服务端在 `/legacy` 返回页面时额外注入 `web/auth.js`
  （登录浮层 + 自动带 `Authorization`），**页面本身一行没改**；桌面版 `webserver.py`
  不加载 `auth.js`，所以单人本机的体验完全不受影响。

---

## 八、下一步可以做什么

1. 把网页版前端彻底切到 `/api/v1`（现在靠 `legacy.py` 兼容层，多一层转发）；
2. 老师/班级维度：`classes` 表 + 作业 + 排行榜；
3. 提交走 SSE 推送而不是轮询；
4. 判题容器化（每题目一个受限容器 + `--network=none`），替换掉现在的子进程方案；
5. 每 5 分钟自动备份 + 异地同步（现在 `backup.sh` 要自己挂 cron）。
