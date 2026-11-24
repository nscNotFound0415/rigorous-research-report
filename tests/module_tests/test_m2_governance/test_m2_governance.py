#!/usr/bin/env python3
"""
test_m2_governance.py - M2 模块黑箱与治理协议独立验收测试套件

测试对象:
- src/templates/progress_log.template.md
- src/references/P2_governance_protocol.md
- src/references/storage_adapters.md
- src/scripts/storage_guard.py
- src/scripts/adapter_git_sync.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SRC_SCRIPTS = os.path.join(MODULE_ROOT, "src", "scripts")
SRC_TEMPLATES = os.path.join(MODULE_ROOT, "src", "templates")
SRC_REFERENCES = os.path.join(MODULE_ROOT, "src", "references")
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")

STORAGE_GUARD_PY = os.path.join(SRC_SCRIPTS, "storage_guard.py")
ADAPTER_GIT_SYNC_PY = os.path.join(SRC_SCRIPTS, "adapter_git_sync.py")
GATE_GUARD_PY = os.path.join(SRC_SCRIPTS, "gate_guard.py")


def test_progress_log_template_schema_and_four_fold_state():
    """
    [CRITERION M2-1 & Scenario: Ledger records four-fold state column]
    验证 progress_log.template.md：
    1. 必须包含严格 15 项标准化任务（T-P1-01 至 T-M8-01，包含 T-P6-04 交付回读与两遍法验证）。
    2. 包含必须的 T-P4-02、T-P5-02、T-P6-03、T-P6-04、T-M8-01。
    3. 任务完成复选框初始严格为 [ ]。
    4. 「四分状态」列枚举值必须严格属于 {存在, 已复核, 已同步, 已审定}。
    5. 包含独立「agent_建议」列。
    6. 包含授权边界与决策日志小节。
    """
    template_path = os.path.join(SRC_TEMPLATES, "progress_log.template.md")
    assert os.path.exists(template_path), f"Missing template: {template_path}"

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 验证授权边界与决策日志
    assert "## 1. 授权边界 (Authorization Boundaries)" in content
    assert "## 2. 状态四分铁律 (State Axiom)" in content
    assert "## 3. 阶段流水线任务清单 (Pipeline Checklist)" in content
    assert "## 4. 决策日志 (Decision Log)" in content

    # 2. 解析任务清单表格
    lines = content.splitlines()
    table_lines = [
        l.strip()
        for l in lines
        if l.strip().startswith("|") and not l.strip().startswith("|---")
    ]
    # 提取表头
    header = table_lines[0]
    columns = [c.strip() for c in header.split("|")[1:-1]]
    assert "任务 ID" in columns
    assert "任务完成" in columns
    assert "四分状态" in columns
    assert "agent_建议" in columns

    task_id_col = columns.index("任务 ID")
    checkbox_col = columns.index("任务完成")
    state_col = columns.index("四分状态")

    task_rows = []
    valid_states = {"存在", "已复核", "已同步", "已审定"}

    for line in table_lines[1:]:
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) >= len(columns):
            tid = parts[task_id_col]
            if re.match(r"^T-[A-Za-z0-9_-]+$", tid):
                task_rows.append((tid, parts[checkbox_col], parts[state_col]))

    # 断言严格包含 15 项标准化任务
    assert len(task_rows) == 15, f"Expected exactly 15 task rows, found {len(task_rows)}: {[r[0] for r in task_rows]}"

    # 断言必须包含的指定任务 ID
    task_ids = [r[0] for r in task_rows]
    assert "T-P1-01" in task_ids
    assert "T-P2-01" in task_ids
    assert "T-P3-01" in task_ids
    assert "T-P4-01" in task_ids
    assert "T-P4-02" in task_ids
    assert "T-P5-01" in task_ids
    assert "T-G1-01" in task_ids
    assert "T-P5-02" in task_ids
    assert "T-P6-01" in task_ids
    assert "T-P6-02" in task_ids
    assert "T-G2-01" in task_ids
    assert "T-P6-03" in task_ids
    assert "T-P6-04" in task_ids
    assert "T-G3-01" in task_ids
    assert "T-M8-01" in task_ids

    # 验证每个复选框必须为 [ ]，且四分状态严格属于合法枚举
    for tid, cb, st in task_rows:
        assert cb == "[ ]", f"Template checkbox for task {tid} must be '[ ]', got '{cb}'"
        assert st in valid_states, f"Task {tid} has invalid state '{st}'; must be in {valid_states}"


def test_probe_unregistered_write_intercepted_on_dirty_workspace():
    """
    [CRITERION M2-3 & Scenario: Unregistered file write attempt is rejected]
    向受控目录写入未经 manifest 登记的文件，运行 probe-unregistered-write 必须返回:
    - stdout {"rejected": true, "path": "..."}
    - 退出码 0（拒绝拦截成功）
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 复制 unregistered fixture
        src_ws = os.path.join(FIXTURES_DIR, "unregistered_write_workspace")
        shutil.copytree(src_ws, tmp_dir, dirs_exist_ok=True)

        manifest_file = os.path.join(tmp_dir, "manifest.json")
        cmd = [
            sys.executable,
            STORAGE_GUARD_PY,
            "--root", tmp_dir,
            "--manifest", manifest_file,
            "--probe-unregistered-write"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        assert proc.returncode == 0, f"Expected exit code 0 on successful rejection, got {proc.returncode}. Stderr: {proc.stderr}"
        stdout_clean = proc.stdout.strip()
        data = json.loads(stdout_clean)
        assert data.get("rejected") is True
        assert data.get("path") == "unregistered_leak.txt"


def test_probe_unregistered_write_specific_path():
    """
    针对显式指定的未登记路径进行探测，预期拦截并退出码 0。
    """
    valid_ws = os.path.join(FIXTURES_DIR, "valid_workspace")
    manifest_file = os.path.join(valid_ws, "manifest.json")
    cmd = [
        sys.executable,
        STORAGE_GUARD_PY,
        "--root", valid_ws,
        "--manifest", manifest_file,
        "--probe-unregistered-write",
        "--path", "unauthorized_drop.tmp"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout.strip())
    assert data.get("rejected") is True
    assert data.get("path") == "unauthorized_drop.tmp"


def test_storage_guard_check_clean_workspace():
    """
    在合规的工作区运行 --check，预期全部通过且退出码 0。
    """
    valid_ws = os.path.join(FIXTURES_DIR, "valid_workspace")
    cmd = [
        sys.executable,
        STORAGE_GUARD_PY,
        "--root", valid_ws,
        "--check"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Expected 0 for valid workspace, got {proc.returncode}. Output: {proc.stdout}"
    data = json.loads(proc.stdout.strip())
    assert data.get("valid") is True
    assert len(data.get("unregistered")) == 0
    assert data.get("ledger_valid") is True


def test_tampered_ledger_detection_and_rollback():
    """
    [CRITERION M2 Blackbox & Scenario: Agent attempts unauthorized self-approval checkbox write]
    向治理台账注入伪造的自评放行记录（Agent 试图把 - [ ] 改为 - [x] 并提交）：
    1. 检出未经人类授权的修改。
    2. 自动将该任务状态强行回滚为 - [ ]。
    3. 写入 violations.log。
    4. 退出码为 1（阻断执行）。
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_ws = os.path.join(FIXTURES_DIR, "tampered_ledger_workspace")
        shutil.copytree(src_ws, tmp_dir, dirs_exist_ok=True)

        ledger_file = os.path.join(tmp_dir, "progress-log.md")
        violations_file = os.path.join(tmp_dir, "violations.log")

        # 验证初始状态确实存在非法的 [x]
        with open(ledger_file, "r", encoding="utf-8") as f:
            initial_content = f.read()
        assert "| T-P3-01 |" in initial_content and "[x]" in initial_content

        # 运行 storage_guard --check-ledger
        cmd = [
            sys.executable,
            STORAGE_GUARD_PY,
            "--root", tmp_dir,
            "--check-ledger"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # 1. 退出码必须为 1
        assert proc.returncode == 1, f"Expected exit code 1 on tampered ledger, got {proc.returncode}"
        data = json.loads(proc.stdout.strip())
        assert data.get("ledger_valid") is False
        assert "T-P3-01" in data.get("reverted_tasks")

        # 2. 检查 progress-log.md 是否被自动回滚为 [ ]
        with open(ledger_file, "r", encoding="utf-8") as f:
            rolled_back_content = f.read()
        for line in rolled_back_content.splitlines():
            if "| T-P3-01 |" in line:
                assert "[ ]" in line, f"T-P3-01 should have been rolled back to [ ], but got: {line}"
                assert "[x]" not in line

        # 3. 检查 violations.log 是否记录违规
        assert os.path.exists(violations_file), "violations.log must be created"
        with open(violations_file, "r", encoding="utf-8") as f:
            v_content = f.read()
        assert "VIOLATION" in v_content
        assert "T-P3-01" in v_content


def test_tampered_tp6_04_detection_and_rollback():
    """
    [AL-09 / Scenario: Unauthorized self-approval on T-P6-04 is detected and rolled back]
    测试向治理台账 T-P6-04 注入未经人类授权的自评 [x] 勾选：
    1. storage_guard 检出篡改，返回退出码 1；
    2. 自动回滚该行为 [ ]；
    3. violations.log 记录违规条目。
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_ws = os.path.join(FIXTURES_DIR, "valid_workspace")
        shutil.copytree(src_ws, tmp_dir, dirs_exist_ok=True)

        ledger_file = os.path.join(tmp_dir, "progress-log.md")
        violations_file = os.path.join(tmp_dir, "violations.log")

        with open(ledger_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 注入非法的 T-P6-04 [x] 勾选
        assert "| T-P6-04 |" in content
        tampered_content = content.replace(
            "| P6 | T-P6-04 | 交付回读与两遍法验证 | [ ] |",
            "| P6 | T-P6-04 | 交付回读与两遍法验证 | [x] |"
        )
        assert tampered_content != content
        with open(ledger_file, "w", encoding="utf-8") as f:
            f.write(tampered_content)

        # 运行 storage_guard --check-ledger
        cmd = [
            sys.executable,
            STORAGE_GUARD_PY,
            "--root", tmp_dir,
            "--check-ledger"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        assert proc.returncode == 1, f"Expected exit code 1 on tampered T-P6-04, got {proc.returncode}"
        data = json.loads(proc.stdout.strip())
        assert data.get("ledger_valid") is False
        assert "T-P6-04" in data.get("reverted_tasks")

        # 检查是否回滚为 [ ]
        with open(ledger_file, "r", encoding="utf-8") as f:
            rolled_back_content = f.read()
        for line in rolled_back_content.splitlines():
            if "| T-P6-04 |" in line:
                assert "[ ]" in line
                assert "[x]" not in line

        # 检查 violations.log 是否记录违规
        assert os.path.exists(violations_file), "violations.log must be created"
        with open(violations_file, "r", encoding="utf-8") as f:
            v_content = f.read()
        assert "VIOLATION" in v_content
        assert "T-P6-04" in v_content


def test_manifest_registers_schema_definition():
    """
    [AL-07: Manifest and storage adapter register src/schemas/task.schema.json]
    验证 valid_workspace/manifest.json 与 storage_adapters.md 正确登记 schema 路径。
    """
    manifest_path = os.path.join(FIXTURES_DIR, "valid_workspace", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    paths = [item["path"] for item in data.get("managed_files", [])]
    assert "src/schemas/task.schema.json" in paths, "src/schemas/task.schema.json not registered in manifest"

    schema_entry = next(item for item in data["managed_files"] if item["path"] == "src/schemas/task.schema.json")
    assert schema_entry.get("category") == "schema_definition"
    assert schema_entry.get("writer") == "M3_agent" or "M3_agent" in schema_entry.get("allowed_roles", [])

    # 验证 storage_adapters.md 也包含了此声明
    adapters_doc = os.path.join(SRC_REFERENCES, "storage_adapters.md")
    with open(adapters_doc, "r", encoding="utf-8") as f:
        doc_text = f.read()
    assert "src/schemas/task.schema.json" in doc_text


def test_adapter_git_sync_hash_calculation():
    """
    验证 adapter_git_sync.py --hash 计算 content_sha256 与 nettext_sha256。
    """
    target_file = os.path.join(FIXTURES_DIR, "drift_workspace", "old_draft.md")
    cmd = [
        sys.executable,
        ADAPTER_GIT_SYNC_PY,
        "--hash", target_file
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout.strip())
    assert len(data.get("content_sha256")) == 64
    assert len(data.get("nettext_sha256")) == 64


def test_adapter_git_sync_snapshot_creation():
    """
    验证 adapter_git_sync.py --root <dir> --snapshot <label> 创建备份目录。
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_ws = os.path.join(FIXTURES_DIR, "snapshot_workspace")
        shutil.copytree(src_ws, tmp_dir, dirs_exist_ok=True)

        cmd = [
            sys.executable,
            ADAPTER_GIT_SYNC_PY,
            "--root", tmp_dir,
            "--snapshot", "baseline_v1"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 0
        data = json.loads(proc.stdout.strip())
        assert data.get("success") is True
        assert "snapshot_dir" in data

        snap_dir = data["snapshot_dir"]
        assert os.path.exists(snap_dir)
        assert os.path.exists(os.path.join(snap_dir, "snapshot_meta.json"))
        assert os.path.exists(os.path.join(snap_dir, "brief.md"))


def test_adapter_git_sync_diff_mode_clean_and_dirty():
    """
    验证 adapter_git_sync.py --diff-mode 零漂移比对：
    - clean_diff_draft (仅修改声明的 C-01): undeclared_drift=0, 退出码 0
    - dirty_diff_draft (修改非声明章节): undeclared_drift=1, 退出码 1
    """
    old_file = os.path.join(FIXTURES_DIR, "drift_workspace", "old_draft.md")
    clean_file = os.path.join(FIXTURES_DIR, "drift_workspace", "clean_diff_draft.md")
    dirty_file = os.path.join(FIXTURES_DIR, "drift_workspace", "dirty_diff_draft.md")

    # 1. 干净修改测试
    cmd_clean = [
        sys.executable,
        ADAPTER_GIT_SYNC_PY,
        "--diff-mode",
        "--old", old_file,
        "--new", clean_file,
        "--declared", "C-01"
    ]
    proc_clean = subprocess.run(cmd_clean, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc_clean.returncode == 0
    data_clean = json.loads(proc_clean.stdout.strip())
    assert data_clean.get("undeclared_drift") == 0

    # 2. 脏修改测试 (未声明漂移)
    cmd_dirty = [
        sys.executable,
        ADAPTER_GIT_SYNC_PY,
        "--diff-mode",
        "--old", old_file,
        "--new", dirty_file,
        "--declared", "C-01"
    ]
    proc_dirty = subprocess.run(cmd_dirty, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc_dirty.returncode == 1
    data_dirty = json.loads(proc_dirty.stdout.strip())
    assert data_dirty.get("undeclared_drift") >= 1


def test_p2_governance_protocol_assertions():
    """
    验证 P2_governance_protocol.md 协议手册文本的规范性约束:
    1. 包含必须的宪法引用，声明 brief.md 为唯一事实源。
    2. 包含状态四分枚举定义与误用禁令。
    3. 包含 Agent 勾选剥夺、回滚与 violations 日志规范。
    4. 采用条目化、断言化风格 (SHALL / SHALL NOT)。
    """
    p2_path = os.path.join(SRC_REFERENCES, "P2_governance_protocol.md")
    assert os.path.exists(p2_path)
    with open(p2_path, "r", encoding="utf-8") as f:
        text = f.read()

    assert "唯一事实源约束" in text
    assert "brief.md" in text
    assert "状态四分公理与误用禁令" in text
    assert "存在" in text and "已复核" in text and "已同步" in text and "已审定" in text
    assert "violations.log" in text
    assert "SHALL" in text
    assert "SHALL NOT" in text


def test_criterion_m2_5_source_of_truth_and_planning_files_assertions():
    """
    [CRITERION M2-5 / F3 / F6]:
    1. 验证 P2 协议明文声明本技能不预设权威载体，由 brief §2.7 决定 (ONLINE_AUTHORITATIVE | LOCAL_AUTHORITATIVE)；
    2. 验证 P2 协议明文指定规划文件包含 research-breakdown.md、task.json 与 outline.md，治理台账只记录状态不复制内容；
    3. 验证 storage_adapters.md 包含 ONLINE_AUTHORITATIVE 与 LOCAL_AUTHORITATIVE 双分支。
    """
    p2_path = os.path.join(SRC_REFERENCES, "P2_governance_protocol.md")
    with open(p2_path, "r", encoding="utf-8") as f:
        p2_text = f.read()

    assert "本技能不预设权威载体" in p2_text
    assert "ONLINE_AUTHORITATIVE" in p2_text
    assert "LOCAL_AUTHORITATIVE" in p2_text
    assert "research-breakdown.md" in p2_text
    assert "task.json" in p2_text
    assert "outline.md" in p2_text

    sa_path = os.path.join(SRC_REFERENCES, "storage_adapters.md")
    with open(sa_path, "r", encoding="utf-8") as f:
        sa_text = f.read()

    assert "ONLINE_AUTHORITATIVE" in sa_text
    assert "LOCAL_AUTHORITATIVE" in sa_text


def test_criterion_m2_4_decision_log_human_binding_passes():
    """
    [CRITERION M2-4]:
    台账中每个 [x] 行必须存在 approved_by: human 的决策记录，
    且其 artifact_sha256 与产物当前 SHA256 一致时放行（退出码 0）。
    """
    ws = os.path.join(FIXTURES_DIR, "decision_log_workspace")
    cmd = [
        sys.executable,
        STORAGE_GUARD_PY,
        "--root", ws,
        "--check-decision-log",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Expected 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
    data = json.loads(proc.stdout.strip())
    assert data["decision_log_valid"] is True
    assert data["violations"] == []


def test_criterion_m2_4_decision_log_hash_mismatch_reports_line():
    """
    [CRITERION M2-4 阴性对照]:
    产物被篡改导致 artifact_sha256 不一致时退出码 1，并报告台账行号。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_ws = os.path.join(FIXTURES_DIR, "decision_log_workspace")
        shutil.copytree(src_ws, tmpdir, dirs_exist_ok=True)
        brief_path = os.path.join(tmpdir, "brief.md")
        with open(brief_path, "a", encoding="utf-8") as f:
            f.write("\n<!-- tampered after approval -->\n")

        cmd = [
            sys.executable,
            STORAGE_GUARD_PY,
            "--root", tmpdir,
            "--check-decision-log",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 1
        data = json.loads(proc.stdout.strip())
        assert data["decision_log_valid"] is False
        assert len(data["violations"]) == 1
        violation = data["violations"][0]
        assert violation["task_id"] == "T-P1-01"
        assert violation["line"] >= 1
        assert "artifact_sha256 mismatch" in violation["reason"]


def test_gate_guard_rejects_stub_approval_despite_matching_hash():
    """
    [加固项 G: 桩签署件硬拒绝]
    M2 治理场景中，含 stub: true 的 G1 桩签署件即使 artifact_sha256 完全吻合，
    门禁也必须返回 STUB_REJECTED、blocked=true、退出码 1。
    """
    ws = os.path.join(FIXTURES_DIR, "valid_workspace")
    brief_path = os.path.join(ws, "brief.md")
    stub_approval = os.path.join(FIXTURES_DIR, "G1-approval-stub.md")

    cmd = [
        sys.executable,
        GATE_GUARD_PY,
        "--gate", "G1",
        "--verify",
        "--artifact", brief_path,
        "--approval", stub_approval,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 1, f"Stub approval must exit 1, got {proc.returncode}: {proc.stdout}"
    data = json.loads(proc.stdout.strip())
    assert data["gate"] == "G1"
    assert data["state"] == "STUB_REJECTED"
    assert data["blocked"] is True
