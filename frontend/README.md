# Python 刷题系统 · Web 前端（React SPA）

把原来那份 797 行的单文件网页版（`web/index.html`）重写成正经前端：

| | 老网页版 `web/` | 新前端 `frontend/` |
|---|---|---|
| 技术 | 原生 JS + 手写 DOM | React 18 + Vite + TypeScript + Tailwind CSS 4 |
| 接口 | `/api/*`（兼容层，为它保留） | `/api/v1/*`（版本化接口） |
| 托管 | 服务端在 `/` 注入登录脚本 | 服务端在 `/app` 托管构建产物 |
| 结构 | 一个 32 KB 的 html | `pages/` `components/` `lib/` 分模块，按路由拆包 |

两个版本同时可用：老页面在 `/`，新前端在 `/app`，共用同一套后端、同一份题库和进度。

## 一、本地开发

```powershell
cd frontend
npm install

# 后端另开一个窗口（端口 8000）
cd ..\backend
py -3.10 -m uvicorn app.main:app --reload --port 8000

# 前端开发服务器：http://localhost:5173/app/
npm run dev
```

`vite.config.ts` 里已经配好代理，开发时 `/api/**` 会转发到 `127.0.0.1:8000`，不需要处理跨域。

> 本机（Windows）如果 `npm run build` 报
> `esbuild ... remove ...: Access is denied`，是 esbuild 删临时文件被杀软/索引器占用了，
> 把临时目录指到项目里即可：
>
> ```powershell
> $env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP; npm run build
> ```

## 二、构建与部署

```powershell
npm run typecheck   # tsc --noEmit
npm run build       # 产物在 frontend/dist
```

后端启动时会检查 `QUIZ_FRONTEND_DIR`（默认 `frontend/dist`）：

- 有产物 → 挂到 `/app`，`/app/**` 全部回退到 `index.html`（前端路由接管），`/app/assets/*` 走静态文件；
- 没产物 → 整块跳过，只打一条 info 日志，`/` 的老页面和所有接口都不受影响。

Docker 镜像里是多阶段构建（`backend/Dockerfile` 的 `AS frontend` 阶段），不需要在服务器上装 Node：

```bash
cd backend && docker compose build && docker compose up -d
# 新前端: https://你的域名/app
```

## 三、目录结构

```
frontend/
├── index.html              # Vite 入口（base=/app/）
├── vite.config.ts          # 开发代理 + /app base + Tailwind 插件
├── public/favicon.svg
├── API-CONTRACT.md         # 后端 25 个端点的完整契约（含真实响应样例）
└── src/
    ├── main.tsx            # BrowserRouter(basename=/app) + Auth/Toast Provider
    ├── App.tsx             # 路由表（业务页懒加载，编辑器单独拆包）
    ├── styles.css          # 设计令牌 + 组件类（Tailwind v4 @theme）
    ├── lib/
    │   ├── api.ts          # 统一请求/解包/401 处理、异步判题轮询
    │   ├── auth.tsx        # 登录态（localStorage token + /auth/me 校验）
    │   ├── bank.tsx        # 题库与进度上下文（一次拉取，全站共享）
    │   ├── types.ts        # 与 schemas.py 对齐的类型
    │   └── format.ts       # 章节配色、时间、CSV 导出等
    ├── components/
    │   ├── Layout.tsx      # 侧栏 + 移动端抽屉/底部导航
    │   ├── ui.tsx          # Button/Card/Badge/Modal/Toast/Segmented…
    │   ├── CodeEditor.tsx  # CodeMirror 6（Python 高亮，Ctrl+Enter 判题）
    │   ├── Charts.tsx      # 手写 SVG 环形图/趋势图/条形图
    │   ├── QuestionBody.tsx
    │   ├── JudgeResult.tsx # 逐用例比对、首行差异高亮
    │   └── TraceViewer.tsx # 单步执行播放器（变量/累计输出/源码高亮）
    └── pages/
        ├── Login.tsx  Dashboard.tsx  Practice.tsx  Book.tsx
        ├── FreeCoding.tsx  Stats.tsx  Exam.tsx  NotFound.tsx
```

## 四、页面与功能

| 路由 | 做什么 |
|---|---|
| `/app/login` | 登录 / 注册（邀请码可选），失败信息原样展示后端 code |
| `/app` | 概览：四张统计卡、接着上次继续、章节进度、最近提交、快捷入口 |
| `/app/practice/:qid` | 刷题工作台：题目列表（搜索/章节/状态筛选）+ 题面 + 编辑器 + 运行/判题/单步追踪 |
| `/app/book` | 题本：错题本 / 收藏夹 / 没通过，一键跳回刷题；导出 CSV |
| `/app/free` | 自由编程：stdin、运行、追踪、草稿自动保存、代码片段增删 |
| `/app/stats` | 统计：覆盖率环形图、章节/难度掌握度、7 天提交趋势、提交结果分布、最需要复习的题 |
| `/app/exam` | 模拟组卷：题数/章节/策略（错题加权·随机·顺序·只考没做过）/限时 → 逐题判分 → 交卷报告 |

交互细节：

- **判题是异步的**：`POST /api/v1/submissions` 拿 id，前端按 800ms→1.6s 退避轮询（后端限流是每进程 120 次/分钟，不能狂刷）。
- **Ctrl+Enter** 判题 / **Ctrl+S** 保存草稿（自由编程页）。
- 单步追踪弹窗：← → 切步、空格播放暂停、0.5×–5× 速度，源码当前行高亮、局部变量与累计输出同步刷新。
- 刷新不丢：编辑器内容按题号记在内存里，组卷进度存 `localStorage`，回来能接着做。
- 移动端：侧栏变抽屉 + 底部五栏导航，刷题页可横屏写代码。

## 五、和后端的分工

后端 `/api/v1` 只提供账号、题库（139 题全量 155 KB，含测试用例）、进度读写、异步判题、片段/草稿；
**组卷、错题本、章节统计、搜索、CSV 导出全在前端算**——因为 `/bank` 一次就把题目和我的进度都发下来了，
本地过滤比再开接口快得多。单步追踪仍走老兼容层 `POST /api/trace`（v1 暂无等价接口），
等后端补上就可以直接换。
