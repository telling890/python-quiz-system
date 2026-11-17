# -*- coding: utf-8 -*-
"""打卡统计接口：日期窗口、按天计数、连续天数、时区换算、参数校验、用户隔离。"""

from datetime import date, timedelta

from conftest import wait_submission

from app.routers.activity import best_streak, current_streak, local_date, today_of


def _pick_simple_question(client, token):
    status, body = client("GET", "/api/v1/bank", token=token)
    assert status == 200
    for question in body["data"]["questions"]:
        cases = question["cases"]
        if len(cases) == 1 and not cases[0]["stdin"] and cases[0]["expect"].strip():
            return question
    raise AssertionError("题库里没找到单用例、无输入的题")


# ---------------------------------------------------------------- 纯函数
def test_local_date_respects_timezone():
    # 2026-11-16T20:30 UTC = 北京时间 11 月 17 日 04:30
    iso = "2026-11-16T20:30:00+00:00"
    assert local_date(iso, 0).isoformat() == "2026-11-16"
    assert local_date(iso, 480).isoformat() == "2026-11-17"
    assert local_date(iso, -720).isoformat() == "2026-11-16"


def test_local_date_tolerates_bad_input():
    assert local_date("", 0) is None
    assert local_date("not-a-date", 0) is None
    assert local_date(None, 0) is None
    # 没带时区的老数据按 UTC 处理
    assert local_date("2026-11-16T23:00:00", 0).isoformat() == "2026-11-16"


def test_current_streak():
    today = date(2026, 11, 16)
    counts = {today: 2, today - timedelta(days=1): 1, today - timedelta(days=2): 5}
    assert current_streak(counts, today) == 3

    # 今天还没做题但昨天做了：连续记录先算活着
    assert current_streak({today - timedelta(days=1): 1}, today) == 1

    # 今天和昨天都没有：断了
    assert current_streak({today - timedelta(days=2): 3}, today) == 0
    assert current_streak({}, today) == 0

    # 中间空一天，只算最近这一段
    broken = {today: 1, today - timedelta(days=2): 1, today - timedelta(days=3): 1}
    assert current_streak(broken, today) == 1


def test_best_streak():
    base = date(2026, 1, 1)
    counts = {base: 1,
              base + timedelta(days=1): 1,
              base + timedelta(days=2): 1,
              base + timedelta(days=5): 1}
    best, end = best_streak(counts)
    assert best == 3
    assert end == base + timedelta(days=2)
    assert best_streak({}) == (0, None)


# ---------------------------------------------------------------- 接口
def test_activity_requires_token(client):
    status, body = client("GET", "/api/v1/activity")
    assert status == 401
    assert body["ok"] is False


def test_activity_shape(client, user):
    status, body = client("GET", "/api/v1/activity?days=7", token=user["token"])
    assert status == 200
    data = body["data"]
    assert len(data["days"]) == 7
    assert data["days"][-1]["date"] == today_of(0).isoformat()
    assert data["days"][0]["date"] == (today_of(0) - timedelta(days=6)).isoformat()
    assert all(set(point) == {"date", "count"} for point in data["days"])
    # 新用户一次判题都没有
    assert data["today_count"] == 0
    assert data["total"] == 0
    assert data["active_days"] == 0
    assert data["streak"] == 0
    assert data["best_streak"] == 0


def test_activity_counts_submission(client, user):
    question = _pick_simple_question(client, user["token"])
    expected = question["cases"][0]["expect"].strip()
    status, body = client("POST", "/api/v1/submissions",
                          body={"qid": question["id"], "code": "print({!r})".format(expected)},
                          token=user["token"])
    assert status == 202
    submission = wait_submission(client, user["token"], body["data"]["id"])
    assert submission["status"] == "passed", submission

    status, body = client("GET", "/api/v1/activity?days=7", token=user["token"])
    assert status == 200
    data = body["data"]
    assert data["today_count"] == 1
    assert data["total"] == 1
    assert data["active_days"] == 1
    assert data["streak"] == 1
    assert data["days"][-1]["count"] == 1
    # 除今天外都是 0
    assert [point["count"] for point in data["days"]][:-1] == [0] * 6


def test_activity_timezone_is_echoed(client, user):
    status, body = client("GET", "/api/v1/activity?days=7&tz=480", token=user["token"])
    assert status == 200
    data = body["data"]
    assert data["timezone_minutes"] == 480
    assert data["days"][-1]["date"] == today_of(480).isoformat()


def test_activity_validates_params(client, user):
    # days 太小 / 太大都不行
    status, body = client("GET", "/api/v1/activity?days=1", token=user["token"])
    assert status == 422
    assert body["error"]["code"] == "validation_error"

    status, body = client("GET", "/api/v1/activity?days=9999", token=user["token"])
    assert status == 422

    status, body = client("GET", "/api/v1/activity?tz=9999", token=user["token"])
    assert status == 422


def test_activity_is_isolated(client):
    status, body = client("POST", "/api/v1/auth/register",
                          body={"username": "activity-a", "password": "secret-pass-123"})
    assert status == 201, body
    token_a = body["data"]["token"]

    status, body = client("POST", "/api/v1/auth/register",
                          body={"username": "activity-b", "password": "secret-pass-123"})
    assert status == 201, body
    token_b = body["data"]["token"]

    question = _pick_simple_question(client, token_a)
    expected = question["cases"][0]["expect"].strip()
    status, body = client("POST", "/api/v1/submissions",
                          body={"qid": question["id"], "code": "print({!r})".format(expected)},
                          token=token_a)
    assert status == 202
    wait_submission(client, token_a, body["data"]["id"])

    status, body = client("GET", "/api/v1/activity?days=7", token=token_a)
    assert status == 200 and body["data"]["total"] == 1

    # B 看不见 A 的打卡
    status, body = client("GET", "/api/v1/activity?days=7", token=token_b)
    assert status == 200
    assert body["data"]["total"] == 0
    assert body["data"]["streak"] == 0
