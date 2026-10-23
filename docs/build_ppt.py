# -*- coding: utf-8 -*-
"""生成答辩 PPT（第 2 版：以 app 实际内容为主线，截图放大多用局部特写）。

运行： python docs/build_ppt.py
产物： docs/4-答辩演示.pptx
"""

import os
import sys

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from qbank import QUESTIONS, CHAPTERS

BG = RGBColor(0x0F, 0x11, 0x17)
CARD = RGBColor(0x1A, 0x1E, 0x29)
CARD_HI = RGBColor(0x23, 0x2A, 0x3A)
BORDER = RGBColor(0x2A, 0x31, 0x42)
TEXT = RGBColor(0xE9, 0xED, 0xF5)
DIM = RGBColor(0x8B, 0x93, 0xA7)
ACCENT = RGBColor(0x4D, 0x8D, 0xF7)
GREEN = RGBColor(0x3D, 0xDC, 0x84)
YELLOW = RGBColor(0xF5, 0xC4, 0x51)
RED = RGBColor(0xFF, 0x6B, 0x6B)
PURPLE = RGBColor(0xC6, 0x78, 0xDD)

FONT = "微软雅黑"
TOTAL_Q = len(QUESTIONS)
TOTAL_CASES = sum(len(q["cases"]) for q in QUESTIONS)
SHOTS = os.path.join(ROOT, "shots")


# ---------------------------------------------------------------- 基础工具
def set_run(run, text, size, bold=False, color=TEXT, font=FONT):
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = etree.SubElement(rPr, qn("a:ea"))
    ea.set("typeface", font)


def textbox(slide, x, y, w, h, text, size, bold=False, color=TEXT,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.2):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        set_run(p.add_run(), line, size, bold, color)
    return box


def card(slide, x, y, w, h, fill=CARD, line=BORDER, radius=0.04):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                   Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(1)
    shape.adjustments[0] = radius
    shape.shadow.inherit = False
    return shape


def chip(slide, x, y, w, h, text, color=ACCENT, size=12):
    shape = card(slide, x, y, w, h, fill=color, line=color)
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = 0
    tf.margin_right = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    set_run(p.add_run(), text, size, True, BG)
    return shape


def new_slide(prs, footer=True):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    if footer:
        textbox(slide, 0.62, 7.04, 6.0, 0.3, "Python 程序设计刷题系统", 9, False, RGBColor(0x4B, 0x52, 0x66))
    return slide


