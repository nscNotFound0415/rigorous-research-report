#!/usr/bin/env python3
"""
test_m5_outline.py - M5 章节架构规划与 G1 人审门禁 自动化测试套件

涵盖建设方案 §1.2、§1.3、§8.1 与 OpenSpec outline-approval/spec.md 规定的全部场景：
1. CRITERION M5-1a: 并行期允许显式登记的 PENDING 引用并放行
2. CRITERION M5-1b: Join 2 汇合门禁清零检查 (严格模式下 PENDING 必须为 0)
3. 阴性对照 a: outline 中存在 2 条未在 index 登记的悬空引用，必须报出 missing_refs 并返回退出码 1
4. 阴性对照 b: outline 中存在 PENDING 但「待补数据」小节未登记，必须阻断并返回退出码 1
5. 阴性对照 d: §8.1 规定的旧料 dangling_evidence_outline.md 喂入严格模式必报错 (退出码 1)
6. 结构校验: 章节跳级、缺失论证目的、缺失 evidence_ref 均返回退出码 1
7. CRITERION M5-3: 未签署 G1 或 G1 被驳回 (REJECTED/CHANGES_REQUESTED) 时阻断合稿流转 (退出码 1)
8. CRITERION M5-2: 具备合规人类签署的 G1 放行单且哈希一致时顺利放行 (退出码 0)
9. 门禁防伪: Agent 自签与哈希篡改均被无条件阻断 (退出码 1)
"""

import json
import os
import subprocess
import sys
import pytest

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(MODULE_DIR, "../../.."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "src", "scripts")
FIXTURES_DIR = os.path.join(MODULE_DIR, "fixtures")

OUTLINE_CHECK_SCRIPT = os.path.join(SCRIPTS_DIR, "outline_check.py")
GATE_GUARD_SCRIPT = os.path.join(SCRIPTS_DIR, "gate_guard.py")


