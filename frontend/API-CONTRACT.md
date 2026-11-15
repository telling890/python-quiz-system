# Python 刷题系统 · HTTP API 契约（前端对接用）

> 版本：后端 `app.__version__ = 1.0.0`
> 本文只描述**代码里真实存在**的行为。凡是标记说明：
>
> - **【实测】**：起了真实 uvicorn（随机端口）+ 真发 HTTP 请求抓下来的响应，原文贴出。
> - **【代码可证】**：从源码逐行读出，未单独跑请求验证。
> - **【代码中未体现，需实测】**：代码里查不到、依赖运行环境或未验证的，明确标注，不要当成契约用。
>
> 文档覆盖的前端可用端点共 **25 个**（按「方法 + 路径」唯一计）：
> `/api/v1/*` **17 个** + 旧兼容层 `/api/*` **8 个**；
> 另有 6 条非业务路由（`/`、`/auth.js`、`/healthz`、`/docs`、`/redoc`、`/openapi.json`），合计 31 条路由。

---

## 目录

1. [概览](#1-概览)
2. [端点总表](#2-端点总表)
3. [认证 /api/v1/auth](#3-认证-apiv1auth)
4. [题库 /api/v1/bank、/api/v1/questions](#4-题库)
5. [进度 /api/v1/progress](#5-进度)
6. [判题 /api/v1/submissions、/api/v1/run](#6-判题)
7. [片段与草稿 /api/v1/snippets、/api/v1/free](#7-代码片段与自由编程草稿)
8. [导入 /api/v1/import/state](#8-导入)
9. [单步追踪 /api/trace（仅旧层）](#9-单步追踪trace仅旧兼容层)
10. [旧兼容层 /api/* 全量](#10-旧兼容层-api-全量)
11. [非业务路由](#11-非业务路由)
12. [数据字典](#12-数据字典)
13. [前端兼容性注意点](#13-前端兼容性注意点)
14. [缺口：前端必须自己算的部分](#14-缺口前端必须自己算的部分)
15. [附录：结论出处](#15-附录结论出处)

---

## 1. 概览

### 1.1 Base URL

| 环境 | Base URL | 说明 |
|---|---|---|
| 本机开发 | `http://127.0.0.1:8000` | `py -3.10 -m uvicorn app.main:app --reload --port 8000` |
| 生产（仓库自带 Caddy） | `https://pyquit.fun` | Caddy 反代到 `api:8000`，自动 HTTPS |
| 容器内 | `http://api:8000` | 只有 Docker 内网可达 |
| Vite 开发服务器 | `http://127.0.0.1:5173` | `vite.config.ts` 已把 `/api` 代理到 `127.0.0.1:8000` |

前端**推荐用同源相对路径**（`/api/v1/...`）：既避开 CORS，也让 `Authorization` 头、`X-Request-ID` 这类头能被 JS 读到。

### 1.2 两套前缀：`/api/v1` 与 `/api`

| 维度 | `/api/v1/*`（正式） | `/api/*`（旧网页版兼容层） |
|---|---|---|
| 路由代码 | `routers/auth.py, bank.py, submissions.py, snippets.py, imports.py` | `routers/legacy.py` |
| 响应信封 | `{"ok":true,"data":...}` / `{"ok":false,"error":{code,message}}` | **没有 `data` 层**，字段直接在顶层；`ok` 也常在顶层 |
| 业务错误 | `error` 是**对象** `{code,message,request_id?}` | `error` 是**字符串**（如 `"代码是空的"`） |
| 认证失败错误 | `error` 对象 | **也是对象**（见 §10.3，两种形状混用，坑） |
| 判题方式 | 异步队列（202 + 轮询） | **同步**（一次请求等到结果） |
| 单步追踪 | **不存在** | `POST /api/trace` |
| 记录作答 | 由判题 worker 自动写 Record | 需显式 `POST /api/attempt` |
| 谁在用 | 新前端（推荐） | `web/index.html`（旧网页版，靠 `auth.js` 注入令牌） |
| 未来 | 长期保留 | 注释里写明「前端切到 v1 后可整体删掉」 |

> ⚠️ 关键结论：**`trace`（单步执行）只有旧层有**。新前端要做「执行过程」面板，必须调 `POST /api/trace`，并处理它「无信封 + `error` 字符串」的形状。

### 1.3 认证

**方式：纯 Bearer Token（请求头），没有任何 Cookie 参与。**

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIi...
```

| 项 | 值 | 出处 |
|---|---|---|
| 头名称 | `Authorization`（大小写不敏感） | `security.current_user(authorization: str = Header(default=""))` |
| 值格式 | `Bearer <token>`，`Bearer` **大小写不敏感**，中间可多个空格 | `_bearer()`：`authorization.split(None, 1)` + `parts[0].lower() != "bearer"` |
| Token 类型 | 手写 HS256 JWT，三段式 | `security.create_token` |
| payload | `{"sub":"<user_id 字符串>","name":"<username>","iat":<秒>,"exp":<秒>}` | 同左 |
| 有效期 | 默认 `QUIZ_TOKEN_TTL_MINUTES=10080` 分钟 = **7 天** = `604800` 秒 | `config.token_ttl_minutes` |
| 过期字段 | 登录/注册响应里的 `data.expires_in`（**秒**，实测 `604800`） | `auth._token_payload` |
| 刷新机制 | **没有 refresh token、没有续期端点**。过期只能重新登录 | 全仓库无 refresh 相关代码 |
| 登出 | **没有端点**。前端删本地 token 即可（令牌在服务端不可撤销） | 全仓库无 logout |
| 服务端校验 | 验签 + 验 `exp` + 查库确认用户存在且 `is_active` | `current_user` |
| 停用账号 | 停用后**立即** 401（每次都查库） | 同上 |
| 会话隔离 | 所有进度/草稿/片段/提交按 `user_id` 过滤 | 各 router |

**缺少/无效令牌的响应（实测）：**

```
HTTP/1.1 401 Unauthorized
content-type: application/json
x-request-id: ff4f3b2c30b7
x-process-time-ms: 0.7
x-content-type-options: nosniff
x-frame-options: DENY
```

```json
{
  "ok": false,
  "error": {
    "code": "unauthorized",
    "message": "缺少 Bearer 令牌",
    "request_id": "ff4f3b2c30b7"
  }
}
```

令牌无效/过期时 `message` 为 `"令牌无效或已过期"`，`code` 仍是 `unauthorized`；
用户被停用时 `message` 为 `"用户不存在或已停用"`，`code` 仍是 `unauthorized`。

> 【实测】虽然 `security.py` 给 401 的异常挂了 `headers={"WWW-Authenticate": "Bearer"}`，
> 但 `errors.http_error_handler` 走的是 `error_response()`，**不透传 headers**，
> 所以实际响应里**没有** `WWW-Authenticate`。不要依赖它做浏览器原生认证弹窗。

### 1.4 响应信封

**成功：**

```json
{ "ok": true, "data": { "...": "..." } }
```

**失败：**

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "username: String should have at least 3 characters",
    "request_id": "ea33e3a66298"
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | bool | 唯一可靠的成败标志 |
| `data` | any | 仅成功时存在；`data` 可能是对象/数组/null |
| `error.code` | string | 机器可读枚举，见 §1.5 |
| `error.message` | string | 给人看的中文文案（部分为英文，来自 Pydantic / Starlette） |
| `error.request_id` | string? | 12 位十六进制的请求 ID，与服务端日志、响应头 `X-Request-ID` 一致；由中间件写入 `request.state`，因此**几乎总会出现** |
| HTTP 状态码 | — | 与 `ok` 语义一致；**不要只看 body**，`202` 也是成功 |

> 例外：`/healthz` 的 503 分支走裸 `JSONResponse`，形状是
> `{"ok":false,"error":{"code":"db_unavailable","message":"..."}}`（没有 `request_id`）。

### 1.5 错误码枚举（完整）

来源：`errors.py` 的 `http_error_handler` 映射表 + 各 router 里显式 `ApiError(...)` + `legacy._fail`。

| HTTP | `error.code` | 触发场景 | 出处 |
|---|---|---|---|
| 400 | `invalid_name` | `POST /api/v1/snippets` 且 `name` 去空白后为空 | `routers/snippets.py` |
| 400 | `invalid_state` | `POST /api/v1/import/state`：`questions` 不是对象 / 请求体不是对象 | `routers/imports.py` |
| 400 | `bad_request` | 通用 400 映射（当前无业务代码直接抛 400 + 该 code） | `errors.py` |
| 401 | `unauthorized` | 缺令牌 / 令牌无效 / 令牌过期 / 用户被停用 | `security.current_user` |
| 401 | `invalid_credentials` | 登录用户名或密码错误（不区分是哪一个） | `routers/auth.py` |
| 403 | `invalid_invite_code` | 服务端配了 `QUIZ_REGISTER_CODE` 且请求 `code` 不匹配 | `routers/auth.py` |
| 403 | `account_disabled` | 登录时 `is_active=false` | `routers/auth.py` |
| 403 | `forbidden` | 通用 403 映射 | `errors.py` |
| 404 | `not_found` | 路径不存在（Starlette 404 被统一映射） | `errors.py` |
| 404 | `question_not_found` | `/questions/{qid}`、`/submissions` 带未知 qid、收藏未知 qid | bank/submissions |
| 404 | `submission_not_found` | 提交不存在**或不属于当前用户**（不泄露存在性） | `routers/submissions.py` |
| 404 | `snippet_not_found` | `DELETE /api/v1/snippets/{name}` 未命中 | `routers/snippets.py` |
| 405 | `method_not_allowed` | 方法不对（如 `PUT /api/v1/bank`、`GET /api/v1/progress/{qid}/favorite`） | `errors.py` |
| 409 | `username_taken` | 注册时用户名已存在 | `routers/auth.py` |
| 413 | `state_too_large` | 导入的 `questions` 条数 > 2000 | `routers/imports.py` |
| 413 | `payload_too_large` | 通用 413 映射 | `errors.py` |
| 415 | `unsupported_media_type` | 通用 415 映射 | `errors.py` |
| 422 | `validation_error` | Pydantic 校验失败；`message` 形如 `"<字段路径>: <原因>"`，路径里 `body` 前缀被去掉，query 参数会保留 `query.` 前缀 | `errors.validation_error_handler` |
| 429 | `rate_limited` | 触发限流（见 §1.6），另带 `Retry-After: 60` | `main.request_context` |
| 500 | `internal_error` | 未捕获异常；`QUIZ_DEBUG=true` 时 `message` 会带上异常类型与内容，否则固定 `"服务端内部错误"` | `errors.unhandled_error_handler` |
| 503 | `db_unavailable` | `/healthz` 里数据库连不上（此分支无 `request_id`） | `main.healthz` |
| 其它 | `http_error` | 以上都没命中的 HTTPException | `errors.py` |

**422 文案实例（实测）：**

```json
{"ok":false,"error":{"code":"validation_error",
 "message":"username: String should have at least 3 characters",
 "request_id":"ea33e3a66298"}}
```

```json
{"ok":false,"error":{"code":"validation_error",
 "message":"code: String should have at least 1 character",
 "request_id":"b42511908e6c"}}
```

```json
{"ok":false,"error":{"code":"validation_error",
 "message":"query.limit: Input should be greater than or equal to 1",
 "request_id":"15a531a07bd0"}}
```

### 1.6 限流规则

实现：`ratelimit.py` 进程内滑动窗口（60 秒窗口），`main.request_context` 在每个请求前调用。

| 分组 | 命中条件（按 URL path 前缀） | 默认阈值（每分钟） | 环境变量 |
|---|---|---|---|
| `auth` | `path` 以 `/api/v1/auth` 开头 | **10** | `QUIZ_RATE_LIMIT_AUTH_PER_MINUTE` |
| `api` | 其余**所有**路径（含 `/api/*`、`/healthz`、`/`、`/auth.js`、`/docs`） | **120** | `QUIZ_RATE_LIMIT_PER_MINUTE` |

- `OPTIONS` 请求**不计数**（预检永远放行）。
- 超限返回 **429**，`error.code = "rate_limited"`，并带 `Retry-After: 60`（秒）。
- 429 响应**只有** `X-Request-ID`，没有 `X-Process-Time-Ms`（它在限流分支提前返回）。

实测（把 `QUIZ_RATE_LIMIT_PER_MINUTE` 调成 3 后连打 `/api/v1/bank`）：

```json
{"ok":false,"error":{"code":"rate_limited","message":"请求太频繁，请稍后再试",
 "request_id":"83829bc1208f"}}
```

响应头：`retry-after: 60`、`x-request-id: 83829bc1208f`。

> **⚠️ 实现缺陷（非常重要，直接影响前端轮询频率）**：
> `ratelimit.check(name, key)` 的第二个参数 `key`（客户端 IP）**根本没有参与分桶** ——
> `_bucket(name, limit)` 只按分组名 `"auth"`/`"api"` 建**一个**滑窗。也就是说这是
> **每个进程全局配额**，不是 README 里写的「每 IP」。后果：
> - 全站所有用户共享 120 次/分钟；一个用户狂刷会让所有人 429；
> - 全站登录/注册共享 10 次/分钟（默认值下，第 11 次登录就 429）；
> - 前端轮询判题必须节流（建议 ≥ 500ms 间隔），并实现 429 退避重试；
> - 页面自身的静态资源也吃这份配额（`/`、`/auth.js` 都算）。
>
> 多副本部署时每副本各自计数（进程内 `deque`），不存在全局精确限流。

### 1.7 通用响应头

每个**非 429** 响应都会带（中间件统一加）：

| 头 | 值示例 | 说明 |
|---|---|---|
| `X-Request-ID` | `3c3bdc4d55b8` | 12 位十六进制，和 `error.request_id` 同源，报障时贴这个 |
| `X-Process-Time-Ms` | `60.6` | 服务端处理耗时（1 位小数，字符串） |
| `X-Content-Type-Options` | `nosniff` | |
| `X-Frame-Options` | `DENY` | 反代（Caddy）配的是 `SAMEORIGIN`，nginx 配 `DENY` |
| `Content-Type` | `application/json` | 唯一例外：`/` 返回 `text/html`，`/auth.js` 返回 `application/javascript` |

注意：

- 应用层**没有** `Access-Control-Expose-Headers`，所以跨域时 JS **读不到** `X-Request-ID` / `X-Process-Time-Ms`。
- 应用层**没有** gzip 中间件；压缩由 Caddy（`encode zstd gzip`）或 nginx（`gzip on`）做。直连 uvicorn 无压缩。

### 1.8 请求体大小与字段上限

应用层**没有全局 body 上限**，限制来自三层：

| 层 | 限制 | 出处 |
|---|---|---|
| Caddy | `request_body max_size 2MB` | `Caddyfile` |
| nginx | `client_max_body_size 8m` | `nginx.conf` |
| 应用字段级 | 见下表 | `schemas.py` |

字段级上限（`schemas.py`，Pydantic `max_length` 按**字符**计，不是字节）：

| 字段 | 上限 | 端点 |
|---|---|---|
| `username`（注册） | 3–32 | `POST /auth/register` |
| `username`（登录） | 1–32 | `POST /auth/login` |
| `password` | 8–128（注册）/ 1–128（登录） | auth |
| `code`（邀请码） | ≤ 64 | register |
| `code`（代码） | **1–20000** | `POST /submissions`、`POST /run` |
| `stdin` | ≤ 20000 | `POST /submissions`、`POST /run` |
| `qid` | ≤ 24 | `POST /submissions` |
| 片段 `name` | 1–80 | `POST /snippets` |
| 片段 `code` | ≤ **50000** | `POST /snippets` |
| 草稿 `code`/`stdin` | **无上限**（`FreeIn` 没加约束） | `PUT /free` |
| 导入 | `questions` ≤ 2000 条；每段代码截断到 20000；片段最多 500 个（超出静默丢弃）；`attempts/passes/fails` 夹到 0–1000000 | `POST /import/state` |

> `PUT /api/v1/free` 的 `code` 真的没有长度校验，只受反代 2MB 限制 —— 别把它当保险，前端自己限一下。

### 1.9 类型约定

| 类型 | 格式 | 示例 |
|---|---|---|
| 时间戳 | ISO-8601 UTC、秒精度、带 `+00:00`；字段名 `created_at`/`finished_at`/`updated` | `"2026-11-15T12:58:55+00:00"` |
| 「从未发生」的 time 字段 | **空字符串 `""`**（不是 null） | `finished_at: ""`、`updated: ""` |
| 提交 ID | `uuid4().hex`，32 位小写十六进制 | `"91da9c5d34bc4a1d99116070773ff94f"` |
| 题目 ID | 短字符串，最长的现库为 4 字符（如 `3-01`、`3-14`），DB 列 `String(24)` | `"3-06"` |
| 时间比较 | 后端对 `updated` 做**字符串比较**（导入合并用） | — |

---

## 2. 端点总表

### 2.1 `/api/v1/*`（17 个）

| # | 方法 | 路径 | 认证 | 成功码 | 说明 |
|---|---|---|---|---|---|
| 1 | POST | `/api/v1/auth/register` | 否 | **201** | 注册并直接返回 token |
| 2 | POST | `/api/v1/auth/login` | 否 | 200 | 登录返回 token |
| 3 | GET | `/api/v1/auth/me` | 是 | 200 | 当前用户 |
| 4 | GET | `/api/v1/bank` | 是 | 200 | **一次返回全部题目 + 章节 + 我的统计** |
| 5 | GET | `/api/v1/questions/{qid}` | 是 | 200 | 单题（含用例与我的记录） |
| 6 | GET | `/api/v1/progress` | 是 | 200 | 统计 + 每题记录 |
| 7 | POST | `/api/v1/progress/{qid}/favorite` | 是 | 200 | 收藏/取消收藏 |
| 8 | POST | `/api/v1/submissions` | 是 | **202** | 提交判题（异步） |
| 9 | GET | `/api/v1/submissions/{submission_id}` | 是 | 200 | 轮询判题结果 |
| 10 | GET | `/api/v1/submissions?limit=` | 是 | 200 | 最近提交列表 |
| 11 | POST | `/api/v1/run` | 是 | 200 | 自由编程**同步**跑一次 |
| 12 | GET | `/api/v1/snippets` | 是 | 200 | 片段列表 |
| 13 | POST | `/api/v1/snippets` | 是 | 200 | 新建或覆盖片段 |
| 14 | DELETE | `/api/v1/snippets/{name}` | 是 | 200 | 删除片段 |
| 15 | GET | `/api/v1/free` | 是 | 200 | 读自由编程草稿 |
| 16 | PUT | `/api/v1/free` | 是 | 200 | 存自由编程草稿 |
| 17 | POST | `/api/v1/import/state` | 是 | 200 | 导入桌面版 state.json |

### 2.2 `/api/*`（旧兼容层，8 个）

| # | 方法 | 路径 | 认证 | 成功码 | 说明 |
|---|---|---|---|---|---|
| 18 | GET | `/api/bank` | 是 | 200 | 同 #4，但**无 `data` 层** |
| 19 | GET | `/api/free` | 是 | 200 | 读草稿 |
| 20 | POST | `/api/free` | 是 | 200 | 存草稿 |
| 21 | GET | `/api/snippets` | 是 | 200 | 片段列表 |
| 22 | POST | `/api/snippet`（**单数**） | 是 | 200 | 存 / 删片段（`{delete:true}`） |
| 23 | POST | `/api/run` | 是 | 200 | 带 `qid` 判题，不带则自由运行（**同步**） |
| 24 | POST | `/api/trace` | 是 | 200 | **单步执行追踪（v1 没有对应端点）** |
| 25 | POST | `/api/attempt` | 是 | 200 | 记一次作答（v1 由判题 worker 自动记，故无需此端点） |

> 计数口径：按「方法 + 路径」唯一计。`/api/free` 的 GET/POST 算 2 个、`/api/v1/snippets` 的 GET/POST 算 2 个。
> 合计 **17 + 8 = 25** 个业务端点。

### 2.3 OpenAPI 里实际注册的路径（实测）

```
/api/attempt   /api/bank   /api/free   /api/run   /api/snippet   /api/snippets   /api/trace
/api/v1/auth/login   /api/v1/auth/me   /api/v1/auth/register
/api/v1/bank   /api/v1/free   /api/v1/import/state   /api/v1/progress
/api/v1/progress/{qid}/favorite   /api/v1/questions/{qid}   /api/v1/run
/api/v1/snippets   /api/v1/snippets/{name}   /api/v1/submissions
/api/v1/submissions/{submission_id}   /healthz
```

（`/`、`/auth.js`、`/docs`、`/redoc` 用 `include_in_schema=False` 或框架内置，不在里面。）

---

## 3. 认证 `/api/v1/auth`

### 3.1 `POST /api/v1/auth/register`

注册并直接发放令牌。**不需要认证。**

**请求体**

| 字段 | 类型 | 必填 | 约束 | 默认 | 说明 |
|---|---|---|---|---|---|
| `username` | string | 是 | 长度 3–32；先 `strip()`，之后必须满足 `value.replace("_","").replace("-","").isalnum()` | — | 允许字母（含中文？`isalnum()` 对中文返回 True）、数字、`_`、`-`；空格/标点不行 |
| `password` | string | 是 | 长度 8–128 | — | 明文传输（生产必须 HTTPS）；服务端 PBKDF2-SHA256、20 万次迭代 |
| `code` | string | 否 | 长度 ≤ 64 | `""` | 邀请码。**仅当服务端配了 `QUIZ_REGISTER_CODE` 才校验**；未配置时随便填/不填都行 |

**成功 `201`（实测）**

```json
{
  "ok": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6ImNhcHVzZXIiLCJpYXQiOjE3OTQ3NDc1MzUsImV4cCI6MTc5NTM1MjMzNX0.agTb5x4UT_j1jwuVYtkW4xVEzom9PtsfDsuOMsqpYjk",
    "expires_in": 604800,
    "user": {
      "id": 1,
      "username": "capuser",
      "created_at": "2026-11-15T12:58:55+00:00"
    }
  }
}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `data.token` | string | 后续所有请求的 Bearer 令牌 |
| `data.expires_in` | int | 有效期**秒数**（= `QUIZ_TOKEN_TTL_MINUTES * 60`，默认 604800） |
| `data.user.id` | int | 自增主键 |
| `data.user.username` | string | 已 `strip()` 后的用户名（和请求里的可能不同） |
| `data.user.created_at` | string | 注册时间 ISO-8601 |

**失败**

| 状态 | code | 场景 |
|---|---|---|
| 403 | `invalid_invite_code` | 服务端配了邀请码且 `code` 不匹配（`message:"邀请码不对，找管理员要一个"`） |
| 409 | `username_taken` | 用户名已占用（`message:"用户名已被占用"`） |
| 422 | `validation_error` | 用户名/密码长度或字符不合规 |
| 429 | `rate_limited` | 触发 auth 分组限流（**全站共享 10 次/分钟**） |

> 【代码中未体现，需实测】用户名唯一性由数据库唯一索引保证，SQLite 默认**区分大小写**，
> 因此 `Alice` 与 `alice` 很可能是两个账号 —— 前端不要假设大小写不敏感。

### 3.2 `POST /api/v1/auth/login`

**不需要认证。**

**请求体**

| 字段 | 类型 | 必填 | 约束 | 默认 |
|---|---|---|---|---|
| `username` | string | 是 | 1–32，**不 strip、不做格式校验** | — |
| `password` | string | 是 | 1–128 | — |

**成功 `200`（实测）**

```json
{
  "ok": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 604800,
    "user": { "id": 1, "username": "capuser", "created_at": "2026-11-15T12:58:55+00:00" }
  }
}
```

**失败**

| 状态 | code | 场景 |
|---|---|---|
| 401 | `invalid_credentials` | 用户不存在 **或** 密码错误（故意不区分，防枚举） |
| 403 | `account_disabled` | 账号 `is_active=false`（密码校验通过后才判） |
| 422 | `validation_error` | 缺字段/超长 |
| 429 | `rate_limited` | auth 分组限流 |

### 3.3 `GET /api/v1/auth/me`

**需要认证。** 无参数。

**成功 `200`（实测）**

```json
{
  "ok": true,
  "data": { "id": 1, "username": "capuser", "created_at": "2026-11-15T12:58:55+00:00" }
}
```

**失败**：401 `unauthorized`。适合放在前端启动时做「token 是否还有效」的探活（旧 `auth.js` 就是这么干的）。

---

## 4. 题库

### 4.1 `GET /api/v1/bank`

**需要认证。无任何 query 参数。**

> 【实测】`/api/v1/bank?chapter=ch3&q=abc&page=2` 返回的仍然是全部 **139** 题。
> **没有分页、没有章节筛选、没有关键字搜索、没有难度筛选** —— 后端不支持，全部由前端在内存里过滤。

一次返回：全部题目（含**测试用例**、参考答案、解析）+ 章节列表 + 当前用户统计。

**响应大小【实测】**：`159124` 字节（约 155 KB，139 题）。直连 uvicorn 不压缩；经 Caddy 有 gzip。

**成功 `200` 结构**

```json
{
  "ok": true,
  "data": {
    "questions": [ /* Question 数组，见 §12.1 */ ],
    "chapters": [ /* Chapter 数组，见 §12.2 */ ],
    "stats": { /* Stats，见 §12.3 */ }
  }
}
```

**题目排序**：按数据库列 `sort_order` 升序，`sort_order` 就是 `questions.json` 里的数组下标
（当前顺序：`ch3` 35 题 → `ch4` 17 → `ch5` 17 → `extra` 40 → `algo` 30）。

**真实单题对象（实测，第一题）**

```json
{
  "id": "3-01",
  "chapter_id": "ch3",
  "chapter": "第3章 程序控制结构",
  "no": 1,
  "title": "能否同时被 2 和 3 整除",
  "topic": "if / 逻辑运算",
  "level": 1,
  "desc": "输入一个整数，判断它能否同时被 2 和 3 整除：能则输出 Yes，否则输出 No。",
  "hint": "同时满足两个条件用 and 连接；也可以直接判断 n % 6 == 0。",
  "ref": "n = int(input())\nif n % 2 == 0 and n % 3 == 0:\n    print(\"Yes\")\nelse:\n    print(\"No\")\n",
  "explain": "能被 2 和 3 同时整除等价于能被 6 整除，判断 n % 6 == 0 更简洁。\n注意输入要用 int() 转换，字符串不能直接取余。",
  "source": "",
  "cases": [
    { "stdin": "12", "expect": "Yes" },
    { "stdin": "9",  "expect": "No"  },
    { "stdin": "6",  "expect": "Yes" }
  ],
  "last": "",
  "attempts": 0,
  "favorite": false,
  "code": ""
}
```

**字段全集（实测 `Object.keys`，共 17 个）**

| 字段 | 类型 | 含义 | 备注 |
|---|---|---|---|
| `id` | string | 题目编号，如 `3-01`、`3-14` | 主键，`String(24)` |
| `chapter_id` | string | 章节 ID：`ch3` / `ch4` / `ch5` / `extra` / `algo` | 用于筛选，**比 chapter 名更稳** |
| `chapter` | string | 章节全名，如 `"第3章 程序控制结构"` | 与 `chapters[].name` 一一对应 |
| `no` | int | 章节内序号（从 1 开始） | |
| `title` | string | 题目标题 | |
| `topic` | string | 知识点标签，如 `"if / 逻辑运算"`、`"循环嵌套 / 空格排版"` | 自由文本，**不是枚举** |
| `level` | int | 难度：`1` 入门 / `2` 进阶 / `3` 挑战 | 现库只有这三个值；映射文案在**前端**（旧网页版写死 `["","入门","进阶","挑战"][level]`） |
| `desc` | string | 题面（含 `\n`，前端要用 `white-space: pre-wrap`） | |
| `hint` | string | 提示（可能为空） | |
| `ref` | string | 参考答案代码（**完整可运行**） | 可能为空 |
| `explain` | string | 解析与易错点 | 可能为空 |
| `source` | string | 来源标注 | 现库全为空字符串 |
| **`cases`** | **array** | **测试用例全集（公开，无隐藏用例）** | 见下方专述 |
| `last` | string | 我的最近一次判题结果：`""` / `"pass"` / `"fail"` | 来自 `Record.last` |
| `attempts` | int | 我的作答次数 | `Record.attempts` |
| `favorite` | bool | 是否已收藏 | `Record.favorite` |
| `code` | string | 我**最近一次提交**的代码 | `Record.code`；便于「打开题目恢复上次代码」 |

**`cases[]` 元素结构（这是「题目是否含测试用例」的答案：含，且完全公开）**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `stdin` | string | 是 | 该用例的标准输入（多数为空串） |
| `expect` | string | 是 | 期望输出（**原始文本，可能多行**） |
| `raw` | bool | **否** | 仅在需要保留行首空格的题上出现；**出现即 `true`**。现库 338 个用例中只有 7 个带这个键（3 道图形排版题） |

> 前端提示：
> - `raw` 缺失时按「压缩空白 + 去空行」比对；`raw: true` 时只 `rstrip` 每行、保留行首空格。
>   这套归一化规则在服务端 `judge/compare.py` 里，前端若要本地预览必须自己复刻。
> - 用例是**明文**下发，所以「隐藏用例」在本项目不存在 —— 学生能直接看到期望输出。
> - 现库每道题 1–5 个用例（分布：1 个 × 34 题、2 个 × 30、3 个 × 61、4 个 × 9、5 个 × 5），没有空用例的题。

**我**需要的字段（不在题目里，要自己算）：

- 题目**没有** `chapter_short`（只有 `chapters[].short`）、**没有** `sort_order`、**没有** `tags[]`、
  **没有** `time_limit` / `memory_limit`、**没有** `pass_count` / `submit_count`（全站通过率这类字段不存在）。

**真实章节数组（实测）**

```json
[
  { "id": "ch3",   "name": "第3章 程序控制结构", "short": "第3章", "count": 35 },
  { "id": "ch4",   "name": "第4章 序列",         "short": "第4章", "count": 17 },
  { "id": "ch5",   "name": "第5章 字符串",       "short": "第5章", "count": 17 },
  { "id": "extra", "name": "拓展练习",           "short": "拓展",  "count": 40 },
  { "id": "algo",  "name": "进阶算法",           "short": "算法",  "count": 30 }
]
```

章节顺序 = 题目**首次出现**顺序（不是字典序、没有单独排序字段）。

**失败**：401 `unauthorized`；429 `rate_limited`。

### 4.2 `GET /api/v1/questions/{qid}`

单题详情。**需要认证。**

**路径参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `qid` | string | 题目 ID（如 `3-01`）。无格式校验，不存在则 404 |

**成功 `200`**：`data` 就是 §4.1 里的**单个 Question 对象**（字段完全一致，含 `cases`、`ref`、`explain`、我的 `last/attempts/favorite/code`）。

**失败**

| 状态 | code |
|---|---|
| 404 | `question_not_found`（`message:"没有这道题：<qid>"`） |
| 401 | `unauthorized` |

> 实务建议：`/bank` 已经把每道题的全部字段都下发了，所以**这个端点通常可以不用**；
> 只有在「不想一次拉 155 KB、想按需回源」时才值得调。它**没有任何 `/bank` 拿不到的字段**。

---

## 5. 进度

### 5.1 `GET /api/v1/progress`

**需要认证。无参数。**

**成功 `200`（实测，刚判过 2 道题的账号）**

```json
{
  "ok": true,
  "data": {
    "stats": {
      "total": 139,
      "solved": 1,
      "tried": 2,
      "favorite": 0,
      "attempts": 2,
      "passes": 1,
      "rate": 50
    },
    "records": [
      { "qid": "3-06", "attempts": 1, "passes": 1, "fails": 0,
        "last": "pass", "favorite": false, "updated": "2026-11-15T12:58:56+00:00" },
      { "qid": "3-01", "attempts": 1, "passes": 0, "fails": 1,
        "last": "fail", "favorite": false, "updated": "2026-11-15T12:58:56+00:00" }
    ]
  }
}
```

**`records[]` 字段**

| 字段 | 类型 | 含义 |
|---|---|---|
| `qid` | string | 题目 ID |
| `attempts` | int | 累计作答次数（判题+导入+旧接口 attempt 都算） |
| `passes` | int | 累计通过次数（同一题可通过多次） |
| `fails` | int | 累计失败次数 |
| `last` | string | `""` / `"pass"` / `"fail"`，最近一次结果 |
| `favorite` | bool | 是否收藏 |
| `updated` | string | 最后一次**判题**时间；**只有收藏、从未作答的记录会是 `""`**（收藏端点不写这个字段） |

> **注意**：`records[]` **不含 `code`**（即拿不到「上次提交的代码」）。
> 要恢复代码只能用 `/bank`（或 `/questions/{qid}`）里的 `question.code`。
> `records[]` 也**没有** `title`/`chapter`，必须回去和 `/bank` 的 `questions` join。
> `records[]` 的**顺序没有 `ORDER BY`**（代码里直接 `query(Record).filter(user_id==...)`），不要依赖。

**`stats` 语义（`serializers.stats_dict`，逐条对照）**

| 字段 | 计算 | 易错点 |
|---|---|---|
| `total` | `SELECT count(*) FROM questions` | 现为 139；与 `questions.length` 一致 |
| `solved` | `records.count(last == "pass")` | 是「**现在处于通过态**的题数」，不是「曾通过」 |
| `tried` | `records.count(attempts > 0)` | 只收藏没做过的**不计入** |
| `favorite` | `records.count(favorite)` | |
| `attempts` | `sum(record.attempts)` | 是**人次**，可远大于 `total` |
| `passes` | `sum(record.passes)` | 是**通过人次** |
| `rate` | `round(passes * 100 / attempts)`，`attempts==0` 时 0 | 是「通过率（人次口径）」，**不是**「完成率」；完成率请用 `solved/total` |

**失败**：401 `unauthorized`。

### 5.2 `POST /api/v1/progress/{qid}/favorite`

收藏 / 取消收藏。**需要认证。**

**请求体**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `favorite` | bool | 否 | `true` | 目标状态（幂等：传 `true` 两次结果一样） |

实测：直接发 `{}` 也会把题目设为已收藏。

**成功 `200`（实测）**

```json
{ "ok": true, "data": { "qid": "3-01", "favorite": true } }
```

**副作用**：若该题还没有记录，会**创建**一条 `Record`（`attempts=0, passes=0, fails=0, last="", code="", updated=""`）。
所以「收藏了但没做」的题会出现在 `/progress` 的 `records` 里，`updated` 是空串。

**失败**

| 状态 | code |
|---|---|
| 404 | `question_not_found` |
| 401 | `unauthorized` |
| 422 | `validation_error`（`favorite` 不是 bool） |

---

## 6. 判题

### 6.1 `POST /api/v1/submissions` —— 提交判题（**异步，返回 202**）

**需要认证。**

**请求体**

| 字段 | 类型 | 必填 | 约束 | 默认 | 说明 |
|---|---|---|---|---|---|
| `qid` | string \| null | 否 | ≤ 24 | `null` | 有值 → **题目判题模式**；空/缺省/全空白 → **自由运行模式**。有值但不存在 → 404，不会创建提交 |
| `code` | string | 是 | 1–20000 | — | Python 源码。空串/纯空白会被 422 拦掉（`min_length=1`） |
| `stdin` | string | 否 | ≤ 20000 | `""` | **只在自由运行模式生效**。题目判题模式下每个用例用自己的 `stdin`，这个字段被忽略 |

**成功 `202`（实测，注意状态码是 202，body 仍带 `ok:true`）**

```json
{
  "ok": true,
  "data": {
    "id": "91da9c5d34bc4a1d99116070773ff94f",
    "qid": "3-06",
    "status": "queued",
    "result": {},
    "error": "",
    "created_at": "2026-11-15T12:58:56+00:00",
    "finished_at": "",
    "duration_ms": 0
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.id` | string | 提交 ID（32 位 hex），拿去轮询 |
| `data.status` | string | 刚创建时**恒为** `"queued"` |
| `data.result` | object | 此时为 `{}` |
| `data.finished_at` | string | 此时为 `""` |
| 其余 | | 见 §12.4 Submission |

**失败**

| 状态 | code | 场景 |
|---|---|---|
| 404 | `question_not_found` | `qid` 非空但题库里没有 |
| 422 | `validation_error` | `code` 为空/超 20000 字符；`qid` 超 24；`stdin` 超 20000 |
| 401 | `unauthorized` | |
| 429 | `rate_limited` | 全站 120 次/分钟（注意判题轮询也会吃配额） |

**判题是同步还是异步？→ 异步。** 拿到 202 后必须轮询 §6.2。

### 6.2 `GET /api/v1/submissions/{submission_id}` —— 轮询结果

**需要认证**，且只能查自己的：别人的提交也返回 404（不泄露 ID 是否存在）。

**路径参数**：`submission_id`（32 位 hex 字符串）

**成功 `200` —— 判题通过（实测，真实响应）**

```json
{
  "ok": true,
  "data": {
    "id": "91da9c5d34bc4a1d99116070773ff94f",
    "qid": "3-06",
    "status": "passed",
    "result": {
      "mode": "judge",
      "passed": true,
      "status": "passed",
      "total": 1,
      "results": [
        {
          "index": 0,
          "stdin": "",
          "expect": "4550",
          "actual": "4550\n",
          "error": "",
          "timeout": false,
          "truncated": false,
          "expect_lines": ["4550"],
          "actual_lines": ["4550"],
          "status": "pass",
          "first_diff": null
        }
      ],
      "duration_ms": 0
    },
    "error": "",
    "created_at": "2026-11-15T12:58:56+00:00",
    "finished_at": "2026-11-15T12:58:56+00:00",
    "duration_ms": 0
  }
}
```

**成功 `200` —— 判题不通过（实测；注意 `total` 是 3，`results` 只有 1 条）**

```json
{
  "ok": true,
  "data": {
    "id": "78c9c8114c6f487d8b29af610abfc096",
    "qid": "3-01",
    "status": "failed",
    "result": {
      "mode": "judge",
      "passed": false,
      "status": "failed",
      "total": 3,
      "results": [
        {
          "index": 0,
          "stdin": "12",
          "expect": "Yes",
          "actual": "nope\n",
          "error": "",
          "timeout": false,
          "truncated": false,
          "expect_lines": ["Yes"],
          "actual_lines": ["nope"],
          "status": "fail",
          "first_diff": { "line": 1, "expect": "Yes", "actual": "nope" }
        }
      ],
      "duration_ms": 0
    },
    "error": "",
    "created_at": "2026-11-15T12:58:56+00:00",
    "finished_at": "2026-11-15T12:58:56+00:00",
    "duration_ms": 0
  }
}
```

**成功 `200` —— 自由运行模式（`qid:""`，实测）**

```json
{
  "ok": true,
  "data": {
    "id": "aa6aa78c914c425aba97e63a5b1b5b34",
    "qid": "",
    "status": "passed",
    "result": {
      "mode": "free",
      "passed": true,
      "status": "passed",
      "results": [],
      "run": {
        "output": "42\n",
        "error": "",
        "timeout": false,
        "truncated": false,
        "syntax": false,
        "duration_ms": 156
      },
      "duration_ms": 156,
      "error": ""
    },
    "error": "",
    "created_at": "2026-11-15T12:58:56+00:00",
    "finished_at": "2026-11-15T12:58:56+00:00",
    "duration_ms": 156
  }
}
```

**失败**

| 状态 | code |
|---|---|
| 404 | `submission_not_found`（不存在或不属于你） |
| 401 | `unauthorized` |
| 429 | `rate_limited` |

### 6.3 `GET /api/v1/submissions` —— 最近提交列表

**需要认证。**

**Query 参数**

| 参数 | 类型 | 必填 | 范围 | 默认 |
|---|---|---|---|---|
| `limit` | int | 否 | **1–100**（越界 → 422 `validation_error`，`message:"query.limit: Input should be greater than or equal to 1"`） | `20` |

**成功 `200`（实测）**

```json
{
  "ok": true,
  "data": {
    "items": [ /* Submission 数组，同上，按 created_at 倒序 */ ],
    "limit": 5
  }
}
```

- 只有当前用户的提交；按 `created_at DESC` 排序。
- **保留策略**：每次判题完成后会清理，**每用户只留最近 100 条**（`JudgeService._prune(keep=100)`），更早的被物理删除。
- 【代码中未体现，需实测】同一秒内创建的提交之间顺序不稳定（`created_at` 只到秒）。

**失败**：401、422、429。

### 6.4 `POST /api/v1/run` —— 自由编程，**同步**跑一次

**需要认证。这个端点不判题、不写进度、不进队列**：起一个子进程跑一遍就返回。

**请求体**（`FreeRunIn`）

| 字段 | 类型 | 必填 | 约束 | 默认 |
|---|---|---|---|---|
| `code` | string | 是 | 1–20000 | — |
| `stdin` | string | 否 | ≤ 20000 | `""` |

额外字段会被**静默忽略**（实测传 `{"code":"print(1)","qid":"3-01"}` 仍是 free 模式）。

**成功 `200`（实测）**

```json
{
  "ok": true,
  "data": {
    "mode": "free",
    "run": {
      "output": "42\n",
      "error": "",
      "timeout": false,
      "truncated": false,
      "syntax": false,
      "duration_ms": 147
    }
  }
}
```

**超时（实测，`QUIZ_JUDGE_TIMEOUT` 调成 2 后跑 `while True: pass`）**

```json
{ "ok": true, "data": { "mode": "free", "run": {
  "output": "", "error": "", "timeout": true,
  "truncated": false, "syntax": false, "duration_ms": 2700 } } }
```

`RunResult` 字段含义见 §12.8。

**失败**：401、422（`code` 空或超长）、429。**运行时错误不是 HTTP 错误** —— 代码报错也是 `200`，看 `run.error`。

### 6.5 判题子系统完整契约

#### 6.5.1 状态机

```
POST /submissions ──202──> status="queued"
                              │  （worker 从 DB 认领，UPDATE ... WHERE status='queued'）
                              ▼
                          status="running"
                              │
        ┌─────────────┬───────┴──────┬──────────────┐
        ▼             ▼              ▼              ▼
   "passed"      "failed"       "timeout"       "error"
   （终态）        （终态）         （终态）        （终态）
```

| `status` 取值 | 是否终态 | 含义 | 出现条件 |
|---|---|---|---|
| `queued` | 否 | 已入库，等 worker | 刚创建 / 服务重启后被 `_recover_stale` 打回（`running` 超过 10 分钟） |
| `running` | 否 | 正在判 | worker 已认领 |
| `passed` | **是** | 全部用例通过（或自由运行无异常） | |
| `failed` | **是** | 至少一个用例输出不符 | 仅题目判题模式 |
| `timeout` | **是** | 有用例超时（`QUIZ_JUDGE_TIMEOUT`，默认 6 秒/用例） | |
| `error` | **是** | 用例运行抛异常 / 语法错误 / 沙箱异常退出 | |

判状态聚类的优先级（`judge_question`）：`timeout` > `error` > (`passed` / `failed`)。

#### 6.5.2 前端轮询契约

```
1) 轮询 GET /api/v1/submissions/{id}
2) status ∈ {"queued","running"} → 还没好，继续等
3) status ∈ {"passed","failed","timeout","error"} → 终态，停
```

| 项 | 建议值 | 依据 |
|---|---|---|
| 起始间隔 | 300–500 ms | worker 线程 0.5s 轮询队列；单用例耗时约 60–150 ms（本机实测 150 ms 左右） |
| 建议退避 | 前 5 次 300ms，之后 1s | 限流是**全站** 120 次/分钟，轮询很吃配额 |
| 最长等待 | ≥ 60 s 再判超时 | 单题最多 5 个用例 × 6 秒超时 + 进程启动开销 |
| 服务端推送 | **无** SSE / WebSocket / 长轮询 | 全代码库无相关端点 |
| 终态后 | 需要新进度就再拉 `GET /progress` 或 `GET /bank` | 判题响应**不含**最新 stats |

**重要副作用**：题目判题（`qid` 非空）完成后，worker 会**自动**更新 `Record`：
`attempts += 1`；通过则 `passes += 1, last="pass"`，否则 `fails += 1, last="fail"`；
同时写入 `record.code = 本次代码`、`record.updated = 完成时间`。
所以 **v1 不需要也不存在「再调一次记进度」的接口**（旧层才有 `/api/attempt`）。
自由运行模式（`qid` 为空）**不写任何进度**。

#### 6.5.3 `result` 结构（判题模式，`mode:"judge"`）

| 字段 | 类型 | 说明 |
|---|---|---|
| `mode` | `"judge"` | |
| `passed` | bool | 全部用例是否通过 |
| `status` | string | `"passed"` / `"failed"` / `"timeout"` / `"error"`，与顶层 `data.status` 一致 |
| `total` | int | **题目用例总数**（不是 `results.length`！） |
| `results` | array | **已执行**的用例结果；**遇到第一个非 `pass` 就停**，所以可能少于 `total` |
| `duration_ms` | int | ⚠️ **判题模式下恒为 `0`**（缺陷，见 §6.5.6）。自由模式才是真实值 |

`results[]` 每一项（`CaseResult`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `index` | int | 用例序号，**从 0 开始**（UI 上要 +1） |
| `stdin` | string | 该用例输入 |
| `expect` | string | 期望输出原始文本 |
| `actual` | string | 实际输出原始文本（`print` 会带尾随 `\n`） |
| `error` | string | 该用例的异常摘要，如 `"ZeroDivisionError: division by zero"`；无异常为 `""` |
| `timeout` | bool | 该用例是否超时 |
| `truncated` | bool | 输出是否被截断（上限 40000 字符） |
| `expect_lines` | string[] | 归一化后的期望行（比对基准） |
| `actual_lines` | string[] | 归一化后的实际行 |
| `status` | string | `"pass"` / `"fail"` / `"timeout"` / `"error"` |
| `first_diff` | object \| null | `null` 表示无差异；否则 `{line, expect, actual}`，`line` **从 1 开始**，某一侧缺行时对应值为 `null` |

> 「通过率」前端要自己算：`results.filter(r => r.status === "pass").length / result.total`（分母用 `total`，别用 `results.length`）。

#### 6.5.4 `result` 结构（自由运行模式，`mode:"free"`）

| 字段 | 类型 | 说明 |
|---|---|---|
| `mode` | `"free"` | |
| `passed` | bool | `status === "passed"` |
| `status` | string | `"passed"`（无异常无超时）/ `"timeout"` / `"error"` |
| `results` | array | **恒为空数组** |
| `run` | object | `RunResult`，见 §12.8（含 `output`/`error`/`timeout`/`truncated`/`syntax`/`duration_ms`） |
| `duration_ms` | int | 与 `run.duration_ms` 相同 |
| `error` | string | 与 `run.error` 相同 |

判据：`timeout` → `"timeout"`；否则 `error` 非空 → `"error"`；否则 `"passed"`。

#### 6.5.5 执行环境与超时（前端需要知道的运行时事实）

| 项 | 值 | 出处 |
|---|---|---|
| 单用例超时 | `QUIZ_JUDGE_TIMEOUT`，默认 **6.0 秒** | `config.judge_timeout` |
| 单步追踪超时 | `QUIZ_TRACE_TIMEOUT`，默认 **5.0 秒**（父进程多给 2 秒收尾，即 ≤7s） | `config.trace_timeout` |
| 单步最大步数 | `QUIZ_TRACE_MAX_STEPS`，默认 **800 步** | `config.trace_max_steps` |
| 单次输出上限 | **40000 字符**（超出置 `truncated:true`） | `config.judge_output_limit` |
| 内存上限 | `QUIZ_JUDGE_MEMORY_MB`，默认 256MB；**只在 Linux/POSIX 生效**，Windows 靠容器限制 | `executor._sandbox_limits` |
| 执行方式 | 每次运行一个新临时目录 + `python -I -B -S child_runner.py`，超时 `taskkill /T /F`（Windows）或 `killpg`（POSIX） | `executor._execute` |
| 隔离强度 | 学习者代码 **import 不到本项目模块**（`import qbank` → `ModuleNotFoundError`）；**没有**网络/文件系统隔离 | README、`executor.py` 注释 |
| 并发 | 每进程最多 8 个沙箱子进程（信号量），判题线程默认 2 个 | `_MAX_SANDBOX=8`、`judge_workers=2` |
| 判题进程 | 与 API 同进程（默认）或独立容器（`python -m app.judge.worker_entry`），靠 DB 认领不会重复判 | `worker.py` |

#### 6.5.6 已知缺陷（不要在前端依赖这些）

| 缺陷 | 表现 | 影响 |
|---|---|---|
| `duration_ms` 恒 0 | 判题模式的 `result.duration_ms` 与 `data.duration_ms` 都是 `0` | **无法展示「本题耗时」**，除非用自由模式的 `run.duration_ms` 或自己前端计时 |
| 全局限流 | 见 §1.6，`check(name, key)` 未按 IP 分桶 | 轮询容易把全站配额吃光 |
| `updated` 可为空串 | 只收藏没作答的记录 `updated=""` | 排序/时间线要过滤空值 |
| 判题黑名单只在 trace | `trace_runner` 有 `os.system/os.popen/os._exit/subprocess/shutil.rmtree/ctypes` 黑名单，`child_runner`（判题/运行）**没有** | 见 §9.4，属安全边界认知，不影响前端字段 |

---

## 7. 代码片段与自由编程草稿

### 7.1 `GET /api/v1/snippets`

**需要认证。无参数。** 返回当前用户全部片段，按 `updated` **倒序**。

```json
{
  "ok": true,
  "data": {
    "snippets": [
      { "name": "快排", "code": "def qs(a): ...", "updated": "2026-11-15T12:58:56+00:00" }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `snippets[].name` | string | 片段名（每用户唯一，1–80 字符） |
| `snippets[].code` | string | 代码（≤ 50000 字符） |
| `snippets[].updated` | string | 最后保存时间；**导入进来的可能是 `"2025-01-02 10:00:00"` 这种非 ISO 格式**（原样保留桌面版的字符串，别用 `new Date()` 硬解析） |

### 7.2 `POST /api/v1/snippets`（新建或覆盖，同名即覆盖）

**需要认证。**

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `name` | string | 是 | 1–80；服务端 `strip()` 后为空 → 400 `invalid_name` |
| `code` | string | 否 | ≤ 50000，默认 `""` |

**成功 `200`（实测）**

```json
{ "ok": true, "data": { "created": true, "name": "快排" } }
```

同名再发一次 → `"created": false`（覆盖，不报错，也不返回 201/409）。

**失败**

| 状态 | code |
|---|---|
| 400 | `invalid_name`（`message:"片段名字不能为空"`） |
| 422 | `validation_error`（`name` 空串/超 80、`code` 超 50000） |
| 401 / 429 | |

> 只有 `name` + `created`，**不回传 `code`/`updated`**。要刷新列表请紧跟一次 `GET /snippets`（旧网页版就是这么做的）。

### 7.3 `DELETE /api/v1/snippets/{name}`

**需要认证。**

| 路径参数 | 说明 |
|---|---|
| `name` | 片段名。**中文/空格/特殊字符必须 `encodeURIComponent`**；名字里含 `/` 会破坏路由，建议前端在创建时禁止 `/` |

**成功 `200`（实测）**

```json
{ "ok": true, "data": { "removed": true, "name": "快排" } }
```

**失败**：404 `snippet_not_found`（`message:"没有这个片段：<name>"`）、401、429。

### 7.4 `GET /api/v1/free`

**需要认证。无参数。** 自由编程草稿（每人一份）。

```json
{
  "ok": true,
  "data": { "code": "print(1)", "stdin": "", "updated": "2026-11-15T12:58:56+00:00" }
}
```

从未保存过时返回**全空串**（不是 404）：

```json
{ "ok": true, "data": { "code": "", "stdin": "", "updated": "" } }
```

### 7.5 `PUT /api/v1/free`

**需要认证。**

| 字段 | 类型 | 必填 | 约束 | 默认 |
|---|---|---|---|---|
| `code` | string | 否 | **无长度校验** | `""` |
| `stdin` | string | 否 | **无长度校验** | `""` |

> 注意是 **PUT**（不是 POST）。整体覆盖，没有字段级合并。

**成功 `200`（实测）**

```json
{ "ok": true, "data": { "saved": true, "updated": "2026-11-15T12:58:56+00:00" } }
```

**失败**：401、422（字段类型不对）、429。

---

## 8. 导入

### 8.1 `POST /api/v1/import/state`

把桌面版 `state.json` 合并进服务端。**需要认证。幂等**（重复导入不会把次数翻倍）。

**请求体**：任意 JSON 对象，两种写法都接受【实测】

```json
{ "state": { "questions": {...}, "snippets": [...], "free": {...}, "exams": [...] } }
```

或直接把 `state.json` 当请求体：

```json
{ "questions": {...}, "snippets": [...], "free": {...}, "exams": [...] }
```

**`state` 结构（全部可选）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `questions` | object（**必须是对象**） | `{ "<qid>": {"attempts":int,"passes":int,"fails":int,"last":"pass"\|"fail"\|"","code":str,"favorite":bool,"updated":str} }` |
| `snippets` | array | `[{"name","code","updated"}]`，最多取前 500 个 |
| `free` | object | `{"code","stdin"}` |
| `exams` | array | 组卷历史；**服务端没有对应表，直接跳过，只在结果里报条数** |
| `version` 等 | any | 忽略 |

**合并规则（`routers/imports.py` 逐行）**

| 规则 | 细节 |
|---|---|
| 只导入题库里**存在**的 qid | 未知 qid 计入 `skipped` |
| `attempts`/`passes`/`fails` | 取**两边最大值**（不会累加，重复导入安全）；`passes`/`fails` 进一步被 `min(…, attempts)` 夹住 |
| `last` / `code` | 谁 `attempts` 多听谁的；**相等时保留服务端已有的**（导入不会倒退）；服务端 `last` 为空时也接受导入值 |
| `favorite` | **取并集**（`服务端 or 导入`） |
| `updated` | 取字符串更大的那个（原样保存，ISO 与 `"2025-01-02 10:00:00"` 混用） |
| `snippets` | 按名字对齐；同名时只有导入的 `updated` 更大才覆盖 |
| `free` | **只在服务端草稿为空时**填入，绝不覆盖网页上新写的草稿 |
| `exams` | 忽略，仅计数 |

**成功 `200`（实测）**

```json
{
  "ok": true,
  "data": {
    "records": { "created": 0, "merged": 1, "skipped": 0 },
    "snippets": 1,
    "free": false,
    "ignored": { "exams": 1 }
  }
}
```

| 字段 | 含义 |
|---|---|
| `records.created` | 新建的记录数 |
| `records.merged` | 合并到已有记录的数量 |
| `records.skipped` | 题库里没有 / 值不是对象的条目数 |
| `snippets` | 实际写入（新建或更新）的片段数 |
| `free` | 是否填入了草稿（`true`/`false`） |
| `ignored.exams` | 被忽略的组卷历史条数 |

**限制**

| 限制 | 值 | 越界行为 |
|---|---|---|
| `questions` 条数 | ≤ **2000** | 413 `state_too_large`（`message:"一次最多导入 2000 条记录"`） |
| `snippets` 条数 | 前 **500** 个 | 超出**静默丢弃**，不报错 |
| 单段 `code` | **20000** 字符 | 静默截断 |
| `attempts`/`passes`/`fails` | 夹到 0–1000000 | 静默夹紧 |
| `questions` 不是对象 | — | 400 `invalid_state`（`message:"state.json 里的 questions 应该是一个对象"`） |
| 请求体不是 JSON 对象（如数组） | — | 422 `validation_error` |

**失败**：400 `invalid_state`、413 `state_too_large`、401、422、429。

---

## 9. 单步追踪（trace，仅旧兼容层）

> **v1 没有 trace 端点。** 前端做「执行过程」面板只能用 `POST /api/trace`，
> 它**没有 `data` 信封**，`error` 是**字符串**。

### 9.1 `POST /api/trace`

**需要认证。**

**请求体**

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `code` | string | 是 | 非空；> 20000 → 413 | Python 源码，**全新执行一遍**（不是从上次判题状态继续） |
| `stdin` | string | 否 | 无显式上限（受反代 2MB） | 标准输入 |

**成功 `200`（实测，3 行代码）**

```json
{
  "ok": true,
  "trace": {
    "steps": [
      { "line": 1, "event": "call", "func": "<module>", "depth": 0,
        "vars": [], "hidden": 0, "out": "" },
      { "line": 1, "event": "line", "func": "<module>", "depth": 0,
        "vars": [], "hidden": 0, "out": "" },
      { "line": 2, "event": "line", "func": "<module>", "depth": 0,
        "vars": [["a", "1"]], "hidden": 0, "out": "" },
      { "line": 3, "event": "line", "func": "<module>", "depth": 0,
        "vars": [["a", "1"], ["b", "2"]], "hidden": 0, "out": "" },
      { "line": 3, "event": "return", "func": "<module>", "depth": 0,
        "vars": [["a", "1"], ["b", "2"]], "hidden": 0, "out": "2\n" }
    ],
    "error": "",
    "timeout": false,
    "truncated": false,
    "output": "2\n",
    "syntax": false,
    "duration_ms": 166
  },
  "summary": ""
}
```

**`trace` 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `steps` | array | 追踪事件序列，见 §9.2 |
| `error` | string | 异常摘要（`"ZeroDivisionError: division by zero"`）、语法错误全文、或安全拦截文案；正常为 `""` |
| `timeout` | bool | 是否被超时打断（`QUIZ_TRACE_TIMEOUT`，默认 5s） |
| `truncated` | bool | 是否因**步数上限**（默认 800）或**输出超 20000 字符**被截断 |
| `output` | string | 整段代码跑完的完整标准输出（最多 20000 字符） |
| `syntax` | bool | 是否语法错误（此时 `steps` 为空、`error` 为语法错误文本） |
| `duration_ms` | int | 追踪整体耗时（毫秒） |

**`summary`**：`describe_trace()` 生成的一句话，前端可直接显示：

| 情况 | `summary` 内容 |
|---|---|
| 有 `error` | 原样返回 `trace.error` |
| `timeout` | `"执行超时，追踪在第 N 步被打断（检查循环条件）"` |
| `truncated` | `"记录到前 N 步就停了（循环太长，或者写成了死循环）"` |
| 正常 | `""`（**空串**，前端要自己兜一句「共 N 步」） |

### 9.2 `steps[]` 事件格式

| 字段 | 类型 | 说明 |
|---|---|---|
| `line` | int | **1 起的行号**，对应代码字符串按 `\n` 切分的下标 +1 |
| `event` | string | `"call"` / `"line"` / `"return"` / `"exception"`（实测四种都出现过） |
| `func` | string | 所在函数名；模块顶层为 `"<module>"` |
| `depth` | int | 在**学习者代码**内的嵌套层数，顶层为 `0`，进函数为 `1`… |
| `vars` | array | 当前帧局部变量快照：`[[名字, 值文本], ...]`，**最多 12 个**；值文本是 `repr()` 结果，换行变 `⏎`、制表符变 `→`、超 48 字符截断加 `…` |
| `hidden` | int | 因超过 12 个而被省略的变量个数 |
| `out` | string | **截至该步**的累计标准输出（最多 20000 字符） |

要点：

- 每一行的 `vars` 是**当前帧**的快照，不是全局；返回值/异常事件也会记录。
- 变量顺序不保证稳定（来自 `frame.f_locals` 的字典顺序）。
- 只跟踪学习者代码文件（`<你的代码>`）的帧，标准库帧不记录。
- 实测「函数定义 + 调用」8 步的例子（截取前 3 步）：

```json
{"summary":"","steps":[
  {"line":1,"event":"call","func":"<module>","depth":0,"vars":[],"hidden":0,"out":""},
  {"line":1,"event":"line","func":"<module>","depth":0,"vars":[],"hidden":0,"out":""},
  {"line":4,"event":"line","func":"<module>","depth":0,
   "vars":[["f","<function f at 0x0000023EB5DF7250>"]],"hidden":0,"out":""}
],"n_steps":8,"error":"","output":"6\n"}
```

### 9.3 异常与死循环的真实响应（实测）

`1/0`：

```json
{"ok":true,"trace":{
  "steps":[
    {"line":1,"event":"call","func":"<module>","depth":0,"vars":[],"hidden":0,"out":""},
    {"line":1,"event":"line","func":"<module>","depth":0,"vars":[],"hidden":0,"out":""},
    {"line":1,"event":"exception","func":"<module>","depth":0,"vars":[],"hidden":0,"out":""},
    {"line":1,"event":"return","func":"<module>","depth":0,"vars":[],"hidden":0,"out":""}],
  "error":"ZeroDivisionError: division by zero",
  "timeout":false,"truncated":false,"output":"","syntax":false,"duration_ms":150},
 "summary":"ZeroDivisionError: division by zero"}
```

`while True: pass`：【代码可证】`truncated:true`（800 步上限）或 `timeout:true`，
`summary` 里带 `"步"` 或 `"超时"`，`steps` 有内容。

**语法错误**：`steps: []`、`syntax: true`、`error` 为 `"SyntaxError: ..."`，
`summary` 等于这段错误文本。

### 9.4 安全黑名单（**只对 trace 生效**）

`trace_runner.py` 在执行前用正则拦这几类调用，命中即**不执行**、`steps: []`：

| 正则 | 名字 |
|---|---|
| `os.system` | `os.system` |
| `os.popen` | `os.popen` |
| `os._exit` | `os._exit` |
| `subprocess` | `subprocess` |
| `shutil.rmtree` | `shutil.rmtree` |
| `ctypes` | `ctypes` |

命中后的真实响应（实测）：

```json
{"ok":true,"trace":{"steps":[],"error":"为安全起见，练习环境不允许使用 os.system",
 "timeout":false,"truncated":false,"output":"","syntax":false,"duration_ms":166},
 "summary":"为安全起见，练习环境不允许使用 os.system"}
```

> 【代码可证】这套黑名单**只在 trace 子进程里**；判题/运行用的 `child_runner.py` **没有**这段检查。
> 记录在这里只是为了让前端知道：**「trace 里被拦」不代表「判题里也会被拦」**。

---

## 10. 旧兼容层 `/api/*` 全量

给 `web/index.html` 用的，**响应形状必须和桌面版 `webserver.py` 一致**，因此没有 `data` 层。

### 10.1 与 `/api/v1` 的对应关系

| 旧端点 | 对应 v1 | 差异 |
|---|---|---|
| `GET /api/bank` | `GET /api/v1/bank` | 完全相同的数据，只是**没有 `data` 层**（`questions`/`chapters`/`stats` 在顶层） |
| `GET /api/free` | `GET /api/v1/free` | 顶层字段，无信封 |
| `POST /api/free` | `PUT /api/v1/free` | 旧层是 POST；返回 `{ok, saved:true}`，**不回 updated**；`code`/`stdin` 截断到 20000 |
| `GET /api/snippets` | `GET /api/v1/snippets` | 顶层 `{snippets:[...]}` |
| `POST /api/snippet`（**单数**） | `POST /api/v1/snippets` + `DELETE /api/v1/snippets/{name}` | 旧层保存/删除**同一个端点**，靠 `delete:true` 区分；保存后直接回**完整列表** |
| `POST /api/run` | `POST /api/v1/submissions`（qid）/ `POST /api/v1/run`（无 qid） | 旧层**同步**返回判题结果；不写进度 |
| `POST /api/attempt` | **无对应** | v1 由判题 worker 自动写 Record |
| `POST /api/trace` | **无对应** | v1 没有 trace |

**旧网页版实际用到的就是这 8 个**（`web/index.html` 里 `api()` 拼的路径）：
`/api/bank`、`/api/run`、`/api/attempt`、`/api/trace`、`/api/free`（GET+POST）、`/api/snippets`、`/api/snippet`。

### 10.2 各端点细节

#### 10.2.1 `GET /api/bank`

**需要认证。无参数。** 实测顶层键：`["chapters","questions","stats"]`，
`questions[].` 键与 v1 完全一致（17 个，含 `cases`）。

```json
{
  "questions": [ /* 同 §4.1 的 Question */ ],
  "chapters": [ /* 同 §4.1 的 Chapter */ ],
  "stats": { "total": 139, "solved": 0, "tried": 0, "favorite": 0,
             "attempts": 0, "passes": 0, "rate": 0 }
}
```

#### 10.2.2 `GET /api/free`

```json
{ "code": "print(9)", "stdin": "x", "updated": "2026-11-15T12:58:58+00:00" }
```

无草稿时 `{"code":"","stdin":"","updated":""}`。

#### 10.2.3 `POST /api/free`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `code` | string | 否 | 超过 20000 **静默截断** |
| `stdin` | string | 否 | 同上 |

```json
{ "ok": true, "saved": true }
```

#### 10.2.4 `GET /api/snippets`

```json
{ "snippets": [ { "name": "导入片段", "code": "print(2)",
                  "updated": "2025-01-02 10:00:00" } ] }
```

#### 10.2.5 `POST /api/snippet`（保存 / 删除二合一）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | `strip()` 后为空 → 400 `"片段名字不能为空"`；> 80 → 400 `"片段名字太长了（上限 80 字符）"` |
| `code` | string | 否 | 超过 20000 截断 |
| `delete` | bool | 否 | **真值**即走删除分支 |

保存成功（实测）：

```json
{ "ok": true, "created": true,
  "snippets": [ {"name":"片段A","code":"print(1)","updated":"..."},
                {"name":"导入片段","code":"print(2)","updated":"..."} ] }
```

删除成功（实测）：

```json
{ "ok": true, "removed": true }
```

删除不存在的名字**不报错**，返回 `{ "ok": true, "removed": false }`（与 v1 的 404 不同）。

#### 10.2.6 `POST /api/run`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `code` | string | 是 | 空/纯空白 → **400** `{"ok":false,"error":"代码是空的"}`；> 20000 → **413** `"代码太长了（上限 20000 字符）"` |
| `qid` | string | 否 | 有值 → 判题模式；空/缺省 → 自由运行 |
| `stdin` | string | 否 | **仅自由模式生效** |

**判题模式（实测）** —— 同步返回，`judge` 就是 `judge_question()` 的结果：

```json
{
  "ok": true,
  "mode": "judge",
  "judge": {
    "mode": "judge", "passed": true, "status": "passed", "total": 1,
    "results": [ { "index": 0, "stdin": "", "expect": "4550", "actual": "4550\n",
                   "error": "", "timeout": false, "truncated": false,
                   "expect_lines": ["4550"], "actual_lines": ["4550"],
                   "status": "pass", "first_diff": null } ],
    "duration_ms": 0
  }
}
```

**自由模式（实测）**：

```json
{ "ok": true, "mode": "free",
  "run": { "output": "42\n", "error": "", "timeout": false,
           "truncated": false, "syntax": false, "duration_ms": 152 } }
```

**失败**：400 / 404（`"没有这道题：<qid>"`）/ 413 / 401。判题不通过**不是** HTTP 错误，仍是 200。

> 注意：`POST /api/run` **不写进度**。旧网页版判完会紧接着调 `POST /api/attempt`。
> 同一份代码如果既走 `/api/run` 又走 `POST /api/v1/submissions`，进度会被记两次。

#### 10.2.7 `POST /api/attempt`（v1 无对应）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qid` | string | 是 | 缺 → 400 `"缺少题目编号"`；不存在 → 404 `"没有这道题：<qid>"` |
| `passed` | any | 否 | **真值**即记通过（字符串 `"false"` 也会被当真！代码用 `bool(...)`） |
| `code` | string | 否 | 存为「上次提交代码」，截断到 20000 |

**成功 `200`（实测）**

```json
{
  "ok": true,
  "stats": { "total": 139, "solved": 2, "tried": 2, "favorite": 1,
             "attempts": 5, "passes": 4, "rate": 80 },
  "record": { "last": "pass", "attempts": 2 }
}
```

| 字段 | 说明 |
|---|---|
| `stats` | **最新全量统计**（同 §5.1 的 Stats） |
| `record.last` | `"pass"` / `"fail"` |
| `record.attempts` | 该题累计次数（注意：**没有 passes/fails**，与 v1 的 Record 不同） |

每次调用 `attempts += 1`，不幂等 —— 前端**不要重复提交**。

#### 10.2.8 `POST /api/trace`：见 §9。

### 10.3 错误形状不一致（必须处理）

同一个旧层里，**两种错误形状混用**：

**A. 业务错误 → `error` 是字符串**（`_fail` 造）

```json
{"ok": false, "error": "代码是空的"}
```

**B. 认证/框架错误 → `error` 是对象**（走统一 `http_error_handler`，实测）

```json
{"ok": false, "error": {"code":"unauthorized","message":"缺少 Bearer 令牌",
                        "request_id":"f413306e8153"}}
```

**这对旧网页版是个真坑**：`web/index.html` 里

```js
throw new Error((data && data.error) || ("HTTP " + resp.status));
```

`data.error` 是对象时会得到 `"[object Object]"` 的报错文案。新前端必须写成：

```js
const msg = typeof e.error === "string" ? e.error
          : e.error?.message || e.error?.code || `HTTP ${status}`;
```

---

## 11. 非业务路由

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/healthz` | 否 | 健康检查（真的 `SELECT 1`）。**吃 api 限流配额** |
| GET | `/` | 否 | 有 `web/` 目录时返回**旧网页版** `index.html`（注入 `/auth.js`）；没有则返回 JSON |
| GET | `/auth.js` | 否 | 旧网页版登录脚本（登录浮层 + fetch 包装注入 Bearer + 401 弹窗） |
| GET | `/docs` | 否 | Swagger UI |
| GET | `/redoc` | 否 | ReDoc |
| GET | `/openapi.json` | 否 | OpenAPI 3 文档（机器可读，可用于生成 TS 类型） |

**`GET /healthz` 成功（实测）**

```json
{ "ok": true, "data": { "status": "ok", "version": "1.0.0", "judge_workers": 2 } }
```

失败（数据库不通，`503`，**无 `request_id`**）：

```json
{ "ok": false, "error": { "code": "db_unavailable", "message": "<异常文本>" } }
```

**`GET /`**：`text/html`，`Cache-Control: no-store`。用 `grep` 可确认页面里注入了 `<script src="/auth.js"></script>`。
**`GET /auth.js`**：`application/javascript`，`Cache-Control: no-store`。

---

## 12. 数据字典

### 12.1 `Question`

| 字段 | 类型 | 可空/空值 | 含义 |
|---|---|---|---|
| `id` | string | — | 题目 ID（`String(24)`，现库最长 4） |
| `chapter_id` | string | 可 `""` | 章节 ID（`ch3`/`ch4`/`ch5`/`extra`/`algo`） |
| `chapter` | string | 可 `""` | 章节名 |
| `no` | int | 0 | 章节内序号 |
| `title` | string | 可 `""` | 标题 |
| `topic` | string | 可 `""` | 知识点（自由文本） |
| `level` | int | 1 | 难度 1/2/3 |
| `desc` | string | 可 `""` | 题面，含换行 |
| `hint` | string | 可 `""` | 提示 |
| `ref` | string | 可 `""` | 参考代码 |
| `explain` | string | 可 `""` | 解析/易错点 |
| `source` | string | 可 `""` | 来源 |
| `cases` | Case[] | `[]` | **测试用例（公开）** |
| `last` | string | `""` | 我的最近结果：`""`/`pass`/`fail` |
| `attempts` | int | 0 | 我的作答次数 |
| `favorite` | bool | false | 我的收藏 |
| `code` | string | `""` | 我最近一次提交的代码 |

`Case`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `stdin` | string | 输入 |
| `expect` | string | 期望输出（原始） |
| `raw` | bool? | **可选**；出现即 `true`，表示比对时保留行首空格 |

### 12.2 `Chapter`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | `ch3`/`ch4`/`ch5`/`extra`/`algo` |
| `name` | string | 全名（与 `Question.chapter` 对应） |
| `short` | string | 短名（`第3章`/`拓展`/`算法`），**章节标签显示用这个** |
| `count` | int | 该章题数 |

### 12.3 `Stats`

| 字段 | 类型 | 含义 |
|---|---|---|
| `total` | int | 题库总题数 |
| `solved` | int | 当前处于通过态的题数 |
| `tried` | int | 做过的题数（`attempts>0`） |
| `favorite` | int | 收藏题数 |
| `attempts` | int | 总作答人次 |
| `passes` | int | 总通过人次 |
| `rate` | int | `round(passes*100/attempts)`，0–100 |

### 12.4 `Submission`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 32 位 hex |
| `qid` | string | `""` 表示自由运行 |
| `status` | string | `queued`/`running`/`passed`/`failed`/`timeout`/`error` |
| `result` | object | 未完成时 `{}`；完成后见 §6.5.3 / §6.5.4 |
| `error` | string | 判题整体错误（取 `result.error`） |
| `created_at` | string | 创建时间 |
| `finished_at` | string | 完成时间；未完成为 `""` |
| `duration_ms` | int | 判题模式**恒 0**（缺陷）；自由模式为运行耗时 |

> ⚠️ **没有 `code` 字段**（`SubmissionOut` 不含代码）——**无法通过提交接口回放用户提交的代码**。
> 想「恢复上次代码」只能读 `/bank` 的 `question.code`。

### 12.5 `JudgeResult`（`result`，mode=judge）

见 §6.5.3。字段：`mode, passed, status, total, results[], duration_ms`。

### 12.6 `CaseResult`（`result.results[]`）

见 §6.5.3。字段：`index, stdin, expect, actual, error, timeout, truncated, expect_lines[], actual_lines[], status, first_diff`。

`first_diff`：

```json
{ "line": 3, "expect": "3", "actual": "9" }
```

`line` 是**归一化后行数组**的 1 起下标；某侧缺行时该侧为 `null`。

### 12.7 `FreeResult`（`result`，mode=free）

`mode, passed, status, results(空), run, duration_ms, error`。

### 12.8 `RunResult`

| 字段 | 类型 | 说明 |
|---|---|---|
| `output` | string | 标准输出（最多 40000 字符） |
| `error` | string | 异常摘要（`"ZeroDivisionError: division by zero"`）或沙箱提示；无异常为 `""` |
| `timeout` | bool | 是否超时被 kill |
| `truncated` | bool | 输出是否被截断 |
| `syntax` | bool | 是否语法错误（此时 `error` 为语法错误文本） |
| `duration_ms` | int | 子进程耗时（毫秒） |

### 12.9 `Trace` / `TraceStep`

见 §9.1 / §9.2。

### 12.10 `Record`（`/progress` 的 `records[]`）

`qid, attempts, passes, fails, last, favorite, updated`（**无 `code`**）。

### 12.11 `Snippet`

`name, code, updated`。

### 12.12 `FreeDraft`

`code, stdin, updated`。

### 12.13 `ImportResult`

`records{created,merged,skipped}, snippets(int), free(bool), ignored{exams:int}`。

---

## 13. 前端兼容性注意点

### 13.1 CORS（默认关闭）

| 项 | 值 |
|---|---|
| 默认 | `QUIZ_CORS_ORIGINS` 为空 → **不装 CORSMiddleware** → 浏览器跨域请求直接失败（无 `Access-Control-Allow-Origin`） |
| 开启方式 | `QUIZ_CORS_ORIGINS=https://app.example.com,https://other.example.com`（逗号分隔，启动时读取） |
| 允许方法 | `GET, POST, PUT, DELETE, OPTIONS` |
| 允许请求头 | `Accept, Accept-Language, Authorization, Content-Language, Content-Type`（Starlette 安全头 + 显式加的 `Authorization`/`Content-Type`） |
| `allow_credentials` | **`false`** → 不可能带 Cookie |
| `max_age` | `600` 秒 |
| 暴露响应头 | **无** → 跨域时 JS 读不到 `X-Request-ID`、`X-Process-Time-Ms` |
| 预检（允许的源） | `200`，回 `access-control-allow-origin: <origin>`【实测】 |
| 预检（不允许的源） | **`400`**（不是 403）【实测】 |
| 简单请求（不允许的源） | 照常 `200`，但**没有** `Access-Control-Allow-Origin`，浏览器会拦【实测】 |

> 结论：**同源部署最省事**（Vite dev 已配 `/api` 代理；生产可让 Caddy/nginx 同域反代）。

### 13.2 Cookie vs Header

- 全站**没有任何 `Set-Cookie`**。认证只认 `Authorization` 头。
- 旧网页版把令牌存在 `localStorage`：键 `pyquiz.token` / `pyquiz.username`（仅作参考，新前端可自定）。
- 令牌过期**没有软续期**：`expires_in` 到点即失效，只能重新登录。

### 13.3 401 之后的行为

1. 所有 401 的 `error.code` 都是 `unauthorized`（登录失败是 `invalid_credentials`，要区分）。
2. 旧 `auth.js` 的做法（可照抄）：拦截任何 `/api/` 请求的 401 → 清本地令牌 → 弹登录层。
3. **不要**在 401 后无限重试（会吃全局限流）。
4. 只有 `GET /auth/me` 适合做启动探活。

### 13.4 请求体大小与超时

| 项 | 值 |
|---|---|
| 应用层 body 上限 | 无 |
| Caddy | 2 MB |
| nginx | 8 MB |
| 代码字段 | 20000 **字符**（不是字节） |
| 片段代码 | 50000 字符 |
| 判题 HTTP 请求本身 | 立即返回（202），不占长连接 |
| 同步端点最坏耗时 | `/api/v1/run`：`wait(timeout=6s)` 超时后 kill 再等最多 5 s → 理论 ≤ ~11 s（实测超时用例 2.7 s 返回）；`/api/trace` ≤ ~7 s；`/api/run`（判题模式）≈ 用例数 × 6 s |
| 反向代理读超时 | nginx `/api/` 配 `proxy_read_timeout 60s`；Caddy 默认无显式超时 |

前端 fetch **不要**给判题轮询设 3 秒级短超时；`/api/run` 与 `/api/trace` 建议 ≥ 15 s。

### 13.5 判题超时时间（准确口径）

- **每个用例** 6 秒（`QUIZ_JUDGE_TIMEOUT`），不是整题 6 秒。
- 一道 5 用例的题理论最坏 ≈ 5 × (6 + 进程启动 ~0.15) ≈ 31 秒；若第一个用例就超时，后面的用例不再跑。
- 追踪 5 秒 / 800 步，取先到者。
- 沙箱并发上限 8/进程；判题线程默认 2 → 高峰期会排队（`queued` 停留变长），轮询要能忍。

### 13.6 缓存

- 应用层不加 `ETag`/`Cache-Control`（除 `/` 与 `/auth.js` 显式 `no-store`）。
- 反代层：Caddy 对 `/`、`/auth.js`、`/api/*` 强制 `Cache-Control: no-store`。
- 前端自己不要缓存 `/bank` 的统计（判题后必须重拉）。

### 13.7 静态挂载缺口（集成时会踩）

`frontend/vite.config.ts` 里写着「构建产物由 FastAPI 挂在 `/app` 下（见 `backend/app/main.py` 的 `mount_frontend`）」，
`base: "/app/"`、`BrowserRouter basename="/app"` 也都按 `/app/` 配好了。但**当前 `main.py` 里没有 `mount_frontend`** ——
它只把 `web/index.html` 挂在 `/`。也就是说：

- 现在直接把 `dist/` 扔给后端，`/app/` 会 404；
- 开发阶段用 Vite dev server（`base=/app/` + `/api` 代理）没问题；
- 生产上线前，需要后端补一个 `/app` 静态挂载（或用 Caddy `root`/`file_server` 直接吐 `dist/`）。
- 【代码中未体现，需实测】该挂载最终选 `StaticFiles(html=True)` 还是显式路由，会影响深链接刷新（`/app/bank/3-01` 需要 SPA fallback）。

---

## 14. 缺口：前端必须自己算的部分

| 需求 | 现状 | 前端对策 |
|---|---|---|
| 章节维度进度（每章 x/y） | 后端只给全局 `stats` | 用 `/bank` 的 `questions[].chapter_id + last` 本地聚合 |
| 错题本 | **没有独立端点**，`/progress` 也没有 `wrong` 筛选 | 从 `/progress` 的 `records` 过滤 `last === "fail"`（或 `fails > 0`），再与 `/bank` 的题目 join 拿标题/章节 |
| 收藏列表 | 同上 | `records.filter(r => r.favorite)` |
| 题目搜索 | `/bank` **不支持任何筛选参数**（实测传 `q=abc` 无效） | 全量 139 题在内存里过滤（标题/知识点/编号） |
| 题目分页 | 无 | 前端分页；一次 155 KB 建议启动时拉一次缓存 |
| 组卷 / 模拟考试 / 错题重练 | **完全没有端点**；`state.json` 的 `exams` 在导入时被忽略 | 只能纯前端做（选题、计时、本地判分都靠 `/api/v1/run` 或 `/submissions` 逐题调） |
| 班级 / 排行榜 / 全站通过率 | 无 | 无解，需要后端加表 |
| 每题耗时 | `result.duration_ms` 判题模式恒 0（缺陷） | 前端自己 `performance.now()` 计；或用 `/api/v1/run` 的 `run.duration_ms` |
| 「上次提交的代码」 | `/progress` 无 `code`；`Submission` 也无 `code` | 读 `/bank` 的 `question.code`（最近一次判题代码） |
| 判题历史回放 | 只保留最近 **100 条**/人，且**不含代码** | 无解；需要后端加字段（不建议） |
| 学习曲线 / 提交时间线 | 可用 `GET /submissions?limit=100` 的 `created_at` 拼，但被裁剪到 100 条 | 需要更久历史就得后端加统计表 |
| 弱项分析（按 topic） | 无聚合端点 | 前端用 `questions[].topic` + `records` 自己算 |
| 改密码 / 找回密码 / 注销 | **无端点**（`auth.js` 文案：「忘记密码目前只能找管理员重置」） | 无解 |
| 登出 | 无端点 | 清本地 token |
| 刷新令牌 | 无 | 过期即重登 |
| 隐藏用例 / 防作弊 | 用例和 `expect` 全量明文下发 | 设计如此；前端不要试图「本地判分代替服务端判分」 |
| 判题进度百分比 | 无（没有 `progress` 字段） | 只能显示 indeterminate 或 `results.length/total`（终态才有） |

---

## 15. 附录：结论出处

### 15.1 读过的文件（全部实际打开读过，非猜测）

```
backend/app/main.py              路由注册 / 中间件 / 限流接入 / 异常处理 / 静态页 / CORS / healthz
backend/app/config.py            QUIZ_* 配置默认值（TTL、超时、限流、CORS）
backend/app/errors.py            响应信封、ApiError、HTTP 状态→code 映射、422 文案拼装
backend/app/security.py          JWT 结构、Bearer 解析、current_user、401 细节
backend/app/ratelimit.py         滑窗实现（发现「key 未参与分桶」缺陷）
backend/app/schemas.py           全部请求/响应字段与长度约束
backend/app/serializers.py       question_dict / stats_dict / submission_dict / record_dict（字段全集来源）
backend/app/models.py            表结构与默认值（updated 空串、submission 保留策略的基础）
backend/app/db.py                会话、SQLite 参数
backend/app/seed.py              题库灌入规则（sort_order = 数组下标）
backend/app/routers/auth.py      注册/登录/me
backend/app/routers/bank.py      bank / questions / progress / favorite
backend/app/routers/submissions.py  202 提交、轮询、列表、同步 run
backend/app/routers/snippets.py  片段 CRUD、草稿 GET/PUT
backend/app/routers/legacy.py    旧层 8 个端点、错误形状、describe_trace
backend/app/routers/imports.py   导入合并语义与各项上限
backend/app/judge/worker.py      状态机、DB 认领、Record 自动更新、_prune(100)、judge_question/run_free_code
backend/app/judge/executor.py    子进程、超时、rlimit、输出上限、run_python/run_trace 返回字段
backend/app/judge/child_runner.py    判题侧子进程（无黑名单）
backend/app/judge/trace_runner.py    追踪侧子进程（黑名单、步数、变量快照、事件）
backend/app/judge/compare.py     归一化与 first_diff 的 line 语义
backend/app/judge/worker_entry.py    独立 worker 入口
backend/tests/conftest.py        真服务夹具、轮询等待逻辑（wait_submission）
backend/tests/test_api.py        接口样例与断言（含字段存在性）
backend/tests/test_legacy.py     旧层字段形状断言（前端依赖点）
backend/tests/test_import.py     导入幂等/不倒退语义
backend/tests/test_units.py      JWT、比对、限流窗口
backend/README.md                接口一览、配置表、判题隔离说明
backend/DEPLOY.md                部署、容量、超时、排查
backend/Caddyfile · nginx.conf   反代层 body 上限、超时、限流、缓存头
backend/.env.example             环境变量默认值
backend/Dockerfile               --proxy-headers 等运行参数
web/index.html                   旧网页版实际调用方式（/api/*、字段消费）
web/auth.js                      令牌注入、401 处理、localStorage 键名
frontend/vite.config.ts          /app base 与 /api 开发代理（挂载缺口来源）
```

### 15.2 实测方式

1. 用 `py -3.10` 起真实 `uvicorn`（随机端口，`sqlite` 临时库，`QUIZ_SEED_ON_START=true`；
   限流阈值按测试目的调高/调低）。
2. 用 `urllib` 真发 HTTP，逐条抓 `status + body + headers`，原文贴进本文（共 5 轮，覆盖正常流、
   错误流、限流、CORS 预检、载荷体积）。
3. 题库数据用 `questions.json` 直接统计：139 题、5 章、338 个用例、7 个用例带 `raw`。
4. 未跑 `pytest` 全量（依赖已有测试文件作为字段形状的第二来源，断言与实测一致）。

### 15.3 仍需实测确认的点（不要当契约）

| 点 | 为什么不确定 |
|---|---|
| 用户名是否大小写敏感 | SQLite 默认敏感，但未实测；换 PostgreSQL 后行为可能不同 |
| 同一秒内多个提交的列表顺序 | `created_at` 只到秒，排序不稳定 |
| 生产环境实际 CORS 配置值 | 取决于部署时的 `.env`，代码只给默认（空） |
| `/app/` 静态挂载最终形态 | 当前 `main.py` 尚无 `mount_frontend` |
| 反代后真实客户端 IP 是否进入限流键 | 即使进来也不影响结论——**限流根本没按 IP 分桶** |