def slide_title(slide, title, kicker=None, kicker_color=DIM):
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.62), Inches(0.58),
                                 Inches(0.09), Inches(0.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()
    bar.shadow.inherit = False
    textbox(slide, 0.9, 0.5, 11.8, 0.65, title, 27, True, TEXT)
    if kicker:
        textbox(slide, 0.92, 1.1, 11.8, 0.35, kicker, 12.5, False, kicker_color)


def picture(slide, name, x, y, w, h):
    """按比例放进 (x,y,w,h) 区域并居中，返回实际尺寸。"""
    path = os.path.join(SHOTS, name)
    iw, ih = Image.open(path).size
    scale = min(w / float(iw), h / float(ih))
    nw, nh = iw * scale, ih * scale
    left = x + (w - nw) / 2.0
    top = y + (h - nh) / 2.0
    slide.shapes.add_picture(path, Inches(left), Inches(top), Inches(nw), Inches(nh))
    return nw, nh


def note(slide, x, y, w, head, body, color=ACCENT, size=12):
    textbox(slide, x, y, w, 0.32, head, size + 0.5, True, color)
    textbox(slide, x, y + 0.3, w, 0.62, body, size - 1.5, False, DIM, line_spacing=1.3)


def big_number(slide, x, y, value, label, color=ACCENT, vsize=30):
    textbox(slide, x, y, 2.4, 0.62, value, vsize, True, color)
    textbox(slide, x, y + 0.58, 2.4, 0.3, label, 10.5, False, DIM)


# ---------------------------------------------------------------- 幻灯片
def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1 封面
    s = new_slide(prs, footer=False)
    band = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(1.45),
                              Inches(0.12), Inches(1.9))
    band.fill.solid()
    band.fill.fore_color.rgb = ACCENT
    band.line.fill.background()
    band.shadow.inherit = False
    textbox(s, 1.2, 1.4, 11.0, 0.85, "Python 程序设计刷题系统", 40, True, TEXT)
    textbox(s, 1.22, 2.25, 11.0, 0.5, "写代码 → 立即判题 → 错题复习 → 随机组卷自测", 17, False, ACCENT)
    textbox(s, 1.22, 2.8, 10.8, 0.4, "把教材第 3～5 章实验题做成一个能判题、能复盘、能组卷的桌面程序",
            12.5, False, DIM)

    stats = [("{} 题".format(TOTAL_Q), "题库", GREEN), ("{} 个".format(TOTAL_CASES), "测试用例", ACCENT),
             ("{} 章".format(len(CHAPTERS)), "章节覆盖", YELLOW), ("0", "运行依赖", PURPLE)]
    for i, (v, label, color) in enumerate(stats):
        x = 1.22 + i * 2.85
        card(s, x, 4.05, 2.55, 1.12, fill=CARD)
        textbox(s, x + 0.22, 4.2, 2.2, 0.5, v, 24, True, color)
        textbox(s, x + 0.22, 4.74, 2.2, 0.3, label, 10.5, False, DIM)

    textbox(s, 1.22, 5.65, 11.0, 0.35, "答辩人：____________      指导教师：____________      2026-10-21",
            11.5, False, RGBColor(0x6B, 0x73, 0x87))

    # 2 目录
    s = new_slide(prs)
    slide_title(s, "汇报路线", "从问题到交付，四个板块")
    items = [
        ("01", "为什么做", "教材实验题的练习现状与三个痛点"),
        ("02", "做成了什么", "题库、判题、学习闭环、模拟组卷"),
        ("03", "怎么做的", "分层架构与判题引擎的两个关键设计"),
        ("04", "做得怎么样", "测试数据、交付形态与后续计划"),
    ]
    for i, (num, head, sub) in enumerate(items):
        y = 1.65 + i * 1.3
        card(s, 0.9, y, 11.5, 1.05)
        textbox(s, 1.15, y + 0.22, 0.9, 0.6, num, 24, True, ACCENT)
        textbox(s, 2.1, y + 0.14, 6.8, 0.42, head, 16, True, TEXT)
        textbox(s, 2.1, y + 0.58, 9.8, 0.34, sub, 11, False, DIM)

    # 3 痛点
    s = new_slide(prs)
    slide_title(s, "为什么做：刷题三难", "教材 69 道实验题，学生和老师都费劲")
    pain = [
        ("判不了", "写完只能自己对样例，\n边界情况全靠猜", RED),
        ("记不住", "错题散在 .py 文件里，\n考前找不到", YELLOW),
        ("跑不动", "机房没装 Python，\n发给同学也打不开", ACCENT),
    ]
    for i, (head, body, color) in enumerate(pain):
        x = 0.9 + i * 3.95
        card(s, x, 1.75, 3.7, 2.2)
        textbox(s, x + 0.32, 1.98, 3.0, 0.5, head, 22, True, color)
        textbox(s, x + 0.32, 2.62, 3.1, 1.0, body, 12.5, False, TEXT, line_spacing=1.45)
    textbox(s, 0.9, 4.35, 11.5, 0.4, "目标：一个双击就能用的程序，把「判题、复盘、组卷」都装进去",
            15, True, TEXT)
    textbox(s, 0.9, 4.9, 11.5, 1.4,
            "题库内置 → 不用找题；F5 即判 → 对错立刻知道；错题自动收集 → 复习有的放矢；\n"
            "目录版免安装 → 拷到任何 Windows 电脑都能跑。",
            12.5, False, DIM, line_spacing=1.6)

    # 4 方案总览
    s = new_slide(prs)
    slide_title(s, "做成了什么：一个程序，四条主线", "题库 → 判题 → 复盘 → 组卷")
    steps = ["读题", "写代码", "F5 判题", "看反馈", "错题复习", "随机组卷"]
    for i, name in enumerate(steps):
        x = 0.9 + i * 1.95
        chip(s, x, 1.62, 1.75, 0.52, name, ACCENT if i % 2 == 0 else CARD_HI,
             size=12)
        if i < len(steps) - 1:
            textbox(s, x + 1.75, 1.63, 0.2, 0.4, "›", 15, True, DIM, align=PP_ALIGN.CENTER)

    feats = [
        ("{} 道题 · {} 用例".format(TOTAL_Q, TOTAL_CASES), "教材三章 + 拓展 + 算法，每题含提示/答案/解析", GREEN),
        ("逐条用例判定", "显示期望/实际/首个不一致的行，超时 6 秒保护", ACCENT),
        ("错题本 · 收藏 · 统计", "通过自动移除，进度与每题代码自动保存", YELLOW),
        ("模拟组卷", "题量/章节/难度/限时可选，交卷出得分与明细", PURPLE),
    ]
    for i, (head, sub, color) in enumerate(feats):
        col, row = i % 2, i // 2
        x = 0.9 + col * 5.9
        y = 2.55 + row * 1.25
        card(s, x, y, 5.6, 1.08)
        bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.02), Inches(y + 0.16),
                                 Inches(0.07), Inches(0.72))
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        bar.line.fill.background()
        bar.shadow.inherit = False
        textbox(s, x + 0.28, y + 0.16, 5.0, 0.38, head, 14, True, TEXT)
        textbox(s, x + 0.28, y + 0.58, 5.1, 0.4, sub, 10.5, False, DIM)

    # 5 题库全景
    s = new_slide(prs)
    slide_title(s, "题库全景：{} 题覆盖 5 个章节".format(TOTAL_Q), "教材题按原文整理，拓展与算法题重新命题并标注来源")
    total = float(TOTAL_Q)
    y0 = 1.65
    for i, c in enumerate(CHAPTERS):
        qn_ = len(c["questions"])
        cn_ = sum(len(q["cases"]) for q in c["questions"])
        y = y0 + i * 0.78
        textbox(s, 0.9, y + 0.06, 3.0, 0.3, c["name"], 12.5, True, TEXT)
        # 条形
        bar_bg = card(s, 3.95, y + 0.12, 5.4, 0.26, fill=CARD_HI, line=CARD_HI, radius=0.5)
        w = max(0.25, 5.4 * qn_ / total)
        bar = card(s, 3.95, y + 0.12, w, 0.26, fill=ACCENT, line=ACCENT, radius=0.5)
        textbox(s, 9.45, y + 0.02, 1.2, 0.3, "{} 题".format(qn_), 12, True, GREEN)
        textbox(s, 10.5, y + 0.02, 2.4, 0.3, "{} 用例".format(cn_), 11, False, DIM)

    textbox(s, 0.9, 5.85, 11.6, 0.35, "题目来源", 13, True, ACCENT)
    textbox(s, 0.9, 6.2, 11.6, 0.9,
            "教材：《Python 程序设计实验指导与习题解答》第 3～5 章（69 题，含实验解析纠错）    "
            "拓展：Python100Cases 等公开题集（40 题，重写题干、自写答案与用例）    "
            "算法：排序/查找/递归/栈/DP 入门（30 题）",
            9.5, False, DIM, line_spacing=1.5)

    # 6 一道题的结构
    s = new_slide(prs)
    slide_title(s, "一道题里有什么", "题干 · 提示 · 编辑器 · 用例 · 答案与解析")
    picture(s, "crop_editor.png", 0.62, 1.62, 7.0, 3.3)
    picture(s, "crop_judge.png", 0.62, 5.12, 7.0, 1.55)
    note(s, 7.95, 1.7, 4.9, "题目描述 + 方法提示", "提示默认折叠，先自己想再看")
    note(s, 7.95, 2.75, 4.9, "代码编辑器", "行号 / 语法高亮 / Tab 转 4 空格 / 自动缩进")
    note(s, 7.95, 3.8, 4.9, "三个标签页", "标准输入 · 判题结果 · 参考答案")
    note(s, 7.95, 5.05, 4.9, "判题结果", "逐条用例 + 期望 vs 实际 + 首个不一致行", GREEN)
    textbox(s, 7.95, 6.45, 4.9, 0.5, "每道题都带提示、答案、解析和 1～5 个用例",
            10, False, DIM)

    # 7 刷题页全貌
    s = new_slide(prs)
    slide_title(s, "刷题页：一屏完成读题、写码、判题", "章节按钮可切换范围，题目与答案就在手边")
    picture(s, "03_practice_pass.png", 0.7, 1.5, 8.4, 5.4)
    bullets = [
        ("章节范围", "全部 / 第3章 / 第4章 / 第5章 / 拓展 / 算法"),
        ("代码区", "行号 + 语法高亮，F5 直接跑"),
        ("结果面板", "全部通过后状态变绿"),
        ("答案页", "参考代码 + 易错点解析"),
    ]
    for i, (head, body) in enumerate(bullets):
        note(s, 9.5, 1.7 + i * 1.3, 3.4, head, body, ACCENT)

    # 8 判题反馈（特写）
    s = new_slide(prs)
    slide_title(s, "判题反馈：错在哪一行，直接告诉你", "不是「对 / 错」两个字，而是可定位的反馈")
    picture(s, "02_practice_fail.png", 0.62, 1.6, 6.1, 4.9)
    picture(s, "crop_judge.png", 7.0, 1.7, 5.9, 1.22)
    notes = [
        ("逐条用例", "通过 / 输出不同 / 运行出错 / 超时"),
        ("定位差异", "第几行不一致 + 期望 vs 实际"),
        ("分类提示", "EOF、NameError、死循环各有说明"),
        ("6 秒超时", "死循环也不会卡死界面"),
    ]
    for i, (head, body) in enumerate(notes):
        note(s, 7.0, 3.15 + i * 0.98, 5.9, head, body, ACCENT, size=11)

    # 9 答案与解析
    s = new_slide(prs)
    slide_title(s, "参考答案与解析：学会，而不只是做对", "教材示范代码的问题也逐条指出")
    picture(s, "crop_answer.png", 0.62, 1.5, 8.0, 1.7)
    picture(s, "05_answer.png", 0.62, 3.4, 8.0, 3.4)
    note(s, 8.9, 1.7, 4.0, "来源标注", "拓展题会写明原题编号，方便回溯")
    note(s, 8.9, 2.8, 4.0, "参考代码", "可一键载入编辑器对照运行", GREEN)
    note(s, 8.9, 3.9, 4.0, "易错点解析", "为什么错、正确思路、更好的写法", YELLOW)
    note(s, 8.9, 5.0, 4.0, "教材纠错", "如 while 条件恒真、循环里重复打印", RED)

    # 10 错题本 + 统计
    s = new_slide(prs)
    slide_title(s, "复盘：统计饼图与得分趋势", "统计页把「哪里弱」和「有没有进步」一次说清")
    picture(s, "crop_pies.png", 0.62, 1.58, 7.6, 1.32)
    picture(s, "crop_trend.png", 0.62, 3.02, 7.6, 0.92)
    card(s, 0.62, 4.18, 7.6, 2.45)
    textbox(s, 0.95, 4.35, 7.0, 0.32, "统计页能做什么", 13, True, ACCENT)
    textbox(s, 0.95, 4.72, 7.0, 1.7,
            "· 两张饼图：学习状态（已通过/需复习/已看题/未开始）与各章已通过数\n"
            "· 折线趋势：历次组卷得分、平均分与最高分，看自己有没有进步\n"
            "· 错题本：最近一次未通过的题自动进入，通过后自动移除\n"
            "· 导出报告：一键导出 CSV（汇总 / 章节进度 / 组卷记录 / 逐题明细）",
            10, False, DIM, line_spacing=1.45)
    note(s, 8.6, 1.7, 4.1, "两张饼图", "图例带数量与百分比，环形中心显示总量", ACCENT, size=11)
    note(s, 8.6, 2.9, 4.1, "得分趋势", "按时间顺序画折线，配色区分优良中差", GREEN, size=11)
    note(s, 8.6, 4.1, 4.1, "与列表联动", "图表和下方表格共用同一份数据", YELLOW, size=11)
    note(s, 8.6, 5.3, 4.1, "导出 CSV", "Excel 双击即开，答辩材料可直接引用", PURPLE, size=11)

    # 11 组卷配置
    s = new_slide(prs)
    slide_title(s, "模拟组卷：按需出卷", "题量、章节、难度、限时都可选，题库不足会明确提示")
    picture(s, "crop_setup.png", 0.62, 1.55, 8.3, 1.7)
    card(s, 0.62, 3.55, 8.3, 3.15)
    textbox(s, 0.95, 3.75, 7.6, 0.34, "组卷规则", 13, True, ACCENT)
    rules = [
        ("按错题加权（默认）", "错得多、没掌握的题权重更高；也可切回「章节均衡」按章均匀出题"),
        ("按章节轮转抽题", "章节均衡模式下，每轮从各章剩余题里取一题，保证覆盖面"),
        ("随机且可复现", "用随机数生成器抽样，测试时传固定种子即可复现同一套卷子"),
        ("题量不足会提示", "可用题数少于要求时直接提示「只有 N 题，不够出 M 道」，不出半套卷"),
        ("考试规则同步生效", "限时、禁用答案入口、交卷评分都在进入考试时一起生效"),
    ]
    for i, (head, body) in enumerate(rules):
        y = 4.2 + i * 0.62
        textbox(s, 0.95, y, 2.6, 0.34, head, 11, True, TEXT)
        textbox(s, 3.55, y, 5.1, 0.5, body, 9.5, False, DIM, line_spacing=1.3)
    params = [("题量", "5 / 10 / 20 / 30"), ("章节", "5 章任选，可多选"),
              ("难度", "不限 / 入门 / 进阶 / 挑战"), ("限时", "不限 / 10 / 20 / 30 分钟")]
    for i, (k, v) in enumerate(params):
        y = 1.7 + i * 1.25
        textbox(s, 9.3, y, 3.6, 0.3, k, 12, True, ACCENT)
        textbox(s, 9.3, y + 0.3, 3.6, 0.5, v, 10.5, False, DIM)
    textbox(s, 9.3, 6.75, 3.6, 0.3, "选中项高亮显示", 9.5, False, GREEN)

    # 12 考试中
    s = new_slide(prs)
    slide_title(s, "考试模式：倒计时与进度", "考试中禁用章节切换与答案入口")
    picture(s, "10_exam_running.png", 0.62, 1.5, 8.4, 5.4)
    notes2 = [("倒计时", "剩余时间随时可见，最后 1 分钟变红"),
              ("实时进度", "已通过 x / n 题"),
              ("答案禁用", "按钮变灰，点了会提示"),
              ("超时交卷", "倒计时归零自动提交")]
    for i, (head, body) in enumerate(notes2):
        note(s, 9.5, 1.7 + i * 1.28, 3.4, head, body, ACCENT)

    # 13 交卷报告
    s = new_slide(prs)
    slide_title(s, "交卷报告：得分、评价、逐题明细", "成绩写入历史，可回看最近 10 次")
    picture(s, "crop_result.png", 0.62, 1.62, 7.9, 2.75)
    card(s, 0.62, 4.62, 7.9, 1.98)
    textbox(s, 0.95, 4.78, 7.3, 0.32, "报告里有什么", 12.5, True, ACCENT)
    textbox(s, 0.95, 5.14, 7.3, 1.4,
            "· 得分与评价：按通过率折算百分制，并给出优秀/良好/及格/需加强\n"
            "· 逐题明细：通过、未通过、未作答分别标记，并记录尝试次数\n"
            "· 章节分布：本次卷子各章占比，便于判断偏科\n"
            "· 成绩写入历史，下次组卷可与上次对比",
            10, False, DIM, line_spacing=1.4)
    note(s, 8.75, 1.7, 4.1, "四个指标", "得分、通过题数、用时、评价", ACCENT)
    note(s, 8.75, 2.75, 4.1, "逐题明细", "✓ 通过 / ✗ 未通过 / — 未作答", GREEN)
    note(s, 8.75, 3.8, 4.1, "章节分布", "本次卷子各章占比一目了然", YELLOW)
    note(s, 8.75, 4.85, 4.1, "后续动作", "再来一套 / 去错题本 / 返回主页", PURPLE)

    # 14 架构
    s = new_slide(prs)
    slide_title(s, "技术架构：分层解耦，数据驱动", "Python 3.8 + Tkinter + PyInstaller 5.13.2")
    layers = [
        ("表现层", "ui.py · widgets.py · theme.py · ui_exam.py", "5 个页面 + 自绘控件 + DPI 缩放", ACCENT),
        ("业务层", "judge.py · exam.py", "判题执行与比对 · 组卷/限时/评分", GREEN),
        ("数据层", "qbank.py · bank_ch3/4/5 · bank_extra · bank_algo", "{} 道题的题干、答案、用例、解析".format(TOTAL_Q), YELLOW),
        ("存储层", "store.py", "进度 / 错题 / 收藏 / 考试历史（原子写入）", PURPLE),
    ]
    for i, (name, mods, desc, color) in enumerate(layers):
        y = 1.6 + i * 1.15
        card(s, 0.9, y, 11.5, 0.98)
        chip(s, 1.1, y + 0.24, 1.3, 0.5, name, color, size=12)
        textbox(s, 2.65, y + 0.16, 9.5, 0.34, mods, 11, True, TEXT, )
        textbox(s, 2.65, y + 0.54, 9.5, 0.34, desc, 10, False, DIM)
    textbox(s, 0.9, 6.25, 11.5, 0.4, "判题与组卷都不依赖界面，可以脱离 GUI 单独测试——这是能快速迭代的原因",
            10.5, False, GREEN)

    # 15 判题引擎
    s = new_slide(prs)
    slide_title(s, "判题引擎：判得准，也不卡死", "五个步骤，核心在 judge.py")
    steps = [
        ("静态检查", "拦截 os.system / subprocess / ctypes"),
        ("重定向 I/O", "stdout→StringIO，input() 不回显提示语"),
        ("超时看门狗", "sys.settrace 计时，抛 BaseException 子类"),
        ("执行与捕获", "EOFError / 语法错误 / 运行错误分类提示"),
        ("归一化比对", "忽略行尾空格；图形题保留缩进精确比对"),
    ]
    for i, (head, body) in enumerate(steps):
        x = 0.9 + i * 2.36
        card(s, x, 1.75, 2.15, 2.5)
        num = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.85), Inches(1.95),
                                 Inches(0.45), Inches(0.45))
        num.fill.solid()
        num.fill.fore_color.rgb = ACCENT
        num.line.fill.background()
        num.shadow.inherit = False
        textbox(s, x + 0.85, 2.02, 0.45, 0.32, str(i + 1), 12, True, BG, align=PP_ALIGN.CENTER)
        textbox(s, x + 0.15, 2.55, 1.85, 0.62, head, 12.5, True, TEXT, align=PP_ALIGN.CENTER)
        textbox(s, x + 0.15, 3.15, 1.85, 0.95, body, 9, False, DIM,
                align=PP_ALIGN.CENTER, line_spacing=1.35)

    card(s, 0.9, 4.55, 11.5, 1.9)
    textbox(s, 1.15, 4.72, 5.2, 0.34, "为什么进程内执行，而不是起子进程？", 12.5, True, ACCENT)
    textbox(s, 1.15, 5.1, 5.2, 1.2,
            "打包成 exe 后 sys.executable 指向 exe 自身，\n起子进程会变成再启动一个刷题程序。",
            10.5, False, DIM, line_spacing=1.4)
    textbox(s, 6.7, 4.72, 5.5, 0.34, "为什么目录版而不是单文件？", 12.5, True, ACCENT)
    textbox(s, 6.7, 5.1, 5.5, 1.2,
            "单文件启动要解压到 %TEMP%，个别机器会失败；\n目录版不解压，实测把 TEMP 指到不存在路径也能跑。",
            10.5, False, DIM, line_spacing=1.4)

    # 16 质量
    s = new_slide(prs)
    slide_title(s, "质量保障：能自动测的都自动测了", "四类测试，全部通过")
    nums = [("{}".format(TOTAL_Q), "道题自检", GREEN), ("{}".format(TOTAL_CASES), "个用例", ACCENT),
            ("10", "组卷自检", YELLOW), ("13 + 10", "交互 + 边界", PURPLE)]
    for i, (v, label, color) in enumerate(nums):
        x = 0.9 + i * 3.0
        card(s, x, 1.6, 2.7, 1.15)
        textbox(s, x + 0.25, 1.74, 2.2, 0.5, v, 24, True, color)
        textbox(s, x + 0.25, 2.28, 2.2, 0.3, label, 10.5, False, DIM)

    rows = [
        ["题库自检", "参考答案跑自己的用例", "{} 题 / {} 用例".format(TOTAL_Q, TOTAL_CASES), "全部通过"],
        ["组卷自检", "随机性/覆盖/过滤/评分/限时", "10 项", "全部通过"],
        ["交互测试", "判题、错题、收藏、统计、组卷", "13 项", "全部通过"],
        ["边界测试", "死循环、输入不足、语法错误、危险调用", "10 项", "全部通过"],
        ["打包验证", "启动、图标、进度、高分屏、TEMP 无关", "7 项", "全部通过"],
    ]
    shape = s.shapes.add_table(len(rows) + 1, 4, Inches(0.9), Inches(3.05),
                               Inches(11.5), Inches(0.44 * (len(rows) + 1)))
    tbl = shape.table
    for i, w in enumerate([2.3, 6.2, 1.9, 1.6]):
        tbl.columns[i].width = Emu(int(Inches(w)))
    for j, head in enumerate(["类型", "覆盖内容", "规模", "结果"]):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_HI
        cell.margin_left = Inches(0.12)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        set_run(cell.text_frame.paragraphs[0].add_run(), head, 11, True, TEXT)
    for i, row in enumerate(rows, 1):
        for j, text in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD if i % 2 else BG
            cell.margin_left = Inches(0.12)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            color = GREEN if j == 3 else (TEXT if j != 1 else DIM)
            set_run(cell.text_frame.paragraphs[0].add_run(), text, 10, False, color)

    textbox(s, 0.9, 6.35, 11.5, 0.4,
            "修过的典型问题：单文件解压失败 → 改目录版；DPI 未适配 → 按屏缩放；完数题超时 → 改 √n 枚举",
            10, False, DIM)

    # 17 交付
    s = new_slide(prs)
    slide_title(s, "交付与部署：拷过去就能用", "免安装目录版 + 便携 zip，不依赖 %TEMP%")
    picture(s, "exe_running.png", 0.62, 1.6, 7.4, 4.9)
    rows2 = [("21 MB", "目录版，含 Python 运行库"), ("8.9 MB", "便携 zip，解压即用"),
             ("0 依赖", "目标机不需装 Python"), ("1 秒", "启动速度（不再解压临时文件）")]
    for i, (v, label) in enumerate(rows2):
        y = 1.7 + i * 1.25
        textbox(s, 8.35, y, 1.5, 0.4, v, 15, True, ACCENT)
        textbox(s, 9.9, y + 0.05, 3.2, 0.5, label, 10.5, False, DIM)
    textbox(s, 8.35, 6.55, 4.6, 0.4, "首次运行如遇 SmartScreen：更多信息 → 仍要运行", 9.5, False, YELLOW)

    # 18 总结
    s = new_slide(prs)
    slide_title(s, "总结与下一步", "把教材题变成可练、可测、可复盘的工具体系")
    textbox(s, 0.9, 1.6, 5.6, 0.36, "做完了什么", 15, True, GREEN)
    textbox(s, 0.9, 2.0, 5.5, 2.9,
            "· {} 题四类题库，{} 个用例全部自检通过\n\n"
            "· 判题引擎：沙箱执行 + 超时保护 + 归一化比对\n\n"
            "· 学习闭环：错题本 / 收藏 / 统计 / 进度保存\n\n"
            "· 模拟组卷：随机出卷 + 限时 + 交卷报告\n\n"
            "· 免安装目录版 + 5 份项目文档".format(TOTAL_Q, TOTAL_CASES),
            11.5, False, TEXT, line_spacing=1.35)

    textbox(s, 7.0, 1.6, 5.4, 0.36, "还能怎么走", 15, True, YELLOW)
    textbox(s, 7.0, 2.0, 5.4, 2.9,
            "· 函数题 / 文件题（判题需要新的执行约定）\n\n"
            "· 按错题加权的智能组卷\n\n"
            "· 成绩趋势与章节正确率曲线\n\n"
            "· 机房多人使用：导出成绩 / Web 版",
            11.5, False, TEXT, line_spacing=1.35)

    card(s, 0.9, 5.75, 11.5, 0.8, fill=CARD_HI, line=ACCENT)
    textbox(s, 1.2, 5.95, 11.0, 0.4, "谢谢各位老师，请批评指正", 17, True, TEXT, align=PP_ALIGN.CENTER)

    out = os.path.join(HERE, "4-答辩演示.pptx")
    try:
        prs.save(out)
    except PermissionError:
        alt = os.path.join(HERE, "4-答辩演示(优化版).pptx")
        prs.save(alt)
        print("注意：4-答辩演示.pptx 正被占用，已另存为：", alt)
        return alt
    return out


if __name__ == "__main__":
    p = build()
    print("生成:", p, "%.1f KB" % (os.path.getsize(p) / 1024.0))
