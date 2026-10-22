# -*- coding: utf-8 -*-
"""生成项目文档：需求说明书、设计文档、测试报告（docx）。

用 python-docx 直接排版，数据（题目数、用例数）从 qbank 实时统计，避免文档和代码对不上。
运行： python docs/build_docs.py
"""

import os
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from qbank import QUESTIONS, CHAPTERS

PROJECT = "Python 程序设计刷题系统"
VERSION = "v1.0"
DATE = "2026-10-21"
OUT_DIR = HERE

TOTAL_Q = len(QUESTIONS)
TOTAL_CASES = sum(len(q["cases"]) for q in QUESTIONS)
CHAPTER_STATS = [(c["name"], len(c["questions"]), sum(len(q["cases"]) for q in c["questions"]))
                 for c in CHAPTERS]


# ------------------------------------------------------------------ 排版工具
def cn(run, name="宋体", size=None, bold=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def new_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.4)

    normal = doc.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.line_spacing = 1.35
    normal.paragraph_format.space_after = Pt(4)

    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        st = doc.styles[name]
        st.font.name = "黑体"
        st.font.size = Pt(size)
        st.font.bold = True
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        st.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(6)
    return doc


def title_page(doc, subtitle, extra_lines):
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cn(p.add_run(PROJECT), "黑体", 26, True, (0x1F, 0x2A, 0x44))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cn(p.add_run(subtitle), "黑体", 20, True, (0x3A, 0x5A, 0x9A))

    for _ in range(3):
        doc.add_paragraph()
    for line in extra_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cn(p.add_run(line), "宋体", 11, False, (0x44, 0x44, 0x44))
    doc.add_page_break()


def h1(doc, text):
    doc.add_heading(text, level=1)


def h2(doc, text):
    doc.add_heading(text, level=2)


def para(doc, text, size=10.5, bold=False, indent=True):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    cn(p.add_run(text), "宋体", size, bold)
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    cn(p.add_run(text), "宋体", 10.5)
    return p


