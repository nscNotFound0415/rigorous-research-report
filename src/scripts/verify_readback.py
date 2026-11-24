#!/usr/bin/env python3
"""
verify_readback.py - 四层回读复验、零漂移比对与复核调用证明校验工具
Universal Readback & Drift Verification Engine for M6 Review Loop and M8 Circuit

纯 Python 3 标准库实现，零第三方依赖，无外网访问。
符合 OpenSpec specs/adversarial-review/spec.md 与建设方案 v2.1 规范。

CLI 契约:
  1. 四层回读复验:
     python3 scripts/verify_readback.py --plan correction-diff.md --target draft_full.md
     stdout: {"layer1":true,"layer2_residuals":0,"layer3_match":true,"layer4_hash_match":true,"layer3":true,"layer4":true,"errors":[]}
     exit code: 0 通过 / 1 阻断

  2. 零漂移比对模式:
     python3 scripts/verify_readback.py --diff-mode --old backup/<file> --new <file> --declared <id>
     stdout: {"undeclared_drift":N,"declared_id":"...","drift_details":[...]}
     exit code: 0 (N == 0) / 1 (N > 0)

  3. 备份快照核验:
     python3 scripts/verify_readback.py --verify-backup backup/ [--change-table change-table.md] [--root <dir>]
     stdout: {"backup_present":true,"backup_valid":true,"backup_files":N,"hash_matched":true,"snapshot_path":"..."}
     exit code: 0 通过 / 1 阻断

  4. 复核调用证明校验:
     python3 scripts/verify_readback.py --check-provenance review-reports/<boundary>_provenance.json
     stdout: {"provenance_valid":true,"channel":"...","isolated":true,"boundary":"...","errors":[]}
     exit code: 0 隔离合规 / 1 隔离失败

  5. 辅助哈希计算:
     python3 scripts/verify_readback.py --compute-content-hash <file>
     python3 scripts/verify_readback.py --compute-nettext-hash <file>
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


def compute_file_sha256(file_path: str) -> str:
    """计算文件的二进制 SHA-256 哈希字符串"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def extract_nettext(text: str) -> str:
    """
    提取 Markdown 正文净文本 (Net Text):
    1. 剥离 YAML frontmatter
    2. 剥离 HTML 注释 (<!-- ... -->)
    3. 剥离 Markdown 表格分隔线 (|---|)
    4. 去除标题引导符 (#, ##) 与列表前缀 (-, *, 1.)
    5. 去除表格竖线，折叠多余空白符，按非空行合并为单文本
    """
    # 标准化换行符为 LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 1. 剥离 YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]

    # 2. 剥离 HTML 注释
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    clean_lines = []
    for line in text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue

        # 3. 忽略 Markdown 表格分隔线
        if re.match(r"^\|(?:\s*:?-+:?\s*\|)+\s*$", line_s):
            continue

        # 4. 去除标题前缀
        line_clean = re.sub(r"^#{1,6}\s+", "", line_s)
        # 去除无序列表前缀
        line_clean = re.sub(r"^[-*+]\s+", "", line_clean)
        # 去除有序列表前缀
        line_clean = re.sub(r"^\d+\.\s+", "", line_clean)

        # 5. 去除表格竖线并规范化空格
        line_clean = line_clean.replace("|", " ")
        line_clean = re.sub(r"\s+", " ", line_clean).strip()

        if line_clean:
            clean_lines.append(line_clean)

    return "\n".join(clean_lines)


def compute_nettext_sha256(file_path: str) -> str:
    """计算正文净文本的 SHA-256 哈希"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    net = extract_nettext(content)
    return hashlib.sha256(net.encode("utf-8")).hexdigest().lower()


def count_markdown_structures(text: str) -> Dict[str, int]:
    """
    解析 Markdown 结构块计数:
    - headings: ^#{1,6}\\s+
    - tables: 统计表格块总数
    - paragraphs: 非空连续文本块
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    headings = 0
    tables = 0
    in_table = False

    lines = text.splitlines()
    for line in lines:
        line_s = line.strip()
        if re.match(r"^#{1,6}\s+", line_s):
            headings += 1
            in_table = False
            continue

        if re.match(r"^\|(?:\s*:?-+:?\s*\|)+\s*$", line_s):
            if not in_table:
                tables += 1
                in_table = True
        elif not line_s.startswith("|"):
            in_table = False

    # 统计段落块 (连续非空、非标题、非表格、非纯注释行)
    paragraphs = 0
    in_para = False
    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.startswith("#") or line_s.startswith("|") or line_s == "---":
            in_para = False
            continue
        if re.match(r"^<!--.*?-->$", line_s):
            continue
        if not in_para:
            paragraphs += 1
            in_para = True

    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n+", text.strip()) if b.strip()]

    return {
        "headings": headings,
        "tables": tables,
        "paragraphs": paragraphs,
        "blocks": len(raw_blocks),
    }


