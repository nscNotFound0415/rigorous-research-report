#!/usr/bin/env python3
"""
audit_text_hygiene.py - 元叙述与自述词扫描工具（含 9 类严谨性声明白名单保护）
Text Hygiene & Rigor Declaration Protection Audit Tool for M7 Delivery

纯 Python 3 标准库实现，零第三方依赖，无外网访问。
符合 OpenSpec specs/draft-synthesis/spec.md 与建设方案 v2.1 规范。

CLI 契约:
  python3 scripts/audit_text_hygiene.py draft_full.md --rules templates/forbidden_terms.json [--check-dedup]
  stdout: {"violations":[]} 或 {"violations":[],"shared_substrings":[]}
  退出码: 0 (合规通过) / 1 (检出未在白名单保护的违规项)
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


def load_rules(rules_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """加载违禁规则 patterns 与严谨性声明白名单 allowlist。"""
    if not os.path.exists(rules_path):
        # 尝试常见备选相对路径
        candidates = [
            rules_path,
            os.path.join("src", "templates", os.path.basename(rules_path)),
            os.path.join("templates", os.path.basename(rules_path)),
        ]
        for c in candidates:
            if os.path.exists(c):
                rules_path = c
                break

    if not os.path.exists(rules_path):
        raise FileNotFoundError(f"Rules configuration not found: {rules_path}")

    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    patterns = data.get("patterns", [])
    allowlist = data.get("allowlist", [])
    return patterns, allowlist


def split_sentences(text: str) -> List[str]:
    """按句号、感叹号、问号、分号将文本切分为完整独立句。"""
    delimiters = r"[。！？；\n]"
    raw_sentences = re.split(delimiters, text)
    return [s.strip() for s in raw_sentences if s.strip()]


def split_line_into_sentences(line: str) -> List[Tuple[str, int, int]]:
    """
    按中文句末标点（。！？；）将单行文本切分为独立句子列表。
    返回 [(sentence_text, start_idx, end_idx), ...]
    """
    delimiters = set("。！？；\n")
    sentences: List[Tuple[str, int, int]] = []
    start = 0
    n = len(line)
    for i, ch in enumerate(line):
        if ch in delimiters:
            seg = line[start:i].strip()
            if seg:
                sentences.append((seg, start, i))
            start = i + 1
    if start < n:
        seg = line[start:].strip()
        if seg:
            sentences.append((seg, start, n))
    return sentences


def find_containing_sentence(line: str, match_start: int, match_end: int) -> str:
    """获取命中文本所在的句子上下文。"""
    delimiters = "。！？；\n"
    start = match_start
    while start > 0 and line[start - 1] not in delimiters:
        start -= 1
    end = match_end
    while end < len(line) and line[end] not in delimiters:
        end += 1
    sentence = line[start:end].strip()
    return sentence if sentence else line.strip()


def check_allowlist_match(
    matched_text: str,
    match_start: int,
    match_end: int,
    sentence: str,
    allowlist: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    检查命中文本是否落在某个白名单保护区间内（如合法技术术语闭环控制保护其中闭环词）。
    某句命中白名单则该白名单声明覆盖区间免检，同句命中违禁 patterns 仍报违规；
    跨句的严谨性声明不得豁免同行的违禁句。
    """
    for allow_entry in allowlist:
        allow_regex = allow_entry.get("regex", "")
        if not allow_regex:
            continue
        for am in re.finditer(allow_regex, sentence):
            # 若违禁匹配区间完全落在白名单匹配区间内，则视为受保护豁免
            if am.start() <= match_start and match_end <= am.end():
                return allow_entry
    return None


