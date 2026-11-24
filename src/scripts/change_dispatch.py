#!/usr/bin/env python3
"""
change_dispatch.py - 变更管理与动态维护回路调度编排器
Universal Change Dispatcher & Maintenance Circuit Orchestrator for M8

纯 Python 3 标准库实现，零外部依赖，无外网访问。
符合 OpenSpec specs/change-circuit/spec.md 与建设方案 v2.1 规范。

作为 M8 模块的核心编排器，本脚本协调调用既有工具链：
- gate_guard.py: 变更门禁签署校验 (change-<id>)
- adapter_git_sync.py: 母本只读快照归档 (--snapshot)
- verify_readback.py: 零漂移比对 (--diff-mode) 与备份核验 (--verify-backup)

CLI 契约:
1. 分类与影响分析:
   python3 scripts/change_dispatch.py --root <dir> --instruction-file <file> --classify
   stdout: {"change_id":"...","ceremony_level":"LIGHTWEIGHT|MAJOR","impacted_sections":[...],"affected_evidence_ids":[...],"requires_human_signoff":true}
   exit code: 0 / 1

2. 变更实施执行:
   python3 scripts/change_dispatch.py --root <dir> --apply --change-table <file> [--target <file>] [--declared <id>]
   - 未获签署放行时:
     stdout: {"applied":false,"blocked":true,"reason":"missing_change_approval"}
     exit code: 1
   - 获放行且零漂移核验通过时:
     stdout: {"applied":true,"backup":"...","undeclared_drift":0,"verified":true}
     exit code: 0

3. 变更实施后审计:
   python3 scripts/change_dispatch.py --root <dir> --audit --change-table <file>
   stdout: {"audit_present":true,"backup_present":true,"undeclared_drift":0}
   exit code: 0 / 1
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# 本脚本自身位于 <repo>/src/scripts/；任何写操作严禁落入 <repo>/src/ 目录。
_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_ROOT = os.path.dirname(_SELF_DIR)


def is_under_src(path: str) -> bool:
    """判断给定路径是否位于源码目录 src/ 之内（模板与脚本均属只读资产）。"""
    abs_path = os.path.abspath(path)
    return abs_path == _SRC_ROOT or abs_path.startswith(_SRC_ROOT + os.sep)


def resolve_input_path(path: str, root_dir: str) -> str:
    """
    解析只读输入路径：绝对路径原样返回；相对路径优先按当前工作目录解析
    （若该路径真实存在），否则回落到以 root_dir 为基准。
    避免把调用方基于 cwd 给出的相对路径二次拼接到 root 下。
    """
    if os.path.isabs(path):
        return os.path.normpath(path)
    cwd_candidate = os.path.abspath(path)
    if os.path.exists(cwd_candidate):
        return os.path.normpath(cwd_candidate)
    return os.path.normpath(os.path.join(root_dir, path))


def find_script(script_name: str, root_dir: str) -> str:
    """定位同伴脚本路径 (优先当前脚本所在目录，其次 src/scripts/ 与 scripts/)"""
    self_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(self_dir, script_name),
        os.path.join(root_dir, "src", "scripts", script_name),
        os.path.join(root_dir, "scripts", script_name),
        os.path.join(root_dir, script_name),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return os.path.abspath(c)
    # 默认返回 self_dir 下的路径
    return os.path.join(self_dir, script_name)


def compute_file_sha256(file_path: str) -> str:
    """计算二进制 SHA-256 哈希"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_nettext_sha256(file_path: str) -> str:
    """计算净文本 SHA-256 哈希 (忽略空白行与前后空白)"""
    lines = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
    normalized = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def run_command(cmd: List[str], cwd: str) -> Tuple[int, str, str]:
    """安全执行子命令"""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


# ---------------------------------------------------------------------------
# 1. 分类与影响分析 (--classify)
# ---------------------------------------------------------------------------

MAJOR_KEYWORDS = [
    "口径重构", "重排", "结构重组", "颠覆", "推翻", "重大", "架构重构",
    "口径变更", "全篇重写", "整体重构", "核算模型替换", "结论颠覆",
    "architecture_shift", "major", "restructure", "recalculate_all",
    "overhaul", "pivot", "refactor"
]

