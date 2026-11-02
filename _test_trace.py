# -*- coding: utf-8 -*-
"""执行过程追踪自检：逐步快照、变量、输出、函数调用、超时与安全边界。"""

import os
import sys
import builtins

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import tracer
from judge import normalize_lines
from qbank import QUESTIONS


def _lines(trace):
    return [s["line"] for s in trace["steps"]]


def _var(step, name):
    for k, v in step["vars"]:
        if k == name:
            return v
    return None


def main():
    ok = []

    # 1. 循环：行号顺序、变量累加
    code = "total = 0\nfor i in range(3):\n    total += i\nprint(total)\n"
    tr = tracer.trace_code(code)
    assert not tr["error"], tr["error"]
    assert normalize_lines(tr["output"]) == ["3"], tr["output"]
    lines = _lines(tr)
    assert lines[0] == 1, lines
    assert lines.count(3) == 3, lines          # 循环体执行 3 次
    assert lines.count(2) == 4, lines          # 循环条件判断 3 次 + 最后一次为假
    total_steps = [s for s in tr["steps"] if _var(s, "total") == "3"]
    assert total_steps, "应该有一步 total 累加到 3"
    i_steps = [s for s in tr["steps"] if _var(s, "i") == "2"]
    assert i_steps, "循环变量 i 应出现 2"
    ok.append("循环 3 次：行号顺序正确，total 累加到 3")

    # 2. 输出是逐步累积的：print 之前为空，最后一步包含结果
    assert tr["steps"][-1]["out"] == "3\n", tr["steps"][-1]["out"]
    first_print = [s for s in tr["steps"] if s["line"] == 4][0]
    assert first_print["out"] == "", first_print["out"]
    ok.append("输出逐步累积：进入 print 前为空，结束后为 3")

    # 3. 函数调用：进入函数时深度 +1，参数可见
    code = ("def add(a, b):\n"
            "    s = a + b\n"
            "    return s\n"
            "\n"
            "print(add(1, 2))\n")
    tr = tracer.trace_code(code)
    assert not tr["error"], tr["error"]
    nested = [s for s in tr["steps"] if s["func"] == "add"]
    assert nested, "应记录到函数 add 内部的步骤"
    assert nested[0]["depth"] == 1, nested[0]["depth"]
    assert _var(nested[0], "a") == "1", nested[0]["vars"]
    assert normalize_lines(tr["output"]) == ["3"], tr["output"]
    ok.append("函数调用：add() 内部步骤 depth=1，参数 a=1 可见")

    # 4. input() 从用例取数，且不回显提示语
    code = 'n = int(input("请输入："))\nprint(n * 2)\n'
    tr = tracer.trace_code(code, "21\n")
    assert not tr["error"], tr["error"]
    assert _var(tr["steps"][-1], "n") == "21", tr["steps"][-1]["vars"]
    assert normalize_lines(tr["output"]) == ["42"], tr["output"]
    ok.append("input() 取用例数据、提示语不混入输出")

    # 5. 死循环：看门狗打断，标记 timeout
    #    每步都做一次真实的求和，保证「跑得慢」先于「步数到顶」触发
    tr = tracer.trace_code("while True:\n    x = sum(range(200000))\n", timeout=0.3)
    assert tr["timeout"], "死循环应标记 timeout"
    assert tr["steps"], "超时前应已记录若干步"
    assert "超时" in tracer.describe(tr), tracer.describe(tr)
    ok.append("死循环在第 {} 步被打断（0.3s 看门狗）".format(len(tr["steps"])))

    # 6. 步数封顶：长循环只记前 N 步
    tr = tracer.trace_code("for i in range(1000):\n    pass\n", max_steps=40)
    assert tr["truncated"], "长循环应标记 truncated"
    assert len(tr["steps"]) <= 40, len(tr["steps"])
    assert "只记录了前" in tracer.describe(tr) or "前 40 步" in tracer.describe(tr), tracer.describe(tr)
    ok.append("长循环步数封顶：只记前 {} 步".format(len(tr["steps"])))

    # 7. 语法错误单独标记
    tr = tracer.trace_code("if True print(1)\n")
    assert tr["syntax"], "语法错误应标记 syntax"
    assert "SyntaxError" in tr["error"], tr["error"]
    assert not tr["steps"]
    ok.append("语法错误：标记 syntax 并给出原因")

    # 8. 危险调用与判题一致地拦掉
    tr = tracer.trace_code("import os\nos.system('dir')\n")
    assert "不允许" in tr["error"], tr["error"]
    assert not tr["steps"]
    ok.append("危险调用被拦截（与判题同一套黑名单）")

    # 9. 与判题互不干扰：追踪后 stdout / input 复原
    before_out, before_input = sys.stdout, builtins.input
    tracer.trace_code("print('x')\n")
    assert sys.stdout is before_out, "stdout 未复原"
    assert builtins.input is before_input, "input 未复原"
    ok.append("追踪结束后 stdout / input 已复原")

    # 10. 真实题库：追踪参考答案的输出与判题期望一致（步数超限的题按约定跳过）
    checked = skipped = 0
    for q in QUESTIONS:
        case = q["cases"][0]
        tr = tracer.trace_code(q["ref"], case.get("stdin", ""))
        if tr["truncated"] or tr["timeout"]:
            skipped += 1
            continue
        assert not tr["error"], "{} 追踪出错：{}".format(q["id"], tr["error"])
        raw = bool(case.get("raw"))
        expect = normalize_lines(case.get("expect", ""), keep_indent=raw)
        actual = normalize_lines(tr["output"], keep_indent=raw)
        assert actual == expect, "{} 追踪输出与期望不一致".format(q["id"])
        checked += 1
    assert checked >= 130, "可完整追踪的题目太少：{}".format(checked)
    ok.append("{} 道题的参考答案：追踪输出与判题期望逐字一致"
              "（{} 道循环过长按约定截断）".format(checked, skipped))

    # 11. 变量值展示：超长截断、换行转符号
    assert tracer.format_value("a" * 100).endswith("…"), "超长应截断"
    assert "\n" not in tracer.format_value("a\nb"), "换行应转成符号"
    assert tracer.format_value(None) == "None"
    ok.append("变量值格式化：截断、换行转符号")

    # 12. step_title 区分主流程与函数内部
    tr = tracer.trace_code("def f():\n    return 1\n\nf()\n")
    nested = [s for s in tr["steps"] if s["func"] == "f" and s["depth"] > 0][0]
    top = [s for s in tr["steps"] if s["depth"] == 0][0]
    assert "f()" in tracer.step_title(nested), tracer.step_title(nested)
    assert "行" in tracer.step_title(top)
    ok.append("步骤标题：函数内部标注「在 f() 里」")

    print("执行过程追踪自检通过（{} 项）：".format(len(ok)))
    for line in ok:
        print("  ✓", line)


if __name__ == "__main__":
    main()
