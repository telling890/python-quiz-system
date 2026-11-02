# -*- coding: utf-8 -*-
"""学习进度持久化：收藏、错题、通过状态、上次写的代码、自由编程草稿与片段。

存放位置按这个顺序决定：
1. 环境变量 PYQUIZ_STATE_DIR（想放到别处时用）
2. 程序自己的 data/ 目录 —— 便携：整个文件夹拷到 U 盘或别的电脑，进度跟着走
3. %LOCALAPPDATA%\\PyQuizState —— 程序目录不可写（放在 Program Files 等位置）时兜底

旧版本的数据在 %LOCALAPPDATA%\\PyQuizState 里，第一次用新位置时会自动迁移过来。
"""

import io
import os
import json
import shutil
import time

import sys

STATE_NAME = "state.json"
DATA_DIRNAME = "data"
LEGACY_DIRNAME = "PyQuizState"


def app_dir():
    """程序所在目录：打包后是 exe 所在目录，源码运行时是本文件所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def portable_dir(app_root=None):
    """便携目录：程序旁边的 data/。"""
    return os.path.join(app_root or app_dir(), DATA_DIRNAME)


def legacy_dir(base=None):
    """旧版本（也是兜底）的位置：%LOCALAPPDATA%\\PyQuizState。"""
    root = base if base is not None else (os.environ.get("LOCALAPPDATA")
                                          or os.path.expanduser("~"))
    return os.path.join(root, LEGACY_DIRNAME)


def _writable(folder):
    """真的写一个探针文件，确认这个目录能写（只看权限位不准）。"""
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".pyquiz-write-test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def _first_writable(*folders):
    for folder in folders:
        if folder and _writable(folder):
            return folder
    return os.path.expanduser("~")


def default_path(app_root=None, fallback_root=None):
    """进度文件位置，返回值一定带完整文件名。"""
    custom = os.environ.get("PYQUIZ_STATE_DIR")
    if custom:
        folder = _first_writable(os.path.expanduser(custom))
        return os.path.join(folder, STATE_NAME)

    folder = _first_writable(portable_dir(app_root), legacy_dir(fallback_root))
    return os.path.join(folder, STATE_NAME)


def _copy_if_missing(target, source):
    """把旧位置的同名文件搬到新位置（新位置已有文件时不动）。"""
    try:
        if os.path.exists(target) or not os.path.isfile(source):
            return False
        folder = os.path.dirname(target)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        shutil.copy2(source, target)
        return True
    except OSError:
        return False


def migrate_legacy(target_path, fallback_root=None):
    """把 %LOCALAPPDATA%\\PyQuizState 里的 state.json / custom_bank.json 迁到新位置。

    返回被迁移过来的文件名列表；新位置已有数据时返回空列表（不去覆盖）。
    """
    folder = os.path.dirname(target_path)
    old = legacy_dir(fallback_root)
    if os.path.abspath(folder) == os.path.abspath(old):
        return []
    moved = []
    for name in (STATE_NAME, "custom_bank.json"):
        if _copy_if_missing(os.path.join(folder, name), os.path.join(old, name)):
            moved.append(name)
    return moved


def _blank_record():
    return {
        "attempts": 0,
        "passes": 0,
        "fails": 0,
        "favorite": False,
        "code": "",
        "last": "",
        "seen": 0,
        "updated": "",
    }


def describe_error(exc, path):
    """把写盘异常翻译成用户能看懂的一句话。"""
    if isinstance(exc, PermissionError):
        reason = "没有写入权限（可能被安全软件拦截，或文件被设为只读）"
    elif isinstance(exc, FileNotFoundError):
        reason = "保存目录不存在"
    elif isinstance(exc, OSError) and getattr(exc, "errno", None) == 28:
        reason = "磁盘空间不足"
    elif isinstance(exc, ValueError):
        reason = "进度数据无法序列化"
    else:
        reason = str(exc) or exc.__class__.__name__
    return "{}（{}）".format(reason, path)


class Store(object):
    def __init__(self, path=None, app_root=None, fallback_root=None):
        self.migrated = []
        if path is None:
            self.path = default_path(app_root, fallback_root)
            # 新位置还没有数据时，把老位置（%LOCALAPPDATA%）的进度搬过来
            self.migrated = migrate_legacy(self.path, fallback_root)
        else:
            self.path = path
        self.data = {"version": 1, "questions": {}, "last_qid": None, "exams": [],
                     "free": {"code": "", "stdin": ""}, "snippets": []}
        self.last_error = ""
        self.fail_count = 0
        self.on_save_error = None     # 写入失败时回调（参数：错误说明）
        self.on_save_ok = None        # 从失败状态恢复时回调（参数：无）
        self.load()

    # ---------------------------------------------------------------- 位置
    @property
    def folder(self):
        """数据所在目录（设置页展示、打开文件夹用）。"""
        return os.path.dirname(os.path.abspath(self.path))

    @property
    def portable(self):
        """数据是否就存在程序自己的 data/ 目录里。"""
        return os.path.basename(self.folder) == DATA_DIRNAME

    # ---------------------------------------------------------------- 封存 / 恢复
    def export_to(self, target):
        """把当前进度整份导出成一个 JSON（换机、交作业、备份都用它）。"""
        try:
            folder = os.path.dirname(os.path.abspath(target))
            if folder and not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            with io.open(target, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.data, ensure_ascii=False, indent=2))
            return True, ""
        except (OSError, ValueError) as exc:
            return False, describe_error(exc, target)

    def import_from(self, source):
        """从导出的 JSON 恢复进度；格式不对就不动现有数据。"""
        try:
            with io.open(source, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            return False, describe_error(exc, source)
        if not (isinstance(data, dict) and isinstance(data.get("questions"), dict)):
            return False, "这个文件不是本程序导出的进度文件"
        self.data = data
        self.data.setdefault("free", {"code": "", "stdin": ""})
        self.data.setdefault("snippets", [])
        self.data.setdefault("exams", [])
        if not self.save():
            return False, self.last_error
        return True, ""

    # ---------------------------------------------------------------- 读写
    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with io.open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("questions"), dict):
                self.data = data
        except (ValueError, OSError):
            # 文件损坏时不阻塞启动，从空进度开始
            self.data = {"version": 1, "questions": {}, "last_qid": None, "exams": []}

    def save(self):
        """写盘。成功返回 True；失败返回 False 并把原因记在 last_error。"""
        tmp = self.path + ".tmp"
        try:
            folder = os.path.dirname(self.path)
            if folder and not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            with io.open(tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.data, ensure_ascii=False, indent=2))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except (OSError, ValueError) as exc:
            self.last_error = describe_error(exc, self.path)
            self.fail_count += 1
            try:                      # 别把写了一半的临时文件留在那里
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            if self.on_save_error:
                self.on_save_error(self.last_error)
            return False

        recovered = self.fail_count > 0
        self.fail_count = 0
        self.last_error = ""
        if recovered and self.on_save_ok:
            self.on_save_ok()
        return True

    # ---------------------------------------------------------------- 记录
    def record(self, qid):
        rec = self.data["questions"].setdefault(qid, _blank_record())
        return rec

    def mark_seen(self, qid):
        rec = self.record(qid)
        rec["seen"] = rec.get("seen", 0) + 1

    def save_code(self, qid, code):
        self.record(qid)["code"] = code

    def get_code(self, qid):
        return self.record(qid).get("code", "")

    def record_attempt(self, qid, passed, code=""):
        rec = self.record(qid)
        rec["attempts"] = rec.get("attempts", 0) + 1
        if passed:
            rec["passes"] = rec.get("passes", 0) + 1
            rec["last"] = "pass"
        else:
            rec["fails"] = rec.get("fails", 0) + 1
            rec["last"] = "fail"
        rec["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if code:
            rec["code"] = code
        self.save()
        return rec

    def toggle_favorite(self, qid):
        rec = self.record(qid)
        rec["favorite"] = not rec.get("favorite", False)
        self.save()
        return rec["favorite"]

    # ---------------------------------------------------------------- 查询
    def is_favorite(self, qid):
        return bool(self.record(qid).get("favorite", False))

    def is_solved(self, qid):
        return self.record(qid).get("last") == "pass"

    def is_wrong(self, qid):
        rec = self.record(qid)
        return rec.get("attempts", 0) > 0 and rec.get("last") != "pass"

    def favorites(self, questions):
        return [q for q in questions if self.is_favorite(q["id"])]

    def wrongs(self, questions):
        return [q for q in questions if self.is_wrong(q["id"])]

    def stats(self, questions):
        total = len(questions)
        solved = sum(1 for q in questions if self.is_solved(q["id"]))
        tried = sum(1 for q in questions if self.record(q["id"]).get("attempts", 0) > 0)
        fav = sum(1 for q in questions if self.is_favorite(q["id"]))
        attempts = sum(self.record(q["id"]).get("attempts", 0) for q in questions)
        passes = sum(self.record(q["id"]).get("passes", 0) for q in questions)
        rate = int(round(passes * 100.0 / attempts)) if attempts else 0
        return {
            "total": total,
            "solved": solved,
            "tried": tried,
            "favorite": fav,
            "attempts": attempts,
            "passes": passes,
            "rate": rate,
        }

    # ---------------------------------------------------------------- 考试记录
    def record_exam(self, summary, meta=None):
        """保存一次组卷考试的结果，最多保留最近 50 次。"""
        record = dict(meta or {})
        record.update({
            "finished_at": summary.get("finished_at", ""),
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "score": summary.get("score", 0),
            "seconds": summary.get("seconds", 0),
        })
        exams = self.data.setdefault("exams", [])
        exams.append(record)
        self.data["exams"] = exams[-50:]
        self.save()
        return record

    def exam_history(self, limit=20):
        return list(reversed(self.data.get("exams", [])))[:limit]

    def reset(self):
        self.data = {"version": 1, "questions": {}, "last_qid": None, "exams": [],
                     "free": {"code": "", "stdin": ""},
                     "snippets": self.snippets()}   # 自由编程的片段是用户的素材，保留
        self.save()

    # ---------------------------------------------------------------- 自由编程
    def free_state(self):
        """自由编程页的草稿（代码 + 标准输入），老版本进度文件里没有就先补上。"""
        free = self.data.get("free")
        if not isinstance(free, dict):
            free = {}
        free.setdefault("code", "")
        free.setdefault("stdin", "")
        self.data["free"] = free
        return free

    def save_free(self, code, stdin_text=""):
        free = self.free_state()
        free["code"] = code
        free["stdin"] = stdin_text
        free["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return self.save()

    def snippets(self):
        """代码片段列表，按最近修改排在前面。"""
        items = self.data.get("snippets")
        if not isinstance(items, list):
            items = []
        items = [it for it in items if isinstance(it, dict) and it.get("name")]
        self.data["snippets"] = items
        return sorted(items, key=lambda it: it.get("updated", ""), reverse=True)

    def save_snippet(self, name, code, limit=60):
        """保存/覆盖一个片段，返回 True 表示新增、False 表示覆盖。"""
        name = (name or "").strip()
        if not name:
            return None
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        items = self.snippets()
        created = True
        for it in items:
            if it.get("name") == name:
                it["code"] = code
                it["updated"] = now
                created = False
                break
        if created:
            items.append({"name": name, "code": code, "updated": now})
            items = items[-limit:]
        self.data["snippets"] = items
        self.save()
        return created

    def delete_snippet(self, name):
        before = self.snippets()
        items = [it for it in before if it.get("name") != name]
        if len(items) == len(before):
            return False
        self.data["snippets"] = items
        self.save()
        return True
