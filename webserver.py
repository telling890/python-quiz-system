# -*- coding: utf-8 -*-
"""网页版服务：浏览器打开就能刷题、自由编程，题库与进度和桌面版共用同一份。

只用标准库（http.server），不装依赖、不开新端口以外的服务：
- 默认只监听 127.0.0.1，只有本机能访问；
- 打开「允许局域网访问」后监听 0.0.0.0，并在地址里带一个随机口令 k，
  没带口令的请求一律 403（这个服务会执行代码，不能裸奔）。

安全约定（判题会执行用户代码，所以必须防「别的网页偷偷 POST 过来」）：
- 带 Origin 头且不是本机地址的请求直接拒绝；
- POST 必须是 application/json（表单跨站提交会被这一条挡掉）。
"""

import json
import os
import random
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import judge
import qbank
import tracer

HOST_LOCAL = "127.0.0.1"
HOST_LAN = "0.0.0.0"
DEFAULT_PORT = 8765
HTML_NAME = "index.html"


# ---------------------------------------------------------------- 静态资源
def web_dir():
    """找 web/index.html：源码运行、PyInstaller 目录版、单文件解压三种位置都试一遍。"""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "web"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "web"),
        os.path.join(os.path.dirname(sys.executable), "web"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "web"),
    ]
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, HTML_NAME)):
            return path
    return os.path.join(here, "web")


