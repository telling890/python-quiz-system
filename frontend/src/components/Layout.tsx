import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  BookMarked,
  Code2,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  RefreshCw,
  Sparkles,
  Terminal,
  X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { useBank } from "../lib/bank";
import { IS_STATIC } from "../lib/api";
import { pct } from "../lib/format";
import { cls, ProgressBar, useToast } from "./ui";

const NAV = [
  { to: "/", label: "概览", icon: LayoutDashboard, end: true },
  { to: "/practice", label: "刷题", icon: Code2 },
  { to: "/book", label: "题本", icon: BookMarked },
  { to: "/free", label: "自由编程", icon: Terminal },
  { to: "/stats", label: "统计", icon: BarChart3 },
  { to: "/exam", label: "模拟组卷", icon: ListChecks },
] as const;

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5 px-1.5 py-1">
      <span className="relative grid size-9 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-aqua-400 text-white shadow-lg shadow-brand-600/30">
        <Sparkles size={17} />
      </span>
      <span className="leading-tight">
        <span className="block text-[0.9rem] font-semibold tracking-tight text-fg">Python 刷题系统</span>
        <span className="block text-[0.68rem] text-fg-dim">边写边判 · 第 3～5 章</span>
      </span>
    </Link>
  );
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={"end" in item ? item.end : undefined}
          onClick={onNavigate}
          className={({ isActive }) => cls("nav-item", isActive && "nav-item-active")}
        >
          <item.icon size={16} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { stats, loading, reload, error } = useBank();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawer, setDrawer] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    setDrawer(false);
  }, [location.pathname]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await reload();
      toast.ok("题库与进度已刷新");
    } finally {
      setRefreshing(false);
    }
  };

  const onLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const solvedPct = pct(stats.solved, stats.total);

  const sidebar = (
    <div className="flex h-full flex-col gap-4 p-3">
      <Brand />
      <div className="panel-flat px-3 py-2.5">
        <div className="flex items-baseline justify-between text-[0.7rem] text-fg-dim">
          <span>总进度</span>
          <span className="tabular-nums text-fg-muted">
            {stats.solved}/{stats.total}
          </span>
        </div>
        <ProgressBar value={stats.solved} max={stats.total || 1} className="mt-2" height={5} />
        <div className="mt-1.5 text-[0.66rem] text-fg-dim">
          {loading ? "加载中…" : error ? <span className="text-bad-400">{error}</span> : `覆盖率 ${solvedPct}% · 通过 ${stats.passes} 次`}
        </div>
        {IS_STATIC ? (
          <div className="mt-1.5 rounded-md border border-line bg-ink-900/60 px-1.5 py-1 text-[0.6rem] leading-snug text-fg-dim">
            静态版 · 进度存在本机浏览器
          </div>
        ) : null}
      </div>
      <NavItems />
      <div className="mt-auto flex flex-col gap-2">
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing || loading}
          className="nav-item w-full disabled:opacity-50"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : undefined} />
          刷新进度
        </button>
        <div className="flex items-center gap-2 rounded-xl border border-line bg-ink-850 px-2.5 py-2">
          <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-brand-500/20 text-xs font-semibold text-brand-300">
            {(user?.username ?? "?").slice(0, 1).toUpperCase()}
          </span>
          <span className="min-w-0 flex-1 truncate text-xs text-fg-muted">{user?.username}</span>
          <button
            type="button"
            onClick={onLogout}
            title="退出登录"
            className="rounded-lg p-1.5 text-fg-dim transition-colors hover:bg-ink-750 hover:text-bad-400"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="relative z-10 flex min-h-dvh">
      {/* 桌面侧栏 */}
      <aside className="sticky top-0 hidden h-dvh w-[15.5rem] shrink-0 border-r border-line bg-ink-900/60 backdrop-blur lg:block">
        {sidebar}
      </aside>

      {/* 移动端抽屉 */}
      {drawer ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink-950/80 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <aside className="animate-rise absolute inset-y-0 left-0 w-[16rem] border-r border-line bg-ink-900">
            {sidebar}
          </aside>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* 移动端顶栏 */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-ink-950/85 px-4 py-2.5 backdrop-blur lg:hidden">
          <button
            type="button"
            onClick={() => setDrawer((v) => !v)}
            className="rounded-lg border border-line p-1.5 text-fg-muted"
            aria-label="打开菜单"
          >
            {drawer ? <X size={18} /> : <Menu size={18} />}
          </button>
          <span className="text-sm font-semibold">Python 刷题系统</span>
          <span className="rounded-full bg-brand-500/15 px-2 py-1 text-[0.7rem] tabular-nums text-brand-300">
            {stats.solved}/{stats.total}
          </span>
        </header>

        <main className="mx-auto w-full max-w-[1500px] flex-1 px-3 pt-4 pb-24 sm:px-5 lg:pb-8">
          <Outlet />
        </main>

        {/* 移动端底部导航 */}
        <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-6 border-t border-line bg-ink-900/95 backdrop-blur lg:hidden">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : undefined}
              className={({ isActive }) =>
                cls(
                  "flex flex-col items-center gap-1 py-2 text-[0.62rem] transition-colors",
                  isActive ? "text-brand-300" : "text-fg-dim",
                )
              }
            >
              <item.icon size={17} />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}

export function PageTitle({
  title,
  subtitle,
  right,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg sm:text-2xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-xs text-fg-dim sm:text-sm">{subtitle}</p> : null}
      </div>
      {right ? <div className="flex flex-wrap items-center gap-2">{right}</div> : null}
    </div>
  );
}
