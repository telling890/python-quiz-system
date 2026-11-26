# -*- coding: utf-8 -*-
"""量页码：把「标题 -> 页码」映射写出来，供第二轮构建回填目录。

用法：
    python docs/build_toc_map.py --toc docs/_toc --pdf docs/_pdf1 --out docs/_pages

原理：第一轮先用占位页码生成 docx 并转成 PDF，此时版面与最终版一致。
docx 里的一二级标题用的是 Word 的 Heading 样式，LibreOffice 导出 PDF 时
会生成书签（outline），书签里带页码——直接读书签即可，比在正文里
匹配文字可靠得多（中文标题在 PDF 里常被拆成单字、顺序也会乱）。

读 PDF 书签需要 PyMuPDF（fitz）；没装 fitz 时自动改用本目录的
pdf_outline.py（纯标准库，实测与 fitz 结果一致），所以这条流水线
在任何只装了 python-docx / python-pptx 的机器上都能跑。
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:                      # 有 fitz 就用 fitz
    import fitz
except ImportError:       # 没装也能跑
    fitz = None

import pdf_outline

DOCS = [
    ("req", "1-需求说明书"),
    ("design", "2-设计文档"),
    ("test", "3-测试报告"),
    ("report", "5-项目汇报"),
]


def norm(s):
    return "".join(s.split())


def build_pages(outline, page_count, headings):
    """用 PDF 书签建立「标题 -> 页码」，并核对与标题清单是否一一对应。"""
    bookmark = {}
    for _level, title, page in outline:
        key = norm(title)
        if key and key not in bookmark:
            bookmark[key] = page

    pages = {}
    missing = []
    for item in headings:
        key = norm(item["text"])
        if key in bookmark:
            pages[item["text"]] = bookmark[key]
        else:
            missing.append(item["text"])
    return pages, missing, len(outline)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toc", required=True, help="标题清单目录")
    ap.add_argument("--pdf", required=True, help="第一轮 PDF 目录")
    ap.add_argument("--out", required=True, help="页码 JSON 输出目录")
    args = ap.parse_args()

    if not os.path.isdir(args.out):
        os.makedirs(args.out)

    print("读书签用：{}".format("PyMuPDF" if fitz else "pdf_outline.py（纯标准库）"))

    for stem, name in DOCS:
        toc_path = os.path.join(args.toc, stem + ".json")
        pdf_path = os.path.join(args.pdf, name + ".pdf")
        if not (os.path.exists(toc_path) and os.path.exists(pdf_path)):
            print("跳过 {}：缺少标题清单或 PDF".format(stem))
            continue

        with open(toc_path, encoding="utf-8") as f:
            headings = json.load(f)

        if fitz:
            pdf = fitz.open(pdf_path)
            outline = pdf.get_toc()
            page_count = pdf.page_count
            pdf.close()
        else:
            outline = pdf_outline.outline_of(pdf_path)
            page_count = pdf_outline.page_count_of(pdf_path)

        pages, missing, n_bookmarks = build_pages(outline, page_count, headings)
        out_path = os.path.join(args.out, stem + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=1)

        print("{:6s} {}/{} 个标题定位成功（书签 {} 条，PDF {} 页）".format(
            stem, len(pages), len(headings), n_bookmarks, page_count))
        if missing:
            print("      未定位：{}".format("、".join(missing)))


if __name__ == "__main__":
    sys.exit(main())
