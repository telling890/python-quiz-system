# -*- coding: utf-8 -*-
"""后台判题 worker：线程池从数据库里认领 queued 提交，判完写回。

为什么用数据库认领而不是纯内存队列：
- 进程内 queue 只在单进程内有效，uvicorn 起多个 worker 或把判题拆到独立容器后，
  提交会被「排到另一个进程的队列里」，前端永远等到 running；
- 数据库认领（UPDATE ... WHERE status='queued'）靠乐观更新保证不会被跑两次，
  于是 API 可以横向扩容，worker 也可以单独起（见 scripts/run_worker.py）。

接口因此是异步的：POST /submissions 立刻返回 id，前端轮询 GET /submissions/{id}。
"""

import json
import queue
import threading
import time
import traceback

from ..db import SessionLocal
from ..models import Question, Record, Submission, now_iso
from .compare import first_diff, normalize_lines
from .executor import run_python

_STOP = object()
_POLL_SECONDS = 0.5
_STALE_RUNNING_MINUTES = 10


class JudgeService:
    def __init__(self, workers=2):
        self.workers = max(1, int(workers))
        self.queue = queue.Queue()
        self.threads = []
        self.started = False
        self._stop_flag = threading.Event()

    # ------------------------------------------------------------ 生命周期
    def start(self):
        if self.started:
            return
        self._recover_stale()
        self._stop_flag.clear()
        for i in range(self.workers):
            thread = threading.Thread(target=self._loop, name="judge-{}".format(i), daemon=True)
            thread.start()
            self.threads.append(thread)
        self.started = True

    def stop(self):
        if not self.started:
            return
        self._stop_flag.set()
        for _ in self.threads:
            self.queue.put(_STOP)
        for thread in self.threads:
            thread.join(timeout=5)
        self.threads = []
        self.started = False

    def enqueue(self, submission_id):
        """本地快速通道：同进程的 worker 立刻被叫醒；跨进程靠轮询兜底。"""
        self.queue.put(submission_id)

    def _recover_stale(self):
        """把「卡在 running」的僵尸提交捞回来（比如判题进程被 kill -9）。"""
        cutoff = time.strftime("%Y-%m-%dT%H:%M:%S",
                               time.gmtime(time.time() - _STALE_RUNNING_MINUTES * 60))
        with SessionLocal() as db:
            stale = (db.query(Submission)
                     .filter(Submission.status == "running",
                             Submission.created_at < cutoff).all())
            for item in stale:
                item.status = "queued"
            if stale:
                db.commit()

    # ------------------------------------------------------------ 消费
    def _loop(self):
        while not self._stop_flag.is_set():
            try:
                item = self.queue.get(timeout=_POLL_SECONDS)
            except queue.Empty:
                item = self._claim_next()
                if item is None:
                    continue
            if item is _STOP:
                return
            try:
                self._process(item)
            except Exception:                        # noqa: BLE001 - worker 不能死
                traceback.print_exc()
            finally:
                try:
                    self.queue.task_done()
                except ValueError:
                    pass

    def _claim_next(self):
        """从数据库里挑一条 queued 并原子地改成 running；没有就返回 None。"""
        with SessionLocal() as db:
            candidate = (db.query(Submission)
                         .filter(Submission.status == "queued")
                         .order_by(Submission.created_at)
                         .first())
            if candidate is None:
                return None
            claimed = (db.query(Submission)
                       .filter(Submission.id == candidate.id, Submission.status == "queued")
                       .update({"status": "running"}, synchronize_session=False))
            db.commit()
            return candidate.id if claimed == 1 else None

    def _process(self, submission_id):
        with SessionLocal() as db:
            submission = db.get(Submission, submission_id)
            if submission is None:
                return
            if submission.status != "running":
                # 内存队列叫醒的这条可能已被别的进程认领，认领失败就放手
                claimed = (db.query(Submission)
                           .filter(Submission.id == submission_id,
                                   Submission.status == "queued")
                           .update({"status": "running"}, synchronize_session=False))
                db.commit()
                if claimed != 1:
                    return
                db.refresh(submission)

            question = None
            if submission.question_id:
                question = db.get(Question, submission.question_id)

            try:
                if question is None:
                    result = self._run_free(submission.code, submission.stdin)
                else:
                    result = self._run_judge(submission.code, question)
            except Exception as exc:                 # noqa: BLE001
                result = {"mode": "judge", "passed": False, "total": 0, "results": [],
                          "status": "error", "error": "判题过程出错：{}".format(exc)}

            status = result.get("status") or "error"
            submission.status = status
            submission.result_json = json.dumps(result, ensure_ascii=False)
            submission.error = result.get("error", "")
            submission.finished_at = now_iso()
            submission.duration_ms = int(result.get("duration_ms") or 0)

            if question is not None:
                try:
                    self._update_record(db, submission, question, status == "passed")
                except Exception:                    # noqa: BLE001 - 进度写失败不影响判题结果
                    db.rollback()
                    traceback.print_exc()

            db.commit()

            # 保留提交历史，只清理过老的数据
            try:
                self._prune(db, submission.user_id)
            except Exception:                        # noqa: BLE001
                db.rollback()

    # ------------------------------------------------------------ 判题
    def _run_free(self, code, stdin_text):
        """自由编程：跑一遍就算过，实现见模块级 run_free_code。"""
        return run_free_code(code, stdin_text)

    def _run_judge(self, code, question):
        """题目判题：逐条用例比对，实现见模块级 judge_question。"""
        return judge_question(code, question)

    def _update_record(self, db, submission, question, passed):
        record = db.query(Record).filter(Record.user_id == submission.user_id,
                                         Record.question_id == question.id).one_or_none()
        if record is None:
            # SQLAlchemy 的 default=0 是 flush 时才生效的，构造时得显式给初值
            record = Record(user_id=submission.user_id, question_id=question.id,
                            attempts=0, passes=0, fails=0, last="", code="", favorite=False)
            db.add(record)
        record.attempts += 1
        if passed:
            record.passes += 1
            record.last = "pass"
        else:
            record.fails += 1
            record.last = "fail"
        record.code = submission.code
        record.updated = now_iso()

    def _prune(self, db, user_id, keep=100):
        stale = (db.query(Submission)
                 .filter(Submission.user_id == user_id)
                 .order_by(Submission.created_at.desc())
                 .offset(keep).all())
        for item in stale:
            db.delete(item)
        if stale:
            db.commit()


