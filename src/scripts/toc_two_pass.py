#!/usr/bin/env python3
"""
toc_two_pass.py - 目录两遍法页码回填工具
TOC Two-Pass Page Number Backfill Engine for M7 Multi-format Delivery

纯 Python 3 标准库实现，零第三方依赖。
第一遍由 build_docx.py 生成含目录占位的 docx；
第二遍由本工具提取 PDF 真实物理页索引，精准回填至 Word 目录条目中，保证页码绝对一致。

CLI 契约:
  python3 scripts/toc_two_pass.py delivery/output.docx delivery/output.pdf
  stdout (成功): {"toc_backfilled":true,"entries_count":N,"pages":{"标题":页码,...}} (退出码 0)
  stdout (PDF缺失): {"toc_backfilled":false,"reason":"pdf_unavailable"} (退出码 0)
  stdout (存在无法定位标题): {"toc_backfilled":false,"unresolved_toc_entries":[...]} (退出码 1)
  退出码: 0 (成功或优雅降级) / 1 (处理失败，含标题无法定位)

页码判定规则 (无任何固定页偏移)：
  1. 先从 PDF 逐页文本中识别「目录实际占用的页数」：从第 1 页起，连续满足
     「该页包含 >= 2 条点前导 + 页码（形如 ......12）」的页，视为目录页；
     目录页数 toc_pages 由实测得出，绝不假定为 1 页。
  2. 正文区域 = 第 toc_pages+1 页至末页。每个目录条目标题只在正文区域内定位。
  3. 同一标题在正文多次出现时，取「按文档顺序、正文区域内首次出现」所在页，
     并施加单调下界（后续条目的搜索起点不低于前一条目命中页），以排除正文
     中对后续章节的提前引用。该判定规则与 delivery_readback.py 各自实现、互不共享。
  4. 任一目录条目标题在正文区域找不到真实页，显式报错退出码 1，绝不猜测。
"""

import argparse
import json
import os
import re
import sys
import xml.sax.saxutils as saxutils
import zipfile
import zlib
from typing import Any, Dict, List, Optional, Set, Tuple

# 点前导 + 页码：目录行的典型形态（如 "第一章 ........ 12"）
DOT_LEADER_PAGE_RE = re.compile(r"\.{5,}\s*\d{1,4}")