def run_cmd(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


class TestOutlineCheckParallelPhase:
    """并行期大纲证据引用校验 (CRITERION M5-1a)"""

    def test_parallel_phase_valid_declared_pending(self):
        outline_file = os.path.join(FIXTURES_DIR, "valid_outline_parallel.md")
        index_file = os.path.join(FIXTURES_DIR, "evidence-index.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--evidence-index", index_file
        ])
        assert res.returncode == 0, f"Expected 0, got {res.returncode}. stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["missing_refs"] == []
        assert "PENDING-01" in data["pending_refs"]
        assert data["pending_declared"] is True
        assert data["refs_total"] >= 4

    def test_missing_refs_negative_control_scenario_a(self):
        """(a) outline 中有 2 条 evidence_ref 指向不存在的证据，期望 missing_refs 报出且退出码 1"""
        outline_file = os.path.join(FIXTURES_DIR, "negative_controls", "missing_refs_outline.md")
        index_file = os.path.join(FIXTURES_DIR, "evidence-index.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--evidence-index", index_file
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert "EVD-998" in data["missing_refs"]
        assert "EVD-999" in data["missing_refs"]
        assert len(data["missing_refs"]) == 2

    def test_unlisted_pending_negative_control_scenario_b(self):
        """(b) outline 有 PENDING 但「待补数据」小节未列出，期望退出码 1"""
        outline_file = os.path.join(FIXTURES_DIR, "negative_controls", "unlisted_pending_outline.md")
        index_file = os.path.join(FIXTURES_DIR, "evidence-index.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--evidence-index", index_file
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert data["pending_declared"] is False
        assert "PENDING-99" in data["pending_refs"]


class TestOutlineCheckJoin2Barrier:
    """Join 2 汇合不可豁免门禁清零检查 (CRITERION M5-1b)"""

    def test_join2_barrier_with_pending_blocks(self):
        """并行期草稿在 Join 2 严格模式下必须被阻断 (存在 PENDING 引用)"""
        outline_file = os.path.join(FIXTURES_DIR, "valid_outline_parallel.md")
        index_file = os.path.join(FIXTURES_DIR, "evidence-index.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--evidence-index", index_file,
            "--require-resolved"
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert len(data["pending_refs"]) > 0

    def test_join2_barrier_resolved_passes(self):
        """全量证据回指清零的大纲在 Join 2 汇合核验中顺利通过"""
        outline_file = os.path.join(FIXTURES_DIR, "valid_outline_resolved.md")
        index_file = os.path.join(FIXTURES_DIR, "evidence-index.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--evidence-index", index_file,
            "--require-resolved"
        ])
        assert res.returncode == 0, f"Expected 0, got {res.returncode}. stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["missing_refs"] == []
        assert data["pending_refs"] == []
        assert data["pending_count"] == 0

    def test_dangling_evidence_fixture_negative_control_scenario_d(self):
        """§8.1 阴性对照旧料 dangling_evidence_outline.md 喂入严格模式必报错 (退出码 1)"""
        outline_file = os.path.join(FIXTURES_DIR, "negative_controls", "dangling_evidence_outline.md")
        index_file = os.path.join(FIXTURES_DIR, "evidence-index.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--evidence-index", index_file,
            "--strict"
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert len(data["pending_refs"]) > 0


class TestOutlineSectionStructure:
    """章节结构、层级与论证目的校验 (--check-sections)"""

    def test_check_sections_valid(self):
        outline_file = os.path.join(FIXTURES_DIR, "valid_outline_parallel.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--check-sections"
        ])
        assert res.returncode == 0, f"Expected 0, got {res.returncode}. stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["invalid_sections"] == []
        assert data["chapter_count"] == 3

    def test_check_sections_skipped_heading(self):
        """标题层级跳级（如 H2 直接跳至 H4）必须报错"""
        outline_file = os.path.join(FIXTURES_DIR, "negative_controls", "skipped_heading_outline.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--check-sections"
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert len(data["invalid_sections"]) > 0
        assert any("skipped" in s.lower() for s in data["invalid_sections"])

    def test_check_sections_missing_objective(self):
        """某章缺失显式论证目的行必须报错"""
        outline_file = os.path.join(FIXTURES_DIR, "negative_controls", "missing_objective_outline.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--check-sections"
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert len(data["invalid_sections"]) > 0
        assert any("论证目的" in s for s in data["invalid_sections"])

    def test_check_sections_no_evidence(self):
        """某章缺少 evidence_ref（少于 1 条）必须报错"""
        outline_file = os.path.join(FIXTURES_DIR, "negative_controls", "no_evidence_outline.md")

        res = run_cmd([
            sys.executable, OUTLINE_CHECK_SCRIPT,
            outline_file,
            "--check-sections"
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert len(data["invalid_sections"]) > 0
        assert any("evidence_ref" in s for s in data["invalid_sections"])


class TestGateG1WorkflowInterception:
    """G1 门禁防伪与人审拦截机制 (CRITERION M5-2 & M5-3)"""

    def test_g1_gate_missing_approval_blocks_scenario_c(self):
        """(c) G1 未签署时 gate_guard.py --gate G1 --check-only 必须退出码 1"""
        empty_root = os.path.join(FIXTURES_DIR, "empty_workspace")

        res = run_cmd([
            sys.executable, GATE_GUARD_SCRIPT,
            "--gate", "G1",
            "--check-only",
            "--root", empty_root
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert data["gate"] == "G1"
        assert data["state"] == "PENDING"
        assert data["blocked"] is True

    def test_g1_gate_rejected_blocks(self):
        """G1 签署件处于 REJECTED 状态时必须退出码 1，阻断向 M7 合稿流转"""
        approval_file = os.path.join(FIXTURES_DIR, "gates", "G1-approval-rejected.md")
        artifact_file = os.path.join(FIXTURES_DIR, "valid_outline_resolved.md")

        res = run_cmd([
            sys.executable, GATE_GUARD_SCRIPT,
            "--gate", "G1",
            "--verify",
            "--artifact", artifact_file,
            "--approval", approval_file
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert data["gate"] == "G1"
        assert data["state"] == "REJECTED"
        assert data["blocked"] is True

    def test_g1_gate_valid_human_approval_passes(self):
        """CRITERION M5-2: 人类有效签署且哈希逐字节一致时顺利放行 (退出码 0)"""
        approval_file = os.path.join(FIXTURES_DIR, "gates", "G1-approval-valid.md")
        artifact_file = os.path.join(FIXTURES_DIR, "valid_outline_resolved.md")

        res = run_cmd([
            sys.executable, GATE_GUARD_SCRIPT,
            "--gate", "G1",
            "--verify",
            "--artifact", artifact_file,
            "--approval", approval_file
        ])
        assert res.returncode == 0, f"Expected 0, got {res.returncode}. stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["gate"] == "G1"
        assert data["state"] == "APPROVED"
        assert data["blocked"] is False
        assert data["artifact_sha256"] == "3a8daa4de28ed6efe783fd66d8da2ead1ab0d9171f5efdf1ef1ef72e5086dcd7"

    def test_g1_gate_fake_agent_signature_blocked(self):
        """门禁防伪：严禁 Agent 自签 (signed_by: agent:*)，必须退出码 1"""
        approval_file = os.path.join(FIXTURES_DIR, "gates", "G1-approval-fake-agent.md")
        artifact_file = os.path.join(FIXTURES_DIR, "valid_outline_resolved.md")

        res = run_cmd([
            sys.executable, GATE_GUARD_SCRIPT,
            "--gate", "G1",
            "--verify",
            "--artifact", artifact_file,
            "--approval", approval_file
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert data["state"] == "AGENT_SIGNATURE_PROHIBITED"
        assert data["blocked"] is True

    def test_g1_gate_hash_mismatch_blocked(self):
        """工件哈希不符时必须退出码 1"""
        approval_file = os.path.join(FIXTURES_DIR, "gates", "G1-approval-hash-mismatch.md")
        artifact_file = os.path.join(FIXTURES_DIR, "valid_outline_resolved.md")

        res = run_cmd([
            sys.executable, GATE_GUARD_SCRIPT,
            "--gate", "G1",
            "--verify",
            "--artifact", artifact_file,
            "--approval", approval_file
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert data["state"] == "HASH_MISMATCH"
        assert data["blocked"] is True

    def test_g1_gate_stub_approval_rejected(self):
        """加固项 G: 含 stub: true 的 G1 桩签署件必须 STUB_REJECTED (即使哈希吻合)"""
        approval_file = os.path.join(FIXTURES_DIR, "gates", "G1-approval-stub.md")
        artifact_file = os.path.join(FIXTURES_DIR, "valid_outline_resolved.md")

        res = run_cmd([
            sys.executable, GATE_GUARD_SCRIPT,
            "--gate", "G1",
            "--verify",
            "--artifact", artifact_file,
            "--approval", approval_file
        ])
        assert res.returncode == 1, f"Expected 1, got {res.returncode}"
        data = json.loads(res.stdout.strip())
        assert data["gate"] == "G1"
        assert data["state"] == "STUB_REJECTED"
        assert data["blocked"] is True
