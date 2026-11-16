import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemeMode = "auto" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "pyquiz.theme";

function readSaved(): ThemeMode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark" || raw === "auto") return raw;
  } catch {
    /* 隐私模式 */
  }
  return "auto";
}

function systemTheme(): ResolvedTheme {
  try {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  } catch {
    return "dark";
  }
}

/** 把 data-theme 写到 <html> 上：auto 时不写，交给 CSS 的 prefers-color-scheme */
export function applyTheme(mode: ThemeMode) {
  const root = document.documentElement;
  if (mode === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", mode);
}

interface ThemeValue {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  setMode: (mode: ThemeMode) => void;
  cycle: () => void;
}

const ThemeCtx = createContext<ThemeValue | null>(null);

const ORDER: ThemeMode[] = ["auto", "light", "dark"];

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readSaved);
  const [system, setSystem] = useState<ResolvedTheme>(systemTheme);

  // 系统主题变化时（比如日落自动切换）跟着变
  useEffect(() => {
    let media: MediaQueryList;
    try {
      media = window.matchMedia("(prefers-color-scheme: light)");
    } catch {
      return;
    }
    const onChange = (event: MediaQueryListEvent) => setSystem(event.matches ? "light" : "dark");
    setSystem(media.matches ? "light" : "dark");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    applyTheme(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    applyTheme(mode);
  }, [mode]);

  const resolved: ResolvedTheme = mode === "auto" ? system : mode;

  // 顺带把浏览器地址栏颜色也切了
  useEffect(() => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", resolved === "light" ? "#eef2f9" : "#0b1020");
  }, [resolved]);

  const value = useMemo<ThemeValue>(
    () => ({
      mode,
      resolved,
      setMode,
      cycle: () => setMode(ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length]),
    }),
    [mode, resolved, setMode],
  );

  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error("useTheme 必须在 <ThemeProvider> 内使用");
  return ctx;
}
