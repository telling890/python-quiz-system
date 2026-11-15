# -*- coding: utf-8 -*-
"""接口集成测试：认证、题库、判题、隔离、片段。"""

from urllib.parse import quote

from conftest import wait_submission


def _pick_simple_question(client, token):
    status, body = client("GET", "/api/v1/bank", token=token)
    assert status == 200
    for question in body["data"]["questions"]:
        cases = question["cases"]
        if len(cases) == 1 and not cases[0]["stdin"] and cases[0]["expect"].strip():
            return question
    raise AssertionError("题库里没找到单用例、无输入的题")


# ---------------------------------------------------------------- 基础
def test_health(client):
    status, body = client("GET", "/healthz")
    assert status == 200
    assert body["data"]["status"] == "ok"


def test_root_serves_web_ui(client):
    """根路径现在是网页版页面（服务端会注入登录脚本），API 元信息看 /docs。"""
    status, body = client("GET", "/")
    assert status == 200
    html = body.get("raw", "")
    assert "auth.js" in html
    assert "/api/bank" in html


# ---------------------------------------------------------------- 认证
def test_register_and_me(client, user):
    status, body = client("GET", "/api/v1/auth/me", token=user["token"])
    assert status == 200
    assert body["data"]["username"] == user["username"]


def test_duplicate_username(client, user):
    status, body = client("POST", "/api/v1/auth/register",
                          body={"username": user["username"],
                                "password": "another-pass-123"})
    assert status == 409
    assert body["error"]["code"] == "username_taken"


def test_login(client, user):
    status, body = client("POST", "/api/v1/auth/login",
                          body={"username": user["username"], "password": user["password"]})
    assert status == 200
    assert body["data"]["token"]


def test_login_wrong_password(client, user):
    status, body = client("POST", "/api/v1/auth/login",
                          body={"username": user["username"], "password": "wrong-pass-123"})
    assert status == 401
    assert body["error"]["code"] == "invalid_credentials"


def test_requires_token(client):
    status, body = client("GET", "/api/v1/bank")
    assert status == 401
    assert body["error"]["code"] == "unauthorized"


def test_bad_token(client):
    status, body = client("GET", "/api/v1/bank", token="not.a.jwt")
    assert status == 401


def test_short_password_rejected(client):
    status, body = client("POST", "/api/v1/auth/register",
                          body={"username": "shortpw", "password": "123"})
    assert status == 422
    assert body["error"]["code"] == "validation_error"


# ---------------------------------------------------------------- 题库
def test_bank_shape(client, user):
    status, body = client("GET", "/api/v1/bank", token=user["token"])
    assert status == 200
    data = body["data"]
    assert len(data["questions"]) > 100
    assert data["stats"]["total"] == len(data["questions"])
    assert {c["id"] for c in data["chapters"]} >= {"ch3", "ch4", "ch5"}
    first = data["questions"][0]
    assert first["cases"]


def test_question_detail(client, user):
    question = _pick_simple_question(client, user["token"])
    status, body = client("GET", "/api/v1/questions/" + question["id"], token=user["token"])
    assert status == 200
    assert body["data"]["id"] == question["id"]


def test_question_404(client, user):
    status, body = client("GET", "/api/v1/questions/nope-404", token=user["token"])
    assert status == 404
    assert body["error"]["code"] == "question_not_found"


# ---------------------------------------------------------------- 判题
def test_submission_pass(client, user):
    question = _pick_simple_question(client, user["token"])
    expected = question["cases"][0]["expect"].strip()
    code = "print({!r})".format(expected)          # noqa: P103 - 测试构造
    status, body = client("POST", "/api/v1/submissions",
                          body={"qid": question["id"], "code": code}, token=user["token"])
    assert status == 202
    submission = wait_submission(client, user["token"], body["data"]["id"])
    assert submission["status"] == "passed", submission
    assert submission["result"]["passed"] is True

    status, body = client("GET", "/api/v1/progress", token=user["token"])
    record = [r for r in body["data"]["records"] if r["qid"] == question["id"]][0]
    assert record["last"] == "pass"
    assert record["passes"] == 1


def test_submission_wrong_answer(client, user):
    question = _pick_simple_question(client, user["token"])
    status, body = client("POST", "/api/v1/submissions",
                          body={"qid": question["id"], "code": "print('nope')"},
                          token=user["token"])
    assert status == 202
    submission = wait_submission(client, user["token"], body["data"]["id"])
    assert submission["status"] == "failed"
    assert submission["result"]["results"][0]["first_diff"]["line"] == 1


