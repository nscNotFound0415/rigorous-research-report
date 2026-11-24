#!/usr/bin/env python3
"""
outline_check.py - 章节大纲结构、论证目的与证据引用合规校验工具

符合 OpenSpec 规格 (specs/outline-approval/spec.md) 与建设方案规范。
纯 Python 3 标准库实现，零第三方依赖，无外网访问，无状态残留。

CLI 契约:
  1. 并行期证据引用与待补数据登记校验:
     python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md
     stdout: {"missing_refs":[],"pending_refs":[],"refs_total":N,"dangling_refs":[],"pending_count":0,"pending_declared":true}
     退出码: 0 (合规) / 1 (存在未锚定 ref 或 PENDING 未在「待补数据」小节登记)

  2. 章节结构与论证目的校验:
     python3 scripts/outline_check.py outline.md --check-sections
     stdout: {"invalid_sections":[],"chapter_count":N}
     退出码: 0 (合规) / 1 (章节跳级、某章缺 evidence_ref 或缺论证目的行)

  3. Join 2 汇合不可豁免门禁校验:
     python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md --require-resolved
     (支持 --strict 别名)
     stdout: {"missing_refs":[],"pending_refs":[],"refs_total":N,"dangling_refs":[],"pending_count":0,"pending_declared":true}
     退出码: 0 (PENDING 归零且全量锚定) / 1 (仍存在 PENDING 或悬空 ref)
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple


def parse_evidence_index(index_path: str) -> Set[str]:
    """从 evidence-index.md 解析所有已知已入库的证据 ID。"""
    if not os.path.exists(index_path):
        return set()

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    ids: Set[str] = set()

    # 1. 匹配表格中的单元格（例如 | EVD-001 | 或 | REF-01 |）
    table_cell_pattern = re.compile(r"\|\s*([A-Za-z0-9_-]+)\s*\|")
    for match in table_cell_pattern.finditer(content):
        val = match.group(1).strip()
        if val and not val.lower().startswith("---") and val.lower() not in ("id", "evidence_id", "ref", "ref_id", "序号", "编号"):
            ids.add(val)

    # 2. 匹配列表项：- **EVD-001**: 或 - [EVD-001]: 或 - EVD-001:
    list_item_pattern = re.compile(
        r"^\s*(?:-\s+|\*\s+|\d+\.\s+)(?:\*\*)?(?:\[)?([A-Za-z0-9_-]+)(?:\])?(?:\*\*)?\s*:\s*",
        re.MULTILINE,
    )
    for match in list_item_pattern.finditer(content):
        val = match.group(1).strip()
        if val and val.lower() not in ("id", "evidence_id", "ref", "note", "summary"):
            ids.add(val)

    # 3. 匹配常见标准前缀 ID: EVD-*, REF-*, FACT-*, DATA-*
    std_prefix_pattern = re.compile(r"\b((?:EVD|REF|FACT|DATA|SRC)-[A-Za-z0-9_-]+)\b")
    for match in std_prefix_pattern.finditer(content):
        ids.add(match.group(1).strip())

    # 4. 匹配显式声明 id: ... / evidence_id: ...
    explicit_pattern = re.compile(r"(?:^|\s)(?:id|evidence_id)\s*[:=]\s*[\"']?([A-Za-z0-9_-]+)[\"']?", re.IGNORECASE)
    for match in explicit_pattern.finditer(content):
        ids.add(match.group(1).strip())

    return ids


def extract_pending_section(content: str) -> Tuple[bool, str]:
    """
    定位 outline.md 中的「待补数据」小节。
    仅匹配 H2 及以下标题，避免把 H1 文档主标题误判为待补小节。
    返回 (section_found, section_text)。
    """
    lines = content.splitlines()
    found = False
    section_lines: List[str] = []
    section_level = 0

    heading_pattern = re.compile(r"^(#{2,6})\s+(.*)$")

    for line in lines:
        h_match = heading_pattern.match(line)
        if h_match:
            hashes, title = h_match.group(1), h_match.group(2).strip()
            level = len(hashes)
            if "待补数据" in title or (title.upper().startswith("PENDING") and ("数据" in title or "引用" in title or "待补" in title)):
                found = True
                section_level = level
                # 标题行本身不计入内容，避免标题自带的 PENDING 字符串干扰匹配
                continue

            if found:
                # 遇到同级或更高级标题，说明待补数据小节结束
                if level <= section_level:
                    break
                else:
                    section_lines.append(line)
        elif found:
            section_lines.append(line)

    return found, "\n".join(section_lines)


def parse_outline_refs(content: str) -> Tuple[List[str], List[str], List[str]]:
    """
    解析 outline.md 中的所有 evidence_ref 字段。
    返回 (all_refs, regular_refs, pending_refs)。
    """
    all_refs: List[str] = []
    regular_refs: List[str] = []
    pending_refs: List[str] = []

    # 匹配 evidence_ref 的不同书写格式:
    # 1. evidence_ref: VAL 或 - evidence_ref: VAL 或 **evidence_ref**: VAL
    # 2. [evidence_ref: VAL]
    # 3. (evidence_ref: VAL)
    patterns = [
        re.compile(r"(?:^|\s)(?:-\s+)?(?:\*\*)?evidence_ref(?:\*\*)?\s*[:=]\s*([^\n\r]+)", re.IGNORECASE),
        re.compile(r"\[evidence_ref\s*[:=]\s*([^\]]+)\]", re.IGNORECASE),
        re.compile(r"\(evidence_ref\s*[:=]\s*([^\)]+)\)", re.IGNORECASE),
    ]

    for line in content.splitlines():
        # 如果整行包含待补数据主标题自身，跳过行避免自匹配
        if re.match(r"^#{1,6}\s+.*待补数据.*", line):
            continue

        for pat in patterns:
            for match in pat.finditer(line):
                raw_val = match.group(1).strip()
                # 剔除可能的外层方括号或引号
                clean_val = raw_val.strip("[]\"'")

                # 支持逗号分隔的多个 ref: [EVD-001, EVD-002]
                parts = [p.strip().strip("\"'") for p in re.split(r"[,;]", clean_val) if p.strip()]
                for part in parts:
                    if not part:
                        continue
                    all_refs.append(part)
                    upper_part = part.upper()
                    if "PENDING" in upper_part:
                        pending_refs.append(part)
                    else:
                        regular_refs.append(part)

    return all_refs, regular_refs, pending_refs


def check_heading_hierarchy(content: str) -> List[str]:
    """
    校验标题层级是否跳级（例如从 H1 直接跳到 H3，或从 H2 直接跳到 H4）。
    """
    errors: List[str] = []
    lines = content.splitlines()
    prev_level = 0
    prev_heading = ""

    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

    for line_idx, line in enumerate(lines, start=1):
        m = heading_pattern.match(line)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()

        if prev_level > 0 and level > prev_level + 1:
            errors.append(
                f"Line {line_idx}: Heading level skipped from H{prev_level} ('{prev_heading}') to H{level} ('{title}')"
            )

        prev_level = level
        prev_heading = title

    return errors


def check_chapter_sections(content: str) -> Tuple[List[str], int]:
    """
    校验章节结构：
    1. 标题不跳级
    2. 每章（H2 级别，排除待补数据/元数据等小节）至少包含 1 条 evidence_ref
    3. 每章有明确的「论证目的」说明行
    返回 (invalid_sections, chapter_count)
    """
    invalid_sections: List[str] = []

    # 1. 检查标题跳级
    hierarchy_errors = check_heading_hierarchy(content)
    invalid_sections.extend(hierarchy_errors)

    # 2. 分解各章节
    lines = content.splitlines()
    h2_pattern = re.compile(r"^##\s+(.*)$")

    meta_keywords = ("待补数据", "附录", "前言", "签署声明", "门禁", "文档信息", "元数据", "appendix", "contracts")

    chapters: List[Tuple[str, List[str]]] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        m = h2_pattern.match(line)
        if m:
            if current_title is not None:
                chapters.append((current_title, current_lines))
            current_title = m.group(1).strip()
            current_lines = [line]
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        chapters.append((current_title, current_lines))

    # 过滤出正文章节（排除元数据/待补数据节）
    content_chapters: List[Tuple[str, List[str]]] = []
    for title, ch_lines in chapters:
        lower_title = title.lower()
        if any(kw in lower_title for kw in meta_keywords):
            continue
        content_chapters.append((title, ch_lines))

    chapter_count = len(content_chapters)
    if chapter_count == 0:
        invalid_sections.append("No valid content chapters (H2) found in outline.md")

    # 论证目的匹配正则
    objective_pattern = re.compile(
        r"^\s*(?:-\s+|\*\s+|\d+\.\s+)?(?:>\s*)?(?:\*\*)?(?:论证目的|argumentation_objective|objective)(?:\*\*)?\s*[:：]\s*(.+)",
        re.IGNORECASE,
    )

    for title, ch_lines in content_chapters:
        ch_text = "\n".join(ch_lines)

        # 检查是否包含至少 1 条 evidence_ref
        ch_all, _, _ = parse_outline_refs(ch_text)
        if len(ch_all) == 0:
            invalid_sections.append(f"Chapter '{title}' has no evidence_ref (minimum 1 required)")

        # 检查是否包含论证目的行
        has_objective = False
        for line in ch_lines:
            if objective_pattern.match(line):
                has_objective = True
                break

        if not has_objective:
            invalid_sections.append(f"Chapter '{title}' missing explicit '论证目的' line")

    return invalid_sections, chapter_count


def verify_pending_declarations(pending_refs: List[str], pending_section_text: str, pending_section_found: bool) -> Tuple[bool, List[str]]:
    """
    检查所有被标记为 PENDING 的引用是否在「待补数据」小节显式登记。
    """
    if not pending_refs:
        return True, []

    if not pending_section_found:
        return False, [f"Pending reference '{r}' used but no '待补数据' section found in outline.md" for r in pending_refs]

    errors: List[str] = []
    for ref in pending_refs:
        # 提取关键 ID 标识，例如 PENDING-01 或 PENDING
        ref_id_match = re.search(r"\b(PENDING(?:-[A-Za-z0-9_]+)?)\b", ref, re.IGNORECASE)
        target = ref_id_match.group(1) if ref_id_match else ref

        if target not in pending_section_text:
            errors.append(f"Pending reference '{ref}' is not listed in '待补数据' section")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(
        description="outline_check.py - 校验 outline.md 章节结构、论证目的与 evidence_ref 前置引用合规性"
    )
    parser.add_argument("outline", nargs="?", default=None, help="Path to outline.md")
    parser.add_argument("--outline", dest="outline_flag", default=None, help="Path to outline.md (flag format)")
    parser.add_argument("--evidence-index", dest="evidence_index", default=None, help="Path to evidence-index.md")
    parser.add_argument("--check-sections", action="store_true", help="Validate section hierarchy, chapter objectives, and minimum evidence_ref")
    parser.add_argument("--require-resolved", action="store_true", help="Join 2 gate mode: require pending_refs to be 0")
    parser.add_argument("--strict", action="store_true", help="Alias for --require-resolved")
    parser.add_argument("--allow-pending", action="store_true", help="Parallel phase mode (allow declared pending refs)")

    args = parser.parse_args()

    outline_path = args.outline_flag if args.outline_flag else args.outline
    if not outline_path:
        sys.stderr.write("Error: outline.md path must be provided.\n")
        sys.exit(1)

    if not os.path.exists(outline_path):
        sys.stderr.write(f"Error: outline file '{outline_path}' does not exist.\n")
        sys.exit(1)

    with open(outline_path, "r", encoding="utf-8") as f:
        outline_content = f.read()

    strict_mode = args.require_resolved or args.strict

    # 1. 仅执行章节结构校验
    if args.check_sections and not args.evidence_index:
        invalid_sections, chapter_count = check_chapter_sections(outline_content)
        result = {
            "invalid_sections": invalid_sections,
            "chapter_count": chapter_count,
        }
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        sys.exit(0 if len(invalid_sections) == 0 and chapter_count > 0 else 1)

    # 2. 执行证据索引比对校验
    if args.evidence_index:
        known_evidence_ids = parse_evidence_index(args.evidence_index)
        all_refs, regular_refs, pending_refs = parse_outline_refs(outline_content)

        # 查找待补数据节
        section_found, section_text = extract_pending_section(outline_content)
        pending_declared, pending_decl_errors = verify_pending_declarations(pending_refs, section_text, section_found)

        missing_refs: List[str] = []
        for ref in regular_refs:
            if ref not in known_evidence_ids:
                missing_refs.append(ref)

        refs_total = len(all_refs)

        # 构建统一 JSON 响应（包含契约字段与向前兼容别名）
        result = {
            "missing_refs": missing_refs,
            "pending_refs": pending_refs,
            "refs_total": refs_total,
            "dangling_refs": missing_refs,
            "pending_count": len(pending_refs),
            "pending_declared": pending_declared,
        }

        # 若同时要求校验章节结构，一并并入输出
        section_check_passed = True
        if args.check_sections:
            inv_sec, ch_cnt = check_chapter_sections(outline_content)
            result["invalid_sections"] = inv_sec
            result["chapter_count"] = ch_cnt
            section_check_passed = (len(inv_sec) == 0 and ch_cnt > 0)

        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()

        # 判定退出码
        # 失败条件:
        # a. missing_refs 非空
        # b. pending_refs 未在待补数据节声明 (pending_declared 为 False)
        # c. strict 模式且 pending_refs 非空
        # d. check_sections 失败
        if len(missing_refs) > 0:
            sys.exit(1)
        if not pending_declared:
            sys.exit(1)
        if strict_mode and len(pending_refs) > 0:
            sys.exit(1)
        if not section_check_passed:
            sys.exit(1)

        sys.exit(0)

    # 若未指定任何动作，默认执行 check_sections
    invalid_sections, chapter_count = check_chapter_sections(outline_content)
    result = {
        "invalid_sections": invalid_sections,
        "chapter_count": chapter_count,
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    sys.exit(0 if len(invalid_sections) == 0 and chapter_count > 0 else 1)


if __name__ == "__main__":
    main()
