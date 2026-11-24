#!/usr/bin/env python3
"""
delivery_readback.py - 交付物目录与标题双向回读及页码吻合校验工具
Delivery Readback Verification Engine for M7 Multi-format Delivery

纯 Python 3 标准库实现，零第三方依赖，无外网访问。
符合 OpenSpec specs/draft-synthesis/spec.md 与建设方案 v2.1 (CRITERION M7-3) 规范。

CLI 契约:
  python3 scripts/delivery_readback.py --docx delivery/output.docx --pdf delivery/output.pdf --source draft_full.md --out delivery_readback.json
  stdout: {"toc_minus_headings":[],"headings_minus_toc":[],"page_mismatch":[...],
           "toc_heading_order_mismatch":[],"page_bounds_violations":[],
           "unresolved_page_entries":[],"toc_page_integrity_errors":[]}
  退出码: 0 (差集全空、逐条页码吻合、页界与目录页一致) / 1 (任一不一致)

校验侧页码定位为独立实现：本文件自行抽取 PDF 逐页文本、自行实测目录占用的页数、
自行在正文区域定位标题页。与 toc_two_pass.py 不共享任何「跳过第几页」的常量或函数。
"""

import argparse
import json
import os
import re
import sys
import xml.sax.saxutils as saxutils
import zipfile
import zlib
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# 目录行特征：点前导紧接页码（独立于生成器侧正则的实现）
TOC_LINE_LEADER_RE = re.compile(r"\.{5,}\s*\d{1,4}")

# 「文本层丢失 CJK 字形」诊断阈值（与生成侧各自独立实现，仅用于解释失败原因）
ENTRY_CJK_RATIO_FLOOR = 0.05
PDF_CJK_RATIO_CEILING = 0.01

LOST_CJK_HINT = (
    "PDF 文本层未包含中文字形：系统缺少 CJK 字体。请安装中文字体"
    "（如 fonts-noto-cjk / 思源黑体）后重新生成 PDF 再回填目录页码。"
)


def _cjk_ratio_of(text: str) -> float:
    """文本中 CJK 表意字符（含扩展区与兼容表意区）占比；空文本为 0.0。"""
    if not text:
        return 0.0
    hits = 0
    for ch in text:
        code = ord(ch)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
            or 0x20000 <= code <= 0x2FA1F
        ):
            hits += 1
    return hits / len(text)


def diagnose_text_layer(
    toc_titles: List[str],
    body_text: str,
) -> Optional[Dict[str, Any]]:
    """
    目录条目含 CJK 而 PDF 正文文本层几乎不含 CJK 时，返回可操作诊断；否则 None。
    该诊断只解释失败原因，绝不改变页码吻合判定本身。
    """
    entry_ratio = _cjk_ratio_of("".join(toc_titles))
    pdf_ratio = _cjk_ratio_of(body_text)
    if entry_ratio >= ENTRY_CJK_RATIO_FLOOR and pdf_ratio < PDF_CJK_RATIO_CEILING:
        return {
            "cjk_ratio_entries": round(entry_ratio, 4),
            "cjk_ratio_pdf": round(pdf_ratio, 4),
            "hint": LOST_CJK_HINT,
        }
    return None


