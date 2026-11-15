# -*- coding: utf-8 -*-
"""沙箱执行器：把学习者代码放进**独立子进程**跑，父进程只负责计时和收尸。

为什么必须离开主进程（相比桌面版 judge.py 的 exec）：
1. 学习者代码再也拿不到本项目的模块，不能 `import qbank` 偷答案、改进度；
2. 死循环靠 kill 进程解决，而不是 settrace 看门狗，`while True:` 也杀得掉；
3. 内存上限（POSIX rlimit）与输出上限在进程边界生效，炸不到 API 服务本身。

Windows 上没有 rlimit，内存限制靠部署层（Docker 的 mem_limit / Job Object）兜底，
这点在 README 里写清楚，不假装自己做到了。

对外只有两个函数：
- run_python(code, stdin)  -> 跑一遍，拿输出（判题/自由编程用）
- run_trace(code, stdin)   -> 跑一遍并录下每一步（单步执行用）
两者共用同一套临时目录、超时、rlimit、杀进程树逻辑，只是换了个子进程脚本。
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from ..config import get_settings

RUNNER = Path(__file__).with_name("child_runner.py")
TRACE_RUNNER = Path(__file__).with_name("trace_runner.py")
_MAX_SANDBOX = threading.BoundedSemaphore(8)


def _sandbox_limits(timeout, memory_mb):
    """POSIX 下的资源限制（Windows 直接跳过）。"""

    def _apply():
        import resource

        mem = max(64, memory_mb) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        cpu = int(timeout) + 1
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024,) * 2)

    return _apply


def _kill_tree(proc):
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                           timeout=10)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


def _child_env(workdir):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TEMP": workdir,
        "TMP": workdir,
        "TMPDIR": workdir,
        "HOME": workdir,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    return {k: v for k, v in env.items() if v}


def _fallback_output(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _execute(code, stdin, runner, timeout, memory_mb, output_limit, extra_env=None):
    """在受限子进程里跑 runner，返回 payload 与现场信息（不做业务解释）。

    runner 约定：自己把结果写进 <workdir>/result.json，格式由 runner 决定。
    """
    settings = get_settings()
    os.makedirs(settings.judge_tmp, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="run-", dir=settings.judge_tmp)
    out_path = os.path.join(workdir, "stdout.txt")
    err_path = os.path.join(workdir, "stderr.txt")

    stat = {"payload": None, "stdout": "", "stderr": "", "timeout": False,
            "duration_ms": 0}

    with _MAX_SANDBOX:
        started = time.time()
        stdout_fh = stderr_fh = None
        proc = None
        try:
            with open(os.path.join(workdir, "main.py"), "w", encoding="utf-8") as f:
                f.write(code)
            with open(os.path.join(workdir, "stdin.txt"), "w", encoding="utf-8") as f:
                f.write(stdin or "")

            stdout_fh = open(out_path, "wb")
            stderr_fh = open(err_path, "wb")
            cmd = [sys.executable, "-I", "-B", "-S", str(runner), workdir]
            env = dict(_child_env(workdir), JUDGE_OUTPUT_LIMIT=str(output_limit))
            for key, value in (extra_env or {}).items():
                env[key] = str(value)
            kwargs = {
                "cwd": workdir,
                "env": env,
                "stdin": subprocess.DEVNULL,
                "stdout": stdout_fh,
                "stderr": stderr_fh,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = (subprocess.CREATE_NO_WINDOW
                                           | subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                kwargs["start_new_session"] = True
                kwargs["preexec_fn"] = _sandbox_limits(timeout, memory_mb)

            proc = subprocess.Popen(cmd, **kwargs)
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                stat["timeout"] = True
                _kill_tree(proc)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            for fh in (stdout_fh, stderr_fh):
                if fh is not None:
                    try:
                        fh.close()
                    except OSError:
                        pass

        stat["duration_ms"] = int((time.time() - started) * 1000)
        try:
            with open(os.path.join(workdir, "result.json"), "r", encoding="utf-8") as f:
                stat["payload"] = json.load(f)
        except (OSError, ValueError):
            stat["payload"] = None

        stat["stdout"] = _fallback_output(out_path)
        stat["stderr"] = _fallback_output(err_path).strip()
        shutil.rmtree(workdir, ignore_errors=True)
    return stat


def run_python(code, stdin="", timeout=None, memory_mb=None, output_limit=None):
    """执行一段 Python 代码，返回 dict(output, error, timeout, truncated, syntax, duration_ms)。"""
    settings = get_settings()
    timeout = float(timeout or settings.judge_timeout)
    memory_mb = int(memory_mb or settings.judge_memory_mb)
    output_limit = int(output_limit or settings.judge_output_limit)

    stat = _execute(code, stdin, RUNNER, timeout, memory_mb, output_limit)
    payload = stat["payload"]

    result = {"output": "", "error": "", "timeout": stat["timeout"], "truncated": False,
              "syntax": False, "duration_ms": stat["duration_ms"]}

    if payload is not None:
        result["output"] = str(payload.get("output") or "")
        result["error"] = str(payload.get("error") or "")
        result["truncated"] = bool(payload.get("truncated"))
        result["syntax"] = bool(payload.get("syntax"))
    elif not result["timeout"]:
        # 子进程没写出结果：多半是被 OOM 杀掉或直接 os._exit 了
        result["output"] = stat["stdout"][:output_limit]
        result["error"] = ("进程异常退出（可能内存超限或被强制终止）"
                           + (": " + stat["stderr"][:500] if stat["stderr"] else ""))
    else:
        result["output"] = stat["stdout"][:output_limit]

    return result


def run_trace(code, stdin="", timeout=None, max_steps=None, memory_mb=None):
    """执行一遍并录下每一步，返回 dict(steps, error, timeout, truncated, output, syntax, duration_ms)。

    steps 里每一步是 {"line", "event", "func", "depth", "vars", "hidden", "out"}，
    与桌面版 tracer.py 的结构完全一致，前端「执行过程」面板直接能用。
    """
    settings = get_settings()
    timeout = float(timeout or settings.trace_timeout)
    max_steps = int(max_steps or settings.trace_max_steps)

    # 子进程内部还有一层自己的看门狗（trace_timeout），父进程多给 2 秒余量，
    # 让它有机会把已经录到的 steps 写进 result.json 再退场。
    stat = _execute(code, stdin, TRACE_RUNNER, timeout + 2.0,
                    int(memory_mb or settings.judge_memory_mb),
                    settings.judge_output_limit,
                    extra_env={"TRACE_TIMEOUT": timeout, "TRACE_MAX_STEPS": max_steps})
    payload = stat["payload"]

    result = {"steps": [], "error": "", "timeout": stat["timeout"] and payload is None,
              "truncated": False, "output": "", "syntax": False,
              "duration_ms": stat["duration_ms"]}

    if payload is None:
        if stat["timeout"]:
            result["error"] = "追踪超时，子进程被强制结束"
        else:
            result["error"] = ("追踪进程异常退出（可能内存超限）"
                               + (": " + stat["stderr"][:500] if stat["stderr"] else ""))
        result["output"] = stat["stdout"][:settings.judge_output_limit]
        return result

    steps = payload.get("steps") or []
    result["steps"] = steps if isinstance(steps, list) else []
    result["error"] = str(payload.get("error") or "")
    result["timeout"] = bool(payload.get("timeout"))
    result["truncated"] = bool(payload.get("truncated"))
    result["output"] = str(payload.get("output") or "")
    result["syntax"] = bool(payload.get("syntax"))
    return result
