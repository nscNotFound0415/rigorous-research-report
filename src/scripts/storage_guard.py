#!/usr/bin/env python3
"""
storage_guard.py - 工作区受控存储与未登记写入拦截守护工具

纯 Python 3 标准库实现，零第三方依赖，无外网访问。
职责：
1. 校验工作区目录文件是否在 manifest.json 登记，拦截/拒绝未登记文件的写入。
2. 守护治理台账 progress-log.md，拦截非人类签名的 [x] 自评勾选，自动回滚为 [ ] 并写入 violations.log。

CLI 契约:
    python3 scripts/storage_guard.py --root <dir> [--manifest <file>] --probe-unregistered-write [--path <file>]
    python3 scripts/storage_guard.py --root <dir> [--manifest <file>] --check
    python3 scripts/storage_guard.py --root <dir> --check-ledger [--ledger <file>]
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


DEFAULT_IGNORED_PATTERNS = [
    "manifest.json",
    "violations.log",
    "backup/**",
    ".git/**",
    ".git",
    "__pycache__/**",
    "__pycache__",
    "*.pyc",
    ".pytest_cache/**",
    ".pytest_cache",
    "*~",
    ".DS_Store",
]


def normalize_rel_path(path: str) -> str:
    """规范化 manifest/probe 中的相对路径，仅剥离前导 './'，不做破坏性 lstrip。"""
    norm = os.path.normpath(path).replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def compute_file_sha256(file_path: str) -> str:
    """计算文件二进制内容的 SHA-256 哈希"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_manifest(manifest_path: str) -> Tuple[Dict[str, Optional[str]], List[str]]:
    """
    加载 manifest.json，返回:
    (dict of {relative_path: expected_sha256 or None}, list of ignored_patterns)
    """
    if not os.path.exists(manifest_path):
        return {}, list(DEFAULT_IGNORED_PATTERNS)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    registered: Dict[str, Optional[str]] = {}
    ignored_patterns = list(DEFAULT_IGNORED_PATTERNS)

    if isinstance(data, dict):
        if "ignored_patterns" in data and isinstance(data["ignored_patterns"], list):
            for pat in data["ignored_patterns"]:
                if pat not in ignored_patterns:
                    ignored_patterns.append(pat)

        files_list = data.get("managed_files") or data.get("files") or []
        if isinstance(files_list, list):
            for item in files_list:
                if isinstance(item, dict) and "path" in item:
                    rel_p = normalize_rel_path(item["path"])
                    registered[rel_p] = item.get("content_sha256")
                elif isinstance(item, str):
                    rel_p = normalize_rel_path(item)
                    registered[rel_p] = None
        elif isinstance(files_list, dict):
            for p, h in files_list.items():
                rel_p = normalize_rel_path(p)
                registered[rel_p] = h
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "path" in item:
                rel_p = normalize_rel_path(item["path"])
                registered[rel_p] = item.get("content_sha256")
            elif isinstance(item, str):
                rel_p = normalize_rel_path(item)
                registered[rel_p] = None

    return registered, ignored_patterns


def is_ignored(rel_path: str, ignored_patterns: List[str]) -> bool:
    """检查相对路径是否匹配忽略模式"""
    norm = rel_path.replace("\\", "/")
    basename = os.path.basename(norm)
    for pat in ignored_patterns:
        pat_clean = pat.replace("\\", "/")
        if fnmatch.fnmatch(norm, pat_clean) or fnmatch.fnmatch(basename, pat_clean):
            return True
        if pat_clean.endswith("/**"):
            prefix = pat_clean[:-3].rstrip("/")
            if norm == prefix or norm.startswith(prefix + "/"):
                return True
    return False


def scan_workspace_files(root_dir: str, ignored_patterns: List[str]) -> List[str]:
    """递归扫描工作区所有非忽略文件，返回相对路径列表"""
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == ".":
            rel_dir = ""

        # 过滤目录
        filtered_dirs = []
        for d in dirnames:
            d_rel = os.path.normpath(os.path.join(rel_dir, d)).replace("\\", "/")
            if not is_ignored(d_rel, ignored_patterns) and not is_ignored(d_rel + "/**", ignored_patterns):
                filtered_dirs.append(d)
        dirnames[:] = filtered_dirs

        for f in filenames:
            f_rel = os.path.normpath(os.path.join(rel_dir, f)).replace("\\", "/")
            if not is_ignored(f_rel, ignored_patterns):
                found.append(f_rel)

    return sorted(found)


