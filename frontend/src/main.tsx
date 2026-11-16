import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./lib/auth";
import { ToastProvider } from "./components/ui";
import { BASENAME } from "./lib/core";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* basename 跟着 Vite 的 base 走：/app/ → /app，/python-quiz-system/ → /python-quiz-system */}
    <BrowserRouter basename={BASENAME || "/"}>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
);
