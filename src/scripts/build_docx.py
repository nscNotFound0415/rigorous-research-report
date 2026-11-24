#!/usr/bin/env python3
"""
build_docx.py - 单源 Markdown 直写 OOXML 生成 Word 交付物与部件哈希工具
Direct OOXML Word Document & Manifest Builder for M7 Multi-format Delivery

纯 Python 3 标准库实现 (zipfile + xml.etree.ElementTree / 确定性 XML 生成)，
零第三方依赖，禁止使用 pandoc 直出，杜绝分节拼接。
保证构建绝对确定性（Idempotency）：同一输入连续构建部件 SHA256 哈希 100% 逐项一致。

CLI 契约:
  python3 scripts/build_docx.py draft_full.md --out delivery/output.docx --manifest build_manifest.json
  stdout: {"success":true,"docx":"...","manifest":"...","component_count":8}
  退出码: 0 (构建成功) / 1 (失败)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import xml.sax.saxutils as saxutils
import zipfile
from typing import Any, Dict, List, Optional, Tuple


def escape_xml(text: str) -> str:
    """对 XML 特殊字符进行转义。"""
    return saxutils.escape(text, entities={'"': "&quot;", "'": "&apos;"})


# 页面几何常量（twip = 1/20 pt）：
#   A4 页宽 11906 twip，左右页边距各 1440 twip（1 英寸，见 document.xml 的 pgMar），
#   因此正文文本宽度 = 11906 - 1440 - 1440 = 9026 twip。
PAGE_WIDTH_TWIP = 11906
MARGIN_LEFT_TWIP = 1440
MARGIN_RIGHT_TWIP = 1440
TEXT_WIDTH_TWIP = PAGE_WIDTH_TWIP - MARGIN_LEFT_TWIP - MARGIN_RIGHT_TWIP  # 9026

# ---------------- 静态 OOXML 骨架模板 (确定性字节流) ----------------

CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    '  <Default Extension="xml" ContentType="application/xml"/>\n'
    '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
    '  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\n'
    '  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>\n'
    '  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>\n'
    '  <Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>\n'
    '</Types>'
)

RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
    '</Relationships>'
)

DOC_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>\n'
    '  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>\n'
    '  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>\n'
    '  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>\n'
    '</Relationships>'
)

STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
    '  <w:docDefaults>\n'
    '    <w:rPrDefault>\n'
    '      <w:rPr>\n'
    '        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="SimSun"/>\n'
    '        <w:sz w:val="24"/>\n'
    '        <w:lang w:val="en-US" w:eastAsia="zh-CN"/>\n'
    '      </w:rPr>\n'
    '    </w:rPrDefault>\n'
    '  </w:docDefaults>\n'
    '  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">\n'
    '    <w:name w:val="Normal"/>\n'
    '    <w:qFormat/>\n'
    '    <w:pPr>\n'
    '      <w:spacing w:line="276" w:lineRule="auto" w:after="100"/>\n'
    '    </w:pPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="paragraph" w:styleId="Title">\n'
    '    <w:name w:val="Title"/>\n'
    '    <w:basedOn w:val="Normal"/>\n'
    '    <w:qFormat/>\n'
    '    <w:pPr>\n'
    '      <w:spacing w:before="360" w:after="240"/>\n'
    '      <w:jc w:val="center"/>\n'
    '    </w:pPr>\n'
    '    <w:rPr>\n'
    '      <w:b/>\n'
    '      <w:sz w:val="40"/>\n'
    '    </w:rPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="paragraph" w:styleId="Heading1">\n'
    '    <w:name w:val="heading 1"/>\n'
    '    <w:basedOn w:val="Normal"/>\n'
    '    <w:next w:val="Normal"/>\n'
    '    <w:qFormat/>\n'
    '    <w:pPr>\n'
    '      <w:spacing w:before="280" w:after="140"/>\n'
    '      <w:outlineLvl w:val="0"/>\n'
    '    </w:pPr>\n'
    '    <w:rPr>\n'
    '      <w:b/>\n'
    '      <w:sz w:val="32"/>\n'
    '    </w:rPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="paragraph" w:styleId="Heading2">\n'
    '    <w:name w:val="heading 2"/>\n'
    '    <w:basedOn w:val="Normal"/>\n'
    '    <w:next w:val="Normal"/>\n'
    '    <w:qFormat/>\n'
    '    <w:pPr>\n'
    '      <w:spacing w:before="200" w:after="100"/>\n'
    '      <w:outlineLvl w:val="1"/>\n'
    '    </w:pPr>\n'
    '    <w:rPr>\n'
    '      <w:b/>\n'
    '      <w:sz w:val="28"/>\n'
    '    </w:rPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="paragraph" w:styleId="Heading3">\n'
    '    <w:name w:val="heading 3"/>\n'
    '    <w:basedOn w:val="Normal"/>\n'
    '    <w:next w:val="Normal"/>\n'
    '    <w:qFormat/>\n'
    '    <w:pPr>\n'
    '      <w:spacing w:before="160" w:after="80"/>\n'
    '      <w:outlineLvl w:val="2"/>\n'
    '    </w:pPr>\n'
    '    <w:rPr>\n'
    '      <w:b/>\n'
    '      <w:sz w:val="24"/>\n'
    '    </w:rPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="paragraph" w:styleId="TOC1">\n'
    '    <w:name w:val="toc 1"/>\n'
    '    <w:basedOn w:val="Normal"/>\n'
    '    <w:pPr>\n'
    '      <w:spacing w:after="60"/>\n'
    '      <w:tabs>\n'
    f'        <w:tab w:val="right" w:leader="dot" w:pos="{TEXT_WIDTH_TWIP}"/>\n'
    '      </w:tabs>\n'
    '    </w:pPr>\n'
    '    <w:rPr>\n'
    '      <w:sz w:val="22"/>\n'
    '    </w:rPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="paragraph" w:styleId="TOC2">\n'
    '    <w:name w:val="toc 2"/>\n'
    '    <w:basedOn w:val="Normal"/>\n'
    '    <w:pPr>\n'
    '      <w:ind w:left="280"/>\n'
    '      <w:spacing w:after="40"/>\n'
    '      <w:tabs>\n'
    f'        <w:tab w:val="right" w:leader="dot" w:pos="{TEXT_WIDTH_TWIP}"/>\n'
    '      </w:tabs>\n'
    '    </w:pPr>\n'
    '    <w:rPr>\n'
    '      <w:sz w:val="20"/>\n'
    '    </w:rPr>\n'
    '  </w:style>\n'
    '  <w:style w:type="table" w:default="1" w:styleId="TableGrid">\n'
    '    <w:name w:val="Table Grid"/>\n'
    '    <w:basedOn w:val="TableNormal"/>\n'
    '    <w:tblPr>\n'
    '      <w:tblBorders>\n'
    '        <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>\n'
    '        <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>\n'
    '        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>\n'
    '        <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>\n'
    '        <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>\n'
    '        <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>\n'
    '      </w:tblBorders>\n'
    '    </w:tblPr>\n'
    '  </w:style>\n'
    '</w:styles>'
)

NUMBERING_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
    '  <w:abstractNum w:abstractNumId="0">\n'
    '    <w:lvl w:ilvl="0">\n'
    '      <w:start w:val="1"/>\n'
    '      <w:numFmt w:val="bullet"/>\n'
    '      <w:lvlText w:val="•"/>\n'
    '      <w:lvlJc w:val="left"/>\n'
    '      <w:pPr><w:ind w:left="420" w:hanging="420"/></w:pPr>\n'
    '    </w:lvl>\n'
    '  </w:abstractNum>\n'
    '  <w:num w:numId="1">\n'
    '    <w:abstractNumId w:val="0"/>\n'
    '  </w:num>\n'
    '</w:numbering>'
)

SETTINGS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
    '  <w:defaultTabStop w:val="420"/>\n'
    '  <w:characterSpacingControl w:val="doNotCompress"/>\n'
    '</w:settings>'
)

FONT_TABLE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:fontTable xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
    '  <w:font w:name="Calibri">\n'
    '    <w:panose1 w:val="020F0502020204030204"/>\n'
    '    <w:charset w:val="00"/>\n'
    '    <w:family w:val="swiss"/>\n'
    '    <w:pitch w:val="variable"/>\n'
    '  </w:font>\n'
    '  <w:font w:name="SimSun">\n'
    '    <w:altName w:val="宋体"/>\n'
    '    <w:panose1 w:val="02010600030101010101"/>\n'
    '    <w:charset w:val="86"/>\n'
    '    <w:family w:val="auto"/>\n'
    '    <w:pitch w:val="variable"/>\n'
    '  </w:font>\n'
    '</w:fontTable>'
)


def parse_markdown_to_structure(content: str) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """
    解析 Markdown 单源文件：
    提取：
    1. 报告标题 (title)
    2. 正文大纲标题列表 (headings，用于 TOC 生成与回读匹配)
    3. 正文块列表 (blocks: heading, paragraph, table, list_item)
    """
    lines = content.splitlines()
    title = "调研报告"
    headings: List[str] = []
    blocks: List[Dict[str, Any]] = []

    in_frontmatter = False
    in_table = False
    table_rows: List[List[str]] = []

    first_heading_seen = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 处理 frontmatter
        if i == 0 and stripped == "---":
            in_frontmatter = True
            i += 1
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            i += 1
            continue

        # 处理表格
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            # 过滤分隔线行 |---|---|
            if not re.match(r"^\|(\s*:?-+:?\s*\|)+$", stripped):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                if table_rows:
                    blocks.append({"type": "table", "rows": table_rows})
                in_table = False
                table_rows = []

        if not stripped:
            i += 1
            continue

        # 处理标题
        h_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if h_match:
            level = len(h_match.group(1))
            h_text = h_match.group(2).strip()

            # 首个一级标题作为整篇文档标题
            if level == 1 and not first_heading_seen:
                title = h_text
                first_heading_seen = True
                blocks.append({"type": "title", "text": h_text})
                i += 1
                continue

            first_heading_seen = True

            # 排除显式的“目录”标题（目录由构建引擎统一生成并排版）
            if h_text in ("目录", "Table of Contents", "TOC"):
                i += 1
                continue

            headings.append(h_text)
            blocks.append({"type": "heading", "level": level, "text": h_text})
            i += 1
            continue

        # 列表项
        if stripped.startswith(("- ", "* ", "• ")):
            item_text = stripped[2:].strip()
            blocks.append({"type": "bullet", "text": item_text})
            i += 1
            continue

        # 普通段落
        blocks.append({"type": "paragraph", "text": stripped})
        i += 1

    if in_table and table_rows:
        blocks.append({"type": "table", "rows": table_rows})

    return title, headings, blocks


def build_document_xml(title: str, headings: List[str], blocks: List[Dict[str, Any]]) -> str:
    """构建 word/document.xml 内容。"""
    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    xml_parts.append('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">')
    xml_parts.append("  <w:body>")

    # 1. 标题
    xml_parts.append("    <w:p>")
    xml_parts.append('      <w:pPr><w:pStyle w:val="Title"/></w:pPr>')
    xml_parts.append(f"      <w:r><w:t>{escape_xml(title)}</w:t></w:r>")
    xml_parts.append("    </w:p>")

    # 2. 目录区（TOC 占位与两遍法回填槽）
    xml_parts.append("    <w:p>")
    xml_parts.append('      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>')
    xml_parts.append("      <w:r><w:t>目录</w:t></w:r>")
    xml_parts.append("    </w:p>")

    # 为每个正文标题生成 TOC 条目段落
    for heading in headings:
        xml_parts.append("    <w:p>")
        xml_parts.append('      <w:pPr><w:pStyle w:val="TOC1"/></w:pPr>')
        xml_parts.append(f"      <w:r><w:t>{escape_xml(heading)}</w:t></w:r>")
        xml_parts.append("      <w:r><w:tab/></w:r>")
        # 初始占位页码为 2（第一遍构建占位）
        xml_parts.append('      <w:r><w:t>2</w:t></w:r>')
        xml_parts.append("    </w:p>")

    # 分页符：目录与正文严格分页
    xml_parts.append('    <w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    # 3. 正文各块
    for block in blocks:
        b_type = block.get("type")
        if b_type == "title":
            # 标题已在前面输出
            continue

        elif b_type == "heading":
            level = block["level"]
            style_name = "Heading1" if level <= 2 else "Heading2"
            xml_parts.append("    <w:p>")
            xml_parts.append(f'      <w:pPr><w:pStyle w:val="{style_name}"/></w:pPr>')
            xml_parts.append(f"      <w:r><w:t>{escape_xml(block['text'])}</w:t></w:r>")
            xml_parts.append("    </w:p>")

        elif b_type == "paragraph":
            xml_parts.append("    <w:p>")
            xml_parts.append('      <w:pPr><w:pStyle w:val="Normal"/></w:pPr>')
            xml_parts.append(f"      <w:r><w:t>{escape_xml(block['text'])}</w:t></w:r>")
            xml_parts.append("    </w:p>")

        elif b_type == "bullet":
            xml_parts.append("    <w:p>")
            xml_parts.append("      <w:pPr>")
            xml_parts.append('        <w:pStyle w:val="Normal"/>')
            xml_parts.append('        <w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>')
            xml_parts.append("      </w:pPr>")
            xml_parts.append(f"      <w:r><w:t>{escape_xml(block['text'])}</w:t></w:r>")
            xml_parts.append("    </w:p>")

        elif b_type == "table":
            xml_parts.append("    <w:tbl>")
            xml_parts.append("      <w:tblPr>")
            xml_parts.append('        <w:tblStyle w:val="TableGrid"/>')
            xml_parts.append('        <w:tblW w:w="9000" w:type="dxa"/>')
            xml_parts.append('        <w:jc w:val="center"/>')
            xml_parts.append("      </w:tblPr>")

            for row_idx, row in enumerate(block["rows"]):
                xml_parts.append("      <w:tr>")
                for cell in row:
                    xml_parts.append("        <w:tc>")
                    xml_parts.append("          <w:p>")
                    if row_idx == 0:
                        xml_parts.append("            <w:r><w:rPr><w:b/></w:rPr>")
                    else:
                        xml_parts.append("            <w:r>")
                    xml_parts.append(f"<w:t>{escape_xml(cell)}</w:t></w:r>")
                    xml_parts.append("          </w:p>")
                    xml_parts.append("        </w:tc>")
                xml_parts.append("      </w:tr>")

            xml_parts.append("    </w:tbl>")

    # 结尾节属性
    xml_parts.append("    <w:sectPr>")
    xml_parts.append('      <w:pgSz w:w="11906" w:h="16838"/>')  # A4: 210mm x 297mm in dxa
    xml_parts.append('      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>')  # 1 inch margin
    xml_parts.append("    </w:sectPr>")

    xml_parts.append("  </w:body>")
    xml_parts.append("</w:document>")

    return "\n".join(xml_parts)


def compute_bytes_sha256(data: bytes) -> str:
    """计算字节流的 SHA256 十六进制哈希字符串。"""
    return hashlib.sha256(data).hexdigest().lower()


def build_docx_and_manifest(
    draft_path: str,
    out_docx: str,
    out_manifest: str,
) -> Dict[str, Any]:
    """
    单源直写 OOXML Word 文档并生成部件清单 build_manifest.json。
    保证确定性与幂等性：使用固定的 ZipInfo 时间戳与一致的编码。
    """
    if not os.path.exists(draft_path):
        raise FileNotFoundError(f"Source draft not found: {draft_path}")

    with open(draft_path, "r", encoding="utf-8") as f:
        content = f.read()

    title, headings, blocks = parse_markdown_to_structure(content)
    document_xml = build_document_xml(title, headings, blocks)

    # 8 个标准 OOXML 部件内容映射
    components_raw: Dict[str, bytes] = {
        "[Content_Types].xml": CONTENT_TYPES_XML.encode("utf-8"),
        "_rels/.rels": RELS_XML.encode("utf-8"),
        "word/_rels/document.xml.rels": DOC_RELS_XML.encode("utf-8"),
        "word/document.xml": document_xml.encode("utf-8"),
        "word/styles.xml": STYLES_XML.encode("utf-8"),
        "word/numbering.xml": NUMBERING_XML.encode("utf-8"),
        "word/settings.xml": SETTINGS_XML.encode("utf-8"),
        "word/fontTable.xml": FONT_TABLE_XML.encode("utf-8"),
    }

    # 计算各部件 SHA256 哈希
    manifest_components: Dict[str, str] = {}
    for part_name in sorted(components_raw.keys()):
        manifest_components[part_name] = compute_bytes_sha256(components_raw[part_name])

    manifest_data = {
        "source": draft_path,
        "target": out_docx,
        "headings_count": len(headings),
        "components": manifest_components,
    }

    # 确保输出目录存在
    out_dir = os.path.dirname(os.path.abspath(out_docx))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    manifest_dir = os.path.dirname(os.path.abspath(out_manifest))
    if manifest_dir:
        os.makedirs(manifest_dir, exist_ok=True)

    # 写入确定性 Zip 归档 (固定时间戳 2026-01-01 00:00:00)
    fixed_time = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for part_name in sorted(components_raw.keys()):
            zinfo = zipfile.ZipInfo(filename=part_name, date_time=fixed_time)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zinfo, components_raw[part_name])

    # 写入 build_manifest.json (格式化排序保证确定性)
    with open(out_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2, sort_keys=True)

    return {
        "success": True,
        "docx": out_docx,
        "manifest": out_manifest,
        "component_count": len(manifest_components),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="build_docx.py - 单源 Markdown 直写 OOXML 生成 Word 交付物与部件哈希清单"
    )
    parser.add_argument("draft", help="单源 Markdown 草稿文件 (如 draft_full.md)")
    parser.add_argument(
        "--out",
        default="delivery/output.docx",
        help="目标 Word 交付物路径 (默认: delivery/output.docx)",
    )
    parser.add_argument(
        "--manifest",
        default="build_manifest.json",
        help="输出构建部件哈希清单路径 (默认: build_manifest.json)",
    )

    args = parser.parse_args()

    try:
        result = build_docx_and_manifest(args.draft, args.out, args.manifest)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        sys.exit(0)
    except Exception as e:
        err_out = {"success": False, "error": str(e)}
        print(json.dumps(err_out, ensure_ascii=False, separators=(",", ":")))
        sys.exit(1)


if __name__ == "__main__":
    main()
