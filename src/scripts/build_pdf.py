#!/usr/bin/env python3
"""
build_pdf.py - 基于系统 headless soffice 的无损转 PDF 与优雅降级工具
Lossless PDF Generation Engine with soffice Preflight and Graceful Fallback for M7

纯 Python 3 标准库实现，零第三方依赖。
若系统预装 soffice 可用，执行标准转换；若缺失，执行显式优雅降级，严禁伪造 PDF。

CLI 契约:
  python3 scripts/build_pdf.py delivery/output.docx --out delivery/output.pdf
  stdout (可用): {"pdf":true,"path":"delivery/output.pdf"} (退出码 0)
  stdout (缺失): {"pdf":false,"reason":"soffice_unavailable"} (退出码 0)
  stdout (错误): {"pdf":false,"error":"..."} (退出码 1)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional


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

    return {
        "pdf": True,
        "path": out_pdf_path,
        "size_bytes": os.path.getsize(abs_out_pdf),
    }


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