def run_free_code(code, stdin_text):
    """自由编程：跑一遍，按输出/报错/超时给个状态（不需要测试用例）。"""
    run = run_python(code, stdin_text)
    if run["timeout"]:
        status = "timeout"
    elif run["error"]:
        status = "error"
    else:
        status = "passed"
    return {"mode": "free", "passed": status == "passed", "status": status,
            "results": [], "run": run, "duration_ms": run["duration_ms"],
            "error": run["error"]}


def judge_question(code, question):
    """题目判题：逐条跑用例，第一个不通过就停（与桌面版一致）。

    模块级函数，队列 worker 和同步接口（/api/run）共用同一份实现，
    避免「异步判题」和「即时判题」给出不一样的结果。
    """
    try:
        cases = json.loads(question.cases_json or "[]")
    except ValueError:
        cases = []
    results = []
    passed = True
    for index, case in enumerate(cases):
        run = run_python(code, case.get("stdin", ""))
        raw = bool(case.get("raw"))
        expect_lines = normalize_lines(case.get("expect", ""), keep_indent=raw)
        actual_lines = normalize_lines(run["output"], keep_indent=raw)
        item = {
            "index": index,
            "stdin": case.get("stdin", ""),
            "expect": case.get("expect", ""),
            "actual": run["output"],
            "error": run["error"],
            "timeout": run["timeout"],
            "truncated": run["truncated"],
            "expect_lines": expect_lines,
            "actual_lines": actual_lines,
            "duration_ms": run["duration_ms"],
            "status": "pass",
            "first_diff": None,
        }
        if run["timeout"]:
            item["status"] = "timeout"
        elif run["error"]:
            item["status"] = "error"
        elif actual_lines != expect_lines:
            item["status"] = "fail"
            item["first_diff"] = first_diff(expect_lines, actual_lines)
        results.append(item)
        if item["status"] != "pass":
            passed = False
            break

    if any(r["status"] == "timeout" for r in results):
        status = "timeout"
    elif any(r["status"] == "error" for r in results):
        status = "error"
    else:
        status = "passed" if passed else "failed"

    return {"mode": "judge", "passed": passed, "status": status,
            "total": len(cases), "results": results,
            "duration_ms": sum(int(r.get("duration_ms") or 0) for r in results)}


_service = None
_lock = threading.Lock()


def get_service():
    global _service
    with _lock:
        if _service is None:
            from ..config import get_settings
            _service = JudgeService(get_settings().judge_workers)
        return _service
