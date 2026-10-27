# -*- coding: utf-8 -*-
"""验证「进度保存失败」的提示链路：

1. 正常写入返回 True；
2. 写不进去时返回 False，last_error 有可读原因，并触发 on_save_error；
3. 恢复可写后返回 True 并触发 on_save_ok；
4. 界面上会出现侧栏告警（用假路径触发一次）。
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import store as storelib


def main():
    tmp = tempfile.mkdtemp(prefix="quizstore_")
    try:
        # 1. 正常
        s = storelib.Store(os.path.join(tmp, "state.json"))
        assert s.save() is True, "正常路径应返回 True"
        assert s.last_error == "", s.last_error
        print("✓ 正常写入返回 True")

        # 2. 写失败：把父目录换成一个普通文件，makedirs 会失败
        blocker = os.path.join(tmp, "blocker")
        with open(blocker, "w", encoding="utf-8") as f:
            f.write("x")
        errors = []
        oks = []
        s.path = os.path.join(blocker, "sub", "state.json")
        s.on_save_error = lambda msg: errors.append(msg)
        s.on_save_ok = lambda: oks.append(1)
        ok = s.save()
        assert ok is False, "写不进去时应返回 False"
        assert s.fail_count == 1
        assert s.last_error, "应记录失败原因"
        assert errors and len(errors) == 1, "应触发一次 on_save_error"
        print("✓ 失败返回 False，原因：", s.last_error)

        # 3. 恢复
        s.path = os.path.join(tmp, "state.json")
        assert s.save() is True, "恢复后应返回 True"
        assert oks == [1], "应触发一次 on_save_ok"
        assert s.fail_count == 0 and s.last_error == ""
        print("✓ 恢复后返回 True 并回调 on_save_ok")

        # 4. 只读目录（Windows 上 chmod 不一定拦得住，用文件当目录的方式已验证，这里跳过）
        print("✓ 失败原因翻译：",
              storelib.describe_error(PermissionError(13, "denied"), "C:/x/state.json"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 5. 界面：造一次真实失败，看侧栏是否出现告警（CI 里用 --no-ui 跳过）
    if "--no-ui" in sys.argv:
        print("\n保存失败提示链路自检通过（跳过界面部分）")
        return
    from main import _enable_dpi_awareness
    _enable_dpi_awareness()
    from ui import App

    app = App()
    app.update()
    blocker = os.path.join(tempfile.gettempdir(), "blocked_dir_file")
    with open(blocker, "w", encoding="utf-8") as f:
        f.write("x")
    try:
        app.store.path = os.path.join(blocker, "sub", "state.json")
        app.store.save()
        app.update()
        assert app.save_warning.winfo_ismapped(), "侧栏应出现告警"
        assert "进度未保存" in app.save_warning.cget("text")
        print("✓ 侧栏出现告警：", app.save_warning.cget("text").replace("\n", " / "))
        assert app._save_warned is True, "应标记已弹窗提示过"

        # 恢复后告警消失
        app.store.path = os.path.join(tempfile.gettempdir(), "pyquiz_state_ok", "state.json")
        app.store.save()
        app.update()
        assert not app.save_warning.winfo_ismapped(), "恢复后告警应消失"
        print("✓ 恢复保存后告警自动消失")
        shutil.rmtree(os.path.dirname(app.store.path), ignore_errors=True)
    finally:
        os.remove(blocker)
        app.destroy()

    print("\n保存失败提示链路自检通过")


if __name__ == "__main__":
    main()