def extract_stream_payload(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    """
    按 /Length（直接值或间接对象）精确截取 PDF stream 原始字节。
    直接对 stream...endstream 做正则截取会丢失压缩流末尾恰好落在 \\r 或 \\n 的字节，
    导致 zlib 解压报 "incomplete or truncated stream"（本仓库真实 PDF 第 28 页即如此）。
    """
    m = re.search(rb"stream\r?\n", body)
    if not m:
        return None
    start = m.end()

    indirect = re.search(rb"/Length\s+(\d+)\s+0\s+R", body)
    if indirect:
        length_body = objects.get(int(indirect.group(1)), b"")
        nm = re.match(rb"\s*(\d+)", length_body)
        if not nm:
            return None
        length = int(nm.group(1))
    else:
        direct = re.search(rb"/Length\s+(\d+)\b", body)
        if not direct:
            return None
        length = int(direct.group(1))

    payload = body[start : start + length]
    if len(payload) < length:
        return None
    return payload


def decode_stream(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    """解压（FlateDecode）或原样返回 stream 内容。"""
    payload = extract_stream_payload(objects, body)
    if payload is None:
        return None
    try:
        return zlib.decompress(payload)
    except Exception:
        return payload


def extract_pdf_page_texts(pdf_bytes: bytes) -> Dict[int, str]:
    """
    纯 Python 3 标准库无依赖 PDF 页面文本解析器：
    解析 PDF 对象、ToUnicode CMaps、字体引用及内容流，提取各页完整文本。
    """
    obj_pattern = re.compile(rb"(\d+)\s+0\s+obj\s*(.*?)endobj", re.DOTALL)
    objects = {int(m.group(1)): m.group(2) for m in obj_pattern.finditer(pdf_bytes)}

    # 1. 解析 ToUnicode CMaps
    cmaps: Dict[int, Dict[str, str]] = {}
    for obj_id, body in objects.items():
        decomp = decode_stream(objects, body)
        if decomp is not None:
            try:
                if b"begincmap" in decomp:
                    cmap: Dict[str, str] = {}
                    # 解析 beginbfchar ... endbfchar
                    for bfc in re.finditer(rb"beginbfchar(.*?)endbfchar", decomp, re.DOTALL):
                        for bf in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", bfc.group(1)):
                            src = bf.group(1).decode("ascii").upper()
                            dst = bf.group(2).decode("ascii")
                            try:
                                cmap[src] = bytes.fromhex(dst).decode("utf-16-be")
                            except Exception:
                                pass
                    # 解析 beginbfrange ... endbfrange
                    for bfc in re.finditer(rb"beginbfrange(.*?)endbfrange", decomp, re.DOTALL):
                        for bfr in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", bfc.group(1)):
                            s1 = int(bfr.group(1), 16)
                            s2 = int(bfr.group(2), 16)
                            d1 = int(bfr.group(3), 16)
                            w = len(bfr.group(1))
                            for offset in range(s2 - s1 + 1):
                                src = f"{s1 + offset:0{w}X}"
                                dst_bytes = (d1 + offset).to_bytes(2, "big")
                                try:
                                    cmap[src] = dst_bytes.decode("utf-16-be")
                                except Exception:
                                    pass
                    cmaps[obj_id] = cmap
            except Exception:
                pass

    # 2. 建立 Font -> ToUnicode CMap 映射
    font_cmaps: Dict[int, Dict[str, str]] = {}
    for obj_id, body in objects.items():
        if b"/Type/Font" in body or b"/Type /Font" in body:
            to_uni = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
            if to_uni:
                u_id = int(to_uni.group(1))
                if u_id in cmaps:
                    font_cmaps[obj_id] = cmaps[u_id]

    # 3. 建立资源字典中的命名字体映射 (/F1, /F2, etc.)
    res_fonts: Dict[str, Dict[str, str]] = {}
    for obj_id, body in objects.items():
        for fm in re.finditer(rb"/(\w+)\s+(\d+)\s+0\s+R", body):
            fname = fm.group(1).decode("ascii")
            fobj = int(fm.group(2))
            if fobj in font_cmaps:
                res_fonts[fname] = font_cmaps[fobj]

    # 4. 提取页面树顺序
    page_ids: List[int] = []
    for obj_id, body in objects.items():
        if re.search(rb"/Type\s*/Pages\b", body):
            kids_m = re.search(rb"/Kids\s*\[(.*?)\]", body, re.DOTALL)
            if kids_m:
                page_ids = [int(p.group(1)) for p in re.finditer(rb"(\d+)\s+0\s+R", kids_m.group(1))]
                break

    # 兜底：若未解析到 Kids，遍历所有 /Type /Page
    if not page_ids:
        for obj_id, body in objects.items():
            if re.search(rb"/Type\s*/Page\b", body) and not re.search(rb"/Type\s*/Pages\b", body):
                page_ids.append(obj_id)

    # 5. 逐页提取文字
    page_texts: Dict[int, str] = {}
    for page_num, p_id in enumerate(page_ids, start=1):
        p_body = objects.get(p_id, b"")
        contents_m = re.findall(rb"/Contents\s+(\d+)\s+0\s+R", p_body)
        page_tokens: List[str] = []

        for c_id in contents_m:
            c_body = objects.get(int(c_id), b"")
            stream_bytes = decode_stream(objects, c_body)
            if stream_bytes is not None:
                try:
                    c_text = stream_bytes.decode("latin1", errors="replace")
                    curr_font = "F1"
                    # 匹配字体切换及文本打印操作符
                    ops = re.findall(r"(/\w+\s+\d+(?:\.\d+)?\s+Tf|<[0-9a-fA-F]+>\s*Tj|\[.*?\]\s*TJ)", c_text, re.DOTALL)
                    for tok in ops:
                        if "Tf" in tok:
                            f_m = re.search(r"/(\w+)", tok)
                            if f_m:
                                curr_font = f_m.group(1)
                        elif "Tj" in tok:
                            h_m = re.search(r"<([0-9a-fA-F]+)>", tok)
                            if h_m:
                                h = h_m.group(1).upper()
                                cmap = res_fonts.get(curr_font, {})
                                for k in range(0, len(h), 2):
                                    char = cmap.get(h[k : k + 2], "")
                                    if char:
                                        page_tokens.append(char)
                        elif "TJ" in tok:
                            cmap = res_fonts.get(curr_font, {})
                            for sub_h in re.finditer(r"<([0-9a-fA-F]+)>", tok):
                                h = sub_h.group(1).upper()
                                for k in range(0, len(h), 2):
                                    char = cmap.get(h[k : k + 2], "")
                                    if char:
                                        page_tokens.append(char)
                except Exception:
                    pass

        page_texts[page_num] = "".join(page_tokens)

    return page_texts


def detect_toc_page_count(page_texts: Dict[int, str]) -> int:
    """
    实测「目录实际占用的页数」：从第 1 页起连续统计含点前导页码行（>=2 条）的页。
    返回值即目录页数；正文起始页 = 该值 + 1。本函数不假定目录只有 1 页。
    """
    total_pages = len(page_texts)
    toc_pages = 0
    for page_num in range(1, total_pages + 1):
        if len(DOT_LEADER_PAGE_RE.findall(page_texts.get(page_num, ""))) >= 2:
            toc_pages += 1
        else:
            break
    # 防御：若整本都被判为目录页，则保留至少 1 页正文空间
    if toc_pages >= total_pages and total_pages > 0:
        toc_pages = total_pages - 1
    return toc_pages


def determine_heading_pages(
    headings: List[str],
    page_texts: Dict[int, str],
    body_start_page: int,
) -> Tuple[Dict[str, int], List[str]]:
    """
    在正文区域（第 body_start_page 页至末页）定位每个目录条目标题的真实物理页码。

    判定规则（与 delivery_readback.py 各自实现，互不共享页码推算逻辑）：
      - 正文区域严格排除实测出来的目录页；
      - 同一标题在正文多次出现时，取「按文档顺序、正文区域内首次出现」所在页；
      - 施加单调下界：后一条目的搜索起点不低于前一条目的命中页，避免把正文里
        对后续章节的提前引用误判为该章节标题的起始页；
      - 找不到即返回 unresolved，由调用方显式报错，绝不写入猜测页码。
    """
    heading_pages: Dict[str, int] = {}
    unresolved: List[str] = []
    total_pages = len(page_texts)
    floor = body_start_page

    for heading in headings:
        clean_h = heading.strip()
        matched_page: Optional[int] = None

        for page_num in range(floor, total_pages + 1):
            if clean_h in page_texts.get(page_num, ""):
                matched_page = page_num
                break

        if matched_page is None:
            unresolved.append(clean_h)
            continue

        heading_pages[clean_h] = matched_page
        floor = matched_page

    return heading_pages, unresolved


def backfill_toc_in_docx(
    docx_path: str,
    heading_pages: Dict[str, int],
) -> int:
    """
    在 docx 中更新目录项页码并重新保存。
    返回更新的目录条目数量。
    """
    with zipfile.ZipFile(docx_path, "r") as zf:
        file_map = {name: zf.read(name) for name in zf.namelist()}

    doc_xml_bytes = file_map.get("word/document.xml")
    if not doc_xml_bytes:
        raise ValueError("word/document.xml not found in DOCX file.")

    doc_xml = doc_xml_bytes.decode("utf-8")
    updated_count = 0

    # 匹配 TOC 段落结构：
    # <w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:t>标题</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>旧页码</w:t></w:r></w:p>
    def replace_toc_page(match: re.Match) -> str:
        nonlocal updated_count
        full_para = match.group(0)
        title_match = re.search(r"<w:r><w:t>(.*?)</w:t></w:r>\s*<w:r><w:tab/></w:r>", full_para)
        if title_match:
            title = title_match.group(1).strip()
            if title in heading_pages:
                new_page = heading_pages[title]
                # 替换紧跟 tab 后的页码 run
                sub_pattern = r"(<w:tab/></w:r>\s*<w:r><w:t>)\d+(</w:t></w:r>)"
                new_para, count = re.subn(sub_pattern, rf"\g<1>{new_page}\g<2>", full_para)
                if count > 0:
                    updated_count += 1
                    return new_para
        return full_para

    toc_para_pattern = re.compile(
        r"<w:p>\s*<w:pPr><w:pStyle w:val=\"TOC\d\"/></w:pPr>.*?</w:p>",
        re.DOTALL,
    )
    new_doc_xml = toc_para_pattern.sub(replace_toc_page, doc_xml)

    file_map["word/document.xml"] = new_doc_xml.encode("utf-8")

    # 确定性重写 zip
    fixed_time = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for part_name in sorted(file_map.keys()):
            zinfo = zipfile.ZipInfo(filename=part_name, date_time=fixed_time)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zinfo, file_map[part_name])

    return updated_count


def extract_headings_from_docx_toc(docx_path: str) -> List[str]:
    """从 docx 中提取既有 TOC 目录项标题列表。"""
    with zipfile.ZipFile(docx_path, "r") as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")

    headings: List[str] = []
    toc_para_pattern = re.compile(
        r"<w:p>\s*<w:pPr><w:pStyle w:val=\"TOC\d\"/></w:pPr>.*?</w:p>",
        re.DOTALL,
    )
    for p_match in toc_para_pattern.finditer(doc_xml):
        t_m = re.search(r"<w:r><w:t>(.*?)</w:t></w:r>\s*<w:r><w:tab/></w:r>", p_match.group(0))
        if t_m:
            headings.append(saxutils.unescape(t_m.group(1)).strip())

    return headings


def run_toc_two_pass(docx_path: str, pdf_path: str) -> Dict[str, Any]:
    """执行目录两遍法回填。返回结果字典；调用方据 unresolved_toc_entries 决定退出码。"""
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Input DOCX file not found: {docx_path}")

    if not os.path.exists(pdf_path):
        # PDF 不存在时优雅返回降级状态，退出码 0
        return {
            "toc_backfilled": False,
            "reason": "pdf_unavailable",
            "message": f"PDF file does not exist: {pdf_path}",
        }

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    page_texts = extract_pdf_page_texts(pdf_bytes)
    toc_headings = extract_headings_from_docx_toc(docx_path)

    toc_pages = detect_toc_page_count(page_texts)
    body_start_page = toc_pages + 1

    heading_pages, unresolved = determine_heading_pages(toc_headings, page_texts, body_start_page)

    if unresolved:
        # 严禁静默写入猜测页码：显式失败
        return {
            "toc_backfilled": False,
            "reason": "unresolved_toc_entries",
            "entries_count": len(toc_headings),
            "toc_pages": toc_pages,
            "body_start_page": body_start_page,
            "total_pages": len(page_texts),
            "unresolved_toc_entries": unresolved,
        }

    updated_count = backfill_toc_in_docx(docx_path, heading_pages)

    return {
        "toc_backfilled": True,
        "entries_count": len(toc_headings),
        "updated_count": updated_count,
        "toc_pages": toc_pages,
        "body_start_page": body_start_page,
        "total_pages": len(page_texts),
        "pages": heading_pages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="toc_two_pass.py - 目录两遍法页码回填工具"
    )
    parser.add_argument("docx", help="待回填页码的 Word 文档路径 (如 delivery/output.docx)")
    parser.add_argument("pdf", help="已导出的 PDF 文档路径 (如 delivery/output.pdf)")

    args = parser.parse_args()

    try:
        res = run_toc_two_pass(args.docx, args.pdf)
        print(json.dumps(res, ensure_ascii=False, separators=(",", ":")))
        sys.exit(0 if res.get("toc_backfilled") is True or res.get("reason") == "pdf_unavailable" else 1)
    except Exception as e:
        err_out = {"toc_backfilled": False, "error": str(e)}
        print(json.dumps(err_out, ensure_ascii=False, separators=(",", ":")))
        sys.exit(1)


if __name__ == "__main__":
    main()
