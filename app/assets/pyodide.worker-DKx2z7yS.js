const d="0.27.7",i=`https://cdn.jsdelivr.net/pyodide/v${d}/full/`,l=`
import builtins
import io
import json
import sys
import time
import traceback

_FILENAME = "<你的代码>"
_MAX_VARS = 12
_MAX_VALUE = 48
_MAX_OUTPUT = 20000


class _Timeout(BaseException):
    pass


def _fmt(value):
    try:
        text = repr(value)
    except Exception:
        text = "<{} 对象>".format(type(value).__name__)
    text = text.replace("\\r\\n", "\\n").replace("\\n", "\\u23ce").replace("\\t", "\\u2192")
    if len(text) > _MAX_VALUE:
        text = text[:_MAX_VALUE] + "\\u2026"
    return text


def _snapshot(frame):
    try:
        items = [(k, v) for k, v in list(frame.f_locals.items()) if not k.startswith("__")]
    except Exception:
        return [], 0
    hidden = max(0, len(items) - _MAX_VARS)
    return [[k, _fmt(v)] for k, v in items[:_MAX_VARS]], hidden


def _depth(frame):
    depth = 0
    f = frame.f_back
    while f is not None:
        if f.f_code.co_filename == _FILENAME:
            depth += 1
        f = f.f_back
    return depth


def _reader(stream):
    def _input(prompt=""):
        line = stream.readline()
        if line == "":
            raise EOFError("EOF when reading a line")
        return line.rstrip("\\r\\n")
    return _input


def _pyquiz_run(code, stdin_text):
    """执行一次：捕获 stdout 与异常，返回 JSON 字符串。"""
    buf = io.StringIO()
    old_out, old_in, old_input = sys.stdout, sys.stdin, builtins.input
    if stdin_text and not stdin_text.endswith("\\n"):
        stdin_text += "\\n"
    stream = io.StringIO(stdin_text)
    sys.stdout = buf
    sys.stdin = stream
    builtins.input = _reader(stream)
    err = ""
    started = time.perf_counter()
    try:
        exec(compile(code, _FILENAME, "exec"), {"__name__": "__main__", "__file__": _FILENAME})
    except SystemExit:
        pass
    except BaseException:
        err = "".join(traceback.format_exception_only(*sys.exc_info()[:2])).strip()
    finally:
        sys.stdout, sys.stdin, builtins.input = old_out, old_in, old_input
    # 浏览器里跑一段小代码可能不到 1ms，用 int() 会变成 0（界面上就成了「—」），
    # 所以这里保留 0.1ms 精度
    return json.dumps({"output": buf.getvalue(), "error": err,
                       "duration_ms": round((time.perf_counter() - started) * 1000, 2)}, ensure_ascii=False)


def _pyquiz_trace(code, stdin_text, timeout=5.0, max_steps=800):
    """逐行追踪：记录行号/函数/局部变量/累计输出。"""
    result = {"steps": [], "error": "", "timeout": False, "truncated": False,
              "output": "", "syntax": False}
    if not code.strip():
        result["error"] = "代码为空，先写点代码再单步执行吧"
        return json.dumps(result, ensure_ascii=False)
    try:
        compiled = compile(code, _FILENAME, "exec")
    except SyntaxError:
        result["error"] = "".join(traceback.format_exception_only(*sys.exc_info()[:2])).strip()
        result["syntax"] = True
        return json.dumps(result, ensure_ascii=False)

    steps = []
    buf = io.StringIO()
    old_out, old_in, old_input = sys.stdout, sys.stdin, builtins.input
    if stdin_text and not stdin_text.endswith("\\n"):
        stdin_text += "\\n"
    stream = io.StringIO(stdin_text)
    state = {"timeout": False, "truncated": False}
    deadline = time.time() + timeout

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != _FILENAME:
            return None
        if len(steps) >= max_steps:
            state["truncated"] = True
            raise _Timeout()
        if time.time() > deadline:
            state["timeout"] = True
            raise _Timeout()
        line = frame.f_lineno
        if line <= 0:
            return tracer
        variables, hidden = _snapshot(frame)
        steps.append({
            "line": line,
            "event": event,
            "func": frame.f_code.co_name,
            "depth": _depth(frame),
            "vars": variables,
            "hidden": hidden,
            "out": buf.getvalue()[:_MAX_OUTPUT],
        })
        return tracer

    sys.stdout = buf
    sys.stdin = stream
    builtins.input = _reader(stream)
    try:
        sys.settrace(tracer)
        exec(compiled, {"__name__": "__main__", "__file__": _FILENAME})
    except _Timeout:
        pass
    except SystemExit:
        pass
    except EOFError:
        result["error"] = "EOFError：输入数据不够了，程序还想要更多输入"
    except BaseException:
        result["error"] = "".join(traceback.format_exception_only(*sys.exc_info()[:2])).strip()
    finally:
        sys.settrace(None)
        sys.stdout, sys.stdin, builtins.input = old_out, old_in, old_input

    output = buf.getvalue()
    if len(output) > _MAX_OUTPUT:
        output = output[:_MAX_OUTPUT]
        result["truncated"] = True
    result["steps"] = steps
    result["output"] = output
    result["timeout"] = bool(state["timeout"])
    result["truncated"] = bool(state["truncated"]) or result["truncated"]
    return json.dumps(result, ensure_ascii=False)
`;let s=null;async function p(){const e=await(await import(`${i}pyodide.mjs`)).loadPyodide({indexURL:i});return e.runPython(l),e}self.onmessage=async r=>{const{id:e,kind:n,code:o,stdin:a}=r.data;try{s||(s=p());const t=await s;t.globals.set("__pyquiz_code",o),t.globals.set("__pyquiz_stdin",a??"");const u=n==="trace"?"_pyquiz_trace":"_pyquiz_run",_=t.runPython(`${u}(__pyquiz_code, __pyquiz_stdin)`);self.postMessage({id:e,ok:!0,data:String(_)})}catch(t){s=null,self.postMessage({id:e,ok:!1,error:String((t==null?void 0:t.message)??t)})}};