LIGHTWEIGHT_KEYWORDS = [
    "微调", "措辞", "评级", "调整为", "修补", "增补", "勘误", "润色",
    "段落润色", "局部修正", "tweak", "minor", "wording", "rating", "patch"
]


def classify_instruction(instruction_path: str, root_dir: str) -> Tuple[Dict[str, Any], int]:
    """
    解析外部指示文件，判定变更分级并提取受影响章节与证据 ID
    """
    instruction_path = resolve_input_path(instruction_path, root_dir)

    if not os.path.exists(instruction_path):
        err = {
            "error": f"Instruction file not found: {instruction_path}",
            "requires_human_signoff": True,
        }
        return err, 1

    with open(instruction_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # 1. 提取 change_id
    change_id = "change-01"
    m_id = re.search(r"(?:change_id|change-id|id)\s*[:=]\s*[\"']?([a-zA-Z0-9_-]+)[\"']?", content, re.IGNORECASE)
    if m_id:
        change_id = m_id.group(1).strip()
    else:
        m_tag = re.search(r"\[?(change-[a-zA-Z0-9_-]+)\]?", content, re.IGNORECASE)
        if m_tag:
            change_id = m_tag.group(1).strip()
        else:
            m_c = re.search(r"\b(C-[0-9]{2,})\b", content)
            if m_c:
                change_id = f"change-{m_c.group(1).lower()}"

    # 2. 变更分级判定 (Ceremony Level Triage)
    is_major = any(kw in content for kw in MAJOR_KEYWORDS)
    ceremony_level = "MAJOR" if is_major else "LIGHTWEIGHT"

    # 3. 提取受影响章节与图表定位 (Impacted Sections)
    impacted_sections: List[str] = []
    # 模式匹配: 第X.X节 / 第X章 / 表X-X / 图X-X / 模式X
    section_patterns = [
        r"第\s*[0-9一二三四五六七八九十]+(?:\.[0-9]+)*\s*[章节段]",
        r"表\s*[0-9]+(?:-[0-9]+)?",
        r"图\s*[0-9]+(?:-[0-9]+)?",
        r"模式[一二三四1234二两]",
        r"第\s*[0-9]+\s*部分",
        r"\b\d+\.\d+(?:\.\d+)?\b",
    ]
    for p in section_patterns:
        matches = re.findall(p, content)
        for m in matches:
            clean_m = re.sub(r"\s+", "", m)
            if clean_m not in impacted_sections:
                impacted_sections.append(clean_m)

    # 显式列表提取
    m_sec_block = re.search(r"(?:impacted_sections|受影响章节|涉及章节)\s*[:：]\s*\n((?:\s*[-*]\s*.*?\n)+)", content, re.IGNORECASE)
    if m_sec_block:
        for line in m_sec_block.group(1).splitlines():
            item = re.sub(r"^\s*[-*]\s*", "", line).strip()
            item = item.strip("\"'[]")
            if item and item not in impacted_sections:
                impacted_sections.append(item)

    if not impacted_sections:
        # 若未精准匹配章节，推断指示文本核心主题词
        if "评级" in content or "模式" in content:
            impacted_sections.append("业务模式评级章节")
        else:
            impacted_sections.append("全文受影响小节")

    # 4. 提取受影响证据 ID
    affected_evidence_ids: List[str] = []
    evidence_matches = re.findall(r"\b(?:E|EV|S|REF|SRC)-[0-9A-Za-z_-]+\b", content)
    for ev in evidence_matches:
        if ev not in affected_evidence_ids:
            affected_evidence_ids.append(ev)

    # 显式列表提取
    m_ev_block = re.search(r"(?:affected_evidence_ids|涉及证据|受影响证据)\s*[:：]\s*\n((?:\s*[-*]\s*.*?\n)+)", content, re.IGNORECASE)
    if m_ev_block:
        for line in m_ev_block.group(1).splitlines():
            item = re.sub(r"^\s*[-*]\s*", "", line).strip()
            item = item.strip("\"'[]")
            if item and item not in affected_evidence_ids:
                affected_evidence_ids.append(item)

    # 5. 计算失效传播目标 (stale_targets)
    m_nature = re.search(r"change_nature\s*[:：]\s*[\"']?([a-zA-Z0-9_-]+)[\"']?", content)
    change_nature = m_nature.group(1).lower() if m_nature else ""

    is_brief = (
        change_nature in ("brief_change", "brief_field_change")
        or any(k in content for k in ["brief变更", "简报变更", "背景变更", "读者变更", "格式变更", "权威载体变更", "source_of_truth"])
    )
    is_new_fact = (
        change_nature == "new_evidence"
        or (any(k in content for k in ["一手事实", "新增事实", "修正事实", "底表数值", "fact-store"]) and not is_brief)
    )

    if is_major or change_nature == "architecture_shift":
        stale_targets = ["ALL"]
    elif is_brief:
        stale_targets = [
            "G0", "T-P2-01", "T-P3-01", "T-P4-01", "T-P4-02", "T-P5-01",
            "T-G1-01", "T-P5-02", "T-P6-01", "T-P6-02", "T-G2-01",
            "T-P6-03", "T-P6-04", "T-G3-01"
        ]
    elif is_new_fact:
        stale_targets = [
            "datatable_rows", "T-P4-01", "T-P4-02", "M5b", "T-G1-01",
            "T-P6-01", "T-P6-02", "T-G3-01"
        ]
    else:  # 领导指示 (directive / scope_tweak / 文本层)
        stale_targets = list(dict.fromkeys(impacted_sections + ["T-P6-01", "T-P6-03", "T-G2-01"]))

    result = {
        "change_id": change_id,
        "ceremony_level": ceremony_level,
        "impacted_sections": impacted_sections,
        "affected_evidence_ids": affected_evidence_ids,
        "requires_human_signoff": True,
        "stale_targets": stale_targets,
    }
    return result, 0


# ---------------------------------------------------------------------------
# 2. 对照表解析与条目提取
# ---------------------------------------------------------------------------

def parse_change_table(table_path: str, root_dir: str) -> Dict[str, Any]:
    """
    解析 change-table.md 文件中的元数据与逐条修改项
    """
    table_path = resolve_input_path(table_path, root_dir)

    if not os.path.exists(table_path):
        return {}

    with open(table_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    full_text = "".join(lines)
    data: Dict[str, Any] = {
        "file_path": table_path,
        "change_id": "change-01",
        "parent_baseline_file": "draft_full.md",
        "parent_baseline_sha256": None,
        "approval_signoff": None,
        "ceremony_level": "LIGHTWEIGHT",
        "entries": [],
    }

    # 提取键值元信息
    kv_pattern = re.compile(r"^\s*(?:-\s+)?([a-zA-Z0-9_-]+)\s*[:：]\s*[\"']?(.*?)[\"']?\s*$")
    for line in lines:
        m = kv_pattern.match(line.strip())
        if m:
            k, v = m.group(1).strip(), m.group(2).strip()
            if k == "change_id":
                data["change_id"] = v
            elif k in ("parent_baseline_file", "target_file"):
                data["parent_baseline_file"] = v
            elif k == "parent_baseline_sha256":
                data["parent_baseline_sha256"] = v.lower()
            elif k in ("approval_signoff", "approval_path"):
                data["approval_signoff"] = v
            elif k == "ceremony_level":
                data["ceremony_level"] = v.upper()

    # 提取变更矩阵中的条目
    # 格式: | 条目 ID | 外部指示/输入原文 | 涉及章节与定位 | 涉及图表/证据 ID | 现状表述/旧口径 | 拟修订表述/新方案 | ... | 人审状态 |
    table_rows = [l.strip() for l in lines if l.strip().startswith("|") and not l.strip().startswith("|---")]
    for r in table_rows:
        parts = [p.strip() for p in r.strip("|").split("|")]
        if len(parts) >= 6:
            entry_id = parts[0].strip()
            # 排除表头行
            if entry_id in ("条目 ID", "条目ID", "ID", "item_id", "entry_id"):
                continue

            directive_text = parts[1].strip().strip("\"'")
            location = parts[2].strip()

            # 兼容 7 列、8 列或 9 列格式
            if len(parts) >= 8:
                old_text = parts[4].strip().strip("\"'")
                new_text = parts[5].strip().strip("\"'")
                status = parts[-1].strip().strip("[]")
            else:
                old_text = parts[3].strip().strip("\"'")
                new_text = parts[4].strip().strip("\"'")
                status = parts[-1].strip().strip("[]")

            data["entries"].append({
                "entry_id": entry_id,
                "directive": directive_text,
                "location": location,
                "old_text": old_text,
                "new_text": new_text,
                "status": status,
            })

    return data


# ---------------------------------------------------------------------------
# 3. 变更实施执行 (--apply)
# ---------------------------------------------------------------------------

def apply_change_table(
    table_path: str,
    root_dir: str,
    target_override: Optional[str] = None,
    declared_override: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    执行维护回路应用实施:
    1. 内部调用 gate_guard.py --gate change-<id> --check-only 验证签署件。未放行则无条件拒绝 (exit 1)。
    2. 放行后，调用 adapter_git_sync.py --snapshot 产生变更前快照。
    3. 执行精准局部改写。
    4. 调用 verify_readback.py --diff-mode 验证非声明区域零漂移。
    5. 记录执行留痕并输出。
    """
    table_data = parse_change_table(table_path, root_dir)
    if not table_data:
        res = {
            "applied": False,
            "blocked": True,
            "reason": f"Change table not found or empty: {table_path}",
        }
        return res, 1

    change_id = table_data.get("change_id", "change-01")
    # 门禁名称归一化
    norm_gate = change_id if change_id.lower().startswith("change-") else f"change-{change_id}"

    # 确定目标母本文件
    target_rel = target_override or table_data.get("parent_baseline_file", "draft_full.md")
    target_abs = target_rel if os.path.isabs(target_rel) else os.path.normpath(os.path.join(root_dir, target_rel))

    if is_under_src(target_abs):
        return {
            "applied": False,
            "blocked": True,
            "reason": "refuse_to_write_src_assets",
            "target": target_abs,
        }, 1

    if not os.path.exists(target_abs):
        res = {
            "applied": False,
            "blocked": True,
            "reason": f"Target baseline file not found: {target_abs}",
        }
        return res, 1

    # 1. 门禁签署校验 (Gate Guard Check)
    gate_guard_script = find_script("gate_guard.py", root_dir)
    gate_cmd = [
        sys.executable,
        gate_guard_script,
        "--gate", norm_gate,
        "--check-only",
        "--root", root_dir,
    ]
    gate_code, gate_out, gate_err = run_command(gate_cmd, cwd=root_dir)

    if gate_code != 0:
        # 未获放行，必须拒绝执行！
        res = {
            "applied": False,
            "blocked": True,
            "reason": "missing_change_approval",
        }
        return res, 1

    # 2. 生成变更前快照归档 (Snapshot via adapter_git_sync.py)
    adapter_script = find_script("adapter_git_sync.py", root_dir)
    snap_cmd = [
        sys.executable,
        adapter_script,
        "--root", root_dir,
        "--snapshot", norm_gate,
        "--target", target_abs,
    ]
    snap_code, snap_out, snap_err = run_command(snap_cmd, cwd=root_dir)

    snapshot_dir = ""
    snapshot_file = ""
    try:
        snap_json = json.loads(snap_out)
        snapshot_dir = snap_json.get("snapshot_dir", "")
        if snapshot_dir:
            cand_file = os.path.join(snapshot_dir, os.path.basename(target_abs))
            if os.path.exists(cand_file):
                snapshot_file = cand_file
    except Exception:
        pass

    if not snapshot_file:
        # 若快照工具未返回标准目录，降级在 backup/ 下定位最新快照
        backup_base = os.path.join(root_dir, "backup")
        if os.path.exists(backup_base):
            subdirs = sorted(
                [os.path.join(backup_base, d) for d in os.listdir(backup_base) if os.path.isdir(os.path.join(backup_base, d))],
                reverse=True,
            )
            for sd in subdirs:
                cf = os.path.join(sd, os.path.basename(target_abs))
                if os.path.exists(cf):
                    snapshot_dir = sd
                    snapshot_file = cf
                    break

    if not snapshot_file or not os.path.exists(snapshot_file):
        res = {
            "applied": False,
            "blocked": True,
            "reason": "failed_to_create_backup_snapshot",
        }
        return res, 1

    # 3. 执行局部改写 (Local Precise Rewrite)
    # 提取声明条目 ID
    entries = table_data.get("entries", [])
    declared_id = declared_override
    if not declared_id and entries:
        declared_id = entries[0].get("entry_id", "C-01")
    if not declared_id:
        declared_id = "C-01"

    with open(target_abs, "r", encoding="utf-8", errors="replace") as f:
        target_content = f.read()

    modified_content = target_content
    for entry in entries:
        old_text = entry.get("old_text", "")
        new_text = entry.get("new_text", "")
        status = entry.get("status", "").upper()
        if status in ("APPROVED", "OK", "PASS") or not status:
            if old_text and old_text in modified_content:
                modified_content = modified_content.replace(old_text, new_text)

    # 写入目标文件 (若已有修改或更新改写)
    if modified_content != target_content:
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(modified_content)

    # 4. 零漂移比对核验 (verify_readback.py --diff-mode)
    readback_script = find_script("verify_readback.py", root_dir)
    diff_cmd = [
        sys.executable,
        readback_script,
        "--diff-mode",
        "--old", snapshot_file,
        "--new", target_abs,
        "--declared", declared_id,
    ]
    diff_code, diff_out, diff_err = run_command(diff_cmd, cwd=root_dir)

    undeclared_drift = 0
    try:
        diff_json = json.loads(diff_out)
        undeclared_drift = diff_json.get("undeclared_drift", 0)
    except Exception:
        undeclared_drift = 1

    if diff_code != 0 or undeclared_drift > 0:
        # 拦截未声明漂移并阻断！
        res = {
            "applied": False,
            "blocked": True,
            "reason": "undeclared_drift_detected",
            "undeclared_drift": undeclared_drift,
        }
        return res, 1

    # 5. 执行留痕与状态更新
    new_sha256 = compute_file_sha256(target_abs)
    new_nettext = compute_nettext_sha256(target_abs)
    exec_time = datetime.now(timezone.utc).isoformat()

    # 更新 change-table.md 中的执行留痕字段
    actual_table_path = table_data["file_path"]
    audit_file = os.path.join(root_dir, "change-audit.md")
    if is_under_src(actual_table_path) or is_under_src(audit_file):
        return {
            "applied": False,
            "blocked": True,
            "reason": "refuse_to_write_src_assets",
        }, 1
    with open(actual_table_path, "r", encoding="utf-8", errors="replace") as f:
        table_text = f.read()

    table_text = re.sub(r"\{\{EXEC_TIME\}\}", exec_time, table_text)
    table_text = re.sub(r"\{\{BACKUP_PATH\}\}", snapshot_dir, table_text)
    table_text = re.sub(r"\{\{TARGET_FILE\}\}", target_rel, table_text)
    table_text = re.sub(r"\{\{NEW_SHA256\}\}", new_sha256, table_text)
    table_text = re.sub(r"\{\{NEW_NETTEXT\}\}", new_nettext, table_text)
    table_text = re.sub(r"\{\{UNDECLARED_DRIFT_COUNT\}\}", "0", table_text)
    table_text = re.sub(r"\{\{LAYER_1_RESULT\}\}", "true", table_text)
    table_text = re.sub(r"\{\{LAYER_2_RESULT\}\}", "0", table_text)
    table_text = re.sub(r"\{\{LAYER_3_RESULT\}\}", "true", table_text)
    table_text = re.sub(r"\{\{LAYER_4_RESULT\}\}", "0", table_text)
    table_text = re.sub(r"\{\{DIFF_SUMMARY_TEXT\}\}", "仅声明章节有差异，其余章节全文哈希逐字节一致", table_text)

    with open(actual_table_path, "w", encoding="utf-8") as f:
        f.write(table_text)

    # 产出 change-audit.md 审计证明
    audit_content = f"""# 变更实施审计报告 (Change Audit Report)
- change_id: "{change_id}"
- executed_at: "{exec_time}"
- target_file: "{target_rel}"
- parent_baseline_sha256: "{table_data.get('parent_baseline_sha256', '')}"
- new_baseline_content_sha256: "{new_sha256}"
- new_baseline_nettext_sha256: "{new_nettext}"
- backup_archive_path: "{snapshot_dir}"
- declared_id: "{declared_id}"
- undeclared_drift: 0
- audit_status: "PASSED"
"""
    with open(audit_file, "w", encoding="utf-8") as f:
        f.write(audit_content)

    res = {
        "applied": True,
        "backup": snapshot_dir,
        "undeclared_drift": 0,
        "verified": True,
    }
    return res, 0


# ---------------------------------------------------------------------------
# 4. 变更审计核验 (--audit)
# ---------------------------------------------------------------------------

def audit_change_table(table_path: str, root_dir: str) -> Tuple[Dict[str, Any], int]:
    """
    审计变更实施完整性与零漂移留痕:
    输出 {"audit_present":bool,"backup_present":bool,"undeclared_drift":int}
    """
    table_data = parse_change_table(table_path, root_dir)
    actual_table = table_data.get("file_path", table_path)

    # 1. 检查审计文件与留痕
    audit_file = os.path.join(root_dir, "change-audit.md")
    audit_present = os.path.exists(audit_file)

    # 2. 检查备份快照完整性 (调用 verify_readback.py --verify-backup)
    readback_script = find_script("verify_readback.py", root_dir)
    backup_cmd = [
        sys.executable,
        readback_script,
        "--verify-backup", "backup",
        "--change-table", actual_table,
        "--root", root_dir,
    ]
    b_code, b_out, b_err = run_command(backup_cmd, cwd=root_dir)

    backup_present = False
    try:
        b_json = json.loads(b_out)
        backup_present = b_json.get("backup_valid", False) and b_json.get("hash_matched", False)
    except Exception:
        backup_present = False

    # 3. 检查未声明漂移数
    undeclared_drift = 0
    if audit_present:
        with open(audit_file, "r", encoding="utf-8", errors="replace") as f:
            aud_txt = f.read()
        m_drift = re.search(r"undeclared_drift\s*[:：]\s*(\d+)", aud_txt)
        if m_drift:
            undeclared_drift = int(m_drift.group(1))

    # 若未找到 audit_file 但 change-table.md 中有记录
    if not audit_present and os.path.exists(actual_table):
        with open(actual_table, "r", encoding="utf-8", errors="replace") as f:
            ct_txt = f.read()
        m_drift = re.search(r"(?:undeclared_drift_count|layer_4_undeclared_drift)\s*[:：]\s*(\d+)", ct_txt)
        if m_drift:
            undeclared_drift = int(m_drift.group(1))
            audit_present = True

    all_passed = audit_present and backup_present and (undeclared_drift == 0)
    res = {
        "audit_present": audit_present,
        "backup_present": backup_present,
        "undeclared_drift": undeclared_drift,
    }
    return res, 0 if all_passed else 1


# ---------------------------------------------------------------------------
# 5. 失效传播处理 (--propagate)
# ---------------------------------------------------------------------------

def propagate_invalidation(
    instruction_path: str,
    root_dir: str,
    ledger_path_override: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    [M8 --propagate 模式 / CRITERION M8-4]:
    依据外部指示分析失效影响范围，仅向治理台账写入 STALE 标记与输出失效清单。
    严禁自动执行母本文件的改写；台账复选框 [x] 数量保持绝对不变（Agent 严禁自行复位）。
    """
    classification, code = classify_instruction(instruction_path, root_dir)
    if code != 0:
        return classification, code

    stale_targets = classification.get("stale_targets", [])
    change_id = classification.get("change_id", "change-01")

    ledger_path = ledger_path_override or os.path.join(root_dir, "progress-log.md")
    if not os.path.isabs(ledger_path):
        ledger_path = os.path.normpath(os.path.join(root_dir, ledger_path))

    # 严禁回退到 src/templates/ 模板路径：模板是只读资产，绝不允许被运行期写入。
    if not os.path.exists(ledger_path):
        return {
            "propagated": False,
            "reason": "workspace_ledger_not_found",
            "ledger_path": ledger_path,
        }, 1

    if is_under_src(ledger_path):
        return {
            "propagated": False,
            "reason": "refuse_to_write_src_assets",
            "ledger_path": ledger_path,
        }, 1

    with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    updated_lines = []
    # 匹配任务行: | 阶段 | 任务 ID | 任务内容与目标 | 任务完成 | 四分状态 | ...
    # 例如 | P1 | T-P1-01 | grill-me 八项澄清访谈 | [ ] | 存在 | ...
    row_pattern = re.compile(
        r"^(\s*\|\s*[^|]+\|\s*(T-[A-Za-z0-9_-]+)\s*\|[^|]+\|\s*\[(?:x|X|\s)\]\s*\|\s*)([^|]+?)(\s*\|.*)$"
    )

    stale_tasks_marked: List[str] = []
    for line in lines:
        m = row_pattern.match(line)
        if m:
            prefix = m.group(1)
            task_id = m.group(2)
            current_state = m.group(3).strip()
            suffix = m.group(4)

            should_mark_stale = False
            if "ALL" in stale_targets:
                should_mark_stale = True
            elif task_id in stale_targets:
                should_mark_stale = True
            elif "G0" in stale_targets and task_id in (
                "T-P2-01", "T-P3-01", "T-P4-01", "T-P4-02", "T-P5-01",
                "T-G1-01", "T-P5-02", "T-P6-01", "T-P6-02", "T-G2-01",
                "T-P6-03", "T-P6-04", "T-G3-01"
            ):
                should_mark_stale = True
            elif any(sec in stale_targets for sec in ["全文", "业务模式评级章节"]):
                if task_id in ("T-P6-01", "T-P6-03", "T-G2-01"):
                    should_mark_stale = True

            if should_mark_stale:
                stale_tasks_marked.append(task_id)
                if "STALE" not in current_state:
                    new_state = f"{current_state} [STALE]"
                else:
                    new_state = current_state
                # 保持前缀、复选框与后缀原封不动！
                updated_lines.append(f"{prefix}{new_state}{suffix}\n")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    with open(ledger_path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

    res = {
        "propagated": True,
        "change_id": change_id,
        "stale_targets": stale_targets,
        "marked_tasks": stale_tasks_marked,
        "ledger_updated": True,
        "rewritten": False,
    }
    return res, 0


# ---------------------------------------------------------------------------
# CLI 主入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Universal Change Dispatcher & Maintenance Circuit Orchestrator for M8"
    )
    parser.add_argument("--root", type=str, default=None, help="Workspace root directory (required; must point at the project workspace, never src/)")
    parser.add_argument("--instruction-file", type=str, help="Path to raw instruction input file")
    parser.add_argument("--classify", action="store_true", help="Classify instruction and determine ceremony level")
    parser.add_argument("--propagate", action="store_true", help="Propagate STALE markers and invalidation list without rewriting baseline")
    parser.add_argument("--apply", action="store_true", help="Apply approved change with snapshot and zero-drift verification")
    parser.add_argument("--audit", action="store_true", help="Audit change execution, backup integrity, and zero-drift records")
    parser.add_argument("--change-table", type=str, help="Path to change-table.md")
    parser.add_argument("--ledger", type=str, help="Override path to progress-log.md")
    parser.add_argument("--target", type=str, help="Override target baseline markdown file")
    parser.add_argument("--declared", type=str, help="Override declared change block/section ID (e.g. C-01)")

    args = parser.parse_args()

    # --root 为必填项：缺省时严禁回退到脚本所在目录或 src/，直接 exit 1 且不写任何文件。
    if not args.root:
        payload = {"error": "--root <workspace> is required", "reason": "root_required"}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stderr.write("Error: --root <workspace> is required\n")
        sys.exit(1)

    root_dir = os.path.abspath(args.root)

    if args.classify:
        if not args.instruction_file:
            sys.stderr.write("Error: --classify requires --instruction-file <path>\n")
            sys.exit(1)
        res, code = classify_instruction(args.instruction_file, root_dir)
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    if args.propagate:
        if not args.instruction_file:
            sys.stderr.write("Error: --propagate requires --instruction-file <path>\n")
            sys.exit(1)
        res, code = propagate_invalidation(
            instruction_path=args.instruction_file,
            root_dir=root_dir,
            ledger_path_override=args.ledger,
        )
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    if args.apply:
        if not args.change_table:
            sys.stderr.write("Error: --apply requires --change-table <path>\n")
            sys.exit(1)
        res, code = apply_change_table(
            table_path=args.change_table,
            root_dir=root_dir,
            target_override=args.target,
            declared_override=args.declared,
        )
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    if args.audit:
        if not args.change_table:
            sys.stderr.write("Error: --audit requires --change-table <path>\n")
            sys.exit(1)
        res, code = audit_change_table(table_path=args.change_table, root_dir=root_dir)
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(code)

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
