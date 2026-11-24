#!/usr/bin/env python3
"""
pdf_probe.py - 测试侧独立的 PDF 取证工具（仅标准库）

用途：为 M7 交付物页码回归测试提供一份**不依赖被测脚本**的 PDF 逐页文本提取与
正文页码定位实现。测试用它独立核算「标题在 PDF 正文中的真实页码」，再与被测
toc_two_pass.py / delivery_readback.py 的结果比对，避免校验器与生成器共享同一
错误假设而自证清白。

注意：本模块刻意独立实现，不从 src/scripts 导入任何函数。
"""

import re
import xml.sax.saxutils as saxutils
import zipfile
import zlib
from typing import Dict, List, Optional, Tuple

_OBJ_RE = re.compile(rb"(\d+)\s+0\s+obj\s*(.*?)endobj", re.DOTALL)
_LEADER_RE = re.compile(r"\.{5,}\s*\d{1,4}")


def _stream(objects, body):
    """按 /Length 精确取 stream 字节（支持 Length 为间接对象）。"""
    marker = re.search(rb"stream\r?\n", body)
    if not marker:
        return None
    start = marker.end()
    ref = re.search(rb"/Length\s+(\d+)\s+0\s+R", body)
    if ref:
        holder = objects.get(int(ref.group(1)), b"")
        num = re.match(rb"\s*(\d+)", holder)
        if not num:
            return None
        size = int(num.group(1))
    else:
        direct = re.search(rb"/Length\s+(\d+)\b", body)
        if not direct:
            return None
        size = int(direct.group(1))
    data = body[start:start + size]
    return data if len(data) == size else None


def _inflate(objects, body):
    raw = _stream(objects, body)
    if raw is None:
        return None
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def extract_page_texts(pdf_path: str) -> Dict[int, str]:
    """返回 {物理页号: 页面文本}。"""
    with open(pdf_path, "rb") as fh:
        blob = fh.read()
    objects = {int(m.group(1)): m.group(2) for m in _OBJ_RE.finditer(blob)}

    # ToUnicode CMap -> 字符表
    cmaps: Dict[int, Dict[str, str]] = {}
    for oid, body in objects.items():
        cm = _inflate(objects, body)
        if not cm or b"begincmap" not in cm:
            continue
        table: Dict[str, str] = {}
        for block in re.finditer(rb"beginbfchar(.*?)endbfchar", cm, re.DOTALL):
            for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", block.group(1)):
                try:
                    table[src.decode("ascii").upper()] = bytes.fromhex(dst.decode("ascii")).decode("utf-16-be")
                except Exception:
                    pass
        for block in re.finditer(rb"beginbfrange(.*?)endbfrange", cm, re.DOTALL):
            inp = block.group(1)
            for lo, hi, dst0 in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", inp):
                width = len(lo)
                start = int(lo, 16)
                stop = int(hi, 16)
                base = int(dst0, 16)
                for delta in range(stop - start + 1):
                    key = f"{start + delta:0{width}X}"
                    try:
                        table[key] = (base + delta).to_bytes(2, "big").decode("utf-16-be")
                    except Exception:
                        pass
        cmaps[oid] = table

    # Font 对象 -> CMap
    font_cmap: Dict[int, Dict[str, str]] = {}
    for oid, body in objects.items():
        if b"/Type/Font" in body or b"/Type /Font" in body:
            m = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
            if m and int(m.group(1)) in cmaps:
                font_cmap[oid] = cmaps[int(m.group(1))]

    # 资源名 -> 字符表
    named: Dict[str, Dict[str, str]] = {}
    for body in objects.values():
        for name, ref in re.findall(rb"/(\w+)\s+(\d+)\s+0\s+R", body):
            target = int(ref)
            if target in font_cmap:
                named[name.decode("ascii")] = font_cmap[target]

    # 页面顺序
    page_ids: List[int] = []
    for body in objects.values():
        if re.search(rb"/Type\s*/Pages\b", body):
            kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.DOTALL)
            if kids:
                page_ids = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", kids.group(1))]
                break
    if not page_ids:
        page_ids = [
            oid for oid, body in objects.items()
            if re.search(rb"/Type\s*/Page\b", body) and not re.search(rb"/Type\s*/Pages\b", body)
        ]

    result: Dict[int, str] = {}
    for idx, pid in enumerate(page_ids, start=1):
        page_body = objects.get(pid, b"")
        chars: List[str] = []
        for cid in re.findall(rb"/Contents\s+(\d+)\s+0\s+R", page_body):
            data = _inflate(objects, objects.get(int(cid), b""))
            if data is None:
                continue
            text = data.decode("latin1", errors="replace")
            current = "F1"
            for token in re.findall(r"(/\w+\s+\d+(?:\.\d+)?\s+Tf|<[0-9A-Fa-f]+>\s*Tj|\[.*?\]\s*TJ)", text, re.DOTALL):
                if "Tf" in token:
                    nm = re.search(r"/(\w+)", token)
                    if nm:
                        current = nm.group(1)
                    continue
                cmap = named.get(current, {})
                if "Tj" in token:
                    hm = re.search(r"<([0-9A-Fa-f]+)>", token)
                    if hm:
                        h = hm.group(1).upper()
                        chars.extend(cmap.get(h[k:k + 2], "") for k in range(0, len(h), 2))
                elif "TJ" in token:
                    for sub in re.findall(r"<([0-9A-Fa-f]+)>", token):
                        h = sub.upper()
                        chars.extend(cmap.get(h[k:k + 2], "") for k in range(0, len(h), 2))
        result[idx] = "".join(chars)
    return result


