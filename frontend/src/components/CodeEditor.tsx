import { useEffect, useMemo, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView, keymap } from "@codemirror/view";
import { Prec } from "@codemirror/state";
import { cls } from "./ui";

export interface CodeEditorProps {
  value: string;
  onChange: (next: string) => void;
  /** Ctrl/Cmd + Enter 触发 */
  onRun?: () => void;
  /** Ctrl/Cmd + S 触发 */
  onSave?: () => void;
  readOnly?: boolean;
  height?: string;
  className?: string;
  placeholder?: string;
}

export default function CodeEditor({
  value,
  onChange,
  onRun,
  onSave,
  readOnly = false,
  height = "340px",
  className,
  placeholder,
}: CodeEditorProps) {
  const onRunRef = useRef(onRun);
  const onSaveRef = useRef(onSave);
  onRunRef.current = onRun;
  onSaveRef.current = onSave;

  const extensions = useMemo(
    () => [
      python(),
      EditorView.lineWrapping,
      Prec.highest(
        keymap.of([
          {
            key: "Mod-Enter",
            run: () => {
              onRunRef.current?.();
              return true;
            },
          },
          {
            key: "Mod-s",
            preventDefault: true,
            run: () => {
              onSaveRef.current?.();
              return true;
            },
          },
        ]),
      ),
    ],
    [],
  );

  // CodeMirror 受控更新时尽量保留光标：value 由外部改（切换题目）才重设
  const lastExternal = useRef(value);
  useEffect(() => {
    lastExternal.current = value;
  }, [value]);

  return (
    <div
      className={cls("overflow-hidden rounded-xl border border-line bg-ink-950/60", className)}
      style={{ height }}
    >
      <CodeMirror
        value={value}
        onChange={(next) => onChange(next)}
        theme={oneDark}
        extensions={extensions}
        height="100%"
        readOnly={readOnly}
        placeholder={placeholder}
        basicSetup={{
          lineNumbers: true,
          foldGutter: false,
          highlightActiveLine: true,
          highlightActiveLineGutter: true,
          autocompletion: true,
          bracketMatching: true,
          closeBrackets: true,
          indentOnInput: true,
          tabSize: 4,
        }}
        style={{ fontSize: "0.8125rem" }}
      />
    </div>
  );
}
