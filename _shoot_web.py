# -*- coding: utf-8 -*-
"""网页版入口页：截图 + 冒烟（启动服务、浏览器接口连通、进度与桌面共享、停止）。"""

import json
import os
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

os.environ["PYQUIZ_STATE_DIR"] = tempfile.mkdtemp(prefix="pyquiz-web-shot-")

from PIL import ImageGrab

from main import _enable_dpi_awareness

OUT = os.path.join(HERE, "shots")


def shot(app, name):
    app.update_idletasks()
    app.update()
    time.sleep(0.4)
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(
        os.path.join(OUT, name))
    print("saved", name)


def get_json(url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    _enable_dpi_awareness()
    from ui import App

    app = App()
    app.attributes("-topmost", True)
    app.update()

    app.show("web")
    app.update()
    view = app.web
    shot(app, "17_web.png")

    view.start()
    app.update()
    assert view.server is not None, "服务没启动"
    assert view.url.startswith("http://127.0.0.1:"), view.url
    print("url:", view.url)

    # 浏览器那条路：真的走 HTTP
    html = urllib.request.urlopen(view.url, timeout=10).read().decode("utf-8")
    assert "网页版" in html and "自由编程" in html
    bank = get_json(view.url.rstrip("/") + "/api/bank")
    print("bank questions:", len(bank["questions"]))

    # 网页端判一题通过 → 桌面端 store 立刻能看到（同一份进度）
    q = bank["questions"][0]
    detail = [x for x in __import__("qbank").QUESTIONS if x["id"] == q["id"]][0]
    res = get_json(view.url.rstrip("/") + "/api/run", {"code": detail["ref"], "qid": q["id"]})
    assert res["judge"]["passed"], res
    get_json(view.url.rstrip("/") + "/api/attempt",
             {"qid": q["id"], "passed": True, "code": detail["ref"]})
    assert app.store.is_solved(q["id"]), "网页端判题没有写回桌面进度"
    app.refresh_global()
    app.update()
    print("shared progress ok:", app.progress_label.cget("text"))

    shot(app, "18_web_running.png")

    view.stop()
    app.update()
    assert view.server is None
    assert "已停止" in view.state_label.cget("text")

    app.destroy()
    print("DONE")


if __name__ == "__main__":
    main()
