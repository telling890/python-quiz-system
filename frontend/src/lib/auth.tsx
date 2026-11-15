import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, onUnauthorized, tokenStore } from "./api";
import type { User } from "./types";

interface AuthValue {
  user: User | null;
  /** 首次校验令牌是否完成 */
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, code?: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // 先用本地缓存的用户信息渲染，避免刷新时闪一下登录页
  const [user, setUser] = useState<User | null>(() => (tokenStore.get() ? tokenStore.cachedUser() : null));
  const [ready, setReady] = useState<boolean>(() => !tokenStore.get());

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    onUnauthorized(() => {
      setUser(null);
    });
    return () => onUnauthorized(null);
  }, []);

  useEffect(() => {
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    let alive = true;
    api
      .me()
      .then((me) => {
        if (!alive) return;
        tokenStore.set(tokenStore.get(), me);
        setUser(me);
      })
      .catch(() => {
        if (!alive) return;
        tokenStore.clear();
        setUser(null);
      })
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const payload = await api.login({ username, password });
    tokenStore.set(payload.token, payload.user);
    setUser(payload.user);
  }, []);

  const register = useCallback(async (username: string, password: string, code?: string) => {
    const payload = await api.register({ username, password, code });
    tokenStore.set(payload.token, payload.user);
    setUser(payload.user);
  }, []);

  const value = useMemo<AuthValue>(
    () => ({ user, ready, login, register, logout }),
    [user, ready, login, register, logout],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth 必须在 <AuthProvider> 内使用");
  return ctx;
}
