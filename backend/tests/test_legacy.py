# -*- coding: utf-8 -*-
"""网页版旧接口 `/api/*` 的集成测试。

这一层是给 `web/index.html` 用的，所以断言的重点不是「有数据」，而是
**字段名/结构必须和 webserver.py 当初返回的一模一样** —— 少一个 `chapter`
字段，前端的章节筛选就空了。
"""


def _simple_question(client, token):
    """挑一道「单用例、无输入、有期望输出」的题，方便构造通过/不通过的代码。"""
    status, body = client("GET", "/api/bank", token=token)
    assert status == 200, body
    for question in body["questions"]:
        cases = question["cases"]
        if len(cases) == 1 and not cases[0]["stdin"] and cases[0]["expect"].strip():
            return question
    raise AssertionError("题库里没找到单用例、无输入的题")


def _pass_code(question):
    return "print({!r})".format(question["cases"][0]["expect"].strip())


# ---------------------------------------------------------------- 读接口
def test_bank_shape(client, user):
    status, body = client("GET", "/api/bank", token=user["token"])
    assert status == 200
    assert set(body) >= {"questions", "chapters", "stats"}

    question = body["questions"][0]
    for key in ("id", "chapter", "no", "title", "topic", "level", "desc", "hint",
                "ref", "explain", "source", "cases", "last", "attempts",
                "favorite", "code"):
        assert key in question, "缺字段：" + key

    # 前端按「章节名」过滤题目，名字必须能对上
    names = {c["name"] for c in body["chapters"]}
    assert question["chapter"] in names
    assert body["stats"]["total"] == len(body["questions"])
    # 与 /api/v1 的题库是同一份数据
    _, official = client("GET", "/api/v1/bank", token=user["token"])
    assert len(official["data"]["questions"]) == len(body["questions"])


def test_requires_login(client):
    status, body = client("GET", "/api/bank")
    assert status == 401
    assert body["ok"] is False


def test_legacy_page_served(client):
    status, body = client("GET", "/legacy")
    assert status == 200
    html = body.get("raw", "")
    assert "auth.js" in html          # 登录脚本被注入
    assert "刷题" in html


def test_auth_js_served(client):
    status, body = client("GET", "/auth.js")
    assert status == 200
    assert "/api/v1/auth/login" in body.get("raw", "")


# ---------------------------------------------------------------- 判题
def test_run_judge_pass(client, user):
    question = _simple_question(client, user["token"])
    status, body = client("POST", "/api/run", token=user["token"],
                          body={"code": _pass_code(question), "qid": question["id"]})
    assert status == 200
    assert body["ok"] is True
    assert body["mode"] == "judge"
    judge = body["judge"]
    assert judge["passed"] is True
    assert judge["total"] == 1
    assert judge["results"][0]["status"] == "pass"
    for key in ("stdin", "expect", "actual", "error", "first_diff"):
        assert key in judge["results"][0]


def test_run_judge_fail(client, user):
    question = _simple_question(client, user["token"])
    status, body = client("POST", "/api/run", token=user["token"],
                          body={"code": "print('nope')", "qid": question["id"]})
    assert status == 200
    judge = body["judge"]
    assert judge["passed"] is False
    item = judge["results"][0]
    assert item["status"] == "fail"
    assert item["first_diff"]["line"] == 1


def test_run_free_mode(client, user):
    status, body = client("POST", "/api/run", token=user["token"],
                          body={"code": "a = int(input())\nprint(a * 2)", "stdin": "21"})
    assert status == 200
    assert body["mode"] == "free"
    assert body["run"]["output"] == "42\n"


def test_run_empty_code(client, user):
    status, body = client("POST", "/api/run", token=user["token"], body={"code": "   "})
    assert status == 400
    assert body["ok"] is False
    assert isinstance(body["error"], str)     # 旧接口的 error 是字符串


def test_run_unknown_question(client, user):
    status, body = client("POST", "/api/run", token=user["token"],
                          body={"code": "print(1)", "qid": "nope-404"})
    assert status == 404
    assert isinstance(body["error"], str)


# ---------------------------------------------------------------- 进度
def test_attempt_updates_progress(client, user):
    question = _simple_question(client, user["token"])
    status, body = client("POST", "/api/attempt", token=user["token"],
                          body={"qid": question["id"], "passed": True,
                                "code": _pass_code(question)})
    assert status == 200
    assert body["ok"] is True
    assert body["record"]["last"] == "pass"
    assert body["record"]["attempts"] == 1
    assert body["stats"]["solved"] >= 1

    _, bank = client("GET", "/api/bank", token=user["token"])
    stored = [q for q in bank["questions"] if q["id"] == question["id"]][0]
    assert stored["last"] == "pass"
    assert stored["attempts"] == 1
    assert stored["code"] == _pass_code(question)


def test_attempt_fail_marks_fail(client, user):
    question = _simple_question(client, user["token"])
    status, body = client("POST", "/api/attempt", token=user["token"],
                          body={"qid": question["id"], "passed": False, "code": "print(1)"})
    assert status == 200
    assert body["record"]["last"] == "fail"