def audit_text_hygiene(
    file_path: str,
    patterns: List[Dict[str, Any]],
    allowlist: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """扫描文件中的元叙述、自述词及占位符，返回未受白名单保护的违规列表。"""
    violations: List[Dict[str, Any]] = []

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Target markdown draft not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    compiled_patterns = []
    for pat in patterns:
        try:
            compiled = re.compile(pat["regex"])
            compiled_patterns.append((pat, compiled))
        except re.error as e:
            sys.stderr.write(f"Warning: Invalid regex for pattern {pat.get('id')}: {e}\n")

    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        # 跳过纯注释行或 frontmatter 边界
        if not line or line.startswith("<!--") or line == "---":
            continue

        # 逐句切分判定
        sentences = split_line_into_sentences(raw_line)
        for sent_text, sent_start, sent_end in sentences:
            for pat_dict, regex in compiled_patterns:
                for match in regex.finditer(sent_text):
                    matched_text = match.group(0)
                    m_start = match.start()
                    m_end = match.end()

                    # 白名单逐句保护判定
                    allow_entry = check_allowlist_match(
                        matched_text, m_start, m_end, sent_text, allowlist
                    )
                    if allow_entry:
                        # 严谨性声明保护生效，跳过记录
                        continue

                    violations.append({
                        "line": line_idx,
                        "rule_id": pat_dict.get("id", "UNKNOWN"),
                        "matched_text": matched_text,
                        "sentence": sent_text,
                        "description": pat_dict.get("description", ""),
                    })

    return violations


def extract_sections(text: str) -> Dict[str, str]:
    """提取按二级标题（## ）或一级标题（# ）划分的章节净文本字典。"""
    sections: Dict[str, List[str]] = {}
    current_sec = "SECTION_HEADER"
    sections[current_sec] = []

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if heading_match:
            current_sec = heading_match.group(2).strip()
            sections[current_sec] = []
        else:
            cleaned = line.strip()
            # 忽略空行、表格分隔线与引用标记
            if cleaned and not cleaned.startswith("|") and not cleaned.startswith("<!--"):
                sections[current_sec].append(cleaned)

    result = {}
    for sec_name, sec_lines in sections.items():
        joined = "".join(sec_lines)
        if len(joined) >= 30:
            result[sec_name] = joined
    return result


def check_section_deduplication(
    file_path: str,
    threshold: int = 30,
) -> List[Dict[str, Any]]:
    """
    检查章节间去重判据：
    任意两节间不存在共享的连续 >= 30 字符子串。
    """
    shared_substrings: List[Dict[str, Any]] = []
    if not os.path.exists(file_path):
        return shared_substrings

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = extract_sections(content)
    sec_names = list(sections.keys())

    for i in range(len(sec_names)):
        for j in range(i + 1, len(sec_names)):
            sec_a = sec_names[i]
            sec_b = sec_names[j]
            text_a = sections[sec_a]
            text_b = sections[sec_b]

            # 寻找共享连续子串长度 >= threshold
            found_shared_for_pair = False
            for start in range(len(text_a) - threshold + 1):
                sub = text_a[start : start + threshold]
                if sub in text_b:
                    # 扩展到最长连续公共子串
                    end = start + threshold
                    while end <= len(text_a) and text_a[start:end] in text_b:
                        end += 1
                    longest_sub = text_a[start : end - 1]
                    shared_substrings.append({
                        "section_a": sec_a,
                        "section_b": sec_b,
                        "length": len(longest_sub),
                        "shared_text": longest_sub,
                    })
                    found_shared_for_pair = True
                    break
            if found_shared_for_pair:
                continue

    return shared_substrings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="audit_text_hygiene.py - 元叙述与自述词扫描工具（含 9 类严谨性声明白名单保护）"
    )
    parser.add_argument("draft", help="目标 Markdown 草稿文件路径 (如 draft_full.md)")
    parser.add_argument(
        "--rules",
        default="src/templates/forbidden_terms.json",
        help="违禁词与白名单规则配置文件路径 (默认: src/templates/forbidden_terms.json)",
    )
    parser.add_argument(
        "--check-dedup",
        action="store_true",
        help="启用跨章节连续 30 字符子串去重检查",
    )
    parser.add_argument(
        "--dedup-threshold",
        type=int,
        default=30,
        help="章节去重判据子串长度阈值 (默认: 30)",
    )

    args = parser.parse_args()

    try:
        patterns, allowlist = load_rules(args.rules)
        violations = audit_text_hygiene(args.draft, patterns, allowlist)

        output: Dict[str, Any] = {"violations": violations}

        if args.check_dedup:
            shared_subs = check_section_deduplication(args.draft, threshold=args.dedup_threshold)
            output["shared_substrings"] = shared_subs

        # 输出紧凑单行 JSON 保证管道安全
        print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))

        # 退出码判定：无违规且无重复子串退出 0，否则退出 1
        has_error = len(violations) > 0
        if args.check_dedup and len(output.get("shared_substrings", [])) > 0:
            has_error = True

        sys.exit(1 if has_error else 0)

    except Exception as e:
        err_out = {"violations": [], "error": str(e)}
        print(json.dumps(err_out, ensure_ascii=False, separators=(",", ":")))
        sys.exit(1)


if __name__ == "__main__":
    main()
