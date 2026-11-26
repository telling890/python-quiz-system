# -*- coding: utf-8 -*-
"""不依赖 PyMuPDF 的 PDF 书签（outline）读取。

为什么需要它：文档目录的页码是两遍生成的——先用占位页码排版、转成 PDF、
从 PDF 书签里量出真实页码，再回填重排。原来那一步用 PyMuPDF（fitz），
而 fitz 不是本项目运行时的依赖，换台机器就卡住。这里用纯标准库把
「书签 → 页码」读出来，形状与 fitz.get_toc() 一致：

    [(level, title, page), ...]

只处理 LibreOffice / Word 导出的常见结构（经典 xref、无对象流）；
遇到对象流（/ObjStm）会直接抛 NotImplementedError，让调用方回退到 fitz。
"""

import re

RE_OBJ = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")
RE_REF = re.compile(rb"(\d+)\s+(\d+)\s+R")
RE_TITLE = re.compile(rb"/Title\s*(\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>)")
RE_DEST = re.compile(rb"/Dest\s*\[\s*(\d+)\s+\d+\s+R")
RE_GO_TO = re.compile(rb"/S\s*/GoTo\b")
RE_FIRST = re.compile(rb"/First\s+(\d+)\s+\d+\s+R")
RE_NEXT = re.compile(rb"/Next\s+(\d+)\s+\d+\s+R")
RE_KIDS = re.compile(rb"/Kids\s*\[(.*?)\]", re.S)


def _objects(data):
    """把 "N G obj ... endobj" 全部读进来：{对象号: 内容字节}"""
    out = {}
    for m in RE_OBJ.finditer(data):
        num = int(m.group(1))
        end = data.find(b"endobj", m.end())
        out[num] = data[m.end():end if end != -1 else len(data)]
    return out


def _decode_text(raw):
    """PDF 字符串 → str：支持 (字面量) 与 <十六进制>（CJK 一般是 UTF-16BE）"""
    raw = raw.strip()
    if raw.startswith(b"<"):
        hex_text = re.sub(rb"\s+", b"", raw[1:-1])
        if len(hex_text) % 2:
            hex_text += b"0"
        blob = bytes.fromhex(hex_text.decode("ascii", "replace"))
    else:
        blob = raw[1:-1]
        blob = (blob.replace(rb"\(", b"(").replace(rb"\)", b")")
                    .replace(rb"\\", b"\\"))
    if blob.startswith(b"\xfe\xff"):
        return blob[2:].decode("utf-16-be", "replace")
    if blob.startswith(b"\xff\xfe"):
        return blob[2:].decode("utf-16-le", "replace")
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("latin-1", "replace")


def _catalog(objs):
    """找文档目录（/Root 指向的对象）"""
    for num, body in objs.items():
        if b"/Type" in body and b"/Catalog" in body:
            return num, body
    raise ValueError("找不到 /Catalog：可能不是标准 PDF")


def _page_order(objs, catalog_body):
    """按 /Pages 树的 /Kids 顺序列出页面对象号"""
    ref = re.search(rb"/Pages\s+(\d+)\s+\d+\s+R", catalog_body)
    if not ref:
        raise ValueError("找不到 /Pages 根节点")
    order, stack = [], [int(ref.group(1))]
    while stack:
        num = stack.pop(0)
        body = objs.get(num, b"")
        kids = RE_KIDS.search(body)
        if kids:
            for m in RE_REF.finditer(kids.group(1)):
                stack.append(int(m.group(1)))
        elif b"/Page" in body:
            order.append(num)
    return order


def _outline_items(objs, catalog_body):
    """遍历 /Outlines 树，产出 (层级, 标题, 目标页对象号)。

    PDF 的书签是一棵树：根 → /First 是第一个一级项，一级项之间用 /Next 串，
    每个一级项下面还可以有 /First → 自己的子项。所以要递归走，不能只跟着 /Next。
    """
    head = re.search(rb"/Outlines\s+(\d+)\s+\d+\s+R", catalog_body)
    if not head:
        return []
    root_body = objs.get(int(head.group(1)), b"")
    first = RE_FIRST.search(root_body)
    if not first:
        return []

    items = []

    def walk(num, level):
        while num:
            body = objs.get(num, b"")
            title = RE_TITLE.search(body)
            dest = RE_DEST.search(body)
            page_ref = int(dest.group(1)) if dest else None
            if page_ref is None and RE_GO_TO.search(body):
                inner = re.search(rb"/D\s*\[\s*(\d+)\s+\d+\s+R", body)
                if inner:
                    page_ref = int(inner.group(1))
            if title:
                items.append((level, _decode_text(title.group(1)), page_ref))

            child = RE_FIRST.search(body)
            if child:
                walk(int(child.group(1)), level + 1)
            nxt = RE_NEXT.search(body)
            num = int(nxt.group(1)) if nxt else 0

    walk(int(first.group(1)), 1)
    return items


def outline_of(path):
    """读 PDF 书签，返回 [(level, title, page)]；page 为 1 起的页码。"""
    with open(path, "rb") as f:
        data = f.read()
    if b"/ObjStm" in data:
        raise NotImplementedError("PDF 用了对象流，请改用 PyMuPDF 读取书签")
    objs = _objects(data)
    _num, catalog_body = _catalog(objs)
    pages = {num: i + 1 for i, num in enumerate(_page_order(objs, catalog_body))}

    result = []
    for level, title, page_ref in _outline_items(objs, catalog_body):
        if page_ref is None or page_ref not in pages:
            continue
        result.append((level, title, pages[page_ref]))
    return result


def page_count_of(path):
    with open(path, "rb") as f:
        data = f.read()
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(p, "→", page_count_of(p), "页")
        for level, title, page in outline_of(p):
            print("   {:<40} p{}".format(title, page))
