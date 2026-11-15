# -*- coding: utf-8 -*-
"""把桌面版的 state.json 导进服务端。

用法（先起服务，参数换成你自己的）：

    py -3.10 backend/scripts/import_state.py `
        --base http://127.0.0.1:8000 --user alice --password secret-pass-123

默认从 `quiz_app/data/state.json` 读（便携版的进度文件位置），也可以用 --file 指定。
只依赖标准库，不需要在导出的机器上装任何东西。

退出码：0 成功，1 参数/网络/服务端错误。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
QUIZ_ROOT = os.path.dirname(os.path.dirname(HERE))      # backend/scripts -> quiz_app/
DEFAULT_STATE = os.path.join(QUIZ_ROOT, "data", "state.json")


def request(method, url, body=None, token=""):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"error": {"message": raw[:300]}}
        message = payload.get("error")
        if isinstance(message, dict):
            message = message.get("message") or str(message)
        raise SystemExit("服务端返回 {}：{}".format(exc.code, message))


def main():
    parser = argparse.ArgumentParser(description="把桌面版 state.json 导入服务端")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="服务地址")
    parser.add_argument("--user", required=False, help="用户名")
    parser.add_argument("--password", required=False, help="密码")
    parser.add_argument("--token", default="", help="已有令牌时可直接用，免登录")
    parser.add_argument("--file", default=DEFAULT_STATE, help="state.json 路径")
    parser.add_argument("--dry-run", action="store_true", help="只读文件并打印统计，不发请求")
    args = parser.parse_args()

    path = os.path.abspath(os.path.expanduser(args.file))
    if not os.path.isfile(path):
        raise SystemExit("找不到进度文件：{}\n用 --file 指定你的 state.json".format(path))

    with open(path, "r", encoding="utf-8-sig") as f:
        state = json.load(f)
    questions = state.get("questions") or {}
    print("读到 {}：{} 条作答记录、{} 个片段".format(
        path, len(questions), len(state.get("snippets") or [])))

    if args.dry_run:
        return 0

    base = args.base.rstrip("/")
    token = args.token
    if not token:
        if not args.user or not args.password:
            raise SystemExit("请提供 --user/--password，或者直接给 --token")
        payload = request("POST", base + "/api/v1/auth/login",
                          {"username": args.user, "password": args.password})
        token = payload["data"]["token"]

    result = request("POST", base + "/api/v1/import/state", {"state": state}, token)
    data = result["data"]
    print("导入完成：新建 {created} 条、合并 {merged} 条、跳过 {skipped} 条（题库里没有的题）"
          .format(**data["records"]))
    print("片段：{} 个；自由编程草稿：{}；跳过的组卷历史：{} 条".format(
        data["snippets"], "已填入" if data["free"] else "未改动", data["ignored"]["exams"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
