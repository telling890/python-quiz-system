import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// 构建产物由 FastAPI 挂在 /app 下（见 backend/app/main.py 的 mount_frontend），
// 所以 base 必须是 /app/，否则 CSS/JS 会 404。
export default defineConfig({
  base: "/app/",
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
  },
});