def parse_approval_file(file_path: str) -> Dict[str, str]:
    """解析签署件键值对"""
    if not os.path.exists(file_path):
        return {}

    fields: Dict[str, str] = {}
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    kv_pattern = re.compile(
        r"^\s*(?:-\s+)?(?:\*\*)?([a-zA-Z0-9_-]+)(?:\*\*)?\s*:\s*[\"']?(.*?)[\"']?\s*$"
    )
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean == "---":
            continue
        m = kv_pattern.match(line_clean)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()

    return fields


def check_and_enforce_ledger(
    root_dir: str,
    ledger_path_override: Optional[str] = None,
    log_violation: bool = True,
) -> Tuple[bool, List[str], str]:
    """
    检查台账 progress-log.md 的复选框是否被非法修改为 [x]。
    若存在未经有效 gates/*.md 人类签署批准的 [x]，则强制回滚为 [ ]，并写入 violations.log。
    返回 (is_valid, reverted_tasks, error_reason)
    """
    ledger_path = ledger_path_override or os.path.join(root_dir, "progress-log.md")
    if not os.path.exists(ledger_path):
        return True, [], ""

    with open(ledger_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines(keepends=True)
    reverted_tasks: List[str] = []
    modified_lines: List[str] = []
    has_tampering = False

    task_row_pattern = re.compile(
        r"^(\s*\|\s*[^|]*\|\s*(T-[A-Za-z0-9_-]+)\s*\|[^|]*\|)\s*\[(x|X)\]\s*(\|.*)$"
    )

    gates_dir = os.path.join(root_dir, "gates")

    for line in lines:
        m = task_row_pattern.match(line)
        if m:
            prefix = m.group(1)
            task_id = m.group(2)
            suffix = m.group(4)

            # 验证对应门禁签署件是否存在且由人类签署 APPROVED
            is_authorized = False
            candidate_approvals: List[str] = []

            # 映射已知任务 ID 到门禁文件名
            if task_id == "T-G1-01":
                candidate_approvals.append(os.path.join(gates_dir, "G1-approval.md"))
            elif task_id == "T-G2-01":
                candidate_approvals.append(os.path.join(gates_dir, "G2-approval.md"))
            elif task_id == "T-G3-01":
                candidate_approvals.append(os.path.join(gates_dir, "G3-approval.md"))
            elif task_id == "T-P1-01":
                candidate_approvals.append(os.path.join(gates_dir, "G0-approval.md"))
            elif task_id == "T-P2-01":
                # 初始化台账由人类初始确认
                candidate_approvals.append(os.path.join(gates_dir, "G0-approval.md"))
                candidate_approvals.append(os.path.join(gates_dir, "init-approval.md"))
            elif task_id == "T-P6-04":
                # 交付回读若要打勾，必须由 G3 终审批准件授权
                candidate_approvals.append(os.path.join(gates_dir, "G3-approval.md"))
            elif task_id == "T-M8-01":
                # 遍历 gates/change-*-approval.md
                if os.path.exists(gates_dir):
                    for g_file in os.listdir(gates_dir):
                        if g_file.startswith("change-") and g_file.endswith("-approval.md"):
                            candidate_approvals.append(os.path.join(gates_dir, g_file))

            # 检查 suffix 中是否明确指定了签署件路径
            signed_ref_match = re.search(r"gates/[A-Za-z0-9_-]+\.md", suffix)
            if signed_ref_match:
                explicit_approval = os.path.normpath(os.path.join(root_dir, signed_ref_match.group(0)))
                if explicit_approval not in candidate_approvals:
                    candidate_approvals.insert(0, explicit_approval)

            for app_path in candidate_approvals:
                if os.path.exists(app_path):
                    fields = parse_approval_file(app_path)
                    decision = fields.get("decision", "").strip().upper()
                    signed_by = fields.get("signed_by", "").strip()
                    auth_mode = (fields.get("authorization_mode") or "human_signed").strip().lower()
                    # 代录模式必须留全五个授权溯源字段，且授权人与签署人一致
                    trace_ok = True
                    if auth_mode == "session_transcribed":
                        trace_fields = (
                            "authorization_quote",
                            "authorization_turn",
                            "authorization_at",
                            "authorized_by",
                            "recorded_by",
                        )
                        trace_ok = all((fields.get(k) or "").strip() for k in trace_fields) and (
                            (fields.get("authorized_by") or "").strip().lower() == signed_by.lower()
                        )
                    # 必须由人类签署，禁止 agent:*
                    if (
                        decision == "APPROVED"
                        and signed_by
                        and trace_ok
                        and not re.match(r"^agent:.*", signed_by, re.IGNORECASE)
                    ):
                        is_authorized = True
                        break

            if not is_authorized:
                # 篡改行为被检出：强制回滚为 [ ]
                has_tampering = True
                reverted_tasks.append(task_id)
                new_line = f"{prefix} [ ] {suffix}\n"
                modified_lines.append(new_line)
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)

    if has_tampering:
        # 写回回滚后的台账
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.writelines(modified_lines)

        # 写入 violations.log
        if log_violation:
            violations_path = os.path.join(root_dir, "violations.log")
            timestamp = datetime.now(timezone.utc).isoformat()
            with open(violations_path, "a", encoding="utf-8") as f:
                for t in reverted_tasks:
                    entry = f"[{timestamp}] VIOLATION: Unauthorized checkbox write [x] detected in task '{t}'. Automatically reverted to [ ]. Process blocked.\n"
                    f.write(entry)

        return False, reverted_tasks, f"Unauthorized checkbox [x] detected in task(s) {reverted_tasks}; reverted to [ ] and logged to violations.log"

    return True, [], ""


