# -*- coding: utf-8 -*-
"""网页版服务自检：不打开浏览器，直接用 urllib 打 HTTP 接口。

覆盖：静态页、题库/进度、判题（通过 / 不通过）、执行过程、成绩回写、
片段与自由编程草稿、以及三条安全边界（跨站 Origin、非 JSON、局域网口令）。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import qbank
import webserver
from store import Store


def request(url, body=None, headers=None, method=None):
    """发一个请求，返回 (状态码, 解析后的 JSON 或原始文本)。"""
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs,
                                 method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", "ignore")
            code = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        code = exc.code
    try:
        return code, json.loads(raw)
    except ValueError:
        return code, raw


def check_ids(html):
    """JS 里 $("xxx") 引用的 id 必须真的存在于 HTML 里——等价于提前抓 null 解引用。"""
    ids = set(re.findall(r'id="([^"]+)"', html))
    used = set(re.findall(r'\$\("([^"]+)"\)', html))
    return sorted(used - ids)


def check_js(html):
    """把页面里的 <script> 抽出来交给 node 做语法检查（没有 node 就跳过）。"""
    node = shutil.which("node")
    if not node:
        return None
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not scripts:
        return False
    tmp = os.path.join(tempfile.mkdtemp(prefix="pyquiz-js-"), "page.js")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(scripts))
    proc = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
    return proc.returncode == 0 and "Error" not in (proc.stderr or ""), proc.stderr


def main():
    ok = []
    workdir = tempfile.mkdtemp(prefix="pyquiz-web-")
    store = Store(os.path.join(workdir, "state.json"))

    server = webserver.start(store, port=0, lan=False)
    port = server.server_address[1]
    base = "http://127.0.0.1:{}".format(port)

    # 1. 首页与接口可用
    code, html = request(base + "/")
    assert code == 200 and "网页版" in html, (code, str(html)[:80])
    assert "自由编程" in html, "首页里没有自由编程入口"
    ok.append("GET / 返回页面（{:.0f} KB）".format(len(html) / 1024.0))

    # 1b. 前端脚本语法检查（没有 node 就跳过）
    js = check_js(html)
    if js is None:
        ok.append("前端脚本检查：环境里没有 node，已跳过")
    else:
        passed, err = js
        assert passed, "前端 JS 语法错误：\n{}".format(err)
        ok.append("前端脚本通过 node --check 语法检查")

    # 1c. 前端引用的元素 id 都存在（防止 $("xxx") 拿到 null）
    missing = check_ids(html)
    assert not missing, "前端引用了不存在的 id：{}".format(missing)
    ok.append("前端 {} 处 $() 引用全部能在页面里找到".format(
        len(set(re.findall(r'\$\("([^"]+)"\)', html)))))

    # 2. 题库与进度
    code, bank = request(base + "/api/bank")
    assert code == 200 and bank.get("ok") is not False
    assert len(bank["questions"]) == len(qbank.QUESTIONS), len(bank["questions"])
    assert bank["stats"]["total"] == len(qbank.QUESTIONS)
    ok.append("GET /api/bank 返回 {} 题 / {} 章".format(
        len(bank["questions"]), len(bank["chapters"])))

    # 3. 判题：参考答案应全部通过
    q = None
    for item in qbank.QUESTIONS:
        if item["id"] == "3-01":
            q = item
            break
    code, res = request(base + "/api/run", {"code": q["ref"], "qid": q["id"]})
    assert code == 200 and res["judge"]["passed"], res
    ok.append("POST /api/run 参考答案判题通过（{} 个用例）".format(res["judge"]["total"]))

    # 4. 判题：错答案要给出定位
    code, res = request(base + "/api/run", {"code": "print('no')\n", "qid": q["id"]})
    judge = res["judge"]
    assert not judge["passed"] and judge["results"][0]["status"] in ("fail", "error")
    ok.append("POST /api/run 错误答案判定为不通过（第一条用例 {}）".format(
        judge["results"][0]["status"]))

    # 5. 执行过程
    code, res = request(base + "/api/trace", {"code": "total = 0\nfor i in range(3):\n"
                                                      "    total += i\nprint(total)\n"})
    steps = res["trace"]["steps"]
    assert steps and any(kv[0] == "total" and kv[1] == "3" for s in steps for kv in s["vars"])
    ok.append("POST /api/trace 记录 {} 步，含变量累加".format(len(steps)))

    # 6. 成绩回写：进度真的落到 state 里
    code, res = request(base + "/api/attempt", {"qid": q["id"], "passed": True,
                                                "code": q["ref"]})
    assert code == 200 and res["record"]["last"] == "pass"
    assert store.is_solved(q["id"]), "进度没有写进 Store"
    ok.append("POST /api/attempt 写回进度（已通过 {} / {}）".format(
        res["stats"]["solved"], res["stats"]["total"]))

    # 7. 自由编程草稿
    code, res = request(base + "/api/free", {"code": "print(6 * 7)\n", "stdin": "x\n"})
    assert code == 200 and res["saved"]
    code, res = request(base + "/api/free")
    assert res["code"] == "print(6 * 7)\n" and res["stdin"] == "x\n", res
    ok.append("自由编程草稿可保存可读回")

    # 8. 片段增删
    code, res = request(base + "/api/snippet", {"name": "测试片段", "code": "print(1)\n"})
    assert code == 200 and res["created"] and res["snippets"][0]["name"] == "测试片段"
    code, res = request(base + "/api/snippet", {"name": "测试片段", "code": "print(2)\n"})
    assert res["created"] is False, "同名片段应覆盖而不是新增"
    code, res = request(base + "/api/snippet", {"name": "测试片段", "delete": True})
    assert res["removed"] and not store.snippets()
    ok.append("代码片段可保存 / 覆盖 / 删除")

    # 9. 安全：不带 JSON 头、跨站 Origin 一律拒绝
    code, res = request(base + "/api/run", body=None,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        method="POST")
    assert code in (400, 415), code
    code, res = request(base + "/api/trace", {"code": "print(1)\n"},
                        headers={"Origin": "http://evil.example"})
    assert code == 403, code
    ok.append("安全边界：非 JSON 请求 415、跨站 Origin 403")

    # 10. 局域网模式：必须带口令
    server.shutdown()
    server.server_close()
    lan_server = webserver.start(store, port=0, lan=True)
    lan_port = lan_server.server_address[1]
    code, res = request("http://127.0.0.1:{}/api/bank".format(lan_port))
    assert code == 403, code
    code, res = request("http://127.0.0.1:{}/api/bank?k={}".format(
        lan_port, lan_server.token))
    assert code == 200 and len(res["questions"]) == len(qbank.QUESTIONS)
    ok.append("局域网模式：无口令 403、带口令可用（口令 {} 位）".format(len(lan_server.token)))
    lan_server.shutdown()
    lan_server.server_close()

    print("网页版服务自检通过（{} 项）：".format(len(ok)))
    for line in ok:
        print("  ✓", line)


if __name__ == "__main__":
    main()
