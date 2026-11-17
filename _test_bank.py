# -*- coding: utf-8 -*-
"""题库质量守卫：查「题库本身有没有坏」，而不是「这段代码判得对不对」。

selftest.py 只回答一个问题：每道题的参考答案能不能通过自己的用例。
但题库还会以别的方式坏掉，而且坏得很安静：

  题号重复      进度按 id 存，两条题共用一个 id，通过记录会串到一起
  字段写空      hint / explain 空着，判题页就是一片空白，学员看不到提示
  用例写漏      expect 字段整个缺失 / 写成 None，判题时被当成「空输出」悄悄放水
  难度越界      level = 0 或 4，统计页「按难度」少一格 / 多一格
  章节错位      chapter 跟 CHAPTERS 对不上，概览里这道题就消失了
  代码有语法错  参考答案是照抄的，敲错一个引号，selftest 之前先炸在别处

这些都不会让判题报错，只会悄悄污染统计、组卷和进度。所以这里做结构守卫，
顺手可以把参考答案也跑一遍：

    python _test_bank.py          # 只查结构（毫秒级）
    python _test_bank.py --refs   # 顺带跑 139 份参考答案 / 338 个用例
    python _test_bank.py --strict # 把「提示」也当成失败（想彻底清干净时用）
    python _test_bank.py --all    # 提示不截断，全部列出来

退出码 0 表示全部通过；有错时退出码 1（CI 会拦下来）。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from qbank import QUESTIONS, CHAPTERS  # noqa: E402

LEVELS = (1, 2, 3)
TEXT_FIELDS = ("id", "chapter", "title", "topic", "desc", "hint", "ref", "explain")
# 转录 / 导入时最容易留下的占位符
PLACEHOLDERS = ("TODO", "todo", "FIXME", "待补", "????", "xxxx")


def _nonempty(value):
    return isinstance(value, str) and value.strip() != ""


def check_structure():
    """返回 (errors, warns)，都是 [(题号, 说明)] 列表。"""
    errors = []
    warns = []

    def err(qid, msg):
        errors.append((qid, msg))

    def warn(qid, msg):
        warns.append((qid, msg))

    chapter_names = [c["name"] for c in CHAPTERS]
    chapter_ids = [c["id"] for c in CHAPTERS]
    if len(set(chapter_names)) != len(chapter_names):
        err("(全局)", "章节名有重复：{}".format(chapter_names))
    if len(set(chapter_ids)) != len(chapter_ids):
        err("(全局)", "章节 id 有重复：{}".format(chapter_ids))

    seen_ids = {}
    for index, q in enumerate(QUESTIONS):
        raw_id = q.get("id")
        qid = str(raw_id).strip() if raw_id is not None else ""
        label = qid or "(第{}条无题号)".format(index + 1)

        # 1. 题号：非空、唯一
        if not qid:
            err(label, "题号是空的")
        elif qid in seen_ids:
            err(label, "题号重复（第 {} 条已经用过）".format(seen_ids[qid] + 1))
        else:
            seen_ids[qid] = index

        # 2. 必填文本字段不能空
        for field in TEXT_FIELDS:
            if not _nonempty(q.get(field)):
                err(label, "字段 {} 是空的".format(field))

        # 3. 教材题号 / 难度
        no = q.get("no")
        if not isinstance(no, int) or no <= 0:
            err(label, "no 必须是正整数（现在是 {!r}）".format(no))
        if q.get("level") not in LEVELS:
            err(label, "level 只能是 1 / 2 / 3（现在是 {!r}）".format(q.get("level")))

        # 4. 章节要能在 CHAPTERS 里找到
        if q.get("chapter") not in chapter_names:
            err(label, "chapter「{}」不在 CHAPTERS 里".format(q.get("chapter")))

        # 5. 用例：至少一条、字段齐全、expect 不能空、同一题内不重复
        cases = q.get("cases")
        if not isinstance(cases, list) or not cases:
            err(label, "没有测试用例（至少要有 1 条）")
            cases = []
        signatures = {}
        for case_index, case in enumerate(cases, 1):
            if not isinstance(case, dict):
                err(label, "第 {} 条用例不是对象".format(case_index))
                continue
            stdin = case.get("stdin", "")
            if "expect" not in case:
                err(label, "用例{} 没有 expect 字段".format(case_index))
            expect = case.get("expect")
            if not isinstance(stdin, str):
                err(label, "用例{} 的 stdin 不是字符串".format(case_index))
            if not isinstance(expect, str):
                # expect 写成空串是合法的（本题就是要「什么都不输出」），
                # 但字段整个缺失 / 写成 None 一定是抄漏了
                err(label, "用例{} 的 expect 不是字符串（{!r}）".format(case_index, expect))
            signature = (stdin, expect)
            if signature in signatures:
                err(label, "用例{} 和用例{} 完全一样".format(case_index, signatures[signature]))
            else:
                signatures[signature] = case_index

        # 单个用例 expect 为空是合法的（就是「什么都不该输出」），
        # 但整题都不检查输出，这道题等于没判
        expects = [c.get("expect") for c in cases if isinstance(c, dict)]
        if expects and all(isinstance(e, str) and e.strip() == "" for e in expects):
            err(label, "所有用例的 expect 都是空的，任何代码都能通过这一题")

        # 6. 参考答案至少得是能编译的 Python
        ref = q.get("ref") or ""
        if isinstance(ref, str) and ref.strip():
            try:
                compile(ref, "<{} 参考答案>".format(label), "exec")
            except SyntaxError as exc:
                err(label, "参考答案有语法错误：第 {} 行 {}".format(exc.lineno, exc.msg))

        # 7. 占位符检查（转录没转完就提交很容易出现）
        for field in ("title", "desc", "ref", "explain"):
            value = q.get(field)
            if not isinstance(value, str):
                continue
            for mark in PLACEHOLDERS:
                if mark in value:
                    err(label, "{} 里还留着占位符「{}」".format(field, mark))
                    break

        # --- 以下只是提示，不影响退出码 ---
        if len(cases) < 2:
            warn(label, "只有 1 条用例，建议再补一条边界（空输入 / 0 / 单行）")
        explain = q.get("explain")
        if isinstance(explain, str) and 0 < len(explain.strip()) < 15:
            warn(label, "explain 只有 {} 个字，讲不清易错点".format(len(explain.strip())))
        desc = q.get("desc")
        if isinstance(desc, str) and 0 < len(desc.strip()) < 8:
            warn(label, "desc 只有 {} 个字，学员可能看不懂要做什么".format(len(desc.strip())))

    # 8. 章节表与题目必须对得上（多一道 / 少一道都会让概览数字不对）
    total = 0
    for chapter in CHAPTERS:
        items = chapter.get("questions") or []
        total += len(items)
        if not items:
            err("(章节 {})".format(chapter.get("id")), "章节里一道题也没有")
        for q in items:
            if q.get("chapter") != chapter.get("name"):
                err(str(q.get("id")), "chapter 是「{}」，但被挂在「{}」下".format(
                    q.get("chapter"), chapter.get("name")))
    if total != len(QUESTIONS):
        err("(全局)", "章节题目合计 {} 道，QUESTIONS 里却有 {} 道".format(total, len(QUESTIONS)))

    # 9. 每章里的教材题号不该重复（跨章重复是正常的）
    for chapter in CHAPTERS:
        numbers = {}
        for q in chapter.get("questions") or []:
            no = q.get("no")
            if no in numbers:
                err(str(q.get("id")), "本章题号 {} 和第 {} 题撞了".format(no, numbers[no]))
            else:
                numbers[no] = q.get("id")

    return errors, warns


def check_refs():
    """跑一遍参考答案：每题必须能通过自己全部用例（慢一点，--refs 才做）。"""
    from judge import run_case

    errors = []
    for q in QUESTIONS:
        qid = str(q.get("id") or "?")
        for case_index, case in enumerate(q.get("cases") or [], 1):
            result = run_case(q["ref"], case)
            if result["status"] != "pass":
                detail = "参考答案没过用例{}（{}）".format(case_index, result["status"])
                if result["error"]:
                    detail += "：{}".format(result["error"].splitlines()[0])
                else:
                    detail += "：期望 {!r}，实际 {!r}".format(
                        case.get("expect"), result["actual"])
                errors.append((qid, detail))
                break  # 一道题只报第一条，后面多半是连锁错误
    return errors


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    with_refs = "--refs" in argv
    strict = "--strict" in argv
    show_all = "--all" in argv
    unknown = [a for a in argv if a not in ("--refs", "--strict", "--all", "-h", "--help")]
    if unknown or "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0 if ("-h" in argv or "--help" in argv) else 2

    errors, warns = check_structure()
    ref_errors = check_refs() if with_refs else []
    errors = errors + ref_errors

    cases = sum(len(q.get("cases") or []) for q in QUESTIONS)
    print("题库：{} 道题 / {} 个用例 / {} 个章节".format(
        len(QUESTIONS), cases, len(CHAPTERS)))
    for chapter in CHAPTERS:
        print("  {:<8} {:>3} 道".format(chapter.get("short") or chapter.get("name"),
                                        len(chapter.get("questions") or [])))
    print("参考答案：{}".format("已全量验证" if with_refs else "未运行（加 --refs 才跑）"))

    if errors:
        print("-" * 64)
        print("失败 {} 处：".format(len(errors)))
        for qid, msg in errors:
            print("  [FAIL] {} {}".format(qid, msg))
    if warns:
        shown = warns if show_all else warns[:12]
        print("-" * 64)
        print("提示 {} 处（不阻塞）：".format(len(warns)))
        for qid, msg in shown:
            print("  [提示] {} {}".format(qid, msg))
        if len(shown) < len(warns):
            print("  …… 另有 {} 条同类提示，加 --all 看全部".format(len(warns) - len(shown)))

    print("-" * 64)
    if errors or (strict and warns):
        print("题库守卫：失败（{} 处错误{}）".format(
            len(errors), "，{} 处提示（--strict）".format(len(warns)) if strict else ""))
        return 1
    print("题库守卫：通过（{} 道题{}）".format(
        len(QUESTIONS), " + 参考答案全过" if with_refs else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