def parse_decision_log(decision_log_path: str) -> Dict[str, Dict[str, str]]:
    """
    解析机器可读决策日志 decision-log.md。
    每条记录以 '- task_id: <ID>' 起始，后续缩进行为键值对:
        - task_id: T-P1-01
          approved_by: human
          artifact_sha256: <64-hex>
    """
    records: Dict[str, Dict[str, str]] = {}
    if not os.path.exists(decision_log_path):
        return records

    current: Optional[Dict[str, str]] = None
    with open(decision_log_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            m_task = re.match(r"^-\s+task_id\s*:\s*[\"']?([^\"']+?)[\"']?$", line)
            if m_task:
                current = {"task_id": m_task.group(1).strip()}
                records[current["task_id"]] = current
                continue
            if current is not None:
                m_kv = re.match(r"^(?:-\s+)?([a-zA-Z0-9_-]+)\s*:\s*[\"']?(.*?)[\"']?$", line)
                if m_kv:
                    current[m_kv.group(1).strip()] = m_kv.group(2).strip()
    return records


def check_decision_log_binding(
    root_dir: str,
    ledger_path: Optional[str] = None,
    decision_log_path: Optional[str] = None,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    [CRITERION M2-4] 校验台账中每个已勾选 [x] 任务行均具备人类决策记录，
    且决策记录声明的 artifact_sha256 与该任务产物当前 SHA256 严格一致。
    返回 (is_valid, violations)；violations 每项含 line / task_id / reason。
    """
    ledger = ledger_path or os.path.join(root_dir, "progress-log.md")
    decision_log = decision_log_path or os.path.join(root_dir, "decision-log.md")

    violations: List[Dict[str, Any]] = []
    if not os.path.exists(ledger):
        return True, violations

    records = parse_decision_log(decision_log)

    with open(ledger, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    task_row_pattern = re.compile(
        r"^\s*\|\s*[^|]*\|\s*(T-[A-Za-z0-9_-]+)\s*\|"
    )
    for idx, line in enumerate(lines, start=1):
        if "| [x] |" not in line and "| [X] |" not in line:
            continue
        m = task_row_pattern.match(line)
        if not m:
            continue
        task_id = m.group(1)

        record = records.get(task_id)
        if not record:
            violations.append({
                "line": idx,
                "task_id": task_id,
                "reason": "missing human decision record (approved_by: human)",
            })
            continue
        if record.get("approved_by", "").strip().lower() != "human":
            violations.append({
                "line": idx,
                "task_id": task_id,
                "reason": "decision record approved_by is not 'human'",
            })
            continue

        declared = record.get("artifact_sha256", "").strip().lower()
        m_artifact = re.search(r"`([^`]+)`", line)
        if not m_artifact:
            violations.append({
                "line": idx,
                "task_id": task_id,
                "reason": "artifact path not declared in ledger row",
            })
            continue
        artifact_rel = normalize_rel_path(m_artifact.group(1))
        artifact_abs = os.path.join(root_dir, artifact_rel)
        if not os.path.exists(artifact_abs):
            violations.append({
                "line": idx,
                "task_id": task_id,
                "reason": f"artifact file not found: {artifact_rel}",
            })
            continue
        actual = compute_file_sha256(artifact_abs).lower()
        if not re.match(r"^[a-f0-9]{64}$", declared) or declared != actual:
            violations.append({
                "line": idx,
                "task_id": task_id,
                "reason": f"artifact_sha256 mismatch: approved={declared or 'null'}, actual={actual}",
            })

    return len(violations) == 0, violations


def probe_unregistered_write(
    root_dir: str,
    manifest_path: str,
    target_path: Optional[str] = None,
) -> None:
    """
    探针模式：探测受控目录中的未登记写入操作。
    规范期望：
    向受控目录写入未经 manifest 登记的文件，脚本必须返回 stdout {"rejected":true,"path":"…"}，
    退出码为 0（拒绝成功；若未拒绝则退出码为 1）。
    """
    registered, ignored_patterns = load_manifest(manifest_path)

    # 1. 如果传入了特定目标路径
    if target_path:
        norm_target = os.path.normpath(target_path)
        if os.path.isabs(norm_target):
            rel_target = os.path.relpath(norm_target, root_dir)
        else:
            rel_target = norm_target
        rel_target = normalize_rel_path(rel_target)

        if is_ignored(rel_target, ignored_patterns):
            # 属于忽略模式，允许
            out = {"rejected": False, "path": rel_target, "reason": "path is in ignored patterns"}
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.exit(1)

        if rel_target in registered:
            # 已登记文件，未被拒绝
            out = {"rejected": False, "path": rel_target, "reason": "path is already registered in manifest"}
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.exit(1)
        else:
            # 未登记路径：拦截并拒绝成功！
            out = {
                "rejected": True,
                "path": rel_target,
                "reason": f"Unregistered file write attempt to '{rel_target}' was intercepted and rejected",
            }
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.exit(0)

    # 2. 未指定 target_path 时，全量扫描 root_dir 是否存在未在 manifest 登记的文件
    workspace_files = scan_workspace_files(root_dir, ignored_patterns)
    unregistered = [f for f in workspace_files if f not in registered]

    if unregistered:
        offender = unregistered[0]
        out = {
            "rejected": True,
            "path": offender,
            "unregistered_count": len(unregistered),
            "reason": f"Unregistered file write attempt to '{offender}' was intercepted and rejected",
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(0)
    else:
        out = {
            "rejected": False,
            "unregistered": [],
            "reason": "All existing files are registered in manifest; no unmanaged write detected",
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(1)


def check_workspace(
    root_dir: str,
    manifest_path: str,
    check_ledger_enabled: bool = True,
) -> None:
    """
    自检模式：检查工作区文件登记状态与台账合规性。
    退出码：0 = 全部已登记且校验通过；1 = 存在未登记写入、哈希不匹配或台账违规。
    """
    registered, ignored_patterns = load_manifest(manifest_path)
    workspace_files = scan_workspace_files(root_dir, ignored_patterns)

    unregistered = [f for f in workspace_files if f not in registered]

    # 哈希比对与预留路径校验
    mismatched = []
    missing_registered = []
    for reg_path, expected_hash in registered.items():
        full_p = os.path.join(root_dir, reg_path)
        if not os.path.exists(full_p):
            # 若声明了具体预期 SHA-256 哈希（64 位 hex），则必须实际在位；未指定具体哈希（如 null / "..."）为规划预留路径，不阻断自检
            if expected_hash and re.match(r"^[a-fA-F0-9]{64}$", str(expected_hash)):
                missing_registered.append(reg_path)
        elif expected_hash and re.match(r"^[a-fA-F0-9]{64}$", str(expected_hash)):
            actual_h = compute_file_sha256(full_p).lower()
            if actual_h != expected_hash.lower():
                mismatched.append({"path": reg_path, "expected": expected_hash, "actual": actual_h})

    # 台账复选框防护检查
    ledger_valid = True
    reverted_tasks: List[str] = []
    ledger_msg = ""
    if check_ledger_enabled:
        ledger_valid, reverted_tasks, ledger_msg = check_and_enforce_ledger(root_dir)

    is_all_clean = (
        len(unregistered) == 0
        and len(mismatched) == 0
        and len(missing_registered) == 0
        and ledger_valid
    )

    out = {
        "valid": is_all_clean,
        "registered": len(registered),
        "workspace_files": len(workspace_files),
        "unregistered": unregistered,
        "mismatched": mismatched,
        "missing_registered": missing_registered,
        "ledger_valid": ledger_valid,
        "reverted_tasks": reverted_tasks,
    }

    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    if is_all_clean:
        sys.exit(0)
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Workspace storage guard and manifest verification tool")
    parser.add_argument("--root", type=str, default=".", help="Workspace root directory (default: .)")
    parser.add_argument("--manifest", type=str, help="Path to manifest.json (default: <root>/manifest.json)")
    parser.add_argument("--probe-unregistered-write", action="store_true", help="Probe and reject unregistered file writes")
    parser.add_argument("--path", type=str, help="Target file path to probe against manifest")
    parser.add_argument("--check", action="store_true", help="Perform comprehensive check on workspace registration and ledger")
    parser.add_argument("--check-ledger", action="store_true", help="Verify ledger progress-log.md and revert unauthorized [x]")
    parser.add_argument("--check-decision-log", action="store_true", help="Verify every [x] ledger row is bound to a human decision record with matching artifact_sha256")
    parser.add_argument("--ledger", type=str, help="Explicit path to progress-log.md")
    parser.add_argument("--decision-log", type=str, help="Explicit path to decision-log.md")

    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    # 显式传入的 --manifest / --ledger 由调用方基于当前工作目录给出；
    # 仅未提供时才回落到 <root>/manifest.json。严禁把显式相对路径二次拼接到 root 下。
    if args.manifest:
        manifest_path = (
            args.manifest
            if os.path.isabs(args.manifest)
            else os.path.abspath(args.manifest)
        )
    else:
        manifest_path = os.path.join(root_dir, "manifest.json")
    manifest_path = os.path.normpath(manifest_path)

    if args.check_ledger:
        if args.ledger:
            ledger_path = (
                args.ledger
                if os.path.isabs(args.ledger)
                else os.path.abspath(args.ledger)
            )
        else:
            ledger_path = os.path.join(root_dir, "progress-log.md")
        ledger_path = os.path.normpath(ledger_path)
        valid, reverted, msg = check_and_enforce_ledger(root_dir, ledger_path_override=ledger_path)
        out = {
            "ledger_valid": valid,
            "reverted_tasks": reverted,
            "reason": msg if not valid else "Ledger checkboxes are verified and compliant",
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(0 if valid else 1)

    if args.check_decision_log:
        ledger_path = (
            (args.ledger if os.path.isabs(args.ledger) else os.path.abspath(args.ledger))
            if args.ledger
            else os.path.join(root_dir, "progress-log.md")
        )
        decision_log_path = (
            (args.decision_log if os.path.isabs(args.decision_log) else os.path.abspath(args.decision_log))
            if args.decision_log
            else os.path.join(root_dir, "decision-log.md")
        )
        valid, violations = check_decision_log_binding(
            root_dir,
            ledger_path=os.path.normpath(ledger_path),
            decision_log_path=os.path.normpath(decision_log_path),
        )
        out = {
            "decision_log_valid": valid,
            "violations": violations,
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(0 if valid else 1)

    if args.probe_unregistered_write:
        probe_unregistered_write(
            root_dir=root_dir,
            manifest_path=manifest_path,
            target_path=args.path,
        )
        return

    if args.check:
        check_workspace(
            root_dir=root_dir,
            manifest_path=manifest_path,
        )
        return

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
