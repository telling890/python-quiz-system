# -*- coding: utf-8 -*-
"""打一个可以直接提交的源码压缩包（比赛作品用）。

为什么要单独打包：仓库里有 200 MB 的构建产物，直接右键压缩会让评委解压半天，
而且 node_modules 里可能有本机路径、pylibs 里是 Windows 专用二进制。这里只装「源码 + 文档 + 数据」。

排除：.git、node_modules、pylibs、dist（打包产物）、frontend/dist、__pycache__、
      .tmp、tmp_run、docs/submission、以及各类缓存。
保留：源码、题库、前端与后端源码、docs（含 PDF）、shots（截图）、README、LICENSE。

用法：
    python _pack_submission.py                  # 默认输出 docs/submission/源码包-v1.2.0.zip
    python _pack_submission.py --with-binary    # 额外带上 8.9 MB 的 Windows 便携版
    python _pack_submission.py --no-shots       # 不带截图（再省 ~13 MB）
    python _pack_submission.py -o D:/提交包.zip  # 指定输出位置
"""

import argparse
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.2.0"

# 目录名整段排除（出现在任意层级都跳过）
EXCLUDE_DIRS = {
    ".git", ".github_cache", "node_modules", "pylibs", "dist", "__pycache__",
    ".tmp", "tmp_run", "build", ".venv", "venv", ".idea", ".vscode",
    ".pytest_cache", "submission",  # docs/submission 放的是本脚本的产物，别再套娃
}
# 文件名/后缀排除
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "error.log", ".coverage"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".log", ".zip", ".7z", ".rar",
                  ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3"}
# 单独处理的例外：downloads 里的便携版只在 --with-binary 时带上
BINARY_DIR = "downloads"
SHOTS_DIR = "shots"


def human(n):
    return "{:.1f} MB".format(n / 1024.0 / 1024.0) if n >= 1024 * 1024 else "{:.0f} KB".format(n / 1024.0)


def collect(root, with_binary, with_shots):
    """返回 [(绝对路径, 包内相对路径)]，以及被跳过的统计。"""
    items = []
    skipped = []

    def skip(rel, size=0, reason=""):
        skipped.append((rel, size, reason))

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        parts = [] if rel_dir == "." else rel_dir.split(os.sep)

        # 目录级过滤：从 dirnames 里删掉，os.walk 就不会进去
        keep = []
        for d in dirnames:
            rel = os.path.join(rel_dir, d) if parts else d
            if d in EXCLUDE_DIRS:
                skip(rel, _dir_size(os.path.join(dirpath, d)), "构建产物/依赖目录")
                continue
            if d == BINARY_DIR and not with_binary:
                skip(rel, _dir_size(os.path.join(dirpath, d)), "二进制包（加 --with-binary 才带）")
                continue
            if d == SHOTS_DIR and not with_shots:
                skip(rel, _dir_size(os.path.join(dirpath, d)), "截图（加 --no-shots 反向控制）")
                continue
            keep.append(d)
        dirnames[:] = keep

        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if name in EXCLUDE_FILES or os.path.splitext(name)[1].lower() in EXCLUDE_SUFFIX:
                skip(rel, os.path.getsize(path), "缓存/压缩包")
                continue
            items.append((path, rel))
    return items, skipped


def _dir_size(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def build(output, with_binary, with_shots):
    items, skipped = collect(HERE, with_binary, with_shots)
    if not items:
        print("没有可打包的文件")
        return None

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    total_raw = 0
    largest = []
    root_name = "python-quiz-system-v{}".format(VERSION)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, rel in items:
            arcname = os.path.join(root_name, rel.replace(os.sep, "/"))
            zf.write(path, arcname)
            size = os.path.getsize(path)
            total_raw += size
            largest.append((size, rel))

    largest.sort(reverse=True)
    zsize = os.path.getsize(output)
    print("\n=== 打包完成 ===")
    print("输出：{}".format(output))
    print("文件：{} 个　原始 {}　压缩后 {}".format(len(items), human(total_raw), human(zsize)))

    top = {}
    for _path, rel in items:
        head = rel.split(os.sep)[0]
        top[head] = top.get(head, 0) + 1
    print("\n包内一级目录（文件数）：")
    for name in sorted(top):
        print("  {:<24} {}".format(name, top[name]))

    print("\n包内最大的 8 个文件：")
    for size, rel in largest[:8]:
        print("  {:>9}  {}".format(human(size), rel))
    if skipped:
        total_skipped = sum(s for _r, s, _w in skipped)
        print("\n跳过的目录/文件：{} 项，合计 {}".format(len(skipped), human(total_skipped)))
        for rel, size, reason in sorted(skipped, key=lambda x: -x[1])[:6]:
            print("  {:>9}  {}（{}）".format(human(size), rel, reason))
    print("\n解压后根目录名为 {}，直接打开 README.md 即可看到运行方式。".format(root_name))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="打比赛提交用的源码包")
    parser.add_argument("-o", "--output", default=os.path.join(
        HERE, "docs", "submission", "源码包-v{}.zip".format(VERSION)))
    parser.add_argument("--with-binary", action="store_true",
                        help="把 downloads/ 里的 Windows 便携版一起打进去（约 +9 MB）")
    parser.add_argument("--no-shots", action="store_true",
                        help="不打 shots/ 截图（约 -13 MB）")
    args = parser.parse_args()

    started = time.time()
    result = build(str(args.output), args.with_binary, not args.no_shots)
    if result:
        print("用时 {:.1f} 秒".format(time.time() - started))
    else:
        sys.exit(1)
