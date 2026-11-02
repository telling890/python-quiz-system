# -*- coding: utf-8 -*-
"""执行过程追踪：把代码逐行跑一遍，记下每一步的行号、变量与已输出内容。

判题（judge.py）只回答「输出对不对」，这里回答「代码是怎么跑成这样的」：
用 sys.settrace 的 call / line / return 事件走一遍学习者的代码，
每一步留一份快照（行号、所在函数、局部变量、当前累计输出），
界面拿 steps 就能做成可前后拖动的「时间轴」。

与判题共用同一套安全约定：
- input() 只从测试用例取数据、不回显提示语；
- 危险调用（os.system / subprocess / ctypes 等）沿用 judge 的黑名单；
- 死循环靠 settrace 看门狗打断，并额外限制总步数，避免追踪本身卡死。
"""

import io
import sys
import time
import builtins
import threading
import traceback

import judge

MAX_STEPS = 800          # 最多记录多少步（追踪会把执行放慢，必须封顶）
TRACE_TIMEOUT = 5.0      # 追踪阶段的看门狗（比判题更严一些，因为开追踪更慢）
MAX_VARS = 12            # 每一步最多列几个变量
MAX_VALUE = 48           # 变量值展示长度
MAX_OUTPUT = 20000       # 累计输出上限
FILENAME = "<你的代码>"


def format_value(value, limit=MAX_VALUE):
    """把变量值转成一行的展示文本（超长截断，换行与制表符转成符号）。"""
    try:
        text = repr(value)
    except Exception:
        text = "<{} 对象>".format(type(value).__name__)
    text = text.replace("\r\n", "\n").replace("\n", "⏎").replace("\t", "→")
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def _snapshot(frame):
    """取当前帧的局部变量快照，返回 (前 MAX_VARS 个 [(名字, 值)], 剩余个数)。"""
    try:
        local = frame.f_locals
        items = [(k, v) for k, v in list(local.items()) if not k.startswith("__")]
    except Exception:
        return [], 0
    hidden = max(0, len(items) - MAX_VARS)
    return [(k, format_value(v)) for k, v in items[:MAX_VARS]], hidden


def _depth(frame):
    """当前帧在「学习者的代码」里嵌了几层，用于区分主流程与函数内部。"""
    depth = 0
    f = frame.f_back
    while f is not None:
        if f.f_code.co_filename == FILENAME:
            depth += 1
        f = f.f_back
    return depth


def trace_code(code, stdin_text="", timeout=TRACE_TIMEOUT, max_steps=MAX_STEPS):
    """执行一遍代码并记录每一步。

    返回 dict：
      steps      [{"line", "event", "func", "depth", "vars", "hidden", "out"}, ...]
      error      出错时的提示文本（空字符串表示没出错）
      timeout    是否被看门狗打断
      truncated  是否因为步数超限而提前结束
      output     完整输出
      syntax     是否为语法错误
    """
    result = {"steps": [], "error": "", "timeout": False, "truncated": False,
              "output": "", "syntax": False}

    if not code or not code.strip():
        result["error"] = "代码为空，先写点代码再单步执行吧"
        return result

    denied = judge._denied(code)
    if denied:
        result["error"] = "为安全起见，练习环境不允许使用 {}".format(denied)
        return result

    try:
        compiled = compile(code, FILENAME, "exec")
    except SyntaxError:
        exc_type, exc_value = sys.exc_info()[:2]
        result["error"] = "".join(
            traceback.format_exception_only(exc_type, exc_value)).strip()
        result["syntax"] = True
        return result

    if stdin_text and not stdin_text.endswith("\n"):
        stdin_text += "\n"

    # 与判题共用一把锁：两者都会改 sys.stdout，不能同时跑
    with judge._LOCK:
        buf = io.StringIO()
        stdin = io.StringIO(stdin_text)
        steps = []
        holder = {"error": ""}
        state = {"timeout": False, "truncated": False}

        def worker():
            saved = (sys.stdout, sys.stdin, builtins.input, sys.gettrace())
            sys.stdout = buf
            sys.stdin = stdin
            builtins.input = judge._make_reader(stdin)
            deadline = time.time() + timeout

            def tracer(frame, event, arg):
                if frame.f_code.co_filename != FILENAME:
                    return None          # 别的模块的帧不跟踪
                if len(steps) >= max_steps:
                    state["truncated"] = True
                    raise judge._Timeout()
                if time.time() > deadline:
                    state["timeout"] = True
                    raise judge._Timeout()
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
                exec(compiled, {"__name__": "__main__"})
            except judge._Timeout:
                pass
            except SystemExit:
                pass
            except EOFError:
                holder["error"] = "EOFError：输入数据不够了，程序还想要更多输入"
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                holder["error"] = "".join(
                    traceback.format_exception_only(exc_type, exc_value)).strip()
            finally:
                sys.settrace(None)
                sys.stdout, sys.stdin, builtins.input = saved[0], saved[1], saved[2]

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout + 1.5)
        if thread.is_alive():
            state["timeout"] = True

        output = buf.getvalue()
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT]

    result["steps"] = steps
    result["output"] = output
    result["error"] = holder.get("error", "")
    result["timeout"] = bool(state["timeout"])
    result["truncated"] = bool(state["truncated"])
    return result


def describe(trace):
    """把一次追踪的结果总结成一句给用户看的话。"""
    steps = trace.get("steps") or []
    if trace.get("error"):
        return trace["error"]
    if trace.get("timeout"):
        return "执行超时，追踪在第 {} 步被打断（检查循环条件）".format(len(steps))
    if trace.get("truncated"):
        return "记录到前 {} 步就停了（循环太长，或者写成了死循环）".format(len(steps))
    return ""


def step_title(step):
    """一步的标题：第几行、在哪个函数里。"""
    func = step.get("func") or "<module>"
    line = step.get("line", 0)
    if step.get("depth", 0) > 0 and func != "<module>":
        return "第 {} 行 · 在 {}() 里".format(line, func)
    return "第 {} 行".format(line)
