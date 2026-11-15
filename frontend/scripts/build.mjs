// 生产构建：先把临时目录指到项目内的 .tmp，再跑 tsc + vite。
//
// 为什么不用 `tsc && vite build` 直接了事：Windows 上 esbuild 会把自己的临时文件写到
// %TEMP%，被杀软/索引器占用时删除会失败，报
//   [vite:esbuild-transpile] remove ...: Access is denied
// 把 TEMP 换到项目目录里就绕开了，代价只是多一个 .tmp/（已 gitignore）。
//
// 直接 `node node_modules/<pkg>/...` 而不是 `npx`：跨平台一致，也不需要 shell。
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const cwd = process.cwd();
const tmp = join(cwd, ".tmp");
mkdirSync(tmp, { recursive: true });

const env = { ...process.env, TEMP: tmp, TMP: tmp, TMPDIR: tmp };

function run(label, script, args) {
  const entry = join(cwd, "node_modules", script);
  if (!existsSync(entry)) {
    console.error(`找不到 ${entry}，先跑 npm install`);
    process.exit(1);
  }
  console.log(`\n▶ ${label}`);
  const result = spawnSync(process.execPath, [entry, ...args], { stdio: "inherit", env });
  if (result.error) {
    console.error(`启动失败：${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

run("类型检查（tsc --noEmit）", "typescript/bin/tsc", ["--noEmit"]);
run("打包（vite build）", "vite/bin/vite.js", ["build"]);

console.log("\n✓ 构建完成：frontend/dist（由后端挂在 /app）");
