#!/usr/bin/env python3
"""
build_pdf.py - 基于系统 headless soffice 的无损转 PDF 与优雅降级工具
Lossless PDF Generation Engine with soffice Preflight and Graceful Fallback for M7

纯 Python 3 标准库实现，零第三方依赖。
若系统预装 soffice 可用，执行标准转换；若缺失，执行显式优雅降级，严禁伪造 PDF。

CLI 契约:
  python3 scripts/build_pdf.py delivery/output.docx --out delivery/output.pdf
  stdout (可用): {"pdf":true,"path":"delivery/output.pdf"} (退出码 0)
  stdout (可用但文本层丢失 CJK): {"pdf":true,"path":"...","text_layer_warning":"pdf_text_layer_lost_cjk",
                                   "text_layer_diagnostic":{"cjk_ratio_docx":X,"cjk_ratio_pdf":Y,"hint":"..."}} (退出码 0)
  stdout (缺失): {"pdf":false,"reason":"soffice_unavailable"} (退出码 0)
  stdout (错误): {"pdf":false,"error":"..."} (退出码 1)

文本层预检 [SHALL]:
  PDF 生成成功后，必须主动比对「源 docx 文本」与「生成 PDF 文本层」的 CJK 字符占比。
  若源文本含 CJK 而 PDF 文本层几乎不含 CJK（系统缺 CJK 字体导致字形丢失），
  pdf 仍为 true（文件确实生成），但必须输出 text_layer_warning=pdf_text_layer_lost_cjk
  与可操作 hint，严禁静默伪造成功。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import xml.sax.saxutils as saxutils
import zipfile
import zlib
from typing import Any, Dict, Optional

# 文本层预检阈值：源文本 CJK 占比 >= 0.05 且 PDF 文本层 < 0.01 视为字形丢失
SOURCE_CJK_RATIO_FLOOR = 0.05
PDF_CJK_RATIO_CEILING = 0.01

LOST_CJK_HINT = (
    "PDF 文本层未包含中文字形：系统缺少 CJK 字体。请安装中文字体"
    "（如 fonts-noto-cjk / 思源黑体）后重新生成 PDF 再回填目录页码。"
)


def _cjk_ratio(text: str) -> float:
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


def extract_docx_text(docx_path: str) -> str:
    """提取 docx 正文中的纯文本（word/document.xml 中所有 <w:t> 内容）。"""
    with zipfile.ZipFile(docx_path, "r") as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    return "".join(saxutils.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", doc_xml, re.DOTALL))


def _decompress_stream(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    """按 /Length（直接值或间接引用）截取 stream 并尝试 FlateDecode 解压。"""
    marker = re.search(rb"stream\r?\n", body)
    if not marker:
        return None
    start = marker.end()
    indirect = re.search(rb"/Length\s+(\d+)\s+0\s+R", body)
    if indirect:
        holder = objects.get(int(indirect.group(1)), b"")
        num = re.match(rb"\s*(\d+)", holder)
        if not num:
            return None
        size = int(num.group(1))
    else:
        direct = re.search(rb"/Length\s+(\d+)\b", body)
        if not direct:
            return None
        size = int(direct.group(1))
    raw = body[start : start + size]
    if len(raw) < size:
        return None
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def _parse_cmap(data: bytes) -> Dict[str, str]:
    """解析 ToUnicode CMap 的 bfchar / bfrange 映射。"""
    cmap: Dict[str, str] = {}
    for block in re.finditer(rb"beginbfchar(.*?)endbfchar", data, re.DOTALL):
        for pair in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", block.group(1)):
            src = pair.group(1).decode("ascii").upper()
            try:
                cmap[src] = bytes.fromhex(pair.group(2).decode("ascii")).decode("utf-16-be")
            except Exception:
                pass
    for block in re.finditer(rb"beginbfrange(.*?)endbfrange", data, re.DOTALL):
        for triple in re.finditer(
            rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", block.group(1)
        ):
            lo = int(triple.group(1), 16)
            hi = int(triple.group(2), 16)
            dst = int(triple.group(3), 16)
            width = len(triple.group(1))
            for offset in range(hi - lo + 1):
                try:
                    cmap[f"{lo + offset:0{width}X}"] = (dst + offset).to_bytes(2, "big").decode("utf-16-be")
                except Exception:
                    pass
    return cmap


def extract_pdf_text_layer(pdf_bytes: bytes) -> str:
    """提取 PDF 文本层全部可见文本；仅依赖标准库，用于生成侧 CJK 预检。"""
    obj_pattern = re.compile(rb"(\d+)\s+0\s+obj\s*(.*?)endobj", re.DOTALL)
    objects = {int(m.group(1)): m.group(2) for m in obj_pattern.finditer(pdf_bytes)}

    cmaps: Dict[int, Dict[str, str]] = {}
    for obj_id, body in objects.items():
        data = _decompress_stream(objects, body)
        if data and b"begincmap" in data:
            cmaps[obj_id] = _parse_cmap(data)

    # Font 对象 -> ToUnicode CMap
    font_cmaps: Dict[int, Dict[str, str]] = {}
    for obj_id, body in objects.items():
        if b"/Type/Font" in body or b"/Type /Font" in body:
            ref = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
            if ref and int(ref.group(1)) in cmaps:
                font_cmaps[obj_id] = cmaps[int(ref.group(1))]

    # 资源中命名字体（/F1 等）-> CMap
    res_fonts: Dict[str, Dict[str, str]] = {}
    for body in objects.values():
        for name_ref in re.finditer(rb"/(\w+)\s+(\d+)\s+0\s+R", body):
            if int(name_ref.group(2)) in font_cmaps:
                res_fonts[name_ref.group(1).decode("ascii")] = font_cmaps[int(name_ref.group(2))]

    tokens = []
    for body in objects.values():
        data = _decompress_stream(objects, body)
        if not data or b"begincmap" in data:
            continue
        content = data.decode("latin1", errors="replace")
        if "Tj" not in content and "TJ" not in content:
            continue
        current_font = "F1"
        ops = re.findall(
            r"(/\w+\s+\d+(?:\.\d+)?\s+Tf|<[0-9a-fA-F]+>\s*Tj|\[.*?\]\s*TJ)",
            content,
            re.DOTALL,
        )
        for tok in ops:
            if "Tf" in tok:
                name = re.search(r"/(\w+)", tok)
                if name:
                    current_font = name.group(1)
                continue
            cmap = res_fonts.get(current_font, {})
            hexes = re.findall(r"<([0-9a-fA-F]+)>", tok)
            for hex_str in hexes:
                upper = hex_str.upper()
                for k in range(0, len(upper), 2):
                    char = cmap.get(upper[k : k + 2])
                    if char:
                        tokens.append(char)
    return "".join(tokens)


def preflight_text_layer(docx_path: str, pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    生成后预检：源 docx 含 CJK 而 PDF 文本层不含 CJK 时返回警告诊断，否则 None。
    该预检绝不改变 pdf=true 的事实，只承载风险提示。
    """
    source_ratio = _cjk_ratio(extract_docx_text(docx_path))
    with open(pdf_path, "rb") as f:
        pdf_ratio = _cjk_ratio(extract_pdf_text_layer(f.read()))
    if source_ratio >= SOURCE_CJK_RATIO_FLOOR and pdf_ratio < PDF_CJK_RATIO_CEILING:
        return {
            "cjk_ratio_docx": round(source_ratio, 4),
            "cjk_ratio_pdf": round(pdf_ratio, 4),
            "hint": LOST_CJK_HINT,
        }
    return None


