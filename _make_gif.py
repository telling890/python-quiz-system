# -*- coding: utf-8 -*-
"""用截图合成一张功能巡览 GIF（README 用）。

把几张关键界面按顺序播放，每帧停留 1.4 秒，循环播放。
"""

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")

FRAMES = [
    ("01_home.png", "主页：章节进度"),
    ("03_practice_pass.png", "刷题：写代码"),
    ("02_practice_fail.png", "判题：逐条用例"),
    ("07_stats.png", "统计：饼图与明细"),
    ("09_exam_setup.png", "组卷：配置范围"),
    ("11_exam_result.png", "交卷：得分报告"),
]

WIDTH = 960
DURATION = 1400


def main():
    images = []
    for name, _label in FRAMES:
        path = os.path.join(SHOTS, name)
        im = Image.open(path).convert("RGB")
        h = int(im.height * WIDTH / float(im.width))
        images.append(im.resize((WIDTH, h), Image.LANCZOS))

    # 统一尺寸（取第一张的高度）
    h = images[0].height
    images = [im.resize((WIDTH, h), Image.LANCZOS) for im in images]

    # 转成调色板图像，减小体积
    frames = [im.convert("P", palette=Image.ADAPTIVE, colors=128) for im in images]

    out = os.path.join(SHOTS, "demo.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, optimize=True, disposal=2)
    print("生成:", out, "%.2f MB" % (os.path.getsize(out) / 1024.0 / 1024.0),
          "尺寸:", frames[0].size)


if __name__ == "__main__":
    main()