def parse_correction_plan(plan_path: str) -> Dict[str, Any]:
    """
    解析 correction-diff.md 或类似修改对照稿:
    提取:
    - 逐条 patch: 原文 (old_sentence), 拟改为 (new_sentence), 缺陷级别 (grade), 处置类型, 人审裁决
    - 期望结构块: expected_headings, expected_tables, expected_paragraphs
    - 期望哈希: expected_content_sha256, expected_nettext_sha256
    - 声明的块 ID: declared_block_ids
    """
    with open(plan_path, "r", encoding="utf-8") as f:
        text = f.read()

    plan_data: Dict[str, Any] = {
        "items": [],
        "expected_headings": None,
        "expected_tables": None,
        "expected_paragraphs": None,
        "expected_blocks": None,
        "expected_content_sha256": None,
        "expected_nettext_sha256": None,
        "declared_block_ids": [],
    }

    # 1. 提取元信息与期望值
    m_head = re.search(r"expected_headings\s*:\s*(\d+)", text)
    if m_head:
        plan_data["expected_headings"] = int(m_head.group(1))

    m_tab = re.search(r"expected_tables\s*:\s*(\d+)", text)
    if m_tab:
        plan_data["expected_tables"] = int(m_tab.group(1))

    m_para = re.search(r"expected_paragraphs\s*:\s*(\d+)", text)
    if m_para:
        plan_data["expected_paragraphs"] = int(m_para.group(1))

    m_block = re.search(r"expected_blocks\s*:\s*(\d+)", text)
    if m_block:
        plan_data["expected_blocks"] = int(m_block.group(1))

    m_c_hash = re.search(
        r"(?:expected_)?content_sha256\s*:\s*[\"']?([a-fA-F0-9]{64})[\"']?", text
    )
    if m_c_hash:
        plan_data["expected_content_sha256"] = m_c_hash.group(1).lower()

    m_n_hash = re.search(
        r"(?:expected_)?nettext_sha256\s*:\s*[\"']?([a-fA-F0-9]{64})[\"']?", text
    )
    if m_n_hash:
        plan_data["expected_nettext_sha256"] = m_n_hash.group(1).lower()

    m_blocks = re.search(r"declared_block_ids\s*:\s*\[(.*?)\]", text)
    if m_blocks:
        ids_raw = m_blocks.group(1).split(",")
        plan_data["declared_block_ids"] = [
            i.strip().strip("\"' ") for i in ids_raw if i.strip().strip("\"' ")
        ]

    # 2. 提取对照表格中的条目
    lines = text.splitlines()
    table_lines = [l.strip() for l in lines if l.strip().startswith("|")]

    def clean_text_cell(cell: str) -> str:
        c = cell.strip()
        # 去除首尾常见的包裹引号
        if (c.startswith('"') and c.endswith('"')) or (
            c.startswith("“") and c.endswith("”")
        ):
            c = c[1:-1].strip()
        elif (c.startswith("'") and c.endswith("'")) or (
            c.startswith("`") and c.endswith("`")
        ):
            c = c[1:-1].strip()
        return c

    if len(table_lines) >= 2:
        header_line = table_lines[0]
        headers = [h.strip() for h in header_line.split("|")[1:-1]]

        col_map = {}
        for idx, h in enumerate(headers):
            if "条目" in h or "ID" in h.upper():
                col_map["id"] = idx
            elif "级别" in h or "等级" in h:
                col_map["grade"] = idx
            elif "原文" in h or "现状" in h or "旧口径" in h:
                col_map["old"] = idx
            elif "拟改" in h or "新口径" in h or "拟修订" in h:
                col_map["new"] = idx
            elif "处置" in h:
                col_map["disposition"] = idx
            elif "裁决" in h or "人审" in h:
                col_map["adjudication"] = idx

        for row in table_lines[1:]:
            if re.match(r"^\|(?:\s*:?-+:?\s*\|)+\s*$", row):
                continue
            parts = [p.strip() for p in row.split("|")[1:-1]]
            if len(parts) < len(headers):
                continue

            item_id = (
                parts[col_map["id"]]
                if "id" in col_map and col_map["id"] < len(parts)
                else f"ITEM-{len(plan_data['items'])+1}"
            )
            grade = (
                parts[col_map["grade"]]
                if "grade" in col_map and col_map["grade"] < len(parts)
                else "D0"
            )
            old_val = (
                clean_text_cell(parts[col_map["old"]])
                if "old" in col_map and col_map["old"] < len(parts)
                else ""
            )
            new_val = (
                clean_text_cell(parts[col_map["new"]])
                if "new" in col_map and col_map["new"] < len(parts)
                else ""
            )
            disp = (
                parts[col_map["disposition"]]
                if "disposition" in col_map and col_map["disposition"] < len(parts)
                else "修改"
            )
            adj = (
                parts[col_map["adjudication"]]
                if "adjudication" in col_map and col_map["adjudication"] < len(parts)
                else "[APPROVED]"
            )

            # 过滤模板占位符 ({{...}})
            if old_val.startswith("{{") and old_val.endswith("}}"):
                continue

            plan_data["items"].append(
                {
                    "id": item_id,
                    "grade": grade,
                    "old_text": old_val,
                    "new_text": new_val,
                    "disposition": disp,
                    "adjudication": adj,
                }
            )

    return plan_data


