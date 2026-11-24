#!/usr/bin/env python3
"""
test_m1.py - M1 模块自动化黑箱与单元测试套件

测试对象:
  1. src/references/P1_grill_me_protocol.md (规范合规性与无禁词)
  2. src/templates/brief.template.md (模板变量与内嵌宪法)
  3. src/templates/approval_gate.template.md (门禁申请与审批单契约)
  4. src/scripts/gate_guard.py (通用门禁校验逻辑、防伪与阻断)
  5. 落地澄清决策树与 Frontier 队列推算 (elicitation_evaluator.py)

兼容环境:
  既可由 Python 3 标准库直接执行: python3 test_m1.py
  亦支持 pytest 框架: pytest test_m1.py
"""

import json
import os
import subprocess
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.normpath(os.path.join(CURRENT_DIR, "..", "..", ".."))
SRC_SCRIPTS_DIR = os.path.join(MODULE_ROOT, "src", "scripts")
GATE_GUARD_PATH = os.path.join(SRC_SCRIPTS_DIR, "gate_guard.py")
FIXTURES_DIR = os.path.join(CURRENT_DIR, "fixtures")
GATES_FIXTURES_DIR = os.path.join(FIXTURES_DIR, "gates")


class TestM1BriefElicitation(unittest.TestCase):

    def setUp(self):
        self.assertTrue(os.path.exists(GATE_GUARD_PATH), f"gate_guard.py not found at {GATE_GUARD_PATH}")
        self.assertTrue(os.path.exists(FIXTURES_DIR), f"Fixtures dir not found at {FIXTURES_DIR}")

    def test_p1_protocol_assertions_and_forbidden_terms(self):
        """检验 P1 协议手册：必须采用断言句式，严禁出现'尽量/应当/注意'"""
        protocol_path = os.path.join(MODULE_ROOT, "src", "references", "P1_grill_me_protocol.md")
        self.assertTrue(os.path.exists(protocol_path), f"Protocol file missing: {protocol_path}")

        with open(protocol_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 断言句式检查
        self.assertIn("必须", content)
        self.assertIn("禁止", content)
        self.assertIn("仅当", content)

        # 禁用词扫描
        forbidden = ["尽量", "应当", "注意"]
        for word in forbidden:
            self.assertNotIn(word, content, f"Forbidden word '{word}' found in P1 protocol")

        # 核心规则检查
        self.assertIn("一次一问", content)
        self.assertIn("Active Frontier", content)
        self.assertIn("Decision Summary", content)
        self.assertIn("LOCAL_GIT_FIRST", content)

    def test_brief_template_and_embedded_constitution(self):
        """CRITERION M1-1, M1-2, M2-2: 检查简报模板与内嵌宪法五原则"""
        template_path = os.path.join(MODULE_ROOT, "src", "templates", "brief.template.md")
        self.assertTrue(os.path.exists(template_path))

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 11 个独立小节 (2.1 - 2.11)
        for i in range(1, 12):
            sec_num = f"2.{i} "
            self.assertIn(sec_num, content, f"Missing section {sec_num} in brief template")

        # 唯一事实源派生声明
        sole_decl = "本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准"
        self.assertIn(sole_decl, content)

        # 项目宪法五原则
        constitution_rules = [
            "事实判锤唯二通路",
            "定性裁决权归人类",
            "无隐藏状态",
            "非同族对抗复核且审者只读",
            "严禁跨口径相减",
        ]
        self.assertIn("3. 项目宪法", content)
        for rule in constitution_rules:
            self.assertIn(rule, content, f"Missing constitutional rule: {rule}")

        # 诉求索引必须包含 REQ-ID
        self.assertIn("REQ-01", content)

    def test_elicitation_frontier_missing_dimensions(self):
        """Scenario: Missing mandatory dimension blocks progression & populates frontier"""
        input_file = os.path.join(FIXTURES_DIR, "input_missing_two_dimensions.json")
        evaluator_path = os.path.join(CURRENT_DIR, "elicitation_evaluator.py")

        res = subprocess.run(
            [sys.executable, evaluator_path, "--input", input_file],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Evaluator failed: {res.stderr}")

        data = json.loads(res.stdout)
        self.assertFalse(data["is_complete"])
        self.assertEqual(data["unresolved_count"], 2)

        # 未解决维度必须包含 D5 (format) 与 D6 (delivery path)
        unresolved_ids = [u["id"] for u in data["all_unresolved_dimensions"]]
        self.assertIn("D5", unresolved_ids)
        self.assertIn("D6", unresolved_ids)

        # 活跃 Frontier 队列首项必须为依赖就绪的 D5
        self.assertTrue(len(data["active_frontier"]) >= 1)
        next_q = data["active_frontier"][0]
        self.assertEqual(next_q["id"], "D5")

        # 必须提供推荐选项 (2-4 项) + [Other]
        options = next_q["recommended_options"]
        self.assertTrue(3 <= len(options) <= 5, f"Expected 3-5 options (2-4 + Other), got {len(options)}")
        self.assertTrue(any("[Other]" in opt for opt in options))

    def test_sample_brief_draft_verification(self):
        """Scenario: Brief contains explicit constitutional rules and REQ-ID list, and valid brief_content_sha256"""
        draft_path = os.path.join(FIXTURES_DIR, "sample_brief_draft.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", draft_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Verify brief failed: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertTrue(data["valid"])
        self.assertEqual(len(data["errors"]), 0)

    def test_gate_g0_check_only_missing_blocks(self):
        """CRITERION M1-3 / Scenario: Unapproved G0 blocks pipeline execution (missing approval)"""
        # 在不存在 approval 的临时根目录下运行
        non_existent_root = os.path.join(FIXTURES_DIR, "empty_workspace")
        os.makedirs(non_existent_root, exist_ok=True)

        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--check-only", "--root", non_existent_root],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, "Expected exit code 1 when approval file missing")
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "G0")
        self.assertEqual(data["state"], "PENDING")
        self.assertTrue(data["blocked"])
        self.assertIsNone(data["artifact_sha256"])

        # 清理空目录
        try:
            os.rmdir(non_existent_root)
        except OSError:
            pass

    def test_gate_g0_relative_root_reason_has_no_double_path_join(self):
        """[R6.3 回归] --root 为相对路径时，reason 中的签署件路径严禁双重拼接"""
        rel_root = "tests/module_tests/test_m1_elicitation/fixtures/empty_workspace"
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--check-only", "--root", rel_root],
            capture_output=True,
            text=True,
            cwd=MODULE_ROOT,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout.strip())
        expected = f"Approval file not found: {rel_root}/gates/G0-approval.md"
        self.assertEqual(data["reason"], expected)
        self.assertNotIn(f"{rel_root}/{rel_root}", data["reason"])

    def test_gate_g0_pending_approval_blocks(self):
        """Scenario: Approval file marked PENDING blocks progression"""
        brief_path = os.path.join(FIXTURES_DIR, "sample_brief_draft.md")
        approval_path = os.path.join(GATES_FIXTURES_DIR, "G0-approval-pending.md")

        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--verify", "--artifact", brief_path, "--approval", approval_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "G0")
        self.assertEqual(data["state"], "PENDING")
        self.assertTrue(data["blocked"])

    def test_gate_g0_valid_approval_passes(self):
        """Scenario: Valid G0 approval permits pipeline execution (exit 0, blocked: false)"""
        brief_path = os.path.join(FIXTURES_DIR, "sample_brief_draft.md")
        approval_path = os.path.join(GATES_FIXTURES_DIR, "G0-approval-valid.md")

        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--verify", "--artifact", brief_path, "--approval", approval_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "G0")
        self.assertEqual(data["state"], "APPROVED")
        self.assertFalse(data["blocked"])
        self.assertIsNotNone(data["artifact_sha256"])

    def test_negative_control_fake_agent_signature_prohibited(self):
        """阴性对照用例: 传入 Agent 自签放行件 (signed_by: agent:*)，断言严格阻断"""
        brief_path = os.path.join(FIXTURES_DIR, "sample_brief_draft.md")
        approval_path = os.path.join(GATES_FIXTURES_DIR, "G0-approval-fake-agent.md")

        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--verify", "--artifact", brief_path, "--approval", approval_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, "Agent signature must be rejected with exit code 1")
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "G0")
        self.assertEqual(data["state"], "AGENT_SIGNATURE_PROHIBITED")
        self.assertTrue(data["blocked"])
        self.assertIn("strictly prohibited", data["reason"])

    def test_negative_control_hash_mismatch_blocks(self):
        """阴性对照用例: 签署件中的哈希与工件实际 SHA-256 不符，断言严格阻断"""
        brief_path = os.path.join(FIXTURES_DIR, "sample_brief_draft.md")
        approval_path = os.path.join(GATES_FIXTURES_DIR, "G0-approval-hash-mismatch.md")

        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--verify", "--artifact", brief_path, "--approval", approval_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, "Hash mismatch must be rejected with exit code 1")
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "G0")
        self.assertEqual(data["state"], "HASH_MISMATCH")
        self.assertTrue(data["blocked"])
        self.assertIn("mismatch", data["reason"])

    def test_stub_approval_rejected_even_with_matching_hash(self):
        """加固项 G: 含 stub: true 的桩签署件必须被 STUB_REJECTED 硬拒绝 (即使哈希吻合)"""
        brief_path = os.path.join(FIXTURES_DIR, "sample_brief_draft.md")
        approval_path = os.path.join(GATES_FIXTURES_DIR, "G0-approval-stub.md")

        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "G0", "--verify", "--artifact", brief_path, "--approval", approval_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, "Stub approval must be rejected with exit code 1")
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "G0")
        self.assertEqual(data["state"], "STUB_REJECTED")
        self.assertTrue(data["blocked"])

    def test_gate_guard_change_gate_support(self):
        """通用接口验证: 支持 change-<id> 门禁名称与阻断输出 (AL-08)"""
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--gate", "change-01", "--check-only"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["gate"], "change-01")
        self.assertEqual(data["state"], "PENDING")
        self.assertTrue(data["blocked"])
        self.assertIsNone(data["artifact_sha256"])

    def test_constitution_rules_system_constants_verbatim(self):
        """[AL-05 / CRITERION M2-2] 宪法五原则全局系统常量逐字一致性核验"""
        # 1. 验证 gate_guard.py 中的 CONSTITUTION_RULES
        sys.path.insert(0, SRC_SCRIPTS_DIR)
        try:
            import gate_guard
            const_rules = list(gate_guard.CONSTITUTION_RULES)
        finally:
            if SRC_SCRIPTS_DIR in sys.path:
                sys.path.remove(SRC_SCRIPTS_DIR)

        expected_five = [
            "事实判锤唯二通路",
            "定性裁决权归人类",
            "无隐藏状态",
            "非同族对抗复核且审者只读",
            "严禁跨口径相减",
        ]
        self.assertEqual(const_rules, expected_five, f"CONSTITUTION_RULES mismatch: {const_rules}")

        # 2. 验证 brief.template.md 正文逐字内嵌这 5 条，禁止任何变体
        brief_tpl = os.path.join(MODULE_ROOT, "src", "templates", "brief.template.md")
        with open(brief_tpl, "r", encoding="utf-8") as f:
            tpl_text = f.read()

        for rule in expected_five:
            self.assertIn(rule, tpl_text, f"Constitutional rule '{rule}' missing from brief.template.md")

        # 变体禁令检查
        forbidden_variants = ["事实判定唯二通路", "定性裁决留给人类"]
        for variant in forbidden_variants:
            self.assertNotIn(variant, tpl_text, f"Forbidden variant '{variant}' found in brief.template.md")

    def test_check_provenance_heterogeneous_passes(self):
        """[AL-06 & M6-2] 异族跨厂商模型对抗复核调用证明校验放行 (exit 0)"""
        provenance_path = os.path.join(FIXTURES_DIR, "provenance_valid_heterogeneous.json")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--check-provenance", provenance_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertTrue(data["provenance_valid"])
        self.assertTrue(data["isolated"])
        self.assertEqual(data["channel"], "异族")
        self.assertEqual(len(data.get("errors", [])), 0)

    def test_check_provenance_homologous_reset_passes(self):
        """[AL-06 & M6-2] 同族-零记忆隔离且 context_reset=True 复核证明放行 (exit 0)"""
        provenance_path = os.path.join(FIXTURES_DIR, "provenance_valid_homologous_reset.json")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--check-provenance", provenance_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertTrue(data["provenance_valid"])
        self.assertTrue(data["isolated"])
        self.assertEqual(data["channel"], "同族-零记忆隔离")
        self.assertEqual(len(data.get("errors", [])), 0)

    def test_negative_control_provenance_same_session_fails(self):
        """[AL-06 阴性对照] 伪造隔离但 session 相同 (writer.session == reviewer.session) 必须阻断 (exit 1)"""
        provenance_path = os.path.join(FIXTURES_DIR, "unisolated_provenance.json")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--check-provenance", provenance_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["provenance_valid"])
        self.assertFalse(data["isolated"])
        self.assertTrue(len(data.get("errors", [])) > 0)
        self.assertTrue(any("session" in err for err in data["errors"]))

    def test_negative_control_provenance_same_vendor_fails(self):
        """[AL-06 阴性对照] channel=异族 但两者 model 厂商前缀相同 (如 gpt-* vs gpt-*) 必须阻断 (exit 1)"""
        provenance_path = os.path.join(FIXTURES_DIR, "provenance_invalid_same_vendor.json")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--check-provenance", provenance_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["provenance_valid"])
        self.assertFalse(data["isolated"])
        self.assertTrue(any("differing model vendor" in err for err in data["errors"]))

    def test_negative_control_provenance_no_reset_fails(self):
        """[AL-06 阴性对照] channel=同族-零记忆隔离 但 context_reset=False 必须阻断 (exit 1)"""
        provenance_path = os.path.join(FIXTURES_DIR, "provenance_invalid_no_reset.json")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--check-provenance", provenance_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["provenance_valid"])
        self.assertFalse(data["isolated"])
        self.assertTrue(any("context_reset" in err for err in data["errors"]))

    def test_f1_negative_brief_with_placeholder_rejected(self):
        """[F1 阴性对照 / CRITERION M1-4] 占位符残留 brief 必须被拦截且退出码 1"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_placeholder_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("placeholders" in err.lower() or "READERS" in err for err in data["errors"]))

    def test_f1_negative_brief_with_pending_value_rejected(self):
        """[F1 阴性对照 / CRITERION M1-4] 包含待定值 (待定/TBD) brief 必须被拦截且退出码 1"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_pending_value_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("pending" in err.lower() or "待定" in err for err in data["errors"]))

    def test_f1_negative_brief_with_invalid_enum_rejected(self):
        """[F1 阴性对照 / CRITERION M1-4, M2-5] 枚举越界 brief 必须被拦截且退出码 1"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_invalid_enum_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("source_of_truth" in err for err in data["errors"]))

    def test_f1_negative_brief_with_relative_path_rejected(self):
        """[F1 阴性对照 / CRITERION M1-4] target_local_dir 为相对路径 brief 必须被拦截且退出码 1"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_relative_path_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("absolute path" in err for err in data["errors"]))

    def test_f2_negative_brief_missing_human_decision_rejected(self):
        """[F2 阴性对照 / CRITERION M1-5] 继承声明缺少 CONFIRMED/REVISED 裁决必须被拦截且退出码 1"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_missing_human_decision_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("human_decision" in err for err in data["errors"]))

    def test_f1_positive_brief_with_legal_status_markers_allowed(self):
        """[F1 正例防误报 / CRITERION M1-4] 合法状态标记 '待核' 与 '待索证' 必须正常放行 (exit 0)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_legal_pending_markers_positive.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertTrue(data["valid"])
        self.assertEqual(len(data["errors"]), 0)

    def test_f3_unclarified_soft_item_passes(self):
        """[F3 正例 / CRITERION M1-1, M1-6] 软项登记 NOT_CLARIFIED + 合法 reason 必须放行 (exit 0)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_unclarified_soft_item_positive.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Unclarified soft item must pass, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertTrue(data["valid"])
        self.assertEqual(len(data["errors"]), 0)

    def test_f3_unclarified_item_missing_reason_rejected(self):
        """[F3 阴性对照 / CRITERION M1-1] NOT_CLARIFIED 缺 unclarified_reason 必须阻断 (exit 1)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_unclarified_missing_reason_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("unclarified_reason" in err for err in data["errors"]))

    def test_f3_invalid_clarification_status_rejected(self):
        """[F3 阴性对照 / CRITERION M1-1] clarification_status 取值非法必须阻断 (exit 1)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_invalid_clarification_status_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("clarification_status" in err for err in data["errors"]))

    def test_f3_clarified_item_with_pending_term_rejected(self):
        """[F3 阴性对照 / CRITERION M1-4] CLARIFIED 项内容含「待定」必须阻断 (exit 1)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_clarified_pending_term_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("待定" in err for err in data["errors"]))

    def test_f3_unclarified_item_marker_not_false_positive(self):
        """[F3 正例防误报 / CRITERION M1-4] NOT_CLARIFIED 项内容含「未澄清」不得误报 (exit 0)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_unclarified_content_marker_positive.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Unclarified marker must not be flagged, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertTrue(data["valid"])
        self.assertEqual(len(data["errors"]), 0)

    def test_f3_clarified_source_of_truth_invalid_enum_rejected(self):
        """[F3 阴性对照 / CRITERION M2-5] source_of_truth 标 CLARIFIED 但值越界必须阻断 (exit 1)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_clarified_invalid_source_of_truth_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("source_of_truth" in err for err in data["errors"]))

    def test_f3_unclarified_item_default_behavior_enforced(self):
        """[F3 阴性对照 / CRITERION M1-6] 未澄清项未落默认行为值必须阻断 (exit 1)"""
        brief_path = os.path.join(FIXTURES_DIR, "brief_unclarified_source_of_truth_not_default_negative.md")
        res = subprocess.run(
            [sys.executable, GATE_GUARD_PATH, "--verify-brief", brief_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, f"Expected 1, got {res.returncode}: {res.stdout}")
        data = json.loads(res.stdout.strip())
        self.assertFalse(data["valid"])
        self.assertTrue(any("M1-6" in err for err in data["errors"]))


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestM1BriefElicitation)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
