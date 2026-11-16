import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/**
 * base 的两种取值：
 *  - 有后端（FastAPI 挂在 /app）→ "/app/"
 *  - 静态版（GitHub Pages）→ "/<仓库名>/"，由 scripts/build.mjs 通过 VITE_BASE 传进来
 */
const nodeEnv = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const base = nodeEnv.VITE_BASE || "/app/";

export default defineConfig({
  base,
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    // 开发时把接口转发给本地后端，避免跨域
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // 静态版会把 Pyodide（外部 CDN）单独放，别和业务代码混在一起
        manualChunks: undefined,
      },
    },
  },
  worker: {
    format: "es",
  },
});
