import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, Info, Loader2, TriangleAlert, X } from "lucide-react";

/* ============================== 小工具 ============================== */

export function cls(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/* ============================== Button ============================== */

type ButtonVariant = "primary" | "ghost" | "soft" | "danger";
type ButtonSize = "sm" | "md" | "lg" | "icon";

const VARIANT: Record<ButtonVariant, string> = {
  primary: "btn btn-primary",
  ghost: "btn btn-ghost",
  soft: "btn btn-soft",
  danger: "btn btn-danger",
};

const SIZE: Record<ButtonSize, string> = {
  sm: "text-xs px-2.5 py-1.5 rounded-lg",
  md: "",
  lg: "text-base px-5 py-3",
  icon: "p-2 rounded-lg",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cls(VARIANT[variant], SIZE[size], className)}
    >
      {loading ? <Loader2 size={15} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}

/* ============================== 面板 ============================== */

export function Card({
  children,
  className,
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article" | "aside";
}) {
  return <Tag className={cls("panel", className)}>{children}</Tag>;
}

export function CardHeader({
  title,
  subtitle,
  icon,
  right,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cls("flex items-start justify-between gap-3 px-4 pt-4 pb-3 sm:px-5", className)}>
      <div className="flex min-w-0 items-start gap-2.5">
        {icon ? <span className="mt-0.5 text-brand-300">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className="truncate text-[0.95rem] font-semibold text-fg">{title}</h2>
          {subtitle ? <p className="mt-0.5 text-xs text-fg-dim">{subtitle}</p> : null}
        </div>
      </div>
      {right ? <div className="flex shrink-0 items-center gap-2">{right}</div> : null}
    </div>
  );
}

/* ============================== 标签 ============================== */

type Tone = "neutral" | "brand" | "ok" | "warn" | "bad" | "aqua";

const TONE: Record<Tone, string> = {
  neutral: "border-line bg-ink-800 text-fg-muted",
  brand: "border-brand-500/40 bg-brand-500/15 text-brand-300",
  ok: "border-ok-500/40 bg-ok-500/15 text-ok-400",
  warn: "border-warn-400/40 bg-warn-400/15 text-warn-400",
  bad: "border-bad-500/40 bg-bad-500/15 text-bad-400",
  aqua: "border-aqua-400/40 bg-aqua-400/15 text-aqua-400",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return <span className={cls("chip", TONE[tone], className)}>{children}</span>;
}

/* ============================== 加载 / 空态 ============================== */

export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return <Loader2 size={size} className={cls("animate-spin text-fg-dim", className)} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cls("animate-shimmer rounded-lg bg-ink-750", className)} />;
}

export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode;
  title: string;
  hint?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      {icon ? <div className="rounded-2xl border border-line bg-ink-800 p-3 text-fg-dim">{icon}</div> : null}
      <div>
        <p className="text-sm font-semibold text-fg">{title}</p>
        {hint ? <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-fg-dim">{hint}</p> : null}
      </div>
      {action}
    </div>
  );
}

/* ============================== 进度条 ============================== */

export function ProgressBar({
  value,
  max = 100,
  tone = "brand",
  className,
  height = 6,
}: {
  value: number;
  max?: number;
  tone?: "brand" | "ok" | "warn" | "aqua";
  className?: string;
  height?: number;
}) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  const color = {
    brand: "from-brand-500 to-brand-400",
    ok: "from-ok-500 to-ok-400",
    warn: "from-warn-400 to-amber-300",
    aqua: "from-aqua-400 to-cyan-300",
  }[tone];
  return (
    <div
      className={cls("w-full overflow-hidden rounded-full bg-ink-700", className)}
      style={{ height }}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cls("h-full rounded-full bg-gradient-to-r transition-[width] duration-500 ease-out", color)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/* ============================== 分段控件 ============================== */

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  className,
  size = "md",
}: {
  options: Array<{ value: T; label: ReactNode; count?: number }>;
  value: T;
  onChange: (next: T) => void;
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <div className={cls("inline-flex flex-wrap gap-1 rounded-xl border border-line bg-ink-900 p-1", className)}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cls(
              "inline-flex items-center gap-1.5 rounded-lg font-medium transition-colors",
              size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-[0.8125rem]",
              active ? "bg-brand-500/20 text-brand-300 shadow-[inset_0_0_0_1px_rgba(99,102,241,0.35)]" : "text-fg-muted hover:bg-ink-800 hover:text-fg",
            )}
            aria-pressed={active}
          >
            {opt.label}
            {typeof opt.count === "number" ? (
              <span className={cls("tabular-nums", active ? "text-brand-300/80" : "text-fg-dim")}>{opt.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

/* ============================== 弹窗 ============================== */

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  width = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
      <div className="overlay absolute inset-0 animate-fade-in" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className={cls(
          "panel animate-pop relative z-10 max-h-[88vh] w-full overflow-hidden rounded-b-none sm:rounded-2xl",
          width,
        )}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h3 className="text-sm font-semibold text-fg">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-fg-dim transition-colors hover:bg-ink-750 hover:text-fg"
            aria-label="关闭"
          >
            <X size={16} />
          </button>
        </div>
        <div className="max-h-[62vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer ? <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}

/* ============================== 轻提示 ============================== */

type ToastKind = "ok" | "bad" | "info" | "warn";
interface ToastItem {
  id: number;
  kind: ToastKind;
  text: string;
}

interface ToastApi {
  ok: (text: string) => void;
  bad: (text: string) => void;
  info: (text: string) => void;
  warn: (text: string) => void;
}

const ToastCtx = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);

  const push = useCallback((kind: ToastKind, text: string) => {
    const id = ++seq.current;
    setItems((prev) => [...prev.slice(-3), { id, kind, text }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, kind === "bad" ? 5200 : 3000);
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      ok: (t) => push("ok", t),
      bad: (t) => push("bad", t),
      info: (t) => push("info", t),
      warn: (t) => push("warn", t),
    }),
    [push],
  );

  return (
    <ToastCtx.Provider value={api}>
      {children}
      {createPortal(
        <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:right-6 sm:left-auto sm:items-end">
          {items.map((t) => {
            const Icon = t.kind === "ok" ? CheckCircle2 : t.kind === "bad" ? TriangleAlert : t.kind === "warn" ? TriangleAlert : Info;
            const toneCls =
              t.kind === "ok"
                ? "border-ok-500/40 text-ok-400"
                : t.kind === "bad"
                  ? "border-bad-500/40 text-bad-400"
                  : t.kind === "warn"
                    ? "border-warn-400/40 text-warn-400"
                    : "border-brand-500/40 text-brand-300";
            return (
              <div
                key={t.id}
                className={cls(
                  "animate-rise pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-xl border bg-ink-850/95 px-3.5 py-2.5 text-sm shadow-2xl backdrop-blur",
                  toneCls,
                )}
              >
                <Icon size={16} className="mt-0.5 shrink-0" />
                <span className="text-fg-muted">{t.text}</span>
              </div>
            );
          })}
        </div>,
        document.body,
      )}
    </ToastCtx.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast 必须在 <ToastProvider> 内使用");
  return ctx;
}
