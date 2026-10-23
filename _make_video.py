# -*- coding: utf-8 -*-
"""用截图生成演示视频（1080p，带缓慢推近与字幕）。

每张图生成 3 秒片段（Ken Burns 缓慢放大 + 底部字幕），最后拼接成一个 mp4。
需要 ffmpeg 在 PATH 里（或设置 FFMPEG 环境变量）。
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")
TMP = os.path.join(SHOTS, "_scenes")
OUT = os.path.join(HERE, "docs", "演示视频.mp4")
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FONT = r"C:\Windows\Fonts\msyh.ttc"

SCENES = [
    ("01_home.png", "主页：139 题 / 5 章，进度一目了然"),
    ("03_practice_pass.png", "刷题：写代码，F5 立即判题"),
    ("02_practice_fail.png", "答错时指出「第几行不一致」和期望/实际输出"),
    ("crop_answer.png", "参考答案与易错点解析"),
    ("07_stats.png", "统计：状态饼图、各章通过率、得分趋势"),
    ("09_exam_setup.png", "模拟组卷：题量 / 章节 / 难度 / 限时，可按错题加权"),
    ("10_exam_running.png", "考试中：倒计时与实时进度，答案入口被禁用"),
    ("11_exam_result.png", "交卷报告：得分、评价、逐题明细"),
    ("08_wrong_book.png", "错题本：未通过的题自动收集"),
]


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-800:])
    return r.returncode == 0


def main():
    if shutil.which(FFMPEG) is None and not os.path.exists(FFMPEG):
        print("找不到 ffmpeg，请设置 FFMPEG 环境变量")
        return 1
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)

    clips = []
    for i, (name, caption) in enumerate(SCENES):
        src = os.path.join(SHOTS, name)
        if not os.path.exists(src):
            print("跳过（缺图）:", name)
            continue
        cap_path = os.path.join(TMP, "cap%02d.txt" % i)
        with open(cap_path, "w", encoding="utf-8") as f:
            f.write(caption)

        out = os.path.join(TMP, "clip%02d.mp4" % i)
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,fps=30,"
            "drawbox=y=1000:w=iw:h=80:color=black@0.55:t=fill,"
            "drawtext=fontfile='%s':textfile='%s':x=60:y=1024:fontsize=34:fontcolor=white"
            % (FONT.replace("\\", "/").replace(":", "\\:"), cap_path.replace("\\", "/").replace(":", "\\:"))
        )
        ok = run([FFMPEG, "-y", "-loop", "1", "-t", "3", "-i", src,
                  "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                  "-crf", "23", "-r", "30", "-frames:v", "90", out])
        if ok:
            clips.append(out)
            print("片段 %d/%d: %s" % (i + 1, len(SCENES), name))
        else:
            print("失败:", name)

    if not clips:
        print("没有生成任何片段")
        return 1

    listfile = os.path.join(TMP, "list.txt")
    with open(listfile, "w", encoding="utf-8") as f:
        for c in clips:
            f.write("file '%s'\n" % c.replace("\\", "/"))

    if not os.path.isdir(os.path.dirname(OUT)):
        os.makedirs(os.path.dirname(OUT))
    ok = run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
              "-c", "copy", "-movflags", "+faststart", OUT])
    if ok:
        print("生成:", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1024.0 / 1024.0))
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