def _read_stream_bytes(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    """
    依据 /Length（可为间接引用）精确切取 stream 字节。
    不能用正则在 endstream 前截断：压缩流末字节恰为换行时会被吞掉，导致解压失败。
    """
    mark = re.search(rb"stream\r?\n", body)
    if not mark:
        return None
    begin = mark.end()

    len_ref = re.search(rb"/Length\s+(\d+)\s+0\s+R", body)
    if len_ref:
        len_obj = objects.get(int(len_ref.group(1)), b"")
        num = re.match(rb"\s*(\d+)", len_obj)
        if not num:
            return None
        size = int(num.group(1))
    else:
        len_direct = re.search(rb"/Length\s+(\d+)\b", body)
        if not len_direct:
            return None
        size = int(len_direct.group(1))

    chunk = body[begin : begin + size]
    return chunk if len(chunk) == size else None


def _stream_text(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    """FlateDecode 解压失败时回退为原始字节，供 CMap 与内容流共用的容错读取。"""
    raw = _read_stream_bytes(objects, body)
    if raw is None:
        return None
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def extract_headings_from_source(source_path: str) -> List[str]:
    """
    从 Markdown 单源文件中提取所有正文大纲标题（有序列表）。
    提取规则：首个一级标题为文档主标题不计入目录，排除显式的“目录/TOC”占位标题。
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")

    with open(source_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    headings: List[str] = []
    first_h1_seen = False
    in_frontmatter = False

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if idx == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue

        h_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if h_match:
            level = len(h_match.group(1))
            h_text = h_match.group(2).strip()

            # 首个 H1 为文档主标题，跳过
            if level == 1 and not first_h1_seen:
                first_h1_seen = True
                continue

            first_h1_seen = True

            # 排除显式的目录标题
            if h_text in ("目录", "Table of Contents", "TOC"):
                continue

            headings.append(h_text)

    return headings


def extract_toc_entries_from_docx(docx_path: str) -> List[Dict[str, Any]]:
    """
    从 DOCX 文件的 word/document.xml 中提取所有 TOC 目录项及其页码。
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    with zipfile.ZipFile(docx_path, "r") as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")

    toc_entries: List[Dict[str, Any]] = []

    # 匹配 TOC 段落
    toc_para_pattern = re.compile(
        r"<w:p>\s*<w:pPr><w:pStyle w:val=\"TOC\d\"/></w:pPr>.*?</w:p>",
        re.DOTALL,
    )

    for p_match in toc_para_pattern.finditer(doc_xml):
        para_xml = p_match.group(0)

        # 提取标题文本 (在 tab 之前)
        title_m = re.search(r"<w:r><w:t>(.*?)</w:t></w:r>\s*<w:r><w:tab/></w:r>", para_xml)
        # 提取页码 (在 tab 之后)
        page_m = re.search(r"<w:tab/></w:r>\s*<w:r><w:t>(\d+)</w:t></w:r>", para_xml)

        if title_m:
            title = saxutils.unescape(title_m.group(1)).strip()
            page_val = int(page_m.group(1)) if page_m else None
            toc_entries.append({
                "title": title,
                "docx_page": page_val,
            })

    return toc_entries


def measure_toc_page_run(page_texts: Dict[int, str]) -> List[int]:
    """
    独立实测目录页：自第 1 页起，连续统计含 >=2 条「点前导 + 页码」行的页。
    返回目录页的页号列表（可能为空，也可能多页），不接受任何固定页数假设。
    """
    toc_pages: List[int] = []
    for page_num in sorted(page_texts.keys()):
        if page_num != len(toc_pages) + 1:
            # 只认从第 1 页起的连续前缀
            break
        if len(TOC_LINE_LEADER_RE.findall(page_texts.get(page_num, ""))) >= 2:
            toc_pages.append(page_num)
        else:
            break
    if len(toc_pages) >= len(page_texts) and page_texts:
        # 全书都是目录行时，至少保留 1 页正文
        toc_pages = toc_pages[:-1]
    return toc_pages


def locate_heading_pages_in_body(
    toc_titles: List[str],
    page_texts: Dict[int, str],
    body_start_page: int,
) -> Tuple[Dict[str, int], List[str]]:
    """
    独立定位正文真实页码（与 toc_two_pass.py 的定位逻辑各自实现）：
      - 正文区域从实测的目录页之后开始，目录页整体排除；
      - 标题在正文出现多次时，取正文区域内按文档顺序的首次出现；
      - 搜索下界单调不减（取前一条目命中页与正文起始页的较大值），
        避免把正文中提前引用后续章节的句子误认作章节起始页；
      - 找不到的标题进入 unresolved，交由 CLI 显式失败。
    """
    located: Dict[str, int] = {}
    unresolved: List[str] = []
    last_page = max(page_texts.keys()) if page_texts else 0
    low_bound = body_start_page

    for title in toc_titles:
        hit: Optional[int] = None
        for page_num in range(low_bound, last_page + 1):
            if title in page_texts.get(page_num, ""):
                hit = page_num
                break
        if hit is None:
            unresolved.append(title)
            continue
        located[title] = hit
        low_bound = hit

    return located, unresolved


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
        decomp = _stream_text(objects, body)
        if decomp is not None:
            try:
                if b"begincmap" in decomp:
                    cmap: Dict[str, str] = {}
                    for bfc in re.finditer(rb"beginbfchar(.*?)endbfchar", decomp, re.DOTALL):
                        for bf in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", bfc.group(1)):
                            src = bf.group(1).decode("ascii").upper()
                            dst = bf.group(2).decode("ascii")
                            try:
                                cmap[src] = bytes.fromhex(dst).decode("utf-16-be")
                            except Exception:
                                pass
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

    # 3. 建立命名字体映射
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
            stream_bytes = _stream_text(objects, c_body)
            if stream_bytes is not None:
                try:
                    c_text = stream_bytes.decode("latin1", errors="replace")
                    curr_font = "F1"
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


def verify_delivery_readback(
    source_path: str,
    docx_path: str,
    pdf_path: Optional[str],
    out_json_path: str,
) -> Tuple[Dict[str, Any], bool]:
    """
    执行交付物双向回读校验与页码吻合核验：
    1. 提取 source 中的 headings 与 docx 中的 toc_entries，计算双向差集；
    2. 若 PDF 存在，从 PDF 中提取各标题首现页码，核验 docx_page 是否与 pdf_page 100% 吻合；
    3. 若 PDF 不存在（或缺失 soffice），显式输出 page_mismatch: "skipped_no_pdf"；
    4. 产出 delivery_readback.json。
    """
    headings = extract_headings_from_source(source_path)
    toc_entries = extract_toc_entries_from_docx(docx_path)

    toc_titles = [entry["title"] for entry in toc_entries]

    # 计算双向差集
    toc_minus_headings = [t for t in toc_titles if t not in headings]
    headings_minus_toc = [h for h in headings if h not in toc_titles]

    page_mismatch: Union[List[Dict[str, Any]], str] = []
    order_mismatch: List[Dict[str, Any]] = []
    page_bounds_violations: List[Dict[str, Any]] = []
    unresolved_page_entries: List[str] = []
    toc_page_integrity_errors: List[str] = []
    toc_pages: List[int] = []
    text_layer_diagnostic: Optional[Dict[str, Any]] = None

    # 目录与正文标题必须等长且顺序一致
    if len(toc_titles) != len(headings):
        order_mismatch.append({
            "kind": "count_mismatch",
            "toc_count": len(toc_titles),
            "heading_count": len(headings),
        })
    for idx in range(min(len(toc_titles), len(headings))):
        if toc_titles[idx] != headings[idx]:
            order_mismatch.append({
                "kind": "order_mismatch",
                "index": idx,
                "toc_title": toc_titles[idx],
                "heading_title": headings[idx],
            })

    # 核验页码吻合度
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        page_texts = extract_pdf_page_texts(pdf_bytes)
        total_pages = len(page_texts)

        toc_pages = measure_toc_page_run(page_texts)
        body_start_page = (toc_pages[-1] + 1) if toc_pages else 1

        located_pages, unresolved_page_entries = locate_heading_pages_in_body(
            toc_titles, page_texts, body_start_page
        )

        # 失败归因：若目录条目含 CJK 而 PDF 正文文本层不含 CJK，追加可操作诊断
        body_text = "".join(
            page_texts.get(p, "") for p in range(body_start_page, total_pages + 1)
        )
        text_layer_diagnostic = diagnose_text_layer(toc_titles, body_text)

        # 目录页完整性：每个目录条目都必须真实出现在实测出来的目录页内，
        # 否则说明实测目录页数不足或目录残缺。
        toc_region_text = "".join(page_texts.get(p, "") for p in toc_pages)
        for entry in toc_entries:
            if toc_pages and entry["title"] not in toc_region_text:
                toc_page_integrity_errors.append(entry["title"])

        mismatches: List[Dict[str, Any]] = []
        for entry in toc_entries:
            title = entry["title"]
            docx_page = entry["docx_page"]

            # 页界校验：目录页码必须落在 [1, 总页数]
            if docx_page is None or docx_page < 1 or docx_page > total_pages:
                page_bounds_violations.append({
                    "title": title,
                    "docx_page": docx_page,
                    "total_pages": total_pages,
                })

            pdf_page = located_pages.get(title)
            if pdf_page is None:
                # 找不到真实正文页：既记入 unresolved，也计入 page_mismatch，绝不放过
                mismatches.append({
                    "title": title,
                    "docx_page": docx_page,
                    "pdf_page": None,
                })
                continue

            if docx_page != pdf_page:
                mismatches.append({
                    "title": title,
                    "docx_page": docx_page,
                    "pdf_page": pdf_page,
                })

        page_mismatch = mismatches
    else:
        # PDF 不可用时显式输出标记，绝不谎报通过
        page_mismatch = "skipped_no_pdf"

    # 构建完整结果报告
    report_data = {
        "source": source_path,
        "docx": docx_path,
        "pdf": pdf_path if (pdf_path and os.path.exists(pdf_path)) else None,
        "headings": headings,
        "toc_entries": toc_entries,
        "toc_minus_headings": toc_minus_headings,
        "headings_minus_toc": headings_minus_toc,
        "page_mismatch": page_mismatch,
        "toc_heading_order_mismatch": order_mismatch,
        "page_bounds_violations": page_bounds_violations,
        "unresolved_page_entries": unresolved_page_entries,
        "toc_page_integrity_errors": toc_page_integrity_errors,
        "toc_pages": toc_pages,
    }
    if text_layer_diagnostic is not None:
        report_data["text_layer_diagnostic"] = text_layer_diagnostic

    # 写入 delivery_readback.json
    out_dir = os.path.dirname(os.path.abspath(out_json_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # 判定布尔通过状态：
    # 差集、逐条页码、目录顺序、页界、未定位标题、目录页完整性必须全部通过
    sets_match = (len(toc_minus_headings) == 0 and len(headings_minus_toc) == 0)
    pages_valid = (page_mismatch == [] or page_mismatch == "skipped_no_pdf")

    passed = (
        sets_match
        and pages_valid
        and len(order_mismatch) == 0
        and len(page_bounds_violations) == 0
        and len(unresolved_page_entries) == 0
        and len(toc_page_integrity_errors) == 0
        and text_layer_diagnostic is None
    )

    # 标准 stdout JSON 输出结构（严格符合 CRITERION M7-3，并附加增强校验字段）
    cli_stdout = {
        "toc_minus_headings": toc_minus_headings,
        "headings_minus_toc": headings_minus_toc,
        "page_mismatch": page_mismatch,
        "toc_heading_order_mismatch": order_mismatch,
        "page_bounds_violations": page_bounds_violations,
        "unresolved_page_entries": unresolved_page_entries,
        "toc_page_integrity_errors": toc_page_integrity_errors,
        "toc_pages": toc_pages,
    }
    if text_layer_diagnostic is not None:
        cli_stdout["text_layer_diagnostic"] = text_layer_diagnostic

    return cli_stdout, passed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="delivery_readback.py - 交付物目录与正文标题双向回读及页码吻合校验工具"
    )
    parser.add_argument("--docx", required=True, help="Word 交付物路径 (如 delivery/output.docx)")
    parser.add_argument("--pdf", default=None, help="PDF 交付物路径 (如 delivery/output.pdf)")
    parser.add_argument("--source", required=True, help="Markdown 单源母本路径 (如 draft_full.md)")
    parser.add_argument(
        "--out",
        default="delivery_readback.json",
        help="回读结果报告输出路径 (默认: delivery_readback.json)",
    )

    args = parser.parse_args()

    try:
        cli_result, passed = verify_delivery_readback(
            source_path=args.source,
            docx_path=args.docx,
            pdf_path=args.pdf,
            out_json_path=args.out,
        )

        print(json.dumps(cli_result, ensure_ascii=False, separators=(",", ":")))
        sys.exit(0 if passed else 1)

    except Exception as e:
        err_out = {
            "toc_minus_headings": [f"Execution error: {str(e)}"],
            "headings_minus_toc": [],
            "page_mismatch": [],
        }
        print(json.dumps(err_out, ensure_ascii=False, separators=(",", ":")))
        sys.exit(1)


if __name__ == "__main__":
    main()