def toc_page_numbers(page_texts: Dict[int, str]) -> List[int]:
    """从第 1 页起连续识别目录页（含 >=2 条点前导页码行）。"""
    pages: List[int] = []
    for number in range(1, len(page_texts) + 1):
        if len(_LEADER_RE.findall(page_texts.get(number, ""))) >= 2:
            pages.append(number)
        else:
            break
    if pages and len(pages) == len(page_texts):
        pages = pages[:-1]
    return pages


def locate_body_pages(titles: List[str], page_texts: Dict[int, str], body_start: int) -> Tuple[Dict[str, int], List[str]]:
    """定位标题在正文中的真实页码：正文区域首次出现，搜索下界单调不减。"""
    found: Dict[str, int] = {}
    missing: List[str] = []
    floor = body_start
    last = max(page_texts) if page_texts else 0
    for title in titles:
        hit: Optional[int] = None
        for number in range(floor, last + 1):
            if title in page_texts.get(number, ""):
                hit = number
                break
        if hit is None:
            missing.append(title)
            continue
        found[title] = hit
        floor = hit
    return found, missing


def read_docx_toc(docx_path: str) -> List[Tuple[str, Optional[int]]]:
    """读取 docx 中 TOC 段落的 (标题, 页码) 序列。"""
    with zipfile.ZipFile(docx_path, "r") as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    entries: List[Tuple[str, Optional[int]]] = []
    for para in re.findall(r'<w:p>\s*<w:pPr><w:pStyle w:val="TOC\d"/></w:pPr>.*?</w:p>', xml, re.DOTALL):
        t = re.search(r"<w:r><w:t>(.*?)</w:t></w:r>\s*<w:r><w:tab/></w:r>", para)
        p = re.search(r"<w:tab/></w:r>\s*<w:r><w:t>(\d+)</w:t></w:r>", para)
        if t:
            entries.append((saxutils.unescape(t.group(1)).strip(), int(p.group(1)) if p else None))
    return entries


def rewrite_docx_replace(docx_path: str, old: str, new: str) -> int:
    """在 docx 的 word/document.xml 上做一次确定性字符串替换，返回替换次数。"""
    with zipfile.ZipFile(docx_path, "r") as zf:
        parts = {name: zf.read(name) for name in zf.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    count = xml.count(old)
    if count:
        parts["word/document.xml"] = xml.replace(old, new).encode("utf-8")
        with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(parts):
                info = zipfile.ZipInfo(filename=name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, parts[name])
    return count


def insert_toc_entry(docx_path: str, title: str, page: int) -> None:
    """在 docx 目录区插入一条目录项（用于构造「目录有、正文无」的阴性用例）。"""
    with zipfile.ZipFile(docx_path, "r") as zf:
        parts = {name: zf.read(name) for name in zf.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    marker = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    entry = (
        '<w:p>\n      <w:pPr><w:pStyle w:val="TOC1"/></w:pPr>\n'
        f'      <w:r><w:t>{saxutils.escape(title)}</w:t></w:r>\n'
        '      <w:r><w:tab/></w:r>\n'
        f'      <w:r><w:t>{page}</w:t></w:r>\n    </w:p>\n    '
    )
    assert marker in xml, "page-break marker not found in document.xml"
    xml = xml.replace(marker, entry + marker, 1)
    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(parts):
            info = zipfile.ZipInfo(filename=name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, parts[name])