def load_html():
    path = os.path.join(web_dir(), HTML_NAME)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def lan_ip():
    """尽量猜出局域网 IP（查不到就返回空串）。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.3)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return ""


# ---------------------------------------------------------------- 数据组装
def bank_payload(store):
    """一次性把题库与进度发给浏览器（本地访问，体积无所谓）。"""
    questions = []
    for q in qbank.QUESTIONS:
        rec = store.record(q["id"])
        questions.append({
            "id": q["id"],
            "chapter": q.get("chapter", ""),
            "no": q.get("no", 0),
            "title": q["title"],
            "topic": q.get("topic", ""),
            "level": q.get("level", 1),
            "desc": q.get("desc", ""),
            "hint": q.get("hint", ""),
            "ref": q.get("ref", ""),
            "explain": q.get("explain", ""),
            "source": q.get("source", ""),
            "cases": q.get("cases", []),
            "last": rec.get("last", ""),
            "attempts": rec.get("attempts", 0),
            "favorite": bool(rec.get("favorite")),
            "code": rec.get("code", ""),
        })
    chapters = [{"id": c["id"], "name": c["name"], "short": c["short"],
                 "count": len(c["questions"])} for c in qbank.CHAPTERS]
    return {"questions": questions, "chapters": chapters, "stats": store.stats(qbank.QUESTIONS)}


def run_cases(code, cases):
    """逐条跑用例，和桌面版一致：第一个不通过就停。"""
    results = []
    all_ok = True
    for case in cases:
        item = judge.run_case(code, case)
        results.append(item)
        if item["status"] != "pass":
            all_ok = False
            break
    return {"passed": all_ok, "results": results, "total": len(cases)}


# ---------------------------------------------------------------- HTTP
class QuizHandler(BaseHTTPRequestHandler):
    server_version = "PyQuizWeb/1.0"
    protocol_version = "HTTP/1.1"

    # ---- 小工具
    @property
    def store(self):
        return self.server.store

    @property
    def lock(self):
        return self.server.lock

    def log_message(self, fmt, *args):
        pass  # 别把访问日志打印到宿主程序的控制台

    def _ok_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = (self.headers.get("Host") or "").lower()
        allowed = ("http://" + host, "https://" + host)
        try:
            return origin.lower() in allowed
        except AttributeError:
            return False

    def _token_ok(self, query):
        if not self.server.token:
            return True
        return query.get("k", [""])[0] == self.server.token

    def _send(self, code, body, content_type):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def _html(self, text):
        self._send(200, text, "text/html; charset=utf-8")

    def _fail(self, code, message):
        self._json({"ok": False, "error": message}, code)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 4 * 1024 * 1024:
            return None
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    # ---- 路由
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self._token_ok(query):
            return self._fail(403, "缺少访问口令")
        if not self._ok_origin():
            return self._fail(403, "拒绝来自其他站点的请求")
        path = parsed.path
        try:
            if path in ("/", "/index.html"):
                return self._html(load_html())
            if path == "/api/bank":
                with self.lock:
                    return self._json(bank_payload(self.store))
            if path == "/api/free":
                with self.lock:
                    return self._json(self.store.free_state())
            if path == "/api/snippets":
                with self.lock:
                    return self._json({"snippets": self.store.snippets()})
            return self._fail(404, "没有这个接口：{}".format(path))
        except Exception as exc:                     # noqa: BLE001 - 兜底，别让服务挂掉
            return self._fail(500, "服务端出错：{}".format(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self._token_ok(query):
            return self._fail(403, "缺少访问口令")
        if not self._ok_origin():
            return self._fail(403, "拒绝来自其他站点的请求")
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return self._fail(415, "只接受 application/json")
        data = self._body()
        if data is None:
            return self._fail(400, "请求体不是合法 JSON")

        path = parsed.path
        try:
            if path == "/api/run":
                return self._api_run(data)
            if path == "/api/trace":
                return self._api_trace(data)
            if path == "/api/attempt":
                return self._api_attempt(data)
            if path == "/api/free":
                return self._api_free(data)
            if path == "/api/snippet":
                return self._api_snippet(data)
            return self._fail(404, "没有这个接口：{}".format(path))
        except Exception as exc:                     # noqa: BLE001
            return self._fail(500, "服务端出错：{}".format(exc))

    # ---- 接口实现
    def _question(self, qid):
        for q in qbank.QUESTIONS:
            if q["id"] == qid:
                return q
        return None

    def _api_run(self, data):
        code = data.get("code") or ""
        qid = data.get("qid") or ""
        q = self._question(qid) if qid else None
        if q:
            cases = q.get("cases") or []
        else:
            cases = data.get("cases") or []
        if not code.strip():
            return self._fail(400, "代码是空的")
        if not cases:
            # 自由编程：没有用例就跑一遍，把输出给浏览器
            run = judge.run_code(code, data.get("stdin") or "")
            return self._json({"ok": True, "mode": "free", "run": run})
        with self.lock:
            outcome = run_cases(code, cases)
        return self._json({"ok": True, "mode": "judge", "judge": outcome})

    def _api_trace(self, data):
        code = data.get("code") or ""
        if not code.strip():
            return self._fail(400, "代码是空的")
        result = tracer.trace_code(code, data.get("stdin") or "")
        return self._json({"ok": True, "trace": result, "summary": tracer.describe(result)})

    def _api_attempt(self, data):
        qid = data.get("qid") or ""
        if not self._question(qid):
            return self._fail(404, "没有这道题：{}".format(qid))
        passed = bool(data.get("passed"))
        code = data.get("code") or ""
        with self.lock:
            self.store.record_attempt(qid, passed, code)
            stats = self.store.stats(qbank.QUESTIONS)
            rec = self.store.record(qid)
        return self._json({"ok": True, "stats": stats,
                           "record": {"last": rec.get("last", ""),
                                      "attempts": rec.get("attempts", 0)}})

    def _api_free(self, data):
        with self.lock:
            saved = self.store.save_free(data.get("code") or "", data.get("stdin") or "")
        return self._json({"ok": True, "saved": bool(saved)})

    def _api_snippet(self, data):
        if data.get("delete"):
            with self.lock:
                removed = self.store.delete_snippet(data.get("name") or "")
            return self._json({"ok": True, "removed": bool(removed)})
        name = (data.get("name") or "").strip()
        code = data.get("code") or ""
        if not name:
            return self._fail(400, "片段名字不能为空")
        with self.lock:
            created = self.store.save_snippet(name, code)
            items = self.store.snippets()
        return self._json({"ok": True, "created": bool(created), "snippets": items})


class QuizServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, store, lan=False):
        self.store = store
        self.lock = threading.RLock()
        self.token = "".join(random.choice("abcdefghijkmnpqrstuvwxyz23456789")
                             for _ in range(8)) if lan else ""
        ThreadingHTTPServer.__init__(self, addr, QuizHandler)


def start(store, port=DEFAULT_PORT, lan=False):
    """启动服务并返回 (server, 地址)。失败时抛 OSError（端口被占等）。"""
    host = HOST_LAN if lan else HOST_LOCAL
    server = QuizServer((host, port), store, lan=lan)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2})
    thread.daemon = True
    thread.start()
    server.url = url_for(server, port, lan)
    return server


def url_for(server, port, lan=False):
    if lan:
        ip = lan_ip() or HOST_LOCAL
        base = "http://{}:{}/".format(ip, port)
        if server.token:
            base += "?k=" + server.token
        return base
    return "http://{}:{}/".format(HOST_LOCAL, port)


if __name__ == "__main__":
    # 单独跑：python webserver.py [--lan] [--port 8765]
    from store import Store

    port = DEFAULT_PORT
    lan = "--lan" in sys.argv
    if "--port" in sys.argv:
        try:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        except (IndexError, ValueError):
            pass
    srv = start(Store(), port=port, lan=lan)
    print("网页版已启动：", srv.url)
    print("按 Ctrl+C 退出")
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        srv.shutdown()
