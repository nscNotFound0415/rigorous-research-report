#!/usr/bin/env python3
"""
test_m8_change_circuit.py - M8 模块变更管理与动态维护回路独立黑箱验收测试套件
Testing M8: Change Circuit & Continuous Maintenance Loop

契约绑定:
- openspec/changes/add-rigorous-research-report/specs/change-circuit/spec.md
- 建设方案 v2.1: §1.2 M8, §1.3 (CRITERION M8-1, M8-2, M8-3), §3.2, §5.3, §8.1, §8.2 E2E-08, §9.1
- 审查裁决 2: D-7 (M8 阴性对照夹具闭环), D-14 (M8 变更门禁 CLI 契约)
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_BUILD_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SRC_SCRIPTS = os.path.join(SKILL_BUILD_DIR, "src", "scripts")
SRC_TEMPLATES = os.path.join(SKILL_BUILD_DIR, "src", "templates")
SRC_REFERENCES = os.path.join(SKILL_BUILD_DIR, "src", "references")
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")

GATE_GUARD_PY = os.path.join(SRC_SCRIPTS, "gate_guard.py")
VERIFY_READBACK_PY = os.path.join(SRC_SCRIPTS, "verify_readback.py")
ADAPTER_GIT_SYNC_PY = os.path.join(SRC_SCRIPTS, "adapter_git_sync.py")
CHANGE_DISPATCH_PY = os.path.join(SRC_SCRIPTS, "change_dispatch.py")


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 1. 模板与协议规范测试 (Schema & Protocol Compliance)
# ---------------------------------------------------------------------------

def test_change_table_template_schema_and_placeholders():
    """
    [Scenario: Change table template fields & layout]
    验证 src/templates/change_table.template.md：
    1. 包含核心元信息：change_id, change_nature, source_instruction_raw, proposed_by, created_at, priority, parent_baseline_sha256, approval_signoff
    2. 包含变更分级与升轨：ceremony_level (LIGHTWEIGHT/MAJOR), enhanced_openspec_enabled, impacted_sections, affected_evidence_ids
    3. 包含指示与变更逐条处置矩阵 (Directive & Patch Matrix)
    4. 包含执行留痕与四层回读审计 (Execution & Readback Audit, layer_1 至 layer_4)
    5. 所有占位符均采用 Mustache {{...}} 规范
    """
    tpl_path = os.path.join(SRC_TEMPLATES, "change_table.template.md")
    assert os.path.exists(tpl_path), f"Missing template: {tpl_path}"

    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_fields = [
        "change_id",
        "change_nature",
        "source_instruction_raw",
        "proposed_by",
        "created_at",
        "priority",
        "parent_baseline_sha256",
        "approval_signoff",
        "ceremony_level",
        "enhanced_openspec_enabled",
        "impacted_sections",
        "affected_evidence_ids",
        "execution_timestamp",
        "backup_archive_path",
        "new_baseline_content_sha256",
        "new_baseline_nettext_sha256",
        "undeclared_drift_count",
        "layer_1_new_sentence_present",
        "layer_2_old_sentence_residuals",
        "layer_3_block_count_valid",
        "layer_4_undeclared_drift",
    ]
    for field in required_fields:
        assert field in content, f"change_table.template.md missing required field: {field}"

    # 验证 Mustache 占位符
    assert re.search(r"\{\{CHANGE_ID\}\}", content)
    assert re.search(r"\{\{PARENT_SHA256\}\}", content)
    assert re.search(r"\{\{CEREMONY_LEVEL\}\}", content)
    assert re.search(r"\{\{LAYER_4_RESULT\}\}", content)


def test_change_circuit_reference_protocol_assertions():
    """
    [Scenario: Reference protocol assertions & three-way input triage]
    验证 src/references/change_circuit.md 满足断言句式与架构规范：
    1. 包含断言句式 SHALL, SHALL NOT, ONLY WHEN... THEN...
    2. 明确外部输入三类分流响应路径 (new_evidence, directive/scope_tweak, architecture_shift)
    3. 明确微调走轻量对照表，重大变更可选挂载 OpenSpec (ENHANCED_OPENSPEC)
    4. 明确母本冻结原则（严禁在母本上推倒重写，必须先只读快照归档）
    5. 明确签署件防伪（严禁 Agent 自签，signed_by 必须为人类操作者）
    6. 明确待核事项只标注不改数、定性裁决权归人类
    7. 包含本地 Git 优先、外设只读镜像的载体抽象原则 (§9.1)
    """
    ref_path = os.path.join(SRC_REFERENCES, "change_circuit.md")
    assert os.path.exists(ref_path), f"Missing reference: {ref_path}"

    with open(ref_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "SHALL" in content
    assert "SHALL NOT" in content
    assert "ONLY WHEN" in content

    # 三类外部输入
    assert "new_evidence" in content
    assert "directive" in content or "scope_tweak" in content
    assert "architecture_shift" in content or "fact_refutation" in content

    # 核心原则
    assert "母本冻结" in content or "Baseline Freeze" in content
    assert "零漂移" in content or "Zero-Drift" in content
    assert "只标注不改数" in content or "PENDING" in content
    assert "定性裁决" in content


# ---------------------------------------------------------------------------
# 2. 分类与影响分析编排测试 (--classify)
# ---------------------------------------------------------------------------

def test_classify_lightweight_rating_instruction():
    """
    [Requirement: Change Matrix Dispatch and Ceremony Triage]
    [Scenario: Change table records directive and target sections]
    输入样例法域出海模式评级微调指示，编排脚本输出 LIGHTWEIGHT 分级，
    精准提取受影响章节 [第1.2节, 表4-2] 及一手证据 ID [S-05, E-01]，
    且 requires_human_signoff 为 True。
    """
    instruction_path = os.path.join(FIXTURES_DIR, "instruction_lightweight.md")
    cmd = [
        sys.executable,
        CHANGE_DISPATCH_PY,
        "--root", SKILL_BUILD_DIR,
        "--instruction-file", instruction_path,
        "--classify",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Classify command failed: {proc.stderr}"

    data = json.loads(proc.stdout.strip())
    assert data["change_id"] == "change-01"
    assert data["ceremony_level"] == "LIGHTWEIGHT"
    assert data["requires_human_signoff"] is True
    assert any("1.2" in sec for sec in data["impacted_sections"])
    assert "S-05" in data["affected_evidence_ids"]
    assert "E-01" in data["affected_evidence_ids"]


def test_classify_major_architecture_shift_instruction():
    """
    [Requirement: Change Matrix Dispatch and Ceremony Triage]
    输入推翻既有架构与自建私有IDC结论的重大指示，编排脚本输出 MAJOR 分级。
    """
    instruction_path = os.path.join(FIXTURES_DIR, "instruction_major.md")
    cmd = [
        sys.executable,
        CHANGE_DISPATCH_PY,
        "--root", SKILL_BUILD_DIR,
        "--instruction-file", instruction_path,
        "--classify",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Classify command failed: {proc.stderr}"

    data = json.loads(proc.stdout.strip())
    assert data["change_id"] == "change-02"
    assert data["ceremony_level"] == "MAJOR"
    assert data["requires_human_signoff"] is True


# ---------------------------------------------------------------------------
# 3. 门禁阻断与母本冻结测试 (CRITERION M8-1 & Baseline Freeze)
# ---------------------------------------------------------------------------

def test_m8_1_blocked_without_approval_and_parent_baseline_unmodified():
    """
    [CRITERION M8-1 & Scenario: Modification without change signoff is blocked]
    测试在未获签署放行前：
    1. 直接运行 python3 scripts/gate_guard.py --gate change-01 --check-only 返回退出码 1，
       stdout JSON 包含 {"gate":"change-01","state":"PENDING","blocked":true}
    2. 运行 python3 scripts/change_dispatch.py --apply 返回退出码 1，
       stdout JSON 包含 {"applied":false,"blocked":true,"reason":"missing_change_approval"}
    3. 母本 draft_full.md content_sha256 严格保持不变。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        draft_path = os.path.join(tmpdir, "draft_full.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "baseline_draft_full.md"), draft_path)
        sha_before = compute_sha256(draft_path)

        table_path = os.path.join(tmpdir, "change-table.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "valid_change_table.md"), table_path)

        # 1. 校验 gate_guard.py check-only 阻断
        gate_cmd = [
            sys.executable,
            GATE_GUARD_PY,
            "--gate", "change-01",
            "--check-only",
            "--root", tmpdir,
        ]
        p_gate = subprocess.run(gate_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert p_gate.returncode == 1
        data_gate = json.loads(p_gate.stdout.strip())
        assert data_gate["gate"] == "change-01"
        assert data_gate["state"] == "PENDING"
        assert data_gate["blocked"] is True

        # 2. 校验 change_dispatch.py --apply 拒绝执行
        apply_cmd = [
            sys.executable,
            CHANGE_DISPATCH_PY,
            "--root", tmpdir,
            "--apply",
            "--change-table", table_path,
        ]
        p_apply = subprocess.run(apply_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert p_apply.returncode == 1
        data_apply = json.loads(p_apply.stdout.strip())
        assert data_apply["applied"] is False
        assert data_apply["blocked"] is True
        assert data_apply["reason"] == "missing_change_approval"

        # 3. 校验母本哈希绝对未变
        sha_after = compute_sha256(draft_path)
        assert sha_before == sha_after, "Parent baseline was illegally modified without gate approval!"


def test_m8_1_blocked_when_agent_attempts_forged_self_sign():
    """
    [CRITERION M8-1 & Anti-forgery Axiom]
    当 Agent 试图通过包含 signed_by: agent:xxx 的伪造签署件放行时，
    门禁必须判定为 AGENT_SIGNATURE_PROHIBITED 并无条件阻断 (exit 1)。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        table_path = os.path.join(tmpdir, "change-table.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "valid_change_table.md"), table_path)

        approval_path = os.path.join(tmpdir, "fake_approval.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "approval_fake_agent_negative.md"), approval_path)

        cmd = [
            sys.executable,
            GATE_GUARD_PY,
            "--gate", "change-01",
            "--verify",
            "--artifact", table_path,
            "--approval", approval_path,
            "--root", tmpdir,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 1
        data = json.loads(proc.stdout.strip())
        assert data["blocked"] is True
        assert data["state"] == "AGENT_SIGNATURE_PROHIBITED"


def test_m8_1_blocked_when_approval_is_stub():
    """
    [加固项 G: 桩签署件硬拒绝]
    含 stub: true 的 change-01 桩签署件即使哈希吻合，也必须 STUB_REJECTED 且退出码 1。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        table_path = os.path.join(tmpdir, "change-table.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "valid_change_table.md"), table_path)

        approval_path = os.path.join(tmpdir, "stub_approval.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "change-01-approval-stub.md"), approval_path)

        cmd = [
            sys.executable,
            GATE_GUARD_PY,
            "--gate", "change-01",
            "--verify",
            "--artifact", table_path,
            "--approval", approval_path,
            "--root", tmpdir,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 1
        data = json.loads(proc.stdout.strip())
        assert data["blocked"] is True
        assert data["state"] == "STUB_REJECTED"


# ---------------------------------------------------------------------------
# 4. 实施执行、快照归档与零漂移测试 (CRITERION M8-2 & M8-3)
# ---------------------------------------------------------------------------

def test_m8_apply_success_with_human_signoff_and_zero_drift():
    """
    [Requirement: Zero-Drift Readback and Snapshot Archival]
    [CRITERION M8-2 & M8-3]
    人类在 gates/change-01-approval.md 有效签署后：
    1. change_dispatch.py --apply 成功执行；
    2. 生成 pre-change 快照归档于 backup/ 目录；
    3. 改写母本，将「中高」精准替换为「高」；
    4. 回读复验旧评级残留为 0；
    5. diff-mode 验证非声明区域漂移为 0 (undeclared_drift == 0)；
    6. stdout 输出 {"applied":true,"backup":"...","undeclared_drift":0,"verified":true}，退出码 0。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        draft_path = os.path.join(tmpdir, "draft_full.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "baseline_draft_full.md"), draft_path)
        parent_sha = compute_sha256(draft_path)

        table_path = os.path.join(tmpdir, "change-table.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "valid_change_table.md"), table_path)
        table_sha = compute_sha256(table_path)

        # 准备人类签署件
        gates_dir = os.path.join(tmpdir, "gates")
        os.makedirs(gates_dir, exist_ok=True)
        approval_path = os.path.join(gates_dir, "change-01-approval.md")
        with open(approval_path, "w", encoding="utf-8") as f:
            f.write(f"""# 门禁审批签署件 (change-01 Approval Sign-off)
- gate: change-01
- decision: APPROVED
- signed_by: "human:research_director_wang"
- signed_at: "2026-11-23T11:00:00Z"
- artifact_sha256: "{table_sha}"
- signature: "PASSKEY_DIRECTOR_WANG_APPROVE_CHANGE_01"
""")

        # 执行变更实施
        cmd = [
            sys.executable,
            CHANGE_DISPATCH_PY,
            "--root", tmpdir,
            "--apply",
            "--change-table", table_path,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 0, f"--apply failed: {proc.stderr}"

        res = json.loads(proc.stdout.strip())
        assert res["applied"] is True
        assert res["verified"] is True
        assert res["undeclared_drift"] == 0
        assert "backup" in res
        assert os.path.exists(res["backup"])

        # 检查正文改写正确性
        with open(draft_path, "r", encoding="utf-8") as f:
            modified_text = f.read()

        assert "样例法域出海模式二的市场需求评级为高" in modified_text
        assert "样例法域出海模式二的市场需求评级为中高" not in modified_text

        # 检查备份快照哈希与 parent_baseline_sha256 一致 (CRITERION M8-3)
        check_backup_cmd = [
            sys.executable,
            VERIFY_READBACK_PY,
            "--verify-backup", os.path.join(tmpdir, "backup"),
            "--change-table", table_path,
            "--root", tmpdir,
        ]
        p_backup = subprocess.run(check_backup_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert p_backup.returncode == 0
        b_data = json.loads(p_backup.stdout.strip())
        assert b_data["backup_valid"] is True
        assert b_data["hash_matched"] is True

        # 检查审计命令 (--audit)
        audit_cmd = [
            sys.executable,
            CHANGE_DISPATCH_PY,
            "--root", tmpdir,
            "--audit",
            "--change-table", table_path,
        ]
        p_audit = subprocess.run(audit_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert p_audit.returncode == 0
        aud_data = json.loads(p_audit.stdout.strip())
        assert aud_data["audit_present"] is True
        assert aud_data["backup_present"] is True
        assert aud_data["undeclared_drift"] == 0


# ---------------------------------------------------------------------------
# 5. 阴性对照测试 (Negative Control: D-7 / CRITERION M8-2)
# ---------------------------------------------------------------------------

def test_m8_2_negative_control_undeclared_drift_intercepted():
    """
    [CRITERION M8-2 & 审查裁决 2: D-7 强制阴性对照]
    喂入包含非声明章节篡改的物料 undeclared_drift_patch.md（在第 3.1 节悄悄篡改了电价数据），
    断言 verify_readback.py --diff-mode 精准检出未声明漂移并以退出码 1 阻断。
    """
    baseline_path = os.path.join(FIXTURES_DIR, "baseline_draft_full.md")
    dirty_patch_path = os.path.join(FIXTURES_DIR, "undeclared_drift_patch.md")

    cmd = [
        sys.executable,
        VERIFY_READBACK_PY,
        "--diff-mode",
        "--old", baseline_path,
        "--new", dirty_patch_path,
        "--declared", "C-01",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 1, "Diff mode must fail when undeclared section is modified!"

    res = json.loads(proc.stdout.strip())
    assert res["undeclared_drift"] > 0
    assert len(res["drift_details"]) > 0
    drift_first = res["drift_details"][0]
    # 检出漂移所在行包含被篡改的第 3.1 节电价描述
    assert any("0.99" in s for s in drift_first["new_snippet"])


# ---------------------------------------------------------------------------
# 6. 失效传播与 STALE 标记测试 (CRITERION M8-4 / F4)
# ---------------------------------------------------------------------------

def test_m8_4_classify_stale_targets_and_propagate_invalidation():
    """
    [CRITERION M8-4 / F4]:
    1. --classify 输出必须包含 stale_targets 列表；
    2. 运行 --propagate 处理 brief 变更指示后：
       - 受影响的门禁行与任务行在四分状态列出现 STALE 标记 (如 '已审定 [STALE]');
       - 台账中的 [x] 复选框数量严格保持不变 (Agent 严禁擅自复位);
       - 母本文件 (如 draft_full.md) 哈希保持不变 (只标记不改写);
       - 退出码为 0，stdout 输出 {"propagated":true,"ledger_updated":true,"rewritten":false}。
    """
    instruction_path = os.path.join(FIXTURES_DIR, "instruction_brief_change.md")

    # 1. 测试 --classify 包含 stale_targets
    cmd_classify = [
        sys.executable,
        CHANGE_DISPATCH_PY,
        "--root", SKILL_BUILD_DIR,
        "--instruction-file", instruction_path,
        "--classify",
    ]
    p_c = subprocess.run(cmd_classify, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert p_c.returncode == 0
    data_c = json.loads(p_c.stdout.strip())
    assert "stale_targets" in data_c
    assert "G0" in data_c["stale_targets"]
    assert "T-P2-01" in data_c["stale_targets"]

    # 2. 准备工作区运行 --propagate
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = os.path.join(tmpdir, "progress-log.md")
        tpl_path = os.path.join(SRC_TEMPLATES, "progress_log.template.md")
        with open(tpl_path, "r", encoding="utf-8") as f:
            ledger_text = f.read()

        ledger_text = ledger_text.replace(
            "| P1 | T-P1-01 | grill-me 八项澄清访谈 | [ ] | 存在 |",
            "| P1 | T-P1-01 | grill-me 八项澄清访谈 | [x] | 已审定 |"
        ).replace(
            "| P2 | T-P2-01 | 治理台账与存储契约初始化 | [ ] | 已审定 |",
            "| P2 | T-P2-01 | 治理台账与存储契约初始化 | [x] | 已审定 |"
        ).replace(
            "| -  | T-G1-01 | G1 大纲人审门禁签署 | [ ] | 已审定 |",
            "| -  | T-G1-01 | G1 大纲人审门禁签署 | [x] | 已审定 |"
        )
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.write(ledger_text)

        draft_path = os.path.join(tmpdir, "draft_full.md")
        shutil.copy(os.path.join(FIXTURES_DIR, "baseline_draft_full.md"), draft_path)
        draft_sha_before = compute_sha256(draft_path)

        count_x_before = ledger_text.count("| [x] |")
        assert count_x_before == 3

        # 执行 --propagate
        cmd_propagate = [
            sys.executable,
            CHANGE_DISPATCH_PY,
            "--root", tmpdir,
            "--propagate",
            "--instruction-file", instruction_path,
            "--ledger", ledger_path,
        ]
        p_prop = subprocess.run(cmd_propagate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert p_prop.returncode == 0, f"Propagate failed: {p_prop.stderr}"
        data_prop = json.loads(p_prop.stdout.strip())
        assert data_prop["propagated"] is True
        assert data_prop["ledger_updated"] is True
        assert data_prop["rewritten"] is False

        # 检查台账内容
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger_after = f.read()

        assert "STALE" in ledger_after
        for line in ledger_after.splitlines():
            if "| T-P2-01 |" in line or "| T-G1-01 |" in line:
                assert "STALE" in line, f"Task line missing STALE: {line}"

        count_x_after = ledger_after.count("| [x] |")
        assert count_x_before == count_x_after == 3

        draft_sha_after = compute_sha256(draft_path)
        assert draft_sha_before == draft_sha_after


# ---------------------------------------------------------------------------
# 7. 回归：--root 必填与禁止写入 src/templates (R5)
# ---------------------------------------------------------------------------

def test_change_dispatch_requires_root_and_never_writes_template():
    """
    [回归 R5]:
    --propagate 不带 --root 时必须 exit 1，且严禁写入任何文件
    （尤其不得写 src/templates/progress_log.template.md）。
    """
    instruction_path = os.path.join(FIXTURES_DIR, "instruction_brief_change.md")
    tpl_path = os.path.join(SRC_TEMPLATES, "progress_log.template.md")
    tpl_sha_before = compute_sha256(tpl_path)

    cmd = [
        sys.executable,
        CHANGE_DISPATCH_PY,
        "--propagate",
        "--instruction-file", instruction_path,
    ]
    proc = subprocess.run(
        cmd, cwd=SKILL_BUILD_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    assert proc.returncode == 1, f"Missing --root must exit 1, got {proc.returncode}"
    data = json.loads(proc.stdout.strip())
    assert data.get("reason") == "root_required"

    assert compute_sha256(tpl_path) == tpl_sha_before, "template must never be written"


def test_propagate_missing_ledger_returns_explicit_reason():
    """
    [回归 R5]:
    --root 指向的工作区缺少 progress-log.md 时，必须 exit 1 并返回
    {"propagated":false,"reason":"workspace_ledger_not_found"}，禁止回退到模板路径。
    """
    instruction_path = os.path.join(FIXTURES_DIR, "instruction_brief_change.md")
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            sys.executable,
            CHANGE_DISPATCH_PY,
            "--root", tmpdir,
            "--propagate",
            "--instruction-file", instruction_path,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 1
        data = json.loads(proc.stdout.strip())
        assert data["propagated"] is False
        assert data["reason"] == "workspace_ledger_not_found"
        assert not os.path.exists(os.path.join(tmpdir, "progress-log.md"))


# ---------------------------------------------------------------------------
# 8. 回归：随库 workspace 夹具的快照核验与审计命令 (R4)
# ---------------------------------------------------------------------------

def test_audit_workspace_backup_verification_and_audit_cli():
    """
    [R4 / CRITERION M8-3]:
    README §2.4.1 / §2.4.2 必须能对随库 workspace 夹具直接执行并 exit 0：
    - verify_readback.py --verify-backup <ws>/backup --change-table <ws>/change-table.md
    - change_dispatch.py --root <ws> --audit --change-table change-table.md
    """
    ws = os.path.join(FIXTURES_DIR, "audit_workspace")

    cmd_backup = [
        sys.executable,
        VERIFY_READBACK_PY,
        "--verify-backup", os.path.join(ws, "backup"),
        "--change-table", os.path.join(ws, "change-table.md"),
    ]
    p1 = subprocess.run(cmd_backup, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert p1.returncode == 0, f"verify-backup failed: {p1.stdout} {p1.stderr}"
    d1 = json.loads(p1.stdout.strip())
    assert d1["backup_valid"] is True and d1["hash_matched"] is True

    cmd_audit = [
        sys.executable,
        CHANGE_DISPATCH_PY,
        "--root", ws,
        "--audit",
        "--change-table", "change-table.md",
    ]
    p2 = subprocess.run(cmd_audit, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert p2.returncode == 0, f"audit failed: {p2.stdout} {p2.stderr}"
    d2 = json.loads(p2.stdout.strip())
    assert d2["audit_present"] is True
    assert d2["backup_present"] is True
    assert d2["undeclared_drift"] == 0
