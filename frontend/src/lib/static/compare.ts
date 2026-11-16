/** 输出归一化与首行差异：逻辑与后端 judge/compare.py 完全一致 */
import type { JudgeCaseResult } from "../types";

export function normalizeLines(text: string, keepIndent = false): string[] {
  if (!text) return [];
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const out: string[] = [];
  for (const raw of normalized.split("\n")) {
    if (keepIndent) {
      const line = raw.replace(/\s+$/, "");
      if (line.trim()) out.push(line);
    } else {
      const line = raw.replace(/[ \t\u3000]+/g, " ").trim();
      if (line) out.push(line);
    }
  }
  return out;
}

export function firstDiff(
  expectLines: string[],
  actualLines: string[],
): { line: number; expect: string | null; actual: string | null } | null {
  const total = Math.max(expectLines.length, actualLines.length);
  for (let i = 0; i < total; i += 1) {
    const e = i < expectLines.length ? expectLines[i] : null;
    const a = i < actualLines.length ? actualLines[i] : null;
    if (e !== a) return { line: i + 1, expect: e, actual: a };
  }
  return null;
}

/** 单条用例的判定（把一次 run 的结果变成 JudgeCaseResult） */
export function judgeCase(
  index: number,
  stdin: string,
  expect: string,
  actual: string,
  error: string,
  options: { timeout?: boolean; truncated?: boolean; raw?: boolean } = {},
): JudgeCaseResult {
  const expectLines = normalizeLines(expect, options.raw);
  const actualLines = normalizeLines(actual, options.raw);
  let status: JudgeCaseResult["status"] = "pass";
  let diff: JudgeCaseResult["first_diff"] = null;
  if (options.timeout) {
    status = "timeout";
  } else if (error) {
    status = "error";
  } else if (expectLines.join("\n") !== actualLines.join("\n")) {
    status = "fail";
    diff = firstDiff(expectLines, actualLines);
  }
  return {
    index,
    stdin,
    expect,
    actual,
    error,
    timeout: Boolean(options.timeout),
    truncated: Boolean(options.truncated),
    expect_lines: expectLines,
    actual_lines: actualLines,
    status,
    first_diff: diff,
  };
}