def verify_readback_layers(plan_path: str, target_path: str) -> Tuple[Dict[str, Any], int]:
    """
    四层回读复验:
    Layer 1: 新句在位 (新句 100% 存在于目标)
    Layer 2: 旧句零残留 (旧句残留次数 == 0)
    Layer 3: 结构块数一致 (实际标题数、表格数吻合声明)
    Layer 4: 双哈希匹配 (content_sha256 & nettext_sha256 吻合声明)
    """
    errors: List[str] = []

    if not os.path.exists(plan_path):
        return {
            "layer1": False,
            "layer2_residuals": -1,
            "layer3_match": False,
            "layer4_hash_match": False,
            "errors": [f"Plan file not found: {plan_path}"],
        }, 1

    if not os.path.exists(target_path):
        return {
            "layer1": False,
            "layer2_residuals": -1,
            "layer3_match": False,
            "layer4_hash_match": False,
            "errors": [f"Target file not found: {target_path}"],
        }, 1

    with open(target_path, "r", encoding="utf-8") as f:
        target_content = f.read()

    plan_data = parse_correction_plan(plan_path)

    # 1. Layer 1: 新句在位 (New Sentences Present)
    missing_new_sentences: List[str] = []
    items_to_check = [
        item
        for item in plan_data["items"]
        if "REJECTED" not in item["adjudication"].upper()
    ]

    for item in items_to_check:
        new_text = item["new_text"]
        # 如果是纯删除操作，新句可能为空；非空新句必须 100% 出现
        if new_text and new_text not in ("无", "-", "[已删除]", "[DELETED]"):
            if new_text not in target_content:
                missing_new_sentences.append(
                    f"[{item['id']}] '{new_text}' missing in target"
                )

    layer1 = len(missing_new_sentences) == 0
    if not layer1:
        errors.extend(missing_new_sentences)

    # 2. Layer 2: 旧句零残留 (Zero Residuals of Old Sentences)
    layer2_residuals = 0
    residual_details: List[str] = []

    for item in items_to_check:
        old_text = item["old_text"]
        new_text = item["new_text"]
        # 仅当旧句被要求修改或删除（且新句不同于旧句）时，检查旧句零残留
        if old_text and old_text != new_text:
            count = target_content.count(old_text)
            if count > 0:
                layer2_residuals += count
                residual_details.append(
                    f"[{item['id']}] Old text '{old_text}' found {count} time(s)"
                )

    if layer2_residuals > 0:
        errors.extend(residual_details)

    # 3. Layer 3: 结构块数保真 (Structural Block Counts)
    actual_structs = count_markdown_structures(target_content)
    layer3_match = True

    if plan_data["expected_headings"] is not None:
        if actual_structs["headings"] != plan_data["expected_headings"]:
            layer3_match = False
            errors.append(
                f"Headings count mismatch: actual={actual_structs['headings']}, expected={plan_data['expected_headings']}"
            )

    if plan_data["expected_tables"] is not None:
        if actual_structs["tables"] != plan_data["expected_tables"]:
            layer3_match = False
            errors.append(
                f"Tables count mismatch: actual={actual_structs['tables']}, expected={plan_data['expected_tables']}"
            )

    if plan_data["expected_paragraphs"] is not None:
        if actual_structs["paragraphs"] != plan_data["expected_paragraphs"]:
            layer3_match = False
            errors.append(
                f"Paragraphs count mismatch: actual={actual_structs['paragraphs']}, expected={plan_data['expected_paragraphs']}"
            )

    # 4. Layer 4: 双哈希匹配 (Dual Hash Match)
    actual_content_hash = compute_file_sha256(target_path)
    actual_nettext_hash = compute_nettext_sha256(target_path)
    layer4_hash_match = True

    if plan_data["expected_content_sha256"]:
        if actual_content_hash != plan_data["expected_content_sha256"]:
            layer4_hash_match = False
            errors.append(
                f"content_sha256 mismatch: actual={actual_content_hash}, expected={plan_data['expected_content_sha256']}"
            )

    if plan_data["expected_nettext_sha256"]:
        if actual_nettext_hash != plan_data["expected_nettext_sha256"]:
            layer4_hash_match = False
            errors.append(
                f"nettext_sha256 mismatch: actual={actual_nettext_hash}, expected={plan_data['expected_nettext_sha256']}"
            )

    overall_pass = (
        layer1
        and (layer2_residuals == 0)
        and layer3_match
        and layer4_hash_match
    )
    exit_code = 0 if overall_pass else 1

    result = {
        "layer1": layer1,
        "layer2_residuals": layer2_residuals,
        "layer3_match": layer3_match,
        "layer4_hash_match": layer4_hash_match,
        "layer3": layer3_match,
        "layer4": layer4_hash_match,
        "actual_content_sha256": actual_content_hash,
        "actual_nettext_sha256": actual_nettext_hash,
        "errors": errors,
    }
    return result, exit_code


