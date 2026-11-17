// 组装 GitHub Pages 站点：把「项目介绍页」和「刷题应用」放进同一个站点。
//
//   站点根目录   ← site/（介绍页：index.html + assets/）
//   <base>/app/  ← frontend/dist（静态版刷题应用，base 由 VITE_BASE 决定）
//   站点根 404.html ← 应用外壳 + 一段守卫脚本，刷新深链接仍能进应用
//
// 为什么要搬目录：GitHub Pages 一个仓库只有一个站点根，介绍页和刷题应用都得挂在
// 同一个域名下，所以应用整体挪到 /app/ 子路径；应用自己的 base 已经是绝对路径
// （vite 的 base = /<仓库>/app/），搬到子目录不用改业务代码，前端路由的 basename
// 也跟着 BASE_URL 走。
//
// 用法（在 frontend/ 下执行，先跑过 npm run build:static）：
//   node scripts/assemble-site.mjs
// 环境变量：
//   APP_BASE  应用子路径，默认从 GITHUB_REPOSITORY 推成 /<仓库名>/app/
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url)); // frontend/scripts
const frontend = join(here, "..");
const repoRoot = join(frontend, "..");
const dist = join(frontend, "dist");
const siteDir = join(repoRoot, "site");

/* ------------------------------------------------------------------ 路径推导 */

function repoBase() {
  const repo = (process.env.GITHUB_REPOSITORY || "").split("/")[1] || "";
  if (!repo) return "/";
  if (repo.endsWith(".github.io")) return "/"; // 用户主页仓库挂在根路径
  return `/${repo}/`;
}

function normalizeBase(value) {
  if (!value) return "";
  let base = value.trim();
  if (!base.startsWith("/")) base = "/" + base;
  if (!base.endsWith("/")) base += "/";
  return base;
}

const appBase = normalizeBase(process.env.APP_BASE) || `${repoBase()}app/`;
const siteBase = appBase.replace(/app\/$/, "");
const appDir = join(dist, "app");

function die(message) {
  console.error(`✗ ${message}`);
  process.exit(1);
}

/* ------------------------------------------------------------------ 前置检查 */

if (!existsSync(join(dist, "index.html"))) die(`找不到 ${join(dist, "index.html")}，先跑 npm run build:static`);
if (!existsSync(join(siteDir, "index.html"))) die(`找不到介绍页 ${join(siteDir, "index.html")}`);

/* ----------------------------------------------- 1) 应用整体挪进 dist/app/ */

rmSync(appDir, { recursive: true, force: true });
mkdirSync(appDir, { recursive: true });

// 应用产物的所有东西（index.html / assets / bank.json / favicon.svg / 404.html…）
// 一律搬进 dist/app/，免得和介绍页根目录的文件撞名。readdirSync 返回的是快照，
// 边搬边改目录是安全的；自己刚建的 app/ 要跳过。
for (const name of readdirSync(dist)) {
  if (name === "app") continue;
  renameSync(join(dist, name), join(appDir, name));
}
// 应用自己的 404 副本没有意义（Pages 只认站点根的 404.html）
rmSync(join(appDir, "404.html"), { force: true });

/* ----------------------------------------------- 2) 介绍页放到站点根 */

// site/ 里的 index.html、assets/ 逐个复制到 dist 根（不用 cpSync 整目录，
// 免得变成 dist/site/；介绍页的 assets/ 与应用自己的 dist/app/assets/ 互不干扰）
for (const name of readdirSync(siteDir)) {
  cpSync(join(siteDir, name), join(dist, name), { recursive: true });
}

/* ----------------------------------------------- 3) 站点根 404.html */

// 深链接（/<仓库>/app/practice/3-01）刷新时 Pages 会回落到站点根 404.html，
// 这里放应用外壳，前端路由就能接住；不带 /app/ 前缀的旧地址直接送回介绍页。
const shell = readFileSync(join(appDir, "index.html"), "utf8");
const guard = [
  "<script>",
  "/* 由 scripts/assemble-site.mjs 注入：只接住 /app/ 下的深链接，其它 404 回到介绍页 */",
  "(function(){",
  `var appBase=${JSON.stringify(appBase)};var siteBase=${JSON.stringify(siteBase)};`,
  "if(location.pathname.indexOf(appBase)!==0){location.replace(siteBase);}",
  "})();",
  "</script>",
].join("");

const notFound = /<head[^>]*>/i.test(shell)
  ? shell.replace(/<head[^>]*>/i, (m) => m + guard)
  : guard + shell;
writeFileSync(join(dist, "404.html"), notFound);

/* ----------------------------------------------- 4) 收尾 */

// Jekyll 会忽略下划线开头的文件，静态资源里常有 _ 开头的东西
writeFileSync(join(dist, ".nojekyll"), "");

const summary = [
  `▶ 站点根（介绍页）：${siteBase}`,
  `▶ 刷题应用：      ${appBase}`,
  "▶ 产物：dist/index.html + dist/assets/（介绍页）、dist/app/（应用）、dist/404.html（深链接回落）",
];
console.log(summary.join("\n"));
