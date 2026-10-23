# -*- coding: utf-8 -*-
"""生成《项目汇报》文档：把需求、设计、实现、测试、演示重新梳理成一份汇报稿。

运行： python docs/build_report.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

import build_docs as BD
from build_docs import (new_doc, title_page, h1, h2, para, bullet, table,
                        caption, cn, PROJECT, VERSION, DATE)
from qbank import QUESTIONS, CHAPTERS

SHOTS = os.path.join(ROOT, "shots")
TOTAL_Q = len(QUESTIONS)
TOTAL_CASES = sum(len(q["cases"]) for q in QUESTIONS)
N_CHAPTERS = len(CHAPTERS)


def picture(doc, name, width_cm=15.5, note=None):
    path = os.path.join(SHOTS, name)
    if not os.path.exists(path):
        return
    doc.add_picture(path, width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if note:
        caption(doc, note)


def build():
    del BD.TOC_ENTRIES[:]
    BD.use_pages("report")
    doc = new_doc()
    marker = title_page(doc, "项目汇报", [
        "版本：{}".format(VERSION),
        "日期：{}".format(DATE),
        "内容：题库建设 · 判题引擎 · 学习闭环 · 模拟组卷 · 质量保障",
    ])

    # ---------------------------------------------------------------- 1
    h1(doc, "1 项目概况")
    para(doc, "本项目把《Python 程序设计实验指导与习题解答》第 3～5 章的实验题，做成一个"
              "离线可判题的桌面程序：学生在编辑器里写代码，按 F5 立即得到逐条用例的判定结果，"
              "错题自动收集、进度自动保存；在此之上又扩展了网络经典题与算法入门题，"
              "并加入随机组卷的模拟考试模块。")
    para(doc, "程序打包为免安装目录版（另附便携 zip），拷到任意一台 Windows 电脑双击即可运行，"
              "目标机器不需要安装 Python。")

    table(doc, ["指标", "数值"], [
        ["题库总量", "{} 题（{} 个章节）".format(TOTAL_Q, N_CHAPTERS)],
        ["测试用例", "{} 个".format(TOTAL_CASES)],
        ["判题方式", "内置用例逐条比对，单次运行 6 秒超时"],
        ["组卷能力", "题量 5/10/20/30 任选，可按章节、难度过滤，可限时 10/20/30 分钟"],
        ["交付形态", "目录版 21 MB + 便携 zip 8.9 MB，双击即用，不依赖 %TEMP%"],
        ["配套文档", "需求说明书、设计文档、测试报告、答辩 PPT、本汇报"],
    ], widths=[4.0, 12.0])
    picture(doc, "01_home.png", 15.0, "图 1-1 主界面：章节进度与统计一目了然")

    # ---------------------------------------------------------------- 2
    h1(doc, "2 建设内容")

    h2(doc, "2.1 题库：教材三章 + 拓展 + 算法")
    rows = []
    for c in CHAPTERS:
        rows.append([c["name"], len(c["questions"]),
                     sum(len(q["cases"]) for q in c["questions"])])
    rows.append(["合计", TOTAL_Q, TOTAL_CASES])
    table(doc, ["章节", "题数", "用例数"], rows, widths=[8.0, 3.0, 3.0])
    para(doc, "教材三章（69 题）按原文整理题干，参考答案参考教材「实验解析」并做了纠错；"
              "拓展练习（40 题）取自公开题集 Python100Cases 等，题干重写、答案与用例自行编写；"
              "进阶算法（30 题）覆盖排序、查找、递归、栈、贪心与简单动态规划。"
              "每道题都有方法提示、参考答案、易错点解析与 1～5 个测试用例。")

    h2(doc, "2.2 判题引擎：判得准、不卡死")
    for t in [
        "受限执行：重定向 stdout/stdin，替换 input() 使其不回显提示语；",
        "超时看门狗：sys.settrace 计时，超时抛 BaseException 子类，学习者的 except 吞不掉；",
        "归一化比对：忽略行尾空格、连续空白与空行；图形题用 raw 模式保留行首空格精确比对；",
        "分类提示：EOFError、NameError、SyntaxError、Timeout 等情况分别给出针对性说明；",
        "安全拦截：os.system、subprocess、ctypes 等调用直接拒绝执行。",
    ]:
        bullet(doc, t)
    picture(doc, "02_practice_fail.png", 15.0, "图 2-1 判题失败：给出期望输出、实际输出与首个不一致的行")

    h2(doc, "2.3 学习闭环：错题本 / 收藏 / 统计 / 进度")
    para(doc, "最近一次未通过的题自动进入错题本，通过后自动移除；收藏夹用于单独攒复习清单；"
              "统计页展示已通过数、通过率、每题的尝试次数、状态与最近练习时间；"
              "所有进度（含每题代码）保存在 %LOCALAPPDATA%\\PyQuizState\\state.json，关掉再开接着刷。")
    picture(doc, "07_stats.png", 15.0, "图 2-2 学习统计：按章节、难度、状态逐题追踪")

    h2(doc, "2.4 模拟组卷（本期新增）")
    para(doc, "在「模拟组卷」页选择题量、章节范围、难度与限时，点击「随机组卷并开始」即生成一套卷子。"
              "组卷按章节轮转抽题，保证各章覆盖均衡；随机种子可复现，便于复查。")
    picture(doc, "09_exam_setup.png", 15.0, "图 2-3 组卷配置：题量 / 章节 / 难度 / 限时")
    para(doc, "考试模式下顶部出现倒计时条与「已通过 x/n」进度，交卷按钮常驻；"
              "章节切换被禁用、参考答案按钮变为「考试中不可看答案」，避免考试时直接看答案。")
    picture(doc, "10_exam_running.png", 15.0, "图 2-4 考试中：倒计时、实时进度、答案入口被禁用")
    para(doc, "交卷（手动或倒计时归零自动）后生成成绩报告：得分、评价（优秀/良好/及格/需加强）、"
              "用时、逐题明细（通过/未通过/未作答、尝试次数）与本次卷子的章节分布；成绩写入历史记录。")
    picture(doc, "11_exam_result.png", 15.0, "图 2-5 交卷报告：得分、逐题明细与章节分布")

    h2(doc, "2.5 交付形态")
    table(doc, ["交付物", "说明"], [
        ["dist\\Python刷题系统\\", "目录版主程序，双击 exe 运行，约 21 MB"],
        ["dist\\Python刷题系统-便携版.zip", "压缩包 8.9 MB，解压即用，适合拷给同学"],
        ["docs\\*.docx / .pptx", "需求、设计、测试、汇报与答辩材料"],
        ["源码 + pylibs", "含组卷与判题源码、打包用 PyInstaller 5.13.2"],
    ], widths=[6.0, 10.0])

    # ---------------------------------------------------------------- 3
    h1(doc, "3 技术实现要点")
    table(doc, ["层次", "模块", "职责"], [
        ["表现层", "ui.py / widgets.py / theme.py / ui_exam.py", "五个页面、自绘控件、配色与 DPI 缩放"],
        ["业务层", "judge.py / exam.py", "判题执行与比对；组卷、限时、评分"],
        ["数据层", "qbank.py / bank_ch3,4,5 / bank_extra / bank_algo", "{} 道题的题干、答案、用例、解析".format(TOTAL_Q)],
        ["存储层", "store.py", "进度、错题、收藏、考试历史（JSON 原子写入）"],
        ["构建层", "build.py / selftest.py / _test_exam.py / main.py", "自检、图标、打包、入口"],
    ], widths=[2.2, 7.2, 6.6])

    para(doc, "三个值得一提的设计：")
    for t in [
        "判题放在后台线程，界面不阻塞；超时用追踪器而不是子进程——打包成 exe 后 sys.executable 指向自身，"
        "起子进程会变成再启动一个刷题程序。",
        "组卷做成纯逻辑模块（exam.py），不依赖界面，可以用固定随机种子做单元测试；"
        "题量不足时抛异常，界面提示而不是出半套卷子。",
        "打包用 --onedir 而不是 --onefile：单文件模式启动要解压到 %TEMP%，个别机器上会失败；"
        "目录版启动不解压，实测把 TEMP 指向不存在的路径也能正常运行。",
    ]:
        bullet(doc, t)

    # ---------------------------------------------------------------- 4
    h1(doc, "4 质量保障")
    table(doc, ["测试类型", "覆盖内容", "规模", "结果"], [
        ["题库自检", "参考答案跑自己的用例", "{} 题 / {} 用例".format(TOTAL_Q, TOTAL_CASES), "全部通过"],
        ["组卷自检", "随机性、覆盖、过滤、异常、评分、限时", "10 项", "全部通过"],
        ["交互测试", "判题、错题本、收藏、统计、切题、组卷、重置", "13 项", "全部通过"],
        ["边界测试", "死循环、输入不足、语法错误、空输出、危险调用", "10 项", "全部通过"],
        ["打包验证", "启动、图标、进度写入、高分屏、TEMP 无关性", "7 项", "全部通过"],
    ], widths=[2.6, 7.4, 3.4, 2.6])

    para(doc, "过程中修复的典型缺陷：单文件 exe 解压失败（改目录版）、"
              "150% 缩放下界面被裁（按 DPI 缩放）、完数题判题超时（改 √n 枚举）、"
              "提示控件属性名覆盖同名方法（重命名）、背包题输入约定导致 EOF（改为先读件数）。")

    # ---------------------------------------------------------------- 5
    h1(doc, "5 使用方式")
    for t in [
        "解压便携版 zip（或直接打开目录版文件夹），双击 Python刷题系统.exe；",
        "若出现「Windows 已保护你的电脑」，点「更多信息 → 仍要运行」（未签名程序的系统提示，只需一次）；",
        "主页点章节开始刷题，或进「模拟组卷」出一套卷子自测；F5 运行、Alt+←/→ 切题；",
        "进度自动保存，换电脑时复制 %LOCALAPPDATA%\\PyQuizState\\state.json 即可迁移。",
    ]:
        bullet(doc, t)

    # ---------------------------------------------------------------- 6
    h1(doc, "6 不足与展望")
    table(doc, ["方向", "说明"], [
        ["函数 / 文件题", "当前只支持「读入—处理—输出」型程序，函数题需要调用学生函数，文件题需要虚拟文件系统"],
        ["组卷策略", "目前按章节轮转 + 难度过滤，可增加按考点、按错题加权（哪里弱考哪里）"],
        ["成绩分析", "历史成绩只存汇总，可增加趋势曲线与章节正确率对比"],
        ["多人使用", "目前是单机版，若机房统一使用可考虑导出成绩或改成 Web 版"],
    ], widths=[4.0, 12.0])

    # ---------------------------------------------------------------- 7
    h1(doc, "7 交付清单")
    table(doc, ["文件", "用途"], [
        ["dist\\Python刷题系统\\Python刷题系统.exe", "主程序（免安装目录版）"],
        ["dist\\Python刷题系统-便携版.zip", "便携压缩包"],
        ["docs\\1-需求说明书.docx", "功能/非功能需求、数据设计、验收标准、追踪矩阵"],
        ["docs\\2-设计文档.docx", "架构、模块设计、组卷引擎、数据结构、部署"],
        ["docs\\3-测试报告.docx", "题库自检、组卷自检、交互、边界、打包验证与缺陷记录"],
        ["docs\\4-答辩演示.pptx", "答辩演示稿"],
        ["docs\\5-项目汇报.docx", "本文件"],
        ["README.md", "使用说明与二次开发指引"],
    ], widths=[7.2, 8.8])

    out = os.path.join(HERE, "5-项目汇报.docx")
    BD.apply_toc(doc, marker)
    doc.save(out)
    BD.dump_toc("report")
    return out


def _args():
    """解析 --pages / --toc-dir。"""
    import sys
    args = sys.argv[1:]
    for i, a in enumerate(args):
        val = None
        if a == "--pages" and i + 1 < len(args):
            val = args[i + 1]
        elif a.startswith("--pages="):
            val = a.split("=", 1)[1]
        if val:
            BD.PAGES_DIR = val
        val = None
        if a == "--toc-dir" and i + 1 < len(args):
            val = args[i + 1]
        elif a.startswith("--toc-dir="):
            val = a.split("=", 1)[1]
        if val:
            BD.TOC_DIR = val


if __name__ == "__main__":
    _args()
    p = build()
    print("生成:", p, "%.1f KB" % (os.path.getsize(p) / 1024.0))