def check_diff_mode(old_file: str, new_file: str, declared_id: str) -> Tuple[Dict[str, Any], int]:
    """
    零漂移比对模式:
    比对新旧文件差异，除被 declared_id 标识的声明区域外，
    未声明区域发生的任何字符级漂移均触发阻断 (undeclared_drift > 0 -> exit 1)。
    """
    if not os.path.exists(old_file):
        res = {
            "undeclared_drift": 1,
            "declared_id": declared_id,
            "error": f"Old file not found: {old_file}",
        }
        return res, 1

    if not os.path.exists(new_file):
        res = {
            "undeclared_drift": 1,
            "declared_id": declared_id,
            "error": f"New file not found: {new_file}",
        }
        return res, 1

    with open(old_file, "r", encoding="utf-8") as f:
        old_lines = f.readlines()
    with open(new_file, "r", encoding="utf-8") as f:
        new_lines = f.readlines()

    # 识别 declared_id 作用范围
    # 规则：声明区域可以是带有 declared_id 标记的行、所属小节或注记块
    # 例如：含有 declared_id 的标题所管辖的段落，或 <!-- block: <id> --> 注释包裹区，或行内 [declared_id]
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    opcodes = matcher.get_opcodes()

    undeclared_drift_count = 0
    drift_details: List[Dict[str, Any]] = []

    def is_line_in_declared_scope(lines: List[str], line_idx: int, target_id: str) -> bool:
        """检查给定行是否属于 target_id 所界定的修改范围"""
        if line_idx >= len(lines):
            return False

        current_line = lines[line_idx]
        if target_id in current_line:
            return True

        # 向上回溯查找当前行所属的最近标题或块注释
        for k in range(line_idx, -1, -1):
            cand = lines[k]
            if f"<!-- block: {target_id} -->" in cand or f"<!-- {target_id} -->" in cand:
                return True
            if cand.startswith("#"):
                if target_id in cand:
                    return True
                break  # 遇到上一级标题若不含 ID 则跳出
        return False

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue

        # 检查发生差异的范围
        # 若差异区域内的所有改动均在 declared_id 的作用域内，则属于合法变更
        is_declared = False

        # 1. 检查 old 侧
        for idx in range(i1, i2):
            if is_line_in_declared_scope(old_lines, idx, declared_id):
                is_declared = True
                break

        # 2. 检查 new 侧
        if not is_declared:
            for idx in range(j1, j2):
                if is_line_in_declared_scope(new_lines, idx, declared_id):
                    is_declared = True
                    break

        if not is_declared:
            # 属于未声明区域发生漂移！
            deleted_chars = sum(len(old_lines[x]) for x in range(i1, i2))
            inserted_chars = sum(len(new_lines[y]) for y in range(j1, j2))
            drift_magnitude = deleted_chars + inserted_chars

            undeclared_drift_count += drift_magnitude
            drift_details.append(
                {
                    "tag": tag,
                    "old_lines_range": [i1 + 1, i2],
                    "new_lines_range": [j1 + 1, j2],
                    "old_snippet": [old_lines[x].strip() for x in range(i1, i2)][:3],
                    "new_snippet": [new_lines[y].strip() for y in range(j1, j2)][:3],
                    "drift_chars": drift_magnitude,
                }
            )

    exit_code = 0 if undeclared_drift_count == 0 else 1
    result = {
        "undeclared_drift": undeclared_drift_count,
        "declared_id": declared_id,
        "drift_details": drift_details,
    }
    return result, exit_code


