# -*- coding: utf-8 -*-
"""桌面版进度导入的集成测试。

重点不是「能导入」，而是**导入的语义**：
重复导入不能把次数翻倍，导入旧数据不能覆盖新进度。
"""


def _first_question(client, token):
    status, body = client("GET", "/api/v1/bank", token=token)
    assert status == 200, body
    return body["data"]["questions"][0]


def _state(qid, **overrides):
    item = {"attempts": 3, "passes": 2, "fails": 1, "last": "pass",
            "code": "print(1)", "favorite": True, "updated": "2025-01-02 10:00:00"}
    item.update(overrides)
    return {
        "version": 1,
        "questions": {qid: item},
        "snippets": [{"name": "导入的片段", "code": "print(2)",
                      "updated": "2025-01-02 10:00:00"}],
        "free": {"code": "print(3)", "stdin": "input"},
        "exams": [{"finished_at": "2025-01-01 10:00:00", "score": 90}],
    }


# ---------------------------------------------------------------- 正常导入
def test_import_records_snippets_free(client, user):
    question = _first_question(client, user["token"])
    status, body = client("POST", "/api/v1/import/state",
                          body={"state": _state(question["id"])}, token=user["token"])
    assert status == 200, body
    data = body["data"]
    assert data["records"] == {"created": 1, "merged": 0, "skipped": 0}
    assert data["snippets"] == 1
    assert data["free"] is True
    assert data["ignored"]["exams"] == 1

    _, progress = client("GET", "/api/v1/progress", token=user["token"])
    record = [r for r in progress["data"]["records"] if r["qid"] == question["id"]][0]
    assert record["attempts"] == 3
    assert record["passes"] == 2
    assert record["fails"] == 1
    assert record["last"] == "pass"
    assert record["favorite"] is True

    _, bank = client("GET", "/api/v1/bank", token=user["token"])
    stored = [q for q in bank["data"]["questions"] if q["id"] == question["id"]][0]
    assert stored["code"] == "print(1)"
    assert stored["last"] == "pass"

    _, snippets = client("GET", "/api/v1/snippets", token=user["token"])
    assert [s["name"] for s in snippets["data"]["snippets"]] == ["导入的片段"]

    _, free = client("GET", "/api/v1/free", token=user["token"])
    assert free["data"]["code"] == "print(3)"
    assert free["data"]["stdin"] == "input"


def test_import_is_idempotent(client, user):
    question = _first_question(client, user["token"])
    payload = {"state": _state(question["id"])}
    client("POST", "/api/v1/import/state", body=payload, token=user["token"])
    status, body = client("POST", "/api/v1/import/state", body=payload, token=user["token"])
    assert status == 200
    assert body["data"]["records"] == {"created": 0, "merged": 1, "skipped": 0}

    _, progress = client("GET", "/api/v1/progress", token=user["token"])
    record = [r for r in progress["data"]["records"] if r["qid"] == question["id"]][0]
    # 第二次导入没有把 3 次变成 6 次
    assert record["attempts"] == 3
    assert record["passes"] == 2


def test_import_accepts_raw_state_body(client, user):
    question = _first_question(client, user["token"])
    status, body = client("POST", "/api/v1/import/state",
                          body=_state(question["id"]), token=user["token"])
    assert status == 200
    assert body["data"]["records"]["created"] == 1


# ---------------------------------------------------------------- 合并语义
def test_import_does_not_roll_back_newer_progress(client, user):
    """服务端已经做了 2 次并全部通过，导入一份更旧的 state 不能把它改回去。"""
    question = _first_question(client, user["token"])
    for _ in range(2):
        client("POST", "/api/attempt", token=user["token"],
               body={"qid": question["id"], "passed": True, "code": "print(9)"})

    status, body = client("POST", "/api/v1/import/state", token=user["token"],
                          body={"state": _state(question["id"], attempts=1, passes=1,
                                                fails=0, last="fail", code="print(old)")})
    assert status == 200

    _, progress = client("GET", "/api/v1/progress", token=user["token"])
    record = [r for r in progress["data"]["records"] if r["qid"] == question["id"]][0]
    assert record["attempts"] == 2          # 取最大值，没被 1 覆盖
    assert record["last"] == "pass"         # 旧的 fail 不生效
    assert record["favorite"] is True       # 收藏取并集


def test_import_newer_state_wins(client, user):
    question = _first_question(client, user["token"])
    client("POST", "/api/attempt", token=user["token"],
           body={"qid": question["id"], "passed": True, "code": "print(9)"})

    status, body = client("POST", "/api/v1/import/state", token=user["token"],
                          body={"state": _state(question["id"], attempts=5, passes=2,
                                                fails=3, last="fail", code="print(new)")})
    assert status == 200

    _, bank = client("GET", "/api/v1/bank", token=user["token"])
    stored = [q for q in bank["data"]["questions"] if q["id"] == question["id"]][0]
    assert stored["attempts"] == 5
    assert stored["last"] == "fail"
    assert stored["code"] == "print(new)"


def test_import_skips_unknown_questions(client, user):
    status, body = client("POST", "/api/v1/import/state", token=user["token"],
                          body={"state": {"questions": {"不存在的题": {"attempts": 1}}}})
    assert status == 200
    assert body["data"]["records"] == {"created": 0, "merged": 0, "skipped": 1}


def test_import_does_not_overwrite_draft(client, user):
    client("PUT", "/api/v1/free", token=user["token"],
           body={"code": "print('我的新草稿')", "stdin": ""})
    client("POST", "/api/v1/import/state", token=user["token"],
           body={"state": {"free": {"code": "print('老草稿')"}}})
    _, free = client("GET", "/api/v1/free", token=user["token"])
    assert free["data"]["code"] == "print('我的新草稿')"


# ---------------------------------------------------------------- 边界
def test_import_requires_login(client):
    status, body = client("POST", "/api/v1/import/state", body={"state": {}})
    assert status == 401


def test_import_rejects_bad_questions(client, user):
    status, body = client("POST", "/api/v1/import/state", token=user["token"],
                          body={"state": {"questions": []}})
    assert status == 400
    assert body["error"]["code"] == "invalid_state"


def test_import_truncates_long_code(client, user):
    question = _first_question(client, user["token"])
    long_code = "x = 1\n" * 5000
    status, body = client("POST", "/api/v1/import/state", token=user["token"],
                          body={"state": {"questions": {question["id"]: {
                              "attempts": 1, "last": "pass", "code": long_code}}}})
    assert status == 200
    _, bank = client("GET", "/api/v1/bank", token=user["token"])
    stored = [q for q in bank["data"]["questions"] if q["id"] == question["id"]][0]
    assert len(stored["code"]) <= 20000