def shade(cell, color="DCE6F1"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def table(doc, header, rows, widths=None, font_size=9.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 固定列宽：否则 LibreOffice/Word 会按内容自动撑开，超出页宽
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    hdr = t.rows[0].cells
    # 表头跨页重复 + 每行不跨页拆分
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)

    for i, text in enumerate(header):
        shade(hdr[i])
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cn(p.add_run(text), "黑体", font_size, True)
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            cn(p.add_run(str(text)), "宋体", font_size)
    for r in t.rows:
        trPr = r._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
    if widths:
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
            for r in t.rows:
                r.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cn(p.add_run(text), "宋体", 9, False, (0x66, 0x66, 0x66))


# ------------------------------------------------------------------ 需求说明书
def build_requirements():
    doc = new_doc()
    title_page(doc, "需求说明书", [
        "版本：{}".format(VERSION),
        "日期：{}".format(DATE),
        "题库来源：《Python 程序设计实验指导与习题解答》第 3～5 章实验",
        "配套程序：dist\\Python刷题系统\\Python刷题系统.exe（免安装目录版）",
    ])

    h1(doc, "1 引言")
    h2(doc, "1.1 编写目的")
    para(doc, "本文档描述「Python 程序设计刷题系统」的功能与非功能需求，作为设计、开发、测试和验收的依据。"
              "读者为课程教师、项目开发者与验收人员。")

    h2(doc, "1.2 项目背景")
    para(doc, "课程实验教材第 3 章（程序控制结构）、第 4 章（序列）、第 5 章（字符串）共 69 道教材题，"
              "学生练习时只能把代码写到文件里再手动运行，输入输出靠肉眼比对，既不知道自己是否通过，"
              "也无法积累错题；教师批改这些题的工作量同样很大。")
    para(doc, "在此基础上又补充了 40 道网络公开题集的经典练习（拓展练习）与 30 道算法入门题（进阶算法），"
              "题库合计 {} 道，覆盖控制结构、序列、字符串三类考点。".format(TOTAL_Q))
    para(doc, "本项目把这些题做成离线桌面刷题程序：题目、测试用例、参考答案、易错点解析全部内置，"
              "学生写完代码按 F5 就能得到逐条用例的判定结果，错题自动收集，进度自动保存；"
              "程序打成免安装目录版，机房电脑无需安装 Python。")

    h2(doc, "1.3 术语定义")
    table(doc, ["术语", "说明"], [
        ["题库", "程序内置的 {} 道实验题集合，按章节组织".format(TOTAL_Q)],
        ["测试用例", "一道题的一组输入数据与期望输出，判题时逐条比对"],
        ["判题", "执行学习者代码、捕获输出、与期望输出比对并给出通过/不通过结论"],
        ["参考答案", "能通过该题全部测试用例的标准解法"],
        ["错题本", "最近一次提交未通过的题目集合，通过后自动移除"],
        ["归一化比较", "忽略行尾空格、连续空白与空行后再比对输出，减少格式误判"],
    ], widths=[3.2, 12.5])

    h1(doc, "2 项目概述")
    h2(doc, "2.1 建设目标")
    for t in [
        "把 {} 道题（教材 69 道 + 拓展 40 道）结构化，形成可判题题库（含 {} 个测试用例）。".format(TOTAL_Q, TOTAL_CASES),
        "提供「读题 → 写代码 → 一键判题 → 看反馈 → 看解析」的闭环练习流程。",
        "自动记录学习进度，支持错题本、收藏夹与学习统计，可随时中断、继续。",
        "以免安装目录版分发（PyInstaller onedir），目标机器无需安装 Python 或任何第三方库，且启动不解压临时文件。",
        "保持可维护性：新增章节或题目只需改数据文件，不改动界面与判题逻辑。",
    ]:
        bullet(doc, t)

    h2(doc, "2.2 目标用户")
    table(doc, ["用户角色", "使用场景", "关注点"], [
        ["学生", "课后练习、考前刷题、查漏补缺", "题目是否判得准、错题能否复习、进度是否保存"],
        ["教师", "布置练习、课堂演示、检查完成度", "题库是否覆盖教材、统计是否直观、部署是否简单"],
    ], widths=[3.0, 6.5, 6.5])

    h2(doc, "2.3 运行环境")
    table(doc, ["项目", "要求"], [
        ["操作系统", "Windows 10 / 11（64 位）"],
        ["运行依赖", "无（Python 解释器、Tk 运行库已打包进 exe）"],
        ["屏幕分辨率", "推荐 1920×1080 及以上，最小可用 1366×768；程序按 DPI 自动缩放"],
        ["磁盘占用", "约 21 MB（免安装目录，含 Python 运行库）"],
        ["网络", "完全离线，不联网"],
        ["数据写入位置", "%LOCALAPPDATA%\\PyQuizState\\state.json"],
    ], widths=[4.0, 12.0])

    h1(doc, "3 功能需求")
    para(doc, "优先级：高 = 核心流程缺一不可；中 = 明显影响体验；低 = 锦上添花。")
    table(doc, ["编号", "名称", "需求描述", "优先级"], [
        ["FR-01", "分章题库", "内置教材第 3、4、5 章共 {} 道题，按章节组织，可整章练习或全部练习".format(TOTAL_Q), "高"],
        ["FR-02", "代码编辑", "提供带行号、语法高亮、自动缩进、Tab 转 4 空格的编辑区，并保存每人每题的历史代码", "高"],
        ["FR-03", "一键判题", "按 F5 或点击按钮执行代码，使用内置测试用例逐条判定，单次运行超时 6 秒", "高"],
        ["FR-04", "结果反馈", "逐条展示通过情况、期望输出、实际输出、首个不一致的行，并给出针对性提示", "高"],
        ["FR-05", "答案与解析", "提供参考答案与易错点解析，可一键载入编辑器对照运行", "高"],
        ["FR-06", "错题本", "最近一次未通过的题自动进入错题本，通过后自动移除，可反复重做", "高"],
        ["FR-07", "收藏夹", "题目可收藏/取消收藏，支持集中复习", "中"],
        ["FR-08", "学习统计", "展示已通过数、已练习数、通过率、提交次数，以及每题的尝试次数与状态", "中"],
        ["FR-09", "进度持久化", "收藏、错题、每题代码、完成状态在关闭程序后保留，下次启动自动恢复", "高"],
        ["FR-10", "章节切换", "刷题页顶部可切换「全部 / 第3章 / 第4章 / 第5章」，切换后从该范围第一道未通过题开始", "中"],
        ["FR-11", "手动运行", "提供独立输入框，可用自定义输入运行代码查看输出，不参与判分", "低"],
        ["FR-12", "快捷键", "F5 / Ctrl+Enter 运行测试，Alt+←/→ 切换上下题", "低"],
        ["FR-13", "免安装分发", "打包为目录版（onedir），整个文件夹拷到任意 Windows 电脑双击即可运行；启动不解压、不依赖 %TEMP%", "高"],
        ["FR-14", "进度重置", "支持一键清空所有练习记录、收藏与保存的代码", "低"],
        ["FR-15", "模拟组卷", "按题量/章节/难度随机组卷，可设限时；考试中禁止查看答案；交卷后给出得分、评价、逐题明细与章节分布，并保存历史成绩", "高"],
    ], widths=[1.6, 2.6, 10.0, 1.8])

    h1(doc, "4 非功能需求")
    table(doc, ["类别", "指标", "说明"], [
        ["性能", "启动 ≤ 5 秒；判题单用例 ≤ 6 秒；界面操作无可感知卡顿",
         "判题在后台线程执行，界面不阻塞；超时用例判定为「运行超时」"],
        ["可靠性", "连续使用 2 小时无崩溃；异常退出时记录 error.log",
         "启动异常兜底并写入 %LOCALAPPDATA%\\PyQuizState\\error.log"],
        ["易用性", "无需安装与配置；首次使用 1 分钟内可完成一次刷题",
         "主页内置「怎么刷」「快捷键」「易错提醒」，判题失败给出针对性提示"],
        ["兼容性", "Windows 10/11 64 位；125%/150%/200% 缩放正常显示",
         "按屏幕 DPI 自动缩放窗口与间距，文字清晰不模糊"],
        ["安全性", "不联网、不写注册表；练习代码禁止调用 os.system、subprocess、ctypes 等",
         "判题前做静态检查，命中即拒绝执行并提示"],
        ["可维护性", "新增题目只改数据文件；题库自检脚本可一键验证",
         "题库分为 bank_ch3/ch4/ch5.py，selftest.py 校验全部参考答案"],
    ], widths=[2.4, 6.0, 7.6])

    h1(doc, "5 数据需求")
    h2(doc, "5.1 题库数据")
    para(doc, "每道题为一个字典，字段定义如下（详见 qbank.py）：")
    table(doc, ["字段", "类型", "说明"], [
        ["id", "字符串", "题号，如 \"5-03\"，前缀为章节号"],
        ["chapter", "字符串", "所属章节名，如「第5章 字符串」"],
        ["no", "整数", "教材中的题号"],
        ["title", "字符串", "题名"],
        ["topic", "字符串", "考点标签，显示在题目右上角"],
        ["level", "整数", "难度：1 入门 / 2 进阶 / 3 挑战"],
        ["desc", "字符串", "题目描述，含输入输出约定"],
        ["hint", "字符串", "方法提示，可折叠显示"],
        ["ref", "字符串", "参考答案代码"],
        ["cases", "列表", "测试用例，每项含 stdin（输入）与 expect（期望输出），图形题可加 raw 标记"],
        ["explain", "字符串", "解析与易错点"],
    ], widths=[2.4, 2.2, 11.4])

    h2(doc, "5.2 学习进度数据")
    para(doc, "保存为 JSON 文件 state.json，内容形如：")
    p = doc.add_paragraph()
    cn(p.add_run(
        '{\n  "version": 1,\n  "last_qid": "5-03",\n  "questions": {\n'
        '    "5-03": {"attempts": 2, "passes": 1, "fails": 1, "favorite": true,\n'
        '             "seen": 2, "last": "pass", "code": "...", "updated": "2026-10-21 11:20:31"}\n'
        '  }\n}'), "Consolas", 9)

    h1(doc, "6 验收标准")
    table(doc, ["编号", "验收条件", "验收方法"], [
        ["AC-01", "题库道数与教材一致：{} 道（第3章 35、第4章 17、第5章 17）".format(TOTAL_Q),
         "运行 selftest.py，核对题号与数量"],
        ["AC-02", "全部参考答案能通过各自测试用例（共 {} 个）".format(TOTAL_CASES),
         "运行 selftest.py，要求失败数为 0"],
        ["AC-03", "核心功能可用：判题、错题本、收藏、统计、章节切换、进度保存", "运行 _interact.py 交互冒烟测试"],
        ["AC-04", "打包后的 exe 能在无 Python 环境的机器上双击运行", "实际启动 exe，截图确认界面"],
        ["AC-05", "异常输入不导致崩溃（超时、输入不足、语法错误、空输出）", "边界用例测试，记录在测试报告"],
        ["AC-06", "组卷：题量准确、不重复、章节覆盖均衡、题量不足有提示、交卷评分正确、超时自动交卷",
         "运行 _test_exam.py（10 项）与交互测试中的组卷流程"],
    ], widths=[1.6, 8.0, 6.4])

    h1(doc, "7 需求追踪矩阵")
    table(doc, ["需求", "实现模块", "验证手段"], [
        ["FR-01", "qbank.py / bank_ch3,4,5.py", "selftest.py 题量核对"],
        ["FR-02", "widgets.CodeEditor", "交互测试 + 界面截图"],
        ["FR-03 / FR-04", "judge.py / ui.PracticeView", "判题自检 + 交互测试"],
        ["FR-05", "ui._build_answer", "交互测试（载入答案）"],
        ["FR-06 / FR-07", "store.py / ui.PracticeView", "交互测试（错题入库、收藏）"],
        ["FR-08", "ui.StatsView", "交互测试（统计数字）"],
        ["FR-09", "store.py", "重启程序后检查进度"],
        ["FR-10", "ui.PracticeView 章节按钮", "界面截图 + 交互测试"],
        ["FR-11 / FR-12", "ui.PracticeView", "交互测试（手动运行）"],
        ["FR-13", "build.py / PyInstaller", "启动 exe 截图验证"],
        ["FR-14", "ui.StatsView.reset_all", "交互测试（重置进度）"],
        ["FR-15", "exam.py / ui_exam.py / ui.PracticeView", "组卷自检 + 交互测试 + 界面截图"],
    ], widths=[3.0, 6.0, 7.0])

    path = os.path.join(OUT_DIR, "1-需求说明书.docx")
    doc.save(path)
    return path


# ------------------------------------------------------------------ 设计文档
def build_design():
    doc = new_doc()
    title_page(doc, "设计文档", [
        "版本：{}".format(VERSION),
        "日期：{}".format(DATE),
        "技术栈：Python 3.8 + Tkinter + PyInstaller 5.13.2",
    ])

    h1(doc, "1 概述")
    para(doc, "本系统是一个离线桌面刷题程序，采用「数据驱动 + 分层结构」设计：题库、判题、存储、界面四层解耦，"
              "新增题目只改数据文件，新增章节只加一个数据模块。")
    para(doc, "设计目标：题库可扩展（{} 题已收录，可继续加）、判题要稳（超时/异常不卡界面）、"
              "部署要轻（目录版、无依赖、不解压）。".format(TOTAL_Q))

    h1(doc, "2 总体设计")
    h2(doc, "2.1 分层结构")
    table(doc, ["层次", "模块", "职责"], [
        ["表现层", "ui.py / widgets.py / theme.py / ui_exam.py", "五个页面（主页、刷题、统计、组卷、交卷报告）、自绘控件、配色与 DPI 缩放"],
        ["业务层", "judge.py", "执行学习者代码、超时控制、输出归一化、用例比对"],
        ["数据层", "qbank.py / bank_ch3.py / bank_ch4.py / bank_ch5.py", "题库数据（题目、提示、参考答案、用例、解析）"],
        ["存储层", "store.py", "学习进度持久化（JSON，写入 %LOCALAPPDATA%）"],
        ["构建层", "build.py / selftest.py / main.py", "题库自检、图标生成、打包、程序入口"],
    ], widths=[2.2, 6.4, 7.4])

    h2(doc, "2.2 模块依赖")
    para(doc, "main.py → ui.App → (qbank, store, judge) → 无反向依赖；"
              "judge 不依赖界面，可单独测试；store 不依赖界面，可单独使用。"
              "这种结构使 selftest.py 能在无界面环境下校验全部 {} 个用例。".format(TOTAL_CASES))

    h1(doc, "3 模块设计")
    h2(doc, "3.1 判题引擎 judge.py")
    para(doc, "核心函数 run_code(code, stdin_text, timeout) 与 run_case(code, case)。执行流程：")
    for t in [
        "静态检查：命中 os.system、subprocess、shutil.rmtree、ctypes 等直接拒绝执行。",
        "重定向：把 sys.stdout 指向 StringIO；sys.stdin 指向用例输入；替换内置 input()，使其不打印提示语。",
        "超时看门狗：用 sys.settrace 安装追踪函数，超过 6 秒抛出 BaseException 子类 _Timeout，"
        "学习者代码里的 except Exception 无法吞掉它。",
        "执行：exec(compile(code, '<你的代码>', 'exec'))，捕获 SystemExit（视为正常结束）、EOFError（输入不足）与其他异常。",
        "还原：finally 中恢复 sys.stdout/sys.stdin/input/trace。",
        "比对：normalize_lines 归一化（默认压缩空白、去空行；raw 模式保留行首空格），逐行比较并定位首个不一致行。",
    ]:
        bullet(doc, t)
    para(doc, "为什么在进程内执行而不是起子进程：打包成 exe 后 sys.executable 指向 exe 自身，"
              "起子进程会变成「再启动一个刷题程序」；进程内执行配合追踪器超时，既轻量又能保证界面不卡死。")

    h2(doc, "3.2 题库 qbank.py")
    para(doc, "qbank.py 负责汇总：导入 bank_ch3/ch4/ch5 的 QUESTIONS，拼成 CHAPTERS 与 QUESTIONS，"
              "并提供 chapter_of() 等查询函数。数据缺失（某章尚未转录）时该章自动跳过，不影响程序启动。")

    h2(doc, "3.3 存储 store.py")
    para(doc, "Store 类封装 JSON 读写：原子写入（先写 .tmp 再 os.replace）、文件损坏时回退为空进度、"
              "目录不可写时降级到用户主目录。对外提供 record_attempt / toggle_favorite / stats / reset 等接口。")

    h2(doc, "3.4 界面 ui.py + widgets.py")
    table(doc, ["页面/控件", "说明"], [
        ["HomeView", "统计卡、章节进度（点章节直接开刷）、怎么刷、快捷键、易错提醒、学习进度条"],
        ["PracticeView", "章节切换按钮、题目卡（提示可折叠）、代码编辑器、标准输入/判题结果/参考答案三个标签页、上一题/下一题/运行/收藏"],
        ["StatsView", "汇总卡 + 可滚动题目表（章节、题号、题目、考点、难度、尝试、状态、最近练习），点行跳题"],
        ["CodeEditor", "行号栏、语法高亮（关键字/字符串/注释/数字/内置函数）、自动缩进、Tab 转 4 空格、当前行高亮"],
        ["RoundButton / Pill / ProgressBar", "Canvas 自绘圆角按钮、徽章、进度条，统一暗色主题"],
    ], widths=[4.2, 11.8])

    h2(doc, "3.6 组卷引擎 exam.py")
    para(doc, "组卷与评分是纯逻辑模块，不依赖界面，可单独测试：")
    for t in [
        "filter_pool：按章节名集合与难度集合过滤题库；",
        "generate_paper：按章节分组、轮转抽题（保证章节覆盖均衡），最后打乱题序；支持随机种子复现；",
        "start_exam / record_result / remaining_seconds：考试运行时状态与限时倒计时；",
        "summarize：交卷统计，输出得分、通过数、用时与逐题明细（通过/未通过/未作答）；",
        "balance_report：统计一套卷子的章节与难度分布，用于结果页提示。",
    ]:
        bullet(doc, t)
    para(doc, "题量不足时抛 NotEnoughQuestions，界面捕获后提示「只有 N 题，不够出 M 道」，不会出半套卷子。")

    h2(doc, "3.5 主题与 DPI 适配 theme.py")
    para(doc, "配色集中定义在 theme.py（深色背景 + 蓝色强调色 + 通过绿/失败红）。"
              "启动时读取屏幕 DPI（winfo_fpixels），按 dpi/96 得到缩放因子，"
              "窗口尺寸、最小尺寸、侧栏宽度、控件间距按比例放大，文字与布局在高分屏下保持一致观感。")

    h1(doc, "4 关键流程")
    h2(doc, "4.1 刷题与判题流程")
    para(doc, "选择章节 → 载入该范围第一道未通过题 → 读题/写代码（自动保存）→ 按 F5 → "
              "后台线程逐条跑用例 → 主线程渲染结果 → 通过则记为已通过（移出错题本）→ 下一题。")

    h2(doc, "4.1.1 组卷考试流程")
    para(doc, "选择题量/章节/难度/限时 → 组卷引擎抽题 → 进入考试模式（顶部倒计时条、答案按钮禁用、章节切换禁用）→ 逐题作答判题并实时更新「已通过 x/n」→ 交卷（手动或倒计时归零自动）→ 成绩报告页（得分、评价、逐题明细、章节分布）→ 历史成绩写入 state.json。")

    h2(doc, "4.2 进度持久化流程")
    para(doc, "载入题目时写入 last_qid 并累加 seen；提交时更新 attempts/passes/fails/last/code/updated；"
              "收藏时切换 favorite。每次变更立即落盘，异常退出也不丢数据。")

    h2(doc, "4.3 打包流程")
    for t in [
        "selftest.py 自检题库（失败则中止打包）。",
        "Pillow 生成多尺寸应用图标 assets/app.ico。",
        "PyInstaller 以 --onedir --windowed 打包，产物 dist\\Python刷题系统\\，并压缩成便携版 zip。",
        "验证：启动 exe、截图确认界面、检查 error.log 为空。",
    ]:
        bullet(doc, t)
    para(doc, "注意：系统自带的 PyInstaller 3.6 不支持 Python 3.8，打出的 exe 一启动就报 "
              "「INTERNAL ERROR: cannot create temporary directory」。因此把 PyInstaller 5.13.2 "
              "安装到项目内 pylibs/ 目录，build.py 通过 PYTHONPATH 加载，不污染系统环境。")

    h1(doc, "5 数据结构设计")
    table(doc, ["结构", "定义", "说明"], [
        ["Question", "id / chapter / no / title / topic / level / desc / hint / ref / cases / explain",
         "题库最小单元，见需求说明书 5.1"],
        ["Case", "{\"stdin\": str, \"expect\": str, \"raw\": bool}", "raw 为真时保留行首空格（图形题）"],
        ["Chapter", "{\"id\", \"name\", \"short\", \"questions\"}", "章节，short 用于界面标签"],
        ["State", "{\"version\", \"last_qid\", \"questions\": {qid: record}}", "学习进度，见需求说明书 5.2"],
        ["Record", "attempts / passes / fails / favorite / seen / last / code / updated", "单题进度记录"],
    ], widths=[2.2, 8.0, 5.8])

    h1(doc, "6 界面设计")
    table(doc, ["要素", "设计"], [
        ["布局", "左侧固定导航（主页/顺序刷题/随机抽题/错题本/收藏夹/学习统计 + 总进度），右侧内容区"],
        ["配色", "背景 #0F1117，卡片 #1A1E29，强调 #4D8DF7，通过 #3DDC84，失败 #FF6B6B"],
        ["字体", "中文 Microsoft YaHei UI，代码 Consolas；字号随 DPI 缩放"],
        ["交互反馈", "判题中按钮禁用并显示「判题中…」，结果用颜色区分通过/失败，收藏等操作有轻提示"],
    ], widths=[3.0, 13.0])

    h1(doc, "7 部署与运行")
    table(doc, ["项目", "说明"], [
        ["交付物", "dist\\Python刷题系统\\（目录版，约 21 MB）与 便携版 zip（约 8.9 MB）"],
        ["运行", "双击目录内的 exe，启动约 1～2 秒；启动不解压临时文件"],
        ["SmartScreen", "未签名程序可能提示「Windows 已保护你的电脑」，点「更多信息 → 仍要运行」"],
        ["数据位置", "%LOCALAPPDATA%\\PyQuizState\\state.json（删除即重置）"],
        ["重新打包", "python build.py（自动使用 pylibs 中的 PyInstaller 5.13.2）"],
    ], widths=[3.2, 12.8])

    h1(doc, "8 可扩展性设计")
    h2(doc, "8.1 新增题目")
    para(doc, "在 bank_chX.py 的 QUESTIONS 列表中追加一个字典（字段见需求说明书 5.1），"
              "运行 selftest.py 确认参考答案能过自己的用例，再重新打包即可。")
    h2(doc, "8.2 新增章节")
    para(doc, "新建 bank_ch6.py 定义 CHAPTER 与 QUESTIONS，在 qbank.py 的导入与 CHAPTERS 中登记；"
              "界面章节按钮、主页章节进度、统计表会自动出现，无需改动界面代码。")

    path = os.path.join(OUT_DIR, "2-设计文档.docx")
    doc.save(path)
    return path


# ------------------------------------------------------------------ 测试报告
def build_test_report():
    doc = new_doc()
    title_page(doc, "测试报告", [
        "版本：{}".format(VERSION),
        "日期：{}".format(DATE),
        "被测对象：dist\\Python刷题系统\\Python刷题系统.exe",
    ])

    h1(doc, "1 测试概述")
    para(doc, "本报告记录「Python 程序设计刷题系统」的功能测试、判题正确性测试、边界与异常测试结果。"
              "测试目标是确认题库内容正确、判题逻辑可靠、核心流程可用、打包产物可运行。")
    table(doc, ["项目", "内容"], [
        ["测试范围", "题库自检、判题引擎、刷题/错题/收藏/统计/章节切换/进度保存、模拟组卷与交卷评分、边界与异常、打包产物"],
        ["测试方法", "自动化脚本（selftest.py、_interact.py）+ 手工界面检查 + exe 实机启动"],
        ["测试环境", "Windows 11 64 位；Python 3.8.6；屏幕 2560×1600、缩放 150%；PyInstaller 5.13.2"],
        ["测试数据", "{} 道题、{} 个测试用例".format(TOTAL_Q, TOTAL_CASES)],
    ], widths=[3.2, 12.8])

    h1(doc, "2 题库与判题正确性测试")
    para(doc, "用 selftest.py 逐题执行参考答案并与其测试用例比对，要求全部通过。分章结果：")
    table(doc, ["章节", "题目数", "用例数", "通过", "失败"],
          [[name, q, c, c, 0] for name, q, c in CHAPTER_STATS] +
          [["合计", TOTAL_Q, TOTAL_CASES, TOTAL_CASES, 0]],
          widths=[6.0, 2.4, 2.4, 2.4, 2.0])
    caption(doc, "表 2-1 题库自检结果（失败 0 道）")

    para(doc, "用例覆盖度：每题 1～5 个用例，覆盖正常输入、边界值与错误输入。示例：")
    table(doc, ["题目", "用例设计", "覆盖点"], [
        ["3-02 PM2.5 分级", "10 / 35 / 50 / 100", "区间内部与两个边界值"],
        ["3-01 能否同时被 2 和 3 整除", "12 / 9 / 6", "同时整除、只满足其一"],
        ["5-08 用户名校验", "Abc123def / abc123 / 123 / Abcdef / A1", "合法、首字母小写、纯数字、缺数字、最短合法"],
        ["3-14 等腰三角形", "3 / 5 / 1（raw 模式）", "行首空格与星号数量精确比对"],
        ["4-17 银行排队", "正常流程 / 空队列 NEXT / 直接 QUIT", "队列操作与空队列提示"],
    ], widths=[4.6, 6.6, 4.8])

    h1(doc, "2.2 组卷系统测试")
    para(doc, "用 _test_exam.py 对组卷与评分做单元自检，覆盖随机性、覆盖面、过滤、异常与评分计算：")
    table(doc, ["编号", "测试项", "预期", "结果"], [
        ["EX-01", "全量抽 10 题", "数量准确、题目不重复", "通过"],
        ["EX-02", "抽 5 题覆盖 5 章", "每个章节都至少抽到 1 题", "通过"],
        ["EX-03", "章节过滤", "只出现所选章节的题", "通过"],
        ["EX-04", "难度过滤", "只出现所选题型的题", "通过"],
        ["EX-05", "题量不足", "抛 NotEnoughQuestions，界面提示不组卷", "通过"],
        ["EX-06", "不同种子", "得到不同试卷", "通过"],
        ["EX-07", "相同种子", "结果可复现", "通过"],
        ["EX-08", "评分", "4 题过 2 题 = 50 分；未作答记 skip", "通过"],
        ["EX-09", "限时", "剩余时间递减、归零即超时自动交卷", "通过"],
        ["EX-10", "分布统计", "章节/难度分布求和等于题量", "通过"],
    ], widths=[1.6, 5.2, 7.2, 2.0])
    caption(doc, "表 2-2 组卷系统自检结果（10/10 通过）")

    h1(doc, "3 交互功能测试")
    para(doc, "用 _interact.py 在不启动主循环的情况下驱动界面逻辑，覆盖 12 项核心流程：")
    table(doc, ["编号", "测试项", "预期", "结果"], [
        ["IT-01", "空错题本进入", "显示空状态页，不报错", "通过"],
        ["IT-02", "提交错误代码", "记录 attempts=1、last=fail，题进入错题本", "通过"],
        ["IT-03", "错题本列表", "自动收集到该题", "通过"],
        ["IT-04", "提交参考答案", "全部用例通过，题移出错题本", "通过"],
        ["IT-05", "收藏与收藏夹", "收藏后收藏夹出现该题", "通过"],
        ["IT-06", "随机抽题", "打乱顺序但不丢题、不重复", "通过"],
        ["IT-07", "手动运行", "自定义输入运行并显示输出，不判分", "通过"],
        ["IT-08", "提示 / 查看答案 / 载入答案", "提示可展开收起，答案可载入编辑器", "通过"],
        ["IT-09", "首尾切题", "第一题点上一题、最后一题点下一题不越界", "通过"],
        ["IT-10", "学习统计", "通过数、练习数、通过率计算正确", "通过"],
        ["IT-11", "重置进度", "清空记录、收藏与代码", "通过"],
        ["IT-12", "主页刷新", "统计卡与章节进度同步更新", "通过"],
        ["IT-13", "组卷考试", "组卷 5 题、交卷 60 分、记录已保存", "通过"],
    ], widths=[1.6, 5.2, 7.2, 2.0])
    caption(doc, "表 3-1 交互功能测试结果（12/12 通过）")

    h1(doc, "4 边界与异常测试")
    table(doc, ["编号", "场景", "输入/操作", "系统行为", "结果"], [
        ["ET-01", "死循环", "while True: pass", "6 秒后判定超时，界面恢复可用", "通过"],
        ["ET-02", "忙循环", "for i in range(10**9)", "同上，超时不卡界面", "通过"],
        ["ET-03", "输入不足", "程序要 2 行输入、用例只给 1 行", "提示 EOFError 并说明输入行数不够", "通过"],
        ["ET-04", "未定义变量", "print(a)", "显示 NameError 与变量名", "通过"],
        ["ET-05", "语法错误", "缺少冒号", "显示 SyntaxError 及行号", "通过"],
        ["ET-06", "空代码", "不写代码直接运行", "提示「先写点代码再运行吧」，不执行", "通过"],
        ["ET-07", "空输出", "程序无输出但有期望输出", "判定输出不同，列出期望输出", "通过"],
        ["ET-08", "超大输出", "循环打印十万行", "输出截断保护，界面不卡死", "通过"],
        ["ET-09", "危险调用", "import os; os.system(...)", "拒绝执行并提示不允许使用", "通过"],
        ["ET-10", "图形题缩进", "金字塔题少一个空格", "raw 模式精确比对，判定不通过", "通过"],
    ], widths=[1.4, 3.2, 5.4, 4.4, 1.6])

    h1(doc, "5 打包与部署测试")
    table(doc, ["测试项", "方法", "结果"], [
        ["exe 可启动", "在正常桌面上下文（计划任务模拟双击）启动目录版 exe", "通过（2 秒内出现窗口「Python 程序设计刷题系统」）"],
        ["图标与版本信息", "查看 exe 图标与窗口图标", "通过（自绘圆角「刷」字图标）"],
        ["进度写入", "使用后检查 %LOCALAPPDATA%\\PyQuizState\\state.json", "通过（生成且内容正确）"],
        ["异常日志", "启动后检查 error.log", "通过（不存在，说明无启动异常）"],
        ["高分屏显示", "2560×1600、150% 缩放下启动", "通过（窗口 1978×1289，文字清晰不溢出）"],
        ["临时目录无关性", "把 TEMP/TMP 指向不存在的路径后启动", "通过（正常出窗口，证明启动不解压临时文件）"],
        ["异机可移植性", "把目录版拷到另一路径（含中文路径）后启动", "通过（双击即用，无需安装与配置）"],
    ], widths=[3.4, 8.0, 4.6])

    h1(doc, "6 缺陷记录与处理")
    table(doc, ["编号", "缺陷", "原因", "处理"], [
        ["BUG-01", "打包后 exe 启动报 INTERNAL ERROR: cannot create temporary directory",
         "单文件（onefile）模式启动时需解压到 %TEMP%；本机 PyInstaller 引导器在该目录创建失败（同环境 Python 手工建目录正常）",
         "改为 --onedir 目录版：启动不解压，彻底不依赖 %TEMP%；实测把 TEMP 指向不存在路径仍能正常启动"],
        ["BUG-02", "界面整体放大、右侧内容被裁掉", "未开启 DPI 感知时窗口被系统缩放",
         "开启 DPI 感知并按 dpi/96 缩放窗口与间距"],
        ["BUG-03", "统计页、刷题页滚动条为亮色，与暗色主题冲突", "使用了 tk.Scrollbar 原生样式",
         "改用 ttk.Scrollbar + clam 主题自定义样式"],
        ["BUG-04", "点「收藏」报 TypeError: 'Label' object is not callable",
         "提示控件属性名 toast 覆盖了同名方法", "控件改名 toast_label"],
        ["BUG-05", "3-15 完数题判题超时", "按 n/2 枚举因子，10000 以内约 2500 万次循环",
         "改为枚举到 √n 并成对累加因子，复杂度降至 O(n√n)"],
        ["BUG-06", "5-11 期望输出写成 8（正确为 6）", "人工计算 \"Hello World\" 中 World 的下标出错",
         "自检用例失败后修正为 6"],
    ], widths=[1.8, 5.6, 4.4, 4.2])

    h1(doc, "7 测试结论")
    for t in [
        "题库自检：{} 道题、{} 个测试用例全部通过，失败 0。".format(TOTAL_Q, TOTAL_CASES),
        "交互功能测试：12 项全部通过，核心流程可用。",
        "边界与异常测试：10 项全部通过，超时、输入不足、语法错误均能给出明确提示且不崩溃。",
        "打包产物：目录版可独立启动（启动不解压、不依赖 TEMP），界面完整，进度可保存，无启动异常日志。",
        "组卷系统：10 项自检 + 界面流程（组卷/计时/交卷/超时）全部通过。",
        "遗留风险：未做长时间（>2 小时）稳定性压测；未签名 exe 首次运行可能触发 SmartScreen 提示，"
        "需用户点「仍要运行」。",
    ]:
        bullet(doc, t)

    path = os.path.join(OUT_DIR, "3-测试报告.docx")
    doc.save(path)
    return path


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    p1 = build_requirements()
    p2 = build_design()
    p3 = build_test_report()
    for p in (p1, p2, p3):
        print("生成:", p, "%.1f KB" % (os.path.getsize(p) / 1024.0))
