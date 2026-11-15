import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, KeyRound, Sparkles, Terminal, User } from "lucide-react";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Button, cls, useToast } from "../components/ui";

type Mode = "login" | "register";

const HIGHLIGHTS = [
  "139 道教材题，写完 F5 就判，用例逐条比对",
  "执行过程单步追踪：看得见每一行的变量怎么变",
  "错题本、收藏、模拟组卷，进度跟着账号走",
];

const DEMO_CODE = `# 第 3 章 · 温度换算
c = float(input())
f = c * 9 / 5 + 32
print(f"{f:.1f}")`;

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const from = (location.state as { from?: string } | null)?.from || "/";

  if (user) return <Navigate to={from} replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");

    const name = username.trim();
    if (name.length < 3 || name.length > 32) {
      setError("用户名需要 3～32 个字符");
      return;
    }
    if (mode === "register" && password.length < 8) {
      setError("密码至少 8 位（服务端要求，太短会被拒）");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }

    setBusy(true);
    try {
      if (mode === "login") {
        await login(name, password);
        toast.ok(`欢迎回来，${name}`);
      } else {
        await register(name, password, code.trim());
        toast.ok("注册成功，已经帮你登录了");
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败，请稍后再试");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative z-10 grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      {/* 左：品牌区 */}
      <section className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-ink-900/40 p-10 lg:flex xl:p-14">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-aqua-400 text-white shadow-lg shadow-brand-600/30">
            <Sparkles size={18} />
          </span>
          <div>
            <p className="text-sm font-semibold tracking-tight">Python 程序设计刷题系统</p>
            <p className="text-[0.7rem] text-fg-dim">教材第 3～5 章 · 边写边判</p>
          </div>
        </div>

        <div className="max-w-md">
          <h1 className="text-balance text-3xl font-semibold leading-tight tracking-tight xl:text-4xl">
            把「写完不知道对不对」
            <br />
            变成 <span className="bg-gradient-to-r from-brand-300 to-aqua-400 bg-clip-text text-transparent">一按就判</span>
          </h1>
          <ul className="mt-7 space-y-3">
            {HIGHLIGHTS.map((text) => (
              <li key={text} className="flex items-start gap-2.5 text-sm text-fg-muted">
                <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-400" />
                {text}
              </li>
            ))}
          </ul>

          <div className="mt-8 overflow-hidden rounded-xl border border-line bg-ink-950/70 shadow-2xl">
            <div className="flex items-center gap-1.5 border-b border-line px-3 py-2">
              <span className="size-2.5 rounded-full bg-bad-500/70" />
              <span className="size-2.5 rounded-full bg-warn-400/70" />
              <span className="size-2.5 rounded-full bg-ok-500/70" />
              <span className="ml-2 flex items-center gap-1 text-[0.68rem] text-fg-dim">
                <Terminal size={11} /> main.py
              </span>
            </div>
            <pre className="code-surface overflow-x-auto px-4 py-3 text-[0.78rem] leading-relaxed text-fg-muted">
              {DEMO_CODE}
            </pre>
            <div className="flex items-center justify-between border-t border-line px-4 py-2 text-[0.68rem]">
              <span className="text-ok-400">✓ 3/3 用例通过 · 12 ms</span>
              <span className="text-fg-dim">F5 判题</span>
            </div>
          </div>
        </div>

        <p className="text-[0.68rem] text-fg-dim">
          账号与进度保存在你自己部署的后端（FastAPI + SQLite），不经过第三方。
        </p>
      </section>

      {/* 右：表单区 */}
      <section className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-aqua-400 text-white">
              <Sparkles size={16} />
            </span>
            <p className="text-sm font-semibold">Python 刷题系统</p>
          </div>

          <h2 className="text-xl font-semibold tracking-tight">
            {mode === "login" ? "登录你的账号" : "创建新账号"}
          </h2>
          <p className="mt-1 text-xs text-fg-dim">
            {mode === "login" ? "进度、错题本、草稿都会跟着账号走。" : "用户名 3～32 位字母/数字/下划线，密码至少 8 位。"}
          </p>

          <div className="mt-5 grid grid-cols-2 gap-1 rounded-xl border border-line bg-ink-900 p-1">
            {(["login", "register"] as Mode[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => {
                  setMode(item);
                  setError("");
                }}
                className={cls(
                  "rounded-lg py-1.5 text-[0.8125rem] font-medium transition-colors",
                  mode === item ? "bg-brand-500/20 text-brand-300" : "text-fg-muted hover:text-fg",
                )}
              >
                {item === "login" ? "登录" : "注册"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="mt-5 space-y-3.5">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-fg-muted">用户名</span>
              <div className="relative">
                <User size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-dim" />
                <input
                  className="input pl-9"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="例如 zhangsan"
                  autoComplete="username"
                  autoCapitalize="off"
                  spellCheck={false}
                  maxLength={32}
                />
              </div>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-fg-muted">密码</span>
              <div className="relative">
                <KeyRound size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-dim" />
                <input
                  className="input px-9"
                  type={showPwd ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === "register" ? "至少 8 位" : "输入密码"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  maxLength={128}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-fg-dim hover:text-fg"
                  aria-label={showPwd ? "隐藏密码" : "显示密码"}
                >
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </label>

            {mode === "register" ? (
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-fg-muted">
                  邀请码 <span className="font-normal text-fg-dim">（服务端没开就不填）</span>
                </span>
                <input
                  className="input"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="留空即可"
                  maxLength={64}
                />
              </label>
            ) : null}

            {error ? (
              <p className="animate-fade-in rounded-lg border border-bad-500/40 bg-bad-500/10 px-3 py-2 text-xs text-bad-400">
                {error}
              </p>
            ) : null}

            <Button type="submit" loading={busy} className="w-full" size="lg">
              {mode === "login" ? "登录" : "注册并登录"}
              {!busy ? <ArrowRight size={15} /> : null}
            </Button>
          </form>

          <p className="mt-4 text-center text-[0.7rem] leading-relaxed text-fg-dim">
            本地后端地址 <code className="text-fg-muted">http://127.0.0.1:8000</code>
            <br />
            注册被拒？可能开了邀请码：让管理员在 <code className="text-fg-muted">QUIZ_REGISTER_CODE</code> 里查。
          </p>
        </div>
      </section>
    </div>
  );
}
