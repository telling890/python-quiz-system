# -*- coding: utf-8 -*-
"""测试夹具：起一个真实的 uvicorn 服务（随机端口），用标准库 urllib 发请求。

环境里没有 httpx，所以不用 TestClient —— 顺带把「真进程 + 真端口」也测了。
"""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TMP = tempfile.mkdtemp(prefix="quiz-test-")
os.environ["QUIZ_DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "app.db").replace("\\", "/")
os.environ["QUIZ_JWT_SECRET"] = "test-secret"
os.environ["QUIZ_SEED_ON_START"] = "true"
os.environ["QUIZ_JUDGE_TMP"] = os.path.join(TMP, "judge")
os.environ["QUIZ_JUDGE_TIMEOUT"] = "3"
os.environ["QUIZ_TRACE_TIMEOUT"] = "2"
os.environ["QUIZ_RATE_LIMIT_PER_MINUTE"] = "100000"
os.environ["QUIZ_RATE_LIMIT_AUTH_PER_MINUTE"] = "100000"

import uvicorn  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def base_url():
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 30
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn 没起来"
    port = server.servers[0].sockets[0].getsockname()[1]
    yield "http://127.0.0.1:{}".format(port)
    server.should_exit = True
    thread.join(timeout=10)


def http(method, url, body=None, token=None, timeout=60):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            try:
                return response.status, json.loads(raw)
            except ValueError:                 # 根路径现在是 HTML 页面
                return response.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"raw": raw}


@pytest.fixture(scope="session")
def client(base_url):
    return lambda method, path, **kwargs: http(method, base_url + path, **kwargs)


_counter = {"n": 0}


@pytest.fixture
def user(client):
    _counter["n"] += 1
    name = "tester{}".format(_counter["n"])
    status, body = client("POST", "/api/v1/auth/register",
                          body={"username": name, "password": "secret-pass-123"})
    assert status == 201, body
    return {"username": name, "password": "secret-pass-123", "token": body["data"]["token"]}


def wait_submission(client, token, submission_id, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, body = client("GET", "/api/v1/submissions/" + submission_id, token=token)
        assert status == 200, body
        submission = body["data"]
        if submission["status"] not in ("queued", "running"):
            return submission
        time.sleep(0.2)
    raise AssertionError("判题超时")
