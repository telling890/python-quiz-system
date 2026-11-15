# -*- coding: utf-8 -*-
"""子进程里的「单步执行」追踪器（只用标准库，保持 Python 3.8 兼容）。

与父进程的约定和 child_runner.py 完全一样：
  argv[1] 工作目录，里面必须有 main.py 和 stdin.txt
  结果写到 <workdir>/result.json

为什么追踪也要放进子进程
------------------------
桌面版 tracer.py 是在主进程里 settrace 的，那没问题，因为跑的是自己的代码。
搬到服务端就不一样了：陌生人的代码只要在开头写一句 ``sys.settrace(None)``
再跟一个 ``while True:``，看门狗就再也不会被触发，那个工作线程会被永久挂死。
放进子进程之后，父进程（executor.py）的「超时 + kill 整棵进程树」仍然是最后防线。

本脚本只负责：跑一遍、把每一步的（行号 / 函数 / 变量快照 / 累计输出）写进 result.json。
"""

import builtins
import io
import json
import os
import re
import sys
import threading
import time
import traceback

FILENAME = "<你的代码>"
MAX_OUTPUT = 20000
MAX_VARS = 12
MAX_VALUE = 48

# 与 judge/compare 的教学场景黑名单保持一致（子进程里没有 judge.py，单列一份）
_DENY_PATTERNS = [
    (r"\bos\s*\.\s*system\b", "os.system"),
    (r"\bos\s*\.\s*popen\b", "os.popen"),
    (r"\bos\s*\.\s*_exit\b", "os._exit"),
    (r"\bsubprocess\b", "subprocess"),
    (r"\bshutil\s*\.\s*rmtree\b", "shutil.rmtree"),
    (r"\bctypes\b", "ctypes"),
]


class _Timeout(BaseException):
    """超时/超步数信号：继承 BaseException，学习者的 except Exception 吞不掉。"""


def _denied(code):
    for pattern, name in _DENY_PATTERNS:
        if re.search(pattern, code):
            return name
    return None


def _reader(stream):
    def _input(prompt=""):
        line = stream.readline()
        if line == "":
            raise EOFError("EOF when reading a line")
        return line.rstrip("\r\n")

    return _input


def _format(value, limit=MAX_VALUE):
    """变量值转一行展示文本：换行/制表符变符号，超长截断。"""
    try:
        text = repr(value)
    except Exception:                             # noqa: BLE001 - 学习者对象可能什么都做不了
        text = "<{} 对象>".format(type(value).__name__)
    text = text.replace("\r\n", "\n").replace("\n", "⏎").replace("\t", "→")
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def _snapshot(frame):
    """当前帧的局部变量快照 -> ([[名字, 值], ...], 被省略的个数)。"""
    try:
        items = [(k, v) for k, v in list(frame.f_locals.items()) if not k.startswith("__")]
    except Exception:                             # noqa: BLE001
        return [], 0
    hidden = max(0, len(items) - MAX_VARS)
    return [[k, _format(v)] for k, v in items[:MAX_VARS]], hidden


def _depth(frame):
    """当前帧嵌在「学习者代码」里几层，用于区分主流程和函数内部。"""
    depth = 0
    f = frame.f_back
    while f is not None:
        if f.f_code.co_filename == FILENAME:
            depth += 1
        f = f.f_back
    return depth


def _write(workdir, result):
    path = os.path.join(workdir, "result.json")
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return 0


def main():
    workdir = sys.argv[1]
    with io.open(os.path.join(workdir, "main.py"), "r", encoding="utf-8") as f:
        code = f.read()
    with io.open(os.path.join(workdir, "stdin.txt"), "r", encoding="utf-8") as f:
        stdin_text = f.read()

    timeout = float(os.environ.get("TRACE_TIMEOUT") or 5.0)
    max_steps = max(1, int(os.environ.get("TRACE_MAX_STEPS") or 800))

    result = {"steps": [], "error": "", "timeout": False, "truncated": False,
              "output": "", "syntax": False}

    if not code.strip():
        result["error"] = "代码为空，先写点代码再单步执行吧"
        return _write(workdir, result)

    denied = _denied(code)
    if denied:
        result["error"] = "为安全起见，练习环境不允许使用 {}".format(denied)
        return _write(workdir, result)

    try:
        compiled = compile(code, FILENAME, "exec")
    except SyntaxError:
        exc_type, exc_value = sys.exc_info()[:2]
        result["error"] = "".join(
            traceback.format_exception_only(exc_type, exc_value)).strip()
        result["syntax"] = True
        return _write(workdir, result)

    if stdin_text and not stdin_text.endswith("\n"):
        stdin_text += "\n"

    buf = io.StringIO()
    stdin = io.StringIO(stdin_text)
    saved = (sys.stdout, sys.stdin, builtins.input)
    steps = []
    holder = {"error": ""}
    state = {"timeout": False, "truncated": False}

    def worker():
        sys.stdout = buf
        sys.stdin = stdin
        builtins.input = _reader(stdin)
        deadline = time.time() + timeout

        def tracer(frame, event, arg):
            if frame.f_code.co_filename != FILENAME:
                return None                       # 标准库/别的模块的帧不跟踪
            if len(steps) >= max_steps:
                state["truncated"] = True
                raise _Timeout()
            if time.time() > deadline:
                state["timeout"] = True
                raise _Timeout()
            out = buf.getvalue()
            if len(out) > MAX_OUTPUT:
                out = out[:MAX_OUTPUT]
            variables, hidden = _snapshot(frame)
            steps.append({
                "line": frame.f_lineno,
                "event": event,
                "func": frame.f_code.co_name,
                "depth": _depth(frame),
                "vars": variables,
                "hidden": hidden,
                "out": out,
            })
            return tracer

        try:
            sys.settrace(tracer)
            exec(compiled, {"__name__": "__main__", "__file__": FILENAME})
        except _Timeout:
            pass
        except SystemExit:
            pass
        except EOFError:
            holder["error"] = "EOFError：输入数据不够了，程序还想要更多输入"
        except BaseException:                     # noqa: BLE001 - 学习者代码可能抛任何东西
            exc_type, exc_value = sys.exc_info()[:2]
            holder["error"] = "".join(
                traceback.format_exception_only(exc_type, exc_value)).strip()
        finally:
            sys.settrace(None)
            try:
                sys.stdout, sys.stdin, builtins.input = saved
            except Exception:                     # noqa: BLE001
                pass

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout + 1.5)                    # 兜底：看门狗失效也不让父进程等死
    if thread.is_alive():
        state["timeout"] = True

    output = buf.getvalue()
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT]
        result["truncated"] = True

    result["steps"] = steps
    result["output"] = output
    result["error"] = holder["error"]
    result["timeout"] = bool(state["timeout"])
    result["truncated"] = bool(state["truncated"]) or result["truncated"]
    return _write(workdir, result)


if __name__ == "__main__":
    sys.exit(main())
