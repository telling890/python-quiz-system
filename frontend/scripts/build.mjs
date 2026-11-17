// 生产构建：先把临时目录指到项目内的 .tmp，再跑 tsc + vite。
//
// 两种产物：
//   node scripts/build.mjs            → 有后端用（base=/app/，接口走 /api/v1）
//   node scripts/build.mjs --static   → 静态版（GitHub Pages，base=/<仓库名>/app/，
//                                       题库内置、进度存 localStorage、判题用 Pyodide）
//
// 为什么静态版是 /<仓库名>/app/ 而不是 /<仓库名>/：GitHub Pages 一个仓库只有一个站点根，
// 站点根留给项目介绍页（site/），所以刷题应用整体挂在 /app/ 子路径下。
// 组装脚本 scripts/assemble-site.mjs 用的是同一套推法，两边必须一致（CI 里有断言）。
//
// 为什么先改 TEMP：Windows 上 esbuild 会把自己的临时文件写到 %TEMP%，被杀软/索引器
// 占用时删除会失败，报
//   [vite:esbuild-transpile] remove ...: Access is denied
// 把 TEMP 换到项目目录里就绕开了，代价只是多一个 .tmp/（已 gitignore）。
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, rmSync, statSync } from "node:fs";
import { join } from "node:path";

const cwd = process.cwd();
const args = process.argv.slice(2);
const staticMode = args.includes("--static");

const tmp = join(cwd, ".tmp");
mkdirSync(tmp, { recursive: true });

/* ---------------------------------------------------------------- 静态版准备 */

const publicDir = join(cwd, "public");
const bankTarget = join(publicDir, "bank.json");
const bankSource = join(cwd, "..", "backend", "app", "data", "questions.json");

function repoBase() {
  // GitHub Actions 里 GITHUB_REPOSITORY = "owner/repo"
  const repo = (process.env.GITHUB_REPOSITORY || "").split("/")[1] || "";
  if (!repo) return "/";
  if (repo.endsWith(".github.io")) return "/"; // 用户主页仓库挂在根路径
  return `/${repo}/`;
}

function staticBase() {
  // 站点根给介绍页，刷题应用固定在 app/ 子目录（与 assemble-site.mjs 的 APP_BASE 一致）
  return `${repoBase()}app/`;
}

if (staticMode) {
  if (!existsSync(bankSource)) {
    console.error(`找不到题库：${bankSource}`);
    process.exit(1);
  }
  mkdirSync(publicDir, { recursive: true });
  copyFileSync(bankSource, bankTarget);
  const size = (statSync(bankTarget).size / 1024).toFixed(0);
  console.log(`▶ 题库已内置：public/bank.json（${size} KB）`);
} else if (existsSync(bankTarget)) {
  // 有后端时不带题库，别让产物多 180 KB
  rmSync(bankTarget, { force: true });
}

/* ---------------------------------------------------------------- 环境变量 */

const env = {
  ...process.env,
  TEMP: tmp,
  TMP: tmp,
  TMPDIR: tmp,
  VITE_STATIC: staticMode ? "1" : "0",
  VITE_BASE: process.env.VITE_BASE || (staticMode ? staticBase() : "/app/"),
};

console.log(`▶ 构建模式：${staticMode ? "静态版（GitHub Pages）" : "有后端（FastAPI /app）"}`);
console.log(`▶ base：${env.VITE_BASE}`);

/* ---------------------------------------------------------------- 构建 */

function run(label, script, scriptArgs) {
  const entry = join(cwd, "node_modules", script);
  if (!existsSync(entry)) {
    console.error(`找不到 ${entry}，先跑 npm install`);
    process.exit(1);
  }
  console.log(`\n▶ ${label}`);
  const result = spawnSync(process.execPath, [entry, ...scriptArgs], { stdio: "inherit", env });
  if (result.error) {
    console.error(`启动失败：${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

run("类型检查（tsc --noEmit）", "typescript/bin/tsc", ["--noEmit"]);
run("打包（vite build）", "vite/bin/vite.js", ["build"]);

// GitHub Pages 对深链接（/repo/practice/3-01）只会回 404.html，
// 所以把 index.html 复制一份：刷新任意前端路由都还能进应用。
if (staticMode) {
  const dist = join(cwd, "dist");
  copyFileSync(join(dist, "index.html"), join(dist, "404.html"));
  console.log("▶ 已生成 404.html（GitHub Pages 深链接回退到前端路由）");
}

console.log(
  staticMode
    ? `\n✓ 静态版构建完成：frontend/dist（部署地址 https://<用户名>.github.io${env.VITE_BASE}）`
    : "\n✓ 构建完成：frontend/dist（由后端挂在 /app）",
);
