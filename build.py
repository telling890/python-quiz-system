# -*- coding: utf-8 -*-
"""一键打包：先自检题库，再生成图标，最后用 PyInstaller 打成单文件 exe。

用法：python build.py
产物：dist\\Python字符串刷题系统.exe
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

APP_NAME = "Python刷题系统"
DIST = os.path.join(HERE, "dist")
BUILD = os.path.join(HERE, "build")
ASSETS = os.path.join(HERE, "assets")
ICON = os.path.join(ASSETS, "app.ico")
EXTRA_LIBS = os.path.join(HERE, "pylibs")

# 打包依赖都装在 pylibs 里，本脚本自己也要能 import 到（例如 Pillow 画图标）
if os.path.isdir(EXTRA_LIBS) and EXTRA_LIBS not in sys.path:
    sys.path.insert(0, EXTRA_LIBS)


def build_env():
    """把项目内的 pylibs 目录加到 PYTHONPATH，用其中的新版 PyInstaller。

    PyInstaller 3.x 不支持 Python 3.8，打出来的 exe 一启动就报 Fatal error，
    所以这里固定用 5.x（装在 pylibs 里，不改动系统环境）。
    """
    env = dict(os.environ)
    if os.path.isdir(EXTRA_LIBS):
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = EXTRA_LIBS + (os.pathsep + prev if prev else "")
    return env


def pyinstaller_version(env):
    try:
        out = subprocess.run(
            [sys.executable, "-c", "import PyInstaller;print(PyInstaller.__version__)"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=90)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "ignore").strip()


def check_pyinstaller(env):
    ver = pyinstaller_version(env)
    if not ver:
        print("没有找到可用的 PyInstaller。请先安装到项目目录：")
        print('  python -m pip install --target pylibs "pyinstaller==5.13.2"')
        sys.exit(1)
    major = int(ver.split(".")[0])
    if major < 4:
        print("当前 PyInstaller {} 太旧（不支持 Python 3.8），打出的 exe 会启动失败。".format(ver))
        print('请安装 5.x：python -m pip install --target pylibs "pyinstaller==5.13.2"')
        sys.exit(1)
    print("PyInstaller", ver)


def make_icon():
    """生成应用图标：圆角渐变方块 + 白色「刷」字，导出多尺寸 ico。"""
    from PIL import Image, ImageDraw, ImageFont

    if not os.path.isdir(ASSETS):
        os.makedirs(ASSETS)

    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 竖向渐变背景（先画渐变，再用圆角蒙版裁切）
    gradient = Image.new("RGB", (1, size))
    top = (77, 141, 247)
    bottom = (52, 103, 201)
    for y in range(size):
        t = y / float(size - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        gradient.putpixel((0, y), color)
    gradient = gradient.resize((size, size))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([8, 8, size - 8, size - 8], radius=56, fill=255)
    img.paste(gradient, (0, 0), mask)

    # 白色字符
    text = "刷"
    font = None
    for path in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
                 r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 150)
                break
            except OSError:
                continue
    if font is None:
        font = ImageFont.load_default()

    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1]),
              text, font=font, fill=(255, 255, 255, 255))

    png = os.path.join(ASSETS, "app.png")
    img.save(png)
    img.save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                          (128, 128), (256, 256)])
    print("图标已生成：", ICON)


def run_selftest():
    print("=" * 60)
    print("1/3  题库自检")
    print("=" * 60)
    code = subprocess.call([sys.executable, os.path.join(HERE, "selftest.py")])
    if code != 0:
        print("题库自检未通过，已中止打包。")
        sys.exit(1)


def build_exe():
    env = build_env()
    check_pyinstaller(env)

    print("=" * 60)
    print("2/3  生成图标")
    print("=" * 60)
    make_icon()

    print("=" * 60)
    print("3/3  PyInstaller 打包（目录版，大约 1-3 分钟）")
    print("=" * 60)
    # 用 --onedir（目录版）而不是 --onefile：
    # onefile 启动时要把内容解压到 %TEMP% 才能运行，某些机器（本机就是）
    # 引导器建不了临时目录，会弹 "INTERNAL ERROR: cannot create temporary directory!"。
    # 目录版不解压、不依赖 TEMP，拷到任何 Windows 电脑都能直接双击运行。
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--name", APP_NAME,
        "--icon", ICON,
        "--distpath", DIST,
        "--workpath", BUILD,
        "--specpath", HERE,
        os.path.join(HERE, "main.py"),
    ]
    print(" ".join(cmd))
    code = subprocess.call(cmd, env=env)
    if code != 0:
        print("打包失败，退出码", code)
        sys.exit(code)

    app_dir = os.path.join(DIST, APP_NAME)
    exe = os.path.join(app_dir, APP_NAME + ".exe")
    if not os.path.exists(exe):
        print("未找到产物，请检查上面的日志。")
        sys.exit(1)

    # 打一个 zip，方便拷到别的电脑
    zip_path = os.path.join(DIST, APP_NAME + "-便携版.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app_dir):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, DIST)
                zf.write(full, rel)

    total = 0
    for root, dirs, files in os.walk(app_dir):
        for name in files:
            total += os.path.getsize(os.path.join(root, name))
    print("\n完成：")
    print("  目录版：{}  ({:.1f} MB)".format(exe, total / 1024.0 / 1024.0))
    print("  压缩包：{}  ({:.1f} MB)".format(zip_path, os.path.getsize(zip_path) / 1024.0 / 1024.0))


if __name__ == "__main__":
    run_selftest()
    build_exe()