def verify_backup_directory(
    backup_path: str, change_table_path: Optional[str] = None, root_dir: str = "."
) -> Tuple[Dict[str, Any], int]:
    """
    备份快照核验:
    1. 校验 backup 目录存在且包含非空快照文件；
    2. 若提供 change-table.md，核验快照哈希与 parent_baseline_sha256 是否完全吻合。
    """
    target_backup = (
        backup_path
        if os.path.isabs(backup_path)
        else os.path.normpath(os.path.join(root_dir, backup_path))
    )

    if not os.path.exists(target_backup) or not os.path.isdir(target_backup):
        return {
            "backup_present": False,
            "backup_valid": False,
            "backup_files": 0,
            "hash_matched": False,
            "reason": f"Backup directory not found: {target_backup}",
        }, 1

    # 遍历获取备份目录下的所有实体文件
    backup_files = []
    for root, _, files in os.walk(target_backup):
        for f in files:
            full_p = os.path.join(root, f)
            if os.path.getsize(full_p) > 0:
                backup_files.append(full_p)

    if len(backup_files) == 0:
        return {
            "backup_present": False,
            "backup_valid": False,
            "backup_files": 0,
            "hash_matched": False,
            "reason": f"No valid non-empty snapshot files found in: {target_backup}",
        }, 1

    expected_parent_hash = None
    if change_table_path:
        ct_path = (
            change_table_path
            if os.path.isabs(change_table_path)
            else os.path.normpath(os.path.join(root_dir, change_table_path))
        )
        if os.path.exists(ct_path):
            with open(ct_path, "r", encoding="utf-8") as f:
                ct_text = f.read()
            m = re.search(
                r"parent_baseline_sha256\s*:\s*[\"']?([a-fA-F0-9]{64})[\"']?", ct_text
            )
            if m:
                expected_parent_hash = m.group(1).lower()

    hash_matched = True
    matched_snapshot = backup_files[0]

    if expected_parent_hash:
        hash_matched = False
        for bf in backup_files:
            h = compute_file_sha256(bf)
            if h == expected_parent_hash:
                hash_matched = True
                matched_snapshot = bf
                break

    exit_code = 0 if hash_matched else 1
    result = {
        "backup_present": True,
        "backup_valid": True,
        "backup_files": len(backup_files),
        "hash_matched": hash_matched,
        "snapshot_path": matched_snapshot,
    }
    return result, exit_code