def test_submission_timeout(client, user):
    status, body = client("POST", "/api/v1/submissions",
                          body={"qid": "", "code": "while True:\n    pass\n"},
                          token=user["token"])
    assert status == 202
    submission = wait_submission(client, user["token"], body["data"]["id"])
    assert submission["status"] == "timeout"


def test_submission_error(client, user):
    status, body = client("POST", "/api/v1/submissions",
                          body={"code": "1/0"}, token=user["token"])
    assert status == 202
    submission = wait_submission(client, user["token"], body["data"]["id"])
    assert submission["status"] == "error"
    assert "ZeroDivisionError" in submission["error"]


def test_sandbox_cannot_import_project(client, user):
    """判题在独立进程里跑，学习者的代码 import 不到本项目模块。"""
    status, body = client("POST", "/api/v1/submissions",
                          body={"code": "import qbank\nprint(qbank.QUESTIONS[0])"},
                          token=user["token"])
    assert status == 202
    submission = wait_submission(client, user["token"], body["data"]["id"])
    assert submission["status"] == "error"
    assert "ModuleNotFoundError" in submission["error"]


def test_free_run(client, user):
    status, body = client("POST", "/api/v1/run",
                          body={"code": "a = int(input())\nprint(a * 2)", "stdin": "21"},
                          token=user["token"])
    assert status == 200
    assert body["data"]["run"]["output"] == "42\n"


# ---------------------------------------------------------------- 多用户隔离
def test_user_isolation(client):
    first = client("POST", "/api/v1/auth/register",
                   body={"username": "isolation_a", "password": "secret-pass-123"})[1]
    second = client("POST", "/api/v1/auth/register",
                    body={"username": "isolation_b", "password": "secret-pass-123"})[1]
    token_a = first["data"]["token"]
    token_b = second["data"]["token"]

    question = _pick_simple_question(client, token_a)
    expected = question["cases"][0]["expect"].strip()
    _, created = client("POST", "/api/v1/submissions",
                        body={"qid": question["id"], "code": "print({!r})".format(expected)},
                        token=token_a)
    wait_submission(client, token_a, created["data"]["id"])

    # A 的进度 B 看不到
    _, body = client("GET", "/api/v1/progress", token=token_b)
    assert body["data"]["records"] == []

    # B 也读不到 A 的提交
    status, body = client("GET", "/api/v1/submissions/" + created["data"]["id"], token=token_b)
    assert status == 404

    # A 的收藏不影响 B
    client("POST", "/api/v1/progress/{}/favorite".format(question["id"]),
           body={"favorite": True}, token=token_a)
    _, body = client("GET", "/api/v1/bank", token=token_b)
    assert body["data"]["stats"]["favorite"] == 0


def test_favorite(client, user):
    question = _pick_simple_question(client, user["token"])
    status, body = client("POST", "/api/v1/progress/{}/favorite".format(question["id"]),
                          body={"favorite": True}, token=user["token"])
    assert status == 200 and body["data"]["favorite"] is True
    _, body = client("GET", "/api/v1/bank", token=user["token"])
    assert body["data"]["stats"]["favorite"] == 1


# ---------------------------------------------------------------- 片段 / 草稿
def test_snippets_crud(client, user):
    status, body = client("POST", "/api/v1/snippets",
                          body={"name": "快排", "code": "def qs(a): ..."}, token=user["token"])
    assert status == 200 and body["data"]["created"] is True

    status, body = client("POST", "/api/v1/snippets",
                          body={"name": "快排", "code": "def qs(a): return a"},
                          token=user["token"])
    assert status == 200 and body["data"]["created"] is False

    _, body = client("GET", "/api/v1/snippets", token=user["token"])
    assert [s["name"] for s in body["data"]["snippets"]] == ["快排"]

    quoted = quote("快排")
    status, _ = client("DELETE", "/api/v1/snippets/" + quoted, token=user["token"])
    assert status == 200
    status, body = client("DELETE", "/api/v1/snippets/" + quoted, token=user["token"])
    assert status == 404


def test_free_draft(client, user):
    status, body = client("PUT", "/api/v1/free",
                          body={"code": "print(1)", "stdin": ""}, token=user["token"])
    assert status == 200
    _, body = client("GET", "/api/v1/free", token=user["token"])
    assert body["data"]["code"] == "print(1)"


# ---------------------------------------------------------------- 错误格式
def test_error_envelope(client, user):
    status, body = client("GET", "/api/v1/nope", token=user["token"])
    assert status == 404
    assert body["ok"] is False
    assert set(body["error"]) >= {"code", "message"}
