# -*- coding: utf-8 -*-
"""配色与字体常量：暗色主题。

字体在运行时用 pick_font() 从系统可用字体里挑选，避免缺字体时界面变方块。
"""

BG = "#0f1117"
SIDEBAR = "#12151f"
SIDEBAR_HI = "#1a1f2d"
CARD = "#1a1e29"
CARD_HI = "#232a3a"
BORDER = "#2a3142"
BORDER_HI = "#3a4459"
GUTTER = "#151924"

TEXT = "#e9edf5"
TEXT_DIM = "#c2cadb"
MUTED = "#8b93a7"

ACCENT = "#4d8df7"
ACCENT_HI = "#6ba2ff"
ACCENT_DARK = "#3467c9"
GREEN = "#3ddc84"
GREEN_DARK = "#1f6b45"
RED = "#ff6b6b"
RED_DARK = "#7a2c2c"
YELLOW = "#f5c451"
PURPLE = "#c678dd"
CYAN = "#61afef"

LEVEL_COLORS = {1: "#3ddc84", 2: "#f5c451", 3: "#ff6b6b"}
LEVEL_NAMES = {1: "入门", 2: "进阶", 3: "挑战"}

# 屏幕缩放因子：高分屏（125%/150%/200%）下按比例放大窗口与间距
SCALE = 1.0


def set_scale(value):
    global SCALE
    try:
        SCALE = max(1.0, min(2.5, float(value)))
    except (TypeError, ValueError):
        SCALE = 1.0
    return SCALE


def S(value):
    """把设计稿上的像素值换算成当前屏幕的像素值。"""
    return int(round(value * SCALE))


def pick_font(candidates, root):
    """返回系统里第一个可用的字体名。"""
    try:
        import tkinter.font as tkfont
        available = set(tkfont.families(root))
    except Exception:
        return candidates[-1]
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]
