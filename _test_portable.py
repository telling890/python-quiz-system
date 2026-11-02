# -*- coding: utf-8 -*-
"""数据落盘自检：进度优先存进程序自己的 data/（便携），只读时兜底、旧数据自动迁移、可导出导入。

这条链路是「关掉程序数据还在、换台电脑拷过去也在」的保证，所以单独测。
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import qbank
import store as storelib
from store import Store


def write_state(path, solved_ids):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    data = {"version": 1, "last_qid": None, "exams": [],
            "questions": {qid: {"attempts": 1, "passes": 1, "fails": 0,
                                "last": "pass", "code": "print(1)"}
                          for qid in solved_ids}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def main():
    ok = []
    work = tempfile.mkdtemp(prefix="pyquiz-portable-")
    app_root = os.path.join(work, "app")          # 假装是 exe 所在目录
    legacy = os.path.join(work, "legacy")         # 假装是 %LOCALAPPDATA%
    os.makedirs(app_root)
    os.makedirs(legacy)

    # 1. 默认位置就在程序自己的 data/ 里
    path = storelib.default_path(app_root, legacy)
    assert path == os.path.join(app_root, "data", "state.json"), path
    assert os.path.isdir(os.path.join(app_root, "data")), "data 目录没有建出来"
    ok.append("默认存到程序目录 data/state.json（便携）")

    # 2. 程序目录不可写时退回到用户目录（把 app_root 指向一个文件来模拟）
    blocker = os.path.join(work, "blocker")
    with open(blocker, "w", encoding="utf-8") as f:
        f.write("x")
    fallback = storelib.default_path(blocker, legacy)
    assert fallback == os.path.join(legacy, "PyQuizState", "state.json"), fallback
    ok.append("程序目录不可写时兜底到用户目录")

    # 3. 老位置有进度、新位置没有 → 自动迁移，且进度读得到
    write_state(os.path.join(legacy, "PyQuizState", "state.json"), ["3-01", "3-02"])
    with open(os.path.join(legacy, "PyQuizState", "custom_bank.json"), "w",
              encoding="utf-8") as f:
        json.dump([{"title": "t", "desc": "d", "ref": "print(1)",
                    "cases": [{"stdin": "", "expect": "1"}]}], f)

    s = Store(app_root=app_root, fallback_root=legacy)
    assert s.path == os.path.join(app_root, "data", "state.json"), s.path
    assert sorted(s.migrated) == ["custom_bank.json", "state.json"], s.migrated
    assert s.is_solved("3-01") and s.is_solved("3-02"), "迁移后进度丢了"
    assert os.path.isfile(os.path.join(app_root, "data", "custom_bank.json"))
    ok.append("旧进度与自定义题库自动迁移到 data/（{}）".format("、".join(sorted(s.migrated))))

    # 4. 再开一次不会重复迁移，也不会覆盖已有进度
    s.record_attempt("3-03", True)
    s2 = Store(app_root=app_root, fallback_root=legacy)
    assert s2.migrated == [], s2.migrated
    assert s2.is_solved("3-03"), "第二次启动把进度覆盖了"
    ok.append("第二次启动不再迁移，进度保留")

    # 5. 便携：整个 data 目录拷到「另一台电脑」也能读到
    other_app = os.path.join(work, "other_app")
    os.makedirs(other_app)
    shutil.copytree(os.path.join(app_root, "data"), os.path.join(other_app, "data"))
    s3 = Store(app_root=other_app, fallback_root=os.path.join(work, "empty_legacy"))
    assert s3.is_solved("3-01") and s3.is_solved("3-03"), "拷走后进度丢了"
    ok.append("把 data/ 拷到别处，进度与题库都跟着走")

    # 6. 导出 / 导入
    out = os.path.join(work, "backup.json")
    okk, err = s3.export_to(out)
    assert okk, err
    s3.reset()
    assert not s3.is_solved("3-01")
    okk, err = s3.import_from(out)
    assert okk, err
    assert s3.is_solved("3-01") and s3.is_solved("3-03"), "导入后进度不对"
    okk, err = s3.import_from(os.path.join(work, "not-exist.json"))
    assert not okk and "不存在" in err or err, err
    bad = os.path.join(work, "bad.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write('{"hello": 1}')
    okk, err = s3.import_from(bad)
    assert not okk and "不是本程序" in err, err
    assert s3.is_solved("3-01"), "导入失败时不该动现有数据"
    ok.append("进度可导出成 JSON、可导入恢复；坏文件不动现有数据")

    # 7. 自定义题库与进度用同一个数据目录
    assert os.path.dirname(qbank.CUSTOM_FILE) == os.path.dirname(storelib.default_path()), (
        qbank.CUSTOM_FILE, storelib.default_path())
    ok.append("自定义题库与进度同目录（换机一起带走）")

    # 8. 写入失败仍然会报错（不静默）
    blocked_path = os.path.join(blocker, "sub", "state.json")
    s4 = Store(path=blocked_path)
    assert s4.save() is False and s4.last_error, s4.last_error
    ok.append("写不进去时返回 False 并给出原因")

    print("数据落盘自检通过（{} 项）：".format(len(ok)))
    for line in ok:
        print("  ✓", line)


if __name__ == "__main__":
    main()
