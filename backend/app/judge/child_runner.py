# -*- coding: utf-8 -*-
"""子进程里真正执行学习者代码的脚本（只用标准库，保持 Python 3.8 兼容）。

父进程（executor.py）负责：临时目录、超时、内存限制、杀进程树。
本脚本只负责：把 code 跑一遍，把输出/报错写进 result.json。

约定：
  argv[1] 工作目录，里面必须有 main.py 和 stdin.txt
  执行结果写到 <workdir>/result.json
"""

import builtins
import io
import json
import os
import sys
import traceback

MAX_OUTPUT = 40000
FILENAME = "<你的代码>"


def _reader(stream):
    def _input(prompt=""):
        line = stream.readline()
        if line == "":
            raise EOFError("EOF when reading a line")
        return line.rstrip("\r\n")
    return _input


def main():
    workdir = sys.argv[1]
    with io.open(os.path.join(workdir, "main.py"), "r", encoding="utf-8") as f:
        code = f.read()
    with io.open(os.path.join(workdir, "stdin.txt"), "r", encoding="utf-8") as f:
        stdin_text = f.read()

    result = {"output": "", "error": "", "truncated": False, "syntax": False}

    if not code.strip():
        result["error"] = "代码为空，先写点东西再运行吧"
        return _write(workdir, result)

    if stdin_text and not stdin_text.endswith("\n"):
        stdin_text += "\n"

    try:
        compiled = compile(code, FILENAME, "exec")
    except SyntaxError:
        exc_type, exc_value = sys.exc_info()[:2]
        result["error"] = "".join(traceback.format_exception_only(exc_type, exc_value)).strip()
        result["syntax"] = True
        return _write(workdir, result)

    buf = io.StringIO()
    stdin = io.StringIO(stdin_text)
    saved = (sys.stdout, sys.stdin, builtins.input)
    sys.stdout = buf
    sys.stdin = stdin
    builtins.input = _reader(stdin)

    try:
        exec(compiled, {"__name__": "__main__", "__file__": FILENAME})
    except SystemExit:
        pass
    except KeyboardInterrupt:
        result["error"] = "执行被中断"
    except BaseException:                     # noqa: BLE001 - 学习者代码可能是任何异常
        exc_type, exc_value = sys.exc_info()[:2]
        result["error"] = "".join(
            traceback.format_exception_only(exc_type, exc_value)).strip()
    finally:
        sys.stdout, sys.stdin, builtins.input = saved

    output = buf.getvalue()
    limit = int(os.environ.get("JUDGE_OUTPUT_LIMIT", MAX_OUTPUT))
    if len(output) > limit:
        output = output[:limit]
        result["truncated"] = True
    result["output"] = output
    return _write(workdir, result)


def _write(workdir, result):
    path = os.path.join(workdir, "result.json")
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