def find_soffice_binary() -> Optional[str]:
    """探测系统预装的 LibreOffice / OpenOffice 可执行命令路径。"""
    for binary_name in ["soffice", "libreoffice"]:
        path = shutil.which(binary_name)
        if path:
            return path
    return None


def convert_docx_to_pdf(docx_path: str, out_pdf_path: str) -> Dict[str, Any]:
    """调用系统 headless soffice 执行 docx 转 pdf，并处理目标文件名重定位。"""
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Input DOCX file not found: {docx_path}")

    soffice_bin = find_soffice_binary()
    if not soffice_bin:
        # 预检缺失：必须显式优雅降级，绝不可伪造 PDF 或假装成功
        return {
            "pdf": False,
            "reason": "soffice_unavailable",
            "message": "LibreOffice/soffice executable is not available in the system PATH.",
        }

    # 计算输出目录与默认产出文件名
    abs_out_pdf = os.path.abspath(out_pdf_path)
    out_dir = os.path.dirname(abs_out_pdf)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    abs_docx = os.path.abspath(docx_path)
    docx_basename = os.path.splitext(os.path.basename(abs_docx))[0]
    expected_default_pdf = os.path.join(out_dir, f"{docx_basename}.pdf")

    cmd = [
        soffice_bin,
        "--headless",
        "--convert-to",
        "pdf",
        abs_docx,
        "--outdir",
        out_dir,
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return {
            "pdf": False,
            "error": f"soffice conversion failed with returncode {result.returncode}: {result.stderr.strip()}",
        }

    # 若 soffice 默认生成的 pdf 路径与指定的 out_pdf_path 不一致，进行原子重命名
    if os.path.exists(expected_default_pdf) and expected_default_pdf != abs_out_pdf:
        shutil.move(expected_default_pdf, abs_out_pdf)

    if not os.path.exists(abs_out_pdf) or os.path.getsize(abs_out_pdf) == 0:
        return {
            "pdf": False,
            "error": f"Output PDF file was not created or is empty: {out_pdf_path}",
        }

    result_info: Dict[str, Any] = {
        "pdf": True,
        "path": out_pdf_path,
        "size_bytes": os.path.getsize(abs_out_pdf),
    }

    # 生成后主动预检文本层：PDF 确实已生成，但缺字体时文本层可能丢失中文字形。
    # 这里绝不伪造成功，也不改写 pdf=true，只附加 warning 与可操作 hint。
    diagnostic = preflight_text_layer(abs_docx, abs_out_pdf)
    if diagnostic is not None:
        result_info["text_layer_warning"] = "pdf_text_layer_lost_cjk"
        result_info["text_layer_diagnostic"] = diagnostic

    return result_info


def main() -> None:
    parser = argparse.ArgumentParser(
        description="build_pdf.py - 基于系统 headless soffice 的无损转 PDF 与优雅降级工具"
    )
    parser.add_argument("docx", help="输入 Word 文档路径 (如 delivery/output.docx)")
    parser.add_argument(
        "--out",
        default="delivery/output.pdf",
        help="目标 PDF 交付物路径 (默认: delivery/output.pdf)",
    )

    args = parser.parse_args()

    try:
        res = convert_docx_to_pdf(args.docx, args.out)

        # 紧凑单行 JSON 输出
        print(json.dumps(res, ensure_ascii=False, separators=(",", ":")))

        # 退出码：可用或优雅降级返回 0；执行报错返回 1
        if "error" in res:
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        err_out = {"pdf": False, "error": str(e)}
        print(json.dumps(err_out, ensure_ascii=False, separators=(",", ":")))
        sys.exit(1)


if __name__ == "__main__":
    main()