def test_progress_is_per_user(client):
    first = client("POST", "/api/v1/auth/register",
                   body={"username": "legacy_a", "password": "secret-pass-123"})[1]
    second = client("POST", "/api/v1/auth/register",
                    body={"username": "legacy_b", "password": "secret-pass-123"})[1]
    token_a = first["data"]["token"]
    token_b = second["data"]["token"]

    question = _simple_question(client, token_a)
    client("POST", "/api/attempt", token=token_a,
           body={"qid": question["id"], "passed": True, "code": "print(1)"})

    _, bank_b = client("GET", "/api/bank", token=token_b)
    assert bank_b["stats"]["solved"] == 0
    stored = [q for q in bank_b["questions"] if q["id"] == question["id"]][0]
    assert stored["last"] == ""
    assert stored["attempts"] == 0


# ---------------------------------------------------------------- 草稿 / 片段
def test_free_draft_roundtrip(client, user):
    status, body = client("POST", "/api/free", token=user["token"],
                          body={"code": "print(1)", "stdin": "x"})
    assert status == 200 and body["ok"] is True and body["saved"] is True

    _, body = client("GET", "/api/free", token=user["token"])
    assert body["code"] == "print(1)"
    assert body["stdin"] == "x"


def test_snippet_crud(client, user):
    status, body = client("POST", "/api/snippet", token=user["token"],
                          body={"name": "片段A", "code": "print(1)"})
    assert status == 200
    assert body["ok"] is True and body["created"] is True
    assert [s["name"] for s in body["snippets"]] == ["片段A"]

    status, body = client("POST", "/api/snippet", token=user["token"],
                          body={"name": "片段A", "code": "print(2)"})
    assert body["created"] is False
    assert body["snippets"][0]["code"] == "print(2)"

    _, body = client("GET", "/api/snippets", token=user["token"])
    assert len(body["snippets"]) == 1

    status, body = client("POST", "/api/snippet", token=user["token"],
                          body={"name": "片段A", "delete": True})
    assert body["removed"] is True
    _, body = client("GET", "/api/snippets", token=user["token"])
    assert body["snippets"] == []


def test_snippet_needs_name(client, user):
    status, body = client("POST", "/api/snippet", token=user["token"],
                          body={"name": "  ", "code": "print(1)"})
    assert status == 400
    assert isinstance(body["error"], str)


# ---------------------------------------------------------------- 单步执行
def test_trace_steps(client, user):
    status, body = client("POST", "/api/trace", token=user["token"],
                          body={"code": "a = 1\nb = a + 1\nprint(b)"})
    assert status == 200
    assert body["ok"] is True
    trace = body["trace"]
    assert len(trace["steps"]) >= 3
    first = trace["steps"][0]
    for key in ("line", "event", "func", "depth", "vars", "hidden", "out"):
        assert key in first
    # 变量是 [[名字, 值], ...]，前端按 kv[0]/kv[1] 取值
    last = trace["steps"][-1]
    assert isinstance(last["vars"], list)
    for pair in last["vars"]:
        assert len(pair) == 2 and isinstance(pair[0], str)
    assert trace["output"] == "2\n"


def test_trace_error_and_loops(client, user):
    status, body = client("POST", "/api/trace", token=user["token"],
                          body={"code": "1/0"})
    assert status == 200
    assert "ZeroDivisionError" in body["trace"]["error"]

    # 死循环：要么被步数上限截断（800 步），要么被看门狗按超时打断
    status, body = client("POST", "/api/trace", token=user["token"],
                          body={"code": "while True:\n    pass\n"})
    assert status == 200
    trace = body["trace"]
    assert trace["truncated"] is True or trace["timeout"] is True
    assert "步" in body["summary"]


def test_trace_survives_settrace_disabled(client, user):
    """学习者把 settrace 关掉再死循环，也不能把服务拖住。

    桌面版是在主进程里 settrace 的，这种代码会把工作线程永久挂死；
    服务端因为追踪跑在子进程里，父进程超时后照样能拿到结果（或 kill 掉）。
    """
    code = "import sys\nsys.settrace(None)\nwhile True:\n    pass\n"
    status, body = client("POST", "/api/trace", token=user["token"], body={"code": code})
    assert status == 200
    assert body["trace"]["timeout"] is True
    assert "超时" in body["summary"]


def test_trace_blocks_dangerous_code(client, user):
    status, body = client("POST", "/api/trace", token=user["token"],
                          body={"code": "import os\nos.system('echo hi')"})
    assert status == 200
    assert body["trace"]["steps"] == []
    assert "不允许使用" in body["trace"]["error"]


# ---------------------------------------------------------------- 首页注入
def test_render_index_injects_login_and_beian():
    """登录脚本和备案号都由服务端注入，注入逻辑坏了会「能打开但登录不了」。"""
    from app.main import render_index

    source = "<html><head><title>t</title></head><body>hi</body></html>"

    plain = render_index(source, "")
    assert plain.count("/auth.js") == 1
    assert "pyquiz-beian" not in plain          # 没配备案号就不该出现角标

    out = render_index(source, "蜀ICP备2026000001号-1")
    assert "蜀ICP备2026000001号-1" in out
    assert "beian.miit.gov.cn" in out
    assert out.count("</body>") == 1            # 没破坏原有结构

    # 幂等：重复注入不会变成两份
    again = render_index(out, "蜀ICP备2026000001号-1")
    assert again.count("/auth.js") == 1
    assert again.count("pyquiz-beian") == 1

    # 备案号里的 HTML 必须被转义
    evil = render_index(source, "<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in evil
    assert "&lt;script&gt;" in evil
