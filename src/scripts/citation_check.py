#!/usr/bin/env python3
"""
citation_check.py - 图表编号连续性与文献/证据引用一致性核查工具
Citation & Figure Numbering Consistency Verification Engine for M7 Synthesis

纯 Python 3 标准库实现，零第三方依赖，无外网访问。
符合 OpenSpec specs/draft-synthesis/spec.md, specs/outline-approval/spec.md 与建设方案 v2.1 规范。

CLI 契约:
  1. M7 全文图表与证据引用校验 (主契约):
     python3 scripts/citation_check.py draft_full.md --evidence-index evidence-index.md
     stdout: {"dangling_refs":[],"unnumbered_figs":[],"dangling_tables":[]}
     退出码: 0 (合规闭环) / 1 (检出悬空引用或断号图表)

  2. M5 大纲引用与待补数据核验 (向下兼容):
     python3 scripts/citation_check.py --outline outline.md --evidence-index evidence-index.md [--allow-pending|--strict]
     stdout: {"dangling_refs":[],"pending_declared":true} 或 {"pending_count":0,"dangling_refs":[]}
     退出码: 0 (通过) / 1 (阻断)
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


def parse_evidence_index(index_path: str) -> Set[str]:
    """从 evidence-index.md 解析所有已知入库的有效证据与信源 ID。"""
    if not os.path.exists(index_path):
        return set()

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    ids: Set[str] = set()

    # 1. 匹配表格第一列或单元格（如 | EVD-001 | 或 | REF-01 | 或 | S01 |）
    table_cell_pattern = re.compile(r"\|\s*([A-Za-z0-9_-]+)\s*\|")
    for match in table_cell_pattern.finditer(content):
        val = match.group(1).strip()
        if (
            val
            and not val.startswith("---")
            and val.lower() not in ("id", "evidence_id", "ref", "ref_id", "序号", "编号", "类别", "信源类别")
        ):
            ids.add(val)

    # 2. 匹配列表项：- **EVD-001**: 或 - [EVD-001]: 或 - EVD-001:
    list_item_pattern = re.compile(
        r"^\s*(?:-\s+|\*\s+|\d+\.\s+)(?:\*\*)?(?:\[)?([A-Za-z0-9_-]+)(?:\])?(?:\*\*)?\s*:\s*",
        re.MULTILINE,
    )
    for match in list_item_pattern.finditer(content):
        val = match.group(1).strip()
        if val and val.lower() not in ("id", "evidence_id", "ref", "note", "summary", "说明"):
            ids.add(val)

    # 3. 匹配三级/四级标题：### EVD-001 或 #### [EVD-001]
    heading_pattern = re.compile(r"^#{2,4}\s+(?:\[)?([A-Za-z0-9_-]+)(?:\])?", re.MULTILINE)
    for match in heading_pattern.finditer(content):
        val = match.group(1).strip()
        if val.upper().startswith(("EVD", "REF", "SRC", "FACT", "S")):
            ids.add(val)

    return ids


def extract_citations_from_draft(content: str) -> Set[str]:
    """从 Markdown 正文稿中提取所有引用的证据与信源 ID。"""
    citations: Set[str] = set()

    # 1. 匹配方括号引用 [EVD-001], [REF-01], [S31], [SRC-01]
    bracket_pattern = re.compile(r"\[([A-Za-z0-9_-]+)\]")
    for match in bracket_pattern.finditer(content):
        ref = match.group(1).strip()
        # 排除纯数字 footnote、markdown 链接文本、TOC 占位符
        if ref.upper() in ("TOC", "X", " ") or ref.isdigit():
            continue
        if ref.upper().startswith(("EVD", "REF", "SRC", "FACT")) or re.match(r"^S\d+$", ref):
            citations.add(ref)

    # 2. 匹配圆括号/中文括号引用 (EVD-001), 【REF-01】, (S31)
    paren_pattern = re.compile(r"[（(【]([A-Za-z0-9_-]+)[）)】]")
    for match in paren_pattern.finditer(content):
        ref = match.group(1).strip()
        if ref.upper().startswith(("EVD", "REF", "SRC", "FACT")) or re.match(r"^S\d+$", ref):
            citations.add(ref)

    # 3. 匹配显式属性声明 evidence_ref: EVD-001, EVD-002
    attr_pattern = re.compile(r"(?:evidence_ref|信源引用|证据引用)[：:\s]+([^\n\r]+)")
    for match in attr_pattern.finditer(content):
        raw_val = match.group(1).strip()
        for item in re.split(r"[,;\s]+", raw_val):
            item = item.strip().strip("[]()【】\"'")
            if item and item.upper() != "PENDING":
                citations.add(item)

    return citations


def check_figure_numbering(content: str) -> List[str]:
    """
    检查全文插图编号的完整性与连续性：
    1. 检测无编号图（如仅写“图：拓扑架构”或未带序号的插图标题）；
    2. 检测编号断号（如存在 图 1、图 3 但缺失 图 2）。
    """
    unnumbered_issues: List[str] = []

    # 1. 检测无编号图 (图：xxx 或 图: xxx 而无数字序号)
    unnumbered_pattern = re.compile(r"(?:^|[^\w])(?:图|Figure)[：:\s]+([^\d\s\n\r]{2,})", re.MULTILINE)
    for match in unnumbered_pattern.finditer(content):
        title = match.group(1).strip()
        # 排除“如图所示”、“图表”等正常词汇
        if not title.startswith(("所示", "表", "片", "像", "解")):
            unnumbered_issues.append(f"未编号图表标题: 图：{title[:20]}")

    # 2. 提取所有数字编号图：图 1、图 2、图 1-1、Figure 1 等
    fig_pattern = re.compile(r"(?:^|[^\w])(?:图|Figure)\s*(\d+)(?:[-_](\d+))?", re.MULTILINE)
    primary_numbers: Set[int] = set()
    sub_numbers: Dict[int, Set[int]] = {}

    for match in fig_pattern.finditer(content):
        p_num = int(match.group(1))
        primary_numbers.add(p_num)
        if match.group(2):
            s_num = int(match.group(2))
            sub_numbers.setdefault(p_num, set()).add(s_num)

    if primary_numbers:
        min_p = min(primary_numbers)
        max_p = max(primary_numbers)

        if min_p > 1:
            unnumbered_issues.append(f"图表编号断号: 编号起始于 图 {min_p}，缺少 图 1")

        for expected in range(1, max_p + 1):
            if expected not in primary_numbers:
                unnumbered_issues.append(f"图表编号断号: 缺少 图 {expected} (存在 图 {max_p})")

    # 检查子编号连续性 (如 1-1, 1-2)
    for p_num, s_set in sub_numbers.items():
        if s_set:
            max_s = max(s_set)
            for s_exp in range(1, max_s + 1):
                if s_exp not in s_set:
                    unnumbered_issues.append(f"图表子编号断号: 缺少 图 {p_num}-{s_exp}")

    return unnumbered_issues


def check_table_numbering_and_refs(content: str) -> List[str]:
    """
    检查表格编号连续性及正文中引用的表号是否存在。
    """
    dangling_tables: List[str] = []

    # 1. 提取所有声明的表格编号：表 1、表 2、表 1-1 等
    declared_tables: Set[str] = set()
    table_decl_pattern = re.compile(
        r"(?:^|\n)\s*(?:\*\*)?(?:表|Table)\s*(\d+(?:[-_]\d+)?)[：:\s*]",
        re.MULTILINE,
    )
    for match in table_decl_pattern.finditer(content):
        declared_tables.add(match.group(1).replace("_", "-"))

    # 2. 提取正文中引用的表号：“见表 1”、“如表 2 所示”、“表 3 汇总”
    table_ref_pattern = re.compile(r"(?:见|如|参见|参考|在)?(?:表|Table)\s*(\d+(?:[-_]\d+)?)(?:所示|中|展示|列示)?")
    for match in table_ref_pattern.finditer(content):
        ref_tbl = match.group(1).replace("_", "-")
        # 排除表格自身标题所在行
        line_start = content.rfind("\n", 0, match.start())
        line_end = content.find("\n", match.end())
        cur_line = content[line_start:line_end] if line_start != -1 else content[:line_end]
        if cur_line.strip().startswith(("表", "**表", "#", "|")):
            continue
        if ref_tbl not in declared_tables:
            dangling_tables.append(f"正文引用了未定义的表号: 表 {ref_tbl}")

    # 3. 检查表格编号连续性
    simple_table_nums = [int(t) for t in declared_tables if t.isdigit()]
    if simple_table_nums:
        max_t = max(simple_table_nums)
        for t_exp in range(1, max_t + 1):
            if t_exp not in simple_table_nums:
                dangling_tables.append(f"表格编号断号: 缺少 表 {t_exp} (当前最大编号 表 {max_t})")

    return dangling_tables


def handle_outline_mode(outline_path: str, index_path: str, is_strict: bool) -> None:
    """处理 M5 大纲模式的证据引用与 PENDING 校验。"""
    if not os.path.exists(outline_path):
        out = {"error": f"Outline file not found: {outline_path}"}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(1)

    known_ids = parse_evidence_index(index_path)

    with open(outline_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 evidence_ref
    pending_refs: List[str] = []
    dangling_refs: List[str] = []

    attr_pattern = re.compile(r"(?:evidence_ref)[：:\s]+([^\n\r]+)")
    for match in attr_pattern.finditer(content):
        val = match.group(1).strip()
        for ref in re.split(r"[,;\s]+", val):
            ref = ref.strip().strip("[]\"'")
            if not ref:
                continue
            if ref.upper().startswith("PENDING"):
                pending_refs.append(ref)
            elif ref not in known_ids:
                dangling_refs.append(ref)

    # 检查待补数据小节
    pending_declared = ("待补数据" in content or "PENDING" in content)

    if is_strict:
        # Join 2 汇合门禁：pending_count 必须为 0 且无悬空
        output = {
            "pending_count": len(pending_refs),
            "dangling_refs": dangling_refs,
        }
        passed = (len(pending_refs) == 0 and len(dangling_refs) == 0)
    else:
        # 并行期：允许 PENDING 但必须在待补数据小节显式登记
        output = {
            "dangling_refs": dangling_refs,
            "pending_declared": pending_declared,
        }
        passed = (len(dangling_refs) == 0 and pending_declared)

    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    sys.exit(0 if passed else 1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="citation_check.py - 全文图表编号与文献/证据引用一致性核查工具"
    )
    # 支持两种调用风格：
    # 风格 1: python3 scripts/citation_check.py draft_full.md --evidence-index evidence-index.md
    # 风格 2: python3 scripts/citation_check.py --outline outline.md --evidence-index evidence-index.md [--strict|--allow-pending]
    parser.add_argument("draft", nargs="?", default=None, help="目标 Markdown 文件路径 (如 draft_full.md)")
    parser.add_argument("--outline", default=None, help="[M5 模式] 待校验的大纲文件路径")
    parser.add_argument(
        "--evidence-index",
        default="evidence-index.md",
        help="证据索引表文件路径 (默认: evidence-index.md)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="[M5 模式] Join 2 严格模式：要求 PENDING 数量清零",
    )
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="[M5 模式] 并行期模式：允许 PENDING 但必须显式登记",
    )

    args = parser.parse_args()

    # 1. 检查是否为 M5 大纲模式
    if args.outline:
        handle_outline_mode(args.outline, args.evidence_index, is_strict=args.strict)
        return

    # 2. M7 全文校验模式
    target_path = args.draft
    if not target_path:
        sys.stderr.write("Error: Please provide draft_full.md file path.\n")
        sys.exit(1)

    if not os.path.exists(target_path):
        err_out = {
            "dangling_refs": [f"File not found: {target_path}"],
            "unnumbered_figs": [],
            "dangling_tables": [],
        }
        print(json.dumps(err_out, ensure_ascii=False, separators=(",", ":")))
        sys.exit(1)

    with open(target_path, "r", encoding="utf-8") as f:
        draft_content = f.read()

    known_ids = parse_evidence_index(args.evidence_index)

    # 提取所有正文引用并与索引比对
    citations = extract_citations_from_draft(draft_content)
    dangling_refs = sorted(list(citations - known_ids))

    # 校验图表连续性与未编号图表
    unnumbered_figs = check_figure_numbering(draft_content)

    # 校验正文表格引用与断号
    dangling_tables = check_table_numbering_and_refs(draft_content)

    result = {
        "dangling_refs": dangling_refs,
        "unnumbered_figs": unnumbered_figs,
        "dangling_tables": dangling_tables,
    }

    # 单行紧凑 JSON 格式
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))

    # 退出码判定：若存在悬空引用、断号图表或断号表格，返回 1；全空返回 0
    has_error = bool(dangling_refs or unnumbered_figs or dangling_tables)
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
