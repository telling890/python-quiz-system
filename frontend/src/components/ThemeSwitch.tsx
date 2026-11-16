import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type ThemeMode } from "../lib/theme";
import { cls } from "./ui";

const OPTIONS: Array<{ value: ThemeMode; label: string; Icon: typeof Sun }> = [
  { value: "auto", label: "跟随系统", Icon: Monitor },
  { value: "light", label: "浅色", Icon: Sun },
  { value: "dark", label: "深色", Icon: Moon },
];

/** 侧栏用：三档分段（跟随系统 / 浅色 / 深色） */
export function ThemeSwitch() {
  const { mode, setMode, resolved } = useTheme();
  return (
    <div className="flex items-center justify-between gap-2 rounded-xl border border-line bg-ink-850 px-2 py-1.5">
      <div className="flex min-w-0 items-center gap-1.5">
        <span className="grid size-6 place-items-center rounded-md bg-ink-800 text-fg-dim">
          {resolved === "light" ? <Sun size={12} /> : <Moon size={12} />}
        </span>
        <span className="truncate text-[0.66rem] text-fg-dim">
          {mode === "auto" ? "跟随系统" : mode === "light" ? "浅色" : "深色"}
        </span>
      </div>
      <div className="flex items-center gap-0.5 rounded-lg bg-ink-900 p-0.5">
        {OPTIONS.map(({ value, label, Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setMode(value)}
            title={label}
            aria-label={label}
            aria-pressed={mode === value}
            className={cls(
              "grid size-7 place-items-center rounded-md transition-colors",
              mode === value
                ? "bg-brand-500/20 text-brand-300"
                : "text-fg-dim hover:bg-ink-800 hover:text-fg-muted",
            )}
          >
            <Icon size={13} />
          </button>
        ))}
      </div>
    </div>
  );
}

/** 移动端顶栏用：点一下在 跟随系统 → 浅色 → 深色 之间切 */
export function ThemeCycleButton() {
  const { mode, cycle, resolved } = useTheme();
  const Icon = mode === "auto" ? Monitor : resolved === "light" ? Sun : Moon;
  return (
    <button
      type="button"
      onClick={cycle}
      title={`外观：${mode === "auto" ? "跟随系统" : mode === "light" ? "浅色" : "深色"}（点击切换）`}
      aria-label="切换浅色/深色外观"
      className="rounded-lg border border-line bg-ink-850 p-1.5 text-fg-muted shadow-sm transition-colors hover:bg-ink-800 hover:text-fg"
    >
      <Icon size={18} />
    </button>
  );
}