def get_model_vendor(model_name: str) -> str:
    """提取大模型厂商标识 (Canonical Vendor Prefix)"""
    m = model_name.strip().lower()
    # 去除 path prefix (例: openai/gpt-4 -> gpt-4)
    if "/" in m:
        m = m.split("/")[-1]

    VENDOR_PREFIX_MAP = {
        "gpt": "openai",
        "o1": "openai",
        "o3": "openai",
        "openai": "openai",
        "claude": "anthropic",
        "anthropic": "anthropic",
        "deepseek": "deepseek",
        "gemini": "google",
        "google": "google",
        "minimax": "minimax",
        "qwen": "alibaba",
        "alibaba": "alibaba",
        "antigravity": "deepmind",
    }

    for prefix, vendor in VENDOR_PREFIX_MAP.items():
        if m.startswith(prefix):
            return vendor

    # 默认返回第一个以 - 或 _ 分割的 token
    tokens = re.split(r"[-_]", m)
    return tokens[0] if tokens else m


def verify_provenance_file(prov_path: str, root_dir: str = ".") -> Tuple[Dict[str, Any], int]:
    """
    复核调用证明校验 [CRITERION M6-2]:
    1. 若 gate_guard.py 已具备 --check-provenance 则优先调用并透传
    2. 否则按规格直接判定：
       - boundary ∈ {datatable, outline, draft_full}
       - writer.session ≠ reviewer.session
       - 当 channel = 异族 时，model 厂商前缀必须不同
       - 当 channel = 同族-零记忆隔离 时，context_reset 必须为 true 且 reviewer.session 为新建会话
    """
    target_prov = (
        prov_path
        if os.path.isabs(prov_path)
        else os.path.normpath(os.path.join(root_dir, prov_path))
    )

    if not os.path.exists(target_prov):
        return {
            "provenance_valid": False,
            "isolated": False,
            "errors": [f"Provenance file not found: {target_prov}"],
        }, 1

    # 尝试检查 gate_guard.py 是否原生支持 --check-provenance
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    gate_guard_script = os.path.join(scripts_dir, "gate_guard.py")
    if os.path.exists(gate_guard_script):
        try:
            # 探测帮助信息中是否包含 check-provenance
            probe = subprocess.run(
                [sys.executable, gate_guard_script, "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "--check-provenance" in probe.stdout:
                call_res = subprocess.run(
                    [sys.executable, gate_guard_script, "--check-provenance", target_prov],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                try:
                    out_json = json.loads(call_res.stdout.strip())
                    return out_json, call_res.returncode
                except Exception:
                    pass
        except Exception:
            pass

    # 原生独立校验逻辑
    try:
        with open(target_prov, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "provenance_valid": False,
            "isolated": False,
            "errors": [f"JSON parse error: {str(e)}"],
        }, 1

    errors: List[str] = []

    # 1. boundary 字段校验
    boundary = data.get("boundary", "")
    valid_boundaries = {"datatable", "outline", "draft_full"}
    if boundary not in valid_boundaries:
        errors.append(
            f"Invalid boundary '{boundary}', expected one of {sorted(list(valid_boundaries))}"
        )

    # 2. writer & reviewer 结构校验
    writer = data.get("writer", {})
    reviewer = data.get("reviewer", {})

    if not isinstance(writer, dict) or not isinstance(reviewer, dict):
        errors.append("Fields 'writer' and 'reviewer' must be JSON objects")
        return {"provenance_valid": False, "isolated": False, "errors": errors}, 1

    w_session = str(writer.get("session", "")).strip()
    r_session = str(reviewer.get("session", "")).strip()
    w_model = str(writer.get("model", "")).strip()
    r_model = str(reviewer.get("model", "")).strip()
    channel = str(reviewer.get("channel", "")).strip()
    context_reset = reviewer.get("context_reset")

    if not w_session:
        errors.append("writer.session cannot be empty")
    if not r_session:
        errors.append("reviewer.session cannot be empty")

    # 断言 1: 会话必须分离
    if w_session and r_session and w_session == r_session:
        errors.append(
            f"Reviewer session matches writer session '{w_session}', isolation violated"
        )

    # 断言 2: 通道与异族/同族校验
    if channel == "异族":
        w_vendor = get_model_vendor(w_model)
        r_vendor = get_model_vendor(r_model)
        if not w_vendor or not r_vendor or w_vendor == r_vendor:
            errors.append(
                f"Channel '异族' requires distinct model vendors: writer='{w_vendor}', reviewer='{r_vendor}'"
            )
    elif channel == "同族-零记忆隔离":
        if context_reset is not True and str(context_reset).lower() != "true":
            errors.append(
                "Channel '同族-零记忆隔离' requires reviewer.context_reset to be strictly true"
            )
    else:
        errors.append(
            f"Invalid channel '{channel}', expected '异族' or '同族-零记忆隔离'"
        )

    # 断言 3: read_only_verified
    if not data.get("read_only_verified"):
        errors.append("Field 'read_only_verified' must be true")

    isolated = len(errors) == 0
    exit_code = 0 if isolated else 1

    res = {
        "provenance_valid": isolated,
        "channel": channel,
        "isolated": isolated,
        "boundary": boundary,
        "status": "VERIFIED" if isolated else "BLOCKED_NO_REVIEWER",
        "errors": errors,
    }
    return res, exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Universal Readback & Drift Verification Engine for M6 & M8"
    )

    # 模式 1: 四层回读复验
    parser.add_argument("--plan", type=str, help="Path to correction-diff.md plan")
    parser.add_argument("--target", type=str, help="Path to target markdown artifact")

    # 模式 2: 零漂移比对
    parser.add_argument("--diff-mode", action="store_true", help="Run in zero-drift comparison mode")
    parser.add_argument("--old", type=str, help="Path to old baseline file")
    parser.add_argument("--new", type=str, help="Path to new modified file")
    parser.add_argument("--declared", type=str, help="Declared block or section ID allowed to change")

    # 模式 3: 备份快照核验
    parser.add_argument(
        "--verify-backup",
        nargs="?",
        const="backup",
        default=None,
        help="Verify backup snapshot directory (default: backup/)",
    )
    parser.add_argument("--change-table", type=str, help="Optional path to change-table.md for parent hash matching")
    parser.add_argument("--root", type=str, default=".", help="Root workspace directory")

    # 模式 4: 复核调用证明校验
    parser.add_argument("--check-provenance", type=str, help="Verify review provenance JSON file")

    # 辅助计算
    parser.add_argument("--compute-content-hash", type=str, help="Compute file content SHA-256")
    parser.add_argument("--compute-nettext-hash", type=str, help="Compute file nettext SHA-256")

    args = parser.parse_args()

    # 辅助哈希计算
    if args.compute_content_hash:
        target = args.compute_content_hash
        if not os.path.exists(target):
            sys.stderr.write(f"File not found: {target}\n")
            sys.exit(1)
        h = compute_file_sha256(target)
        sys.stdout.write(json.dumps({"file": target, "content_sha256": h}) + "\n")
        sys.exit(0)

    if args.compute_nettext_hash:
        target = args.compute_nettext_hash
        if not os.path.exists(target):
            sys.stderr.write(f"File not found: {target}\n")
            sys.exit(1)
        h = compute_nettext_sha256(target)
        sys.stdout.write(json.dumps({"file": target, "nettext_sha256": h}) + "\n")
        sys.exit(0)

    # 模式 4: 独立复核证明校验
    if args.check_provenance:
        res, code = verify_provenance_file(args.check_provenance, root_dir=args.root)
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    # 模式 2: 零漂移比对
    if args.diff_mode:
        if not args.old or not args.new or not args.declared:
            sys.stderr.write("Diff mode requires --old, --new, and --declared <id>\n")
            sys.exit(1)
        res, code = check_diff_mode(args.old, args.new, args.declared)
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    # 模式 3: 备份快照核验
    if args.verify_backup is not None:
        backup_dir = args.verify_backup if args.verify_backup != "backup" else "backup"
        res, code = verify_backup_directory(
            backup_dir, change_table_path=args.change_table, root_dir=args.root
        )
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    # 模式 1: 四层回读复验
    if args.plan and args.target:
        res, code = verify_readback_layers(args.plan, args.target)
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
