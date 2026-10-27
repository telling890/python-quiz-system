# -*- coding: utf-8 -*-
"""学习进度持久化：收藏、错题、通过状态、上次写的代码。

保存在 %LOCALAPPDATA%\\PyQuizState\\state.json，不写在 exe 目录里，
避免程序放在只读目录（如 Program Files）时无法保存。
"""

import io
import os
import json
import time


def default_path():
    """进度文件位置：默认 %LOCALAPPDATA%\\PyQuizState，可用 PYQUIZ_STATE_DIR 覆盖。"""
    custom = os.environ.get("PYQUIZ_STATE_DIR")
    if custom:
        folder = os.path.expanduser(custom)
    else:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "PyQuizState")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = os.path.expanduser("~")
    return os.path.join(folder, "state.json")


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
    def __init__(self, path=None):
        self.path = path or default_path()
        self.data = {"version": 1, "questions": {}, "last_qid": None, "exams": []}
        self.last_error = ""
        self.fail_count = 0
        self.on_save_error = None     # 写入失败时回调（参数：错误说明）
        self.on_save_ok = None        # 从失败状态恢复时回调（参数：无）
        self.load()

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
        self.data = {"version": 1, "questions": {}, "last_qid": None, "exams": []}
        self.save()
