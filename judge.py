# -*- coding: utf-8 -*-
"""判题引擎：在受控环境里执行学习者的代码，按测试用例比对输出。

设计要点
--------
1. input() 被替换成「只从测试用例取数据、不回显提示语」的版本，
   因此比较时不会混入 prompt 文本（例如 input("name: ")）。
2. print 的输出重定向到 StringIO，执行结束后取出。
3. sys.settrace 做超时看门狗，超时抛 BaseException 子类，
   学习者的 except Exception 无法吞掉它。
4. 判题前做轻量静态检查，拦掉会破坏本进程的危险调用（仅教学用途）。
"""

import io
import re
import sys
import time
import builtins
import threading
import traceback

RUN_TIMEOUT = 6.0
MAX_OUTPUT = 40000
_LOCK = threading.Lock()

# 教学场景下明显越界的调用，直接拒绝执行
_DENY_PATTERNS = [
    (r"\bos\s*\.\s*system\b", "os.system"),
    (r"\bos\s*\.\s*popen\b", "os.popen"),
    (r"\bos\s*\.\s*_exit\b", "os._exit"),
    (r"\bsubprocess\b", "subprocess"),
    (r"\bshutil\s*\.\s*rmtree\b", "shutil.rmtree"),
    (r"\bctypes\b", "ctypes"),
]


class _Timeout(BaseException):
    """超时信号：继承 BaseException，避免被学习者的 except Exception 捕获。"""


def normalize_lines(text, keep_indent=False):
    """把输出归一化：统一换行、压缩空白、去掉空行。

    默认忽略行首行尾空格与连续空白（expandtabs 对齐、格式微差不算错）；
    keep_indent=True 时保留行首空格，用于金字塔、图形这类靠缩进排版的题目。
    行内容与顺序始终严格比较。
    """
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for line in text.split("\n"):
        if keep_indent:
            line = line.rstrip()
            if line.strip():
                out.append(line)
        else:
            line = re.sub(r"[ \t\u3000]+", " ", line).strip()
            if line:
                out.append(line)
    return out


def _make_reader(stream):
    def _input(prompt=""):
        line = stream.readline()
        if line == "":
            raise EOFError("EOF when reading a line")
        return line.rstrip("\r\n")
    return _input


def _denied(code):
    for pattern, name in _DENY_PATTERNS:
        if re.search(pattern, code):
            return name
    return None


def run_code(code, stdin_text="", timeout=RUN_TIMEOUT):
    """执行一段代码，返回 dict(output, error, timeout, truncated)。"""
    result = {"output": "", "error": "", "timeout": False, "truncated": False}

    if not code or not code.strip():
        result["error"] = "代码为空，先写点东西再运行吧"
        return result

    denied = _denied(code)
    if denied:
        result["error"] = "为安全起见，练习环境不允许使用 {}".format(denied)
        return result

    if stdin_text and not stdin_text.endswith("\n"):
        stdin_text += "\n"

    with _LOCK:
        buf = io.StringIO()
        stdin = io.StringIO(stdin_text)
        holder = {}
        fired = {"v": False}

        def worker():
            saved = (sys.stdout, sys.stdin, builtins.input, sys.gettrace())
            sys.stdout = buf
            sys.stdin = stdin
            builtins.input = _make_reader(stdin)

            deadline = time.time() + timeout

            def tracer(frame, event, arg):
                if not fired["v"] and time.time() > deadline:
                    fired["v"] = True
                    raise _Timeout()
                return tracer

            try:
                sys.settrace(tracer)
                exec(compile(code, "<你的代码>", "exec"), {"__name__": "__main__"})
            except _Timeout:
                holder["timeout"] = True
            except SystemExit:
                pass
            except EOFError:
                holder["error"] = "EOFError：输入数据不够了，程序还想要更多输入（看看测试用例给了几行）"
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                holder["error"] = "".join(
                    traceback.format_exception_only(exc_type, exc_value)
                ).strip()
            finally:
                sys.settrace(None)
                sys.stdout, sys.stdin, builtins.input = saved[0], saved[1], saved[2]

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout + 1.5)

        if thread.is_alive():
            result["timeout"] = True

        output = buf.getvalue()
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT]
            result["truncated"] = True

    result["output"] = output
    result["timeout"] = bool(holder.get("timeout")) or result["timeout"]
    result["error"] = holder.get("error", "")
    return result


def run_case(code, case, timeout=RUN_TIMEOUT):
    """跑单个测试用例并给出判定。

    case["raw"] 为真时保留行首空格（图形类题目需要）。
    """
    run = run_code(code, case.get("stdin", ""), timeout)
    raw = bool(case.get("raw"))
    expect_lines = normalize_lines(case.get("expect", ""), keep_indent=raw)
    actual_lines = normalize_lines(run["output"], keep_indent=raw)

    item = {
        "stdin": case.get("stdin", ""),
        "expect": case.get("expect", ""),
        "actual": run["output"],
        "error": run["error"],
        "timeout": run["timeout"],
        "truncated": run["truncated"],
        "expect_lines": expect_lines,
        "actual_lines": actual_lines,
        "status": "fail",
        "first_diff": None,
    }

    if run["timeout"]:
        item["status"] = "timeout"
    elif run["error"]:
        item["status"] = "error"
    elif actual_lines == expect_lines:
        item["status"] = "pass"
    else:
        item["status"] = "fail"
        item["first_diff"] = _first_diff(expect_lines, actual_lines)

    return item


def _first_diff(expect_lines, actual_lines):
    total = max(len(expect_lines), len(actual_lines))
    for i in range(total):
        e = expect_lines[i] if i < len(expect_lines) else None
        a = actual_lines[i] if i < len(actual_lines) else None
        if e != a:
            return {"line": i + 1, "expect": e, "actual": a}
    return None


def judge(code, cases, timeout=RUN_TIMEOUT):
    """跑完全部用例，返回 (是否全过, 结果列表)。第一个用例失败即停止（可用 stop_on_fail 控制）。"""
    results = []
    for case in cases:
        item = run_case(code, case, timeout)
        results.append(item)
        if item["status"] != "pass":
            break
    passed = bool(results) and all(r["status"] == "pass" for r in results)
    return passed, results
