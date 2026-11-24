#!/usr/bin/env python3
"""
test_m9_skill_entry.py - SKILL.md 主入口契约黑箱验收与集成测试套件

测试对象:
  - src/SKILL.md (主入口契约文件)
  - tests/module_tests/test_m9_skill_entry/entry_validator.py (独立校验器)

覆盖场景与判据:
  1. Frontmatter 5 字段闭环 (SAFE_FRONTMATTER_KEYS)
  2. 行数严格 < 200 行 (目标 120-170 行)
  3. 正文第一条为逐字触发控制硬规则
  4. description 与 when_to_use 均含「默认不触发」否定句与显式调用约定
  5. 核心宪法五原则常量逐字统一
  6. 9 个 references 协议手册全部索引且状态真实
  7. 全部引用的 scripts/*.py 脚本存在或在待建清单中
  8. 四道人审门禁 (G0-G3) 与变更门禁路径闭环
  9. 三边界复核循环出口条件与 BLOCKED_NO_REVIEWER 阻断
  10. 可选增强层标注「默认不启用」
  11. 禁用词与具体项目实例扫描
  12. 阴性对照夹具反向拦截验证 (Negative Controls)
"""

import json
import os
import subprocess
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_BUILD_ROOT = os.path.normpath(os.path.join(CURRENT_DIR, "../../.."))
SRC_DIR = os.path.join(SKILL_BUILD_ROOT, "src")
SKILL_MD_PATH = os.path.join(SRC_DIR, "SKILL.md")
VALIDATOR_PATH = os.path.join(CURRENT_DIR, "entry_validator.py")
FIXTURES_DIR = os.path.join(CURRENT_DIR, "fixtures")

# 引入独立校验器核心函数
sys.path.insert(0, CURRENT_DIR)
from entry_validator import (
    validate_skill,
    SAFE_FRONTMATTER_KEYS,
    MANDATORY_REFERENCES,
    CONSTITUTION_CONSTANTS,
    FORBIDDEN_WORDS,
    SPECIFIC_INSTANCES,
    PLATFORM_NAMES,
)


class TestSkillEntryContract(unittest.TestCase):
    """SKILL.md 主入口黑箱验收测试套件"""

    def setUp(self):
        self.assertTrue(os.path.isfile(SKILL_MD_PATH), f"Missing SKILL.md at {SKILL_MD_PATH}")
        self.assertTrue(os.path.isfile(VALIDATOR_PATH), f"Missing entry_validator.py at {VALIDATOR_PATH}")
        with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
            self.raw_content = f.read()
        self.lines = self.raw_content.splitlines()

    def test_01_frontmatter_keys_exact_set(self):
        """Frontmatter 键集合必须恰好等于 5 个宿主安全键，严禁未知键"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["safe_keys_valid"], f"Frontmatter keys error: {res['errors']}")
        self.assertEqual(
            set(res["frontmatter_keys"]),
            SAFE_FRONTMATTER_KEYS,
            f"Frontmatter keys mismatch: expected {SAFE_FRONTMATTER_KEYS}, got {set(res['frontmatter_keys'])}",
        )

    def test_02_line_count_strictly_under_200(self):
        """文件行数必须严格 < 200 行 (目标 120-170 行)"""
        count = len(self.lines)
        self.assertLess(count, 200, f"SKILL.md line count {count} exceeds maximum of 200 lines")
        self.assertGreaterEqual(count, 80, f"SKILL.md line count {count} is suspiciously short")

    def test_03_first_body_rule_is_trigger_control(self):
        """正文第一条必须是触发控制硬规则，包含停止与零动作硬约束"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["trigger_rule_valid"], "Trigger control rule validation failed")

        # 验证逐字关键短语
        self.assertIn("用户显式调用 /rigorous-research-report", self.raw_content)
        self.assertIn("立即输出「本技能需显式调用 /rigorous-research-report 启动」并停止", self.raw_content)
        self.assertIn("不得发起任何澄清提问、不得创建任何文件", self.raw_content)

    def test_04_negative_phrasing_in_description_and_when_to_use(self):
        """description 与 when_to_use 均须包含「默认不触发」等否定句"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["negative_phrasing_valid"], "Negative phrasing validation failed")

    def test_05_constitution_five_constants_verbatim(self):
        """核心宪法五原则常量必须逐字统一，禁止任何改写或变体"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["constitution_constants_valid"], f"Constitution constants missing: {res['errors']}")
        for c in CONSTITUTION_CONSTANTS:
            self.assertIn(c, self.raw_content, f"Missing verbatim constitution constant: {c}")

    def test_06_all_nine_references_indexed_and_accounted(self):
        """9 个 references 路径全部列入索引表，且存在的已存在、未建的标记待建"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertEqual(res["references_count"], 9, "Must index exactly 9 references")
        for ref in MANDATORY_REFERENCES:
            self.assertIn(ref, res["references_indexed"], f"Missing reference: {ref}")

        # 检查未建的手册是否真实缺失
        for unbuilt in res["unbuilt_references"]:
            ref_path = os.path.join(SRC_DIR, unbuilt)
            self.assertFalse(os.path.isfile(ref_path), f"Reference {unbuilt} exists on disk but was marked unbuilt")

    def test_07_all_scripts_indexed_and_accounted(self):
        """引用的每个 scripts/*.py 路径要么真实存在，要么列入待建清单，且关键 CLI 形式完整"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertGreater(len(res["scripts_indexed"]), 0, "No scripts indexed in SKILL.md")
        for script_rel in res["scripts_indexed"]:
            full_path = os.path.join(SRC_DIR, script_rel)
            if script_rel in res["unbuilt_scripts"]:
                self.assertFalse(os.path.isfile(full_path), f"Script {script_rel} exists on disk but listed as unbuilt")
            else:
                self.assertTrue(os.path.isfile(full_path), f"Script {script_rel} claimed to exist but not on disk: {full_path}")

        # R5: 断言 --check-dedup 与 --guidelines-check 两种关键 CLI 形式已纳入索引
        self.assertIn("audit_text_hygiene.py draft_full.md --check-dedup", self.raw_content)
        self.assertIn("task_schema_check.py task.json --guidelines-check", self.raw_content)

    def test_08_human_gates_and_approval_files_closed(self):
        """G0-G3 四道人审门禁与变更门禁及签署件契约齐全"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["gates_valid"], f"Gates validation failed: {res['errors']}")
        self.assertIn("gates/G0-approval.md", self.raw_content)
        self.assertIn("gates/G1-approval.md", self.raw_content)
        self.assertIn("gates/G2-approval.md", self.raw_content)
        self.assertIn("gates/G3-approval.md", self.raw_content)
        self.assertIn("gates/change-", self.raw_content)

    def test_09_review_loop_exit_criteria_and_redline(self):
        """复核循环必须满足 D0=0、四层回读全过、人放行，缺失独立复核必须 BLOCKED_NO_REVIEWER"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["review_loop_exit_valid"], "Review loop exit criteria validation failed")
        self.assertIn("BLOCKED_NO_REVIEWER", self.raw_content)
        self.assertIn("四层回读", self.raw_content)

    def test_10_optional_enhancement_layers_default_disabled(self):
        """可选增强层 (OpenSpec变更等) 必须明确标注「默认不启用」"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertTrue(res["enhancement_layers_valid"], "Enhancement layers validation failed")

    def test_11_forbidden_words_and_instances_absent(self):
        """禁止出现「应当/尽量/注意」及项目具体词汇「样例法域/词元」与特定平台名"""
        res = validate_skill(SKILL_MD_PATH, SRC_DIR)
        self.assertEqual(res["forbidden_words_found"], [], f"Forbidden words found: {res['forbidden_words_found']}")
        self.assertEqual(res["specific_instances_found"], [], f"Specific instances found: {res['specific_instances_found']}")
        self.assertEqual(res["platform_names_found"], [], f"Platform names found: {res['platform_names_found']}")

    def test_12_standalone_validator_cli_run(self):
        """运行 entry_validator.py CLI，退出码必须为 0，stdout 输出标准 JSON"""
        cmd = [sys.executable, VALIDATOR_PATH, "--skill", SKILL_MD_PATH, "--src-root", SRC_DIR]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0, f"Validator CLI failed: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("valid"), f"Validator reported invalid: {data.get('errors')}")
        self.assertEqual(data.get("references_count"), 9)

    def test_13_negative_controls_rejected(self):
        """阴性对照：所有异常夹具喂入校验器时必须返回非 0 退出码且 valid=False"""
        fixture_files = [
            "bad_frontmatter_disallowed_keys.md",
            "bad_frontmatter_missing_keys.md",
            "bad_overlong.md",
            "bad_first_rule.md",
            "bad_forbidden_words.md",
            "bad_specific_instance.md",
            "bad_missing_references.md",
        ]
        for fname in fixture_files:
            fpath = os.path.join(FIXTURES_DIR, fname)
            self.assertTrue(os.path.isfile(fpath), f"Missing negative fixture: {fpath}")
            cmd = [sys.executable, VALIDATOR_PATH, "--skill", fpath, "--src-root", SRC_DIR]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(
                proc.returncode,
                1,
                f"Negative control {fname} should exit with code 1, got {proc.returncode}. stdout: {proc.stdout}",
            )
            data = json.loads(proc.stdout)
            self.assertFalse(data.get("valid"), f"Negative control {fname} should report valid=False")
            self.assertGreater(len(data.get("errors", [])), 0, f"Negative control {fname} should report errors")


if __name__ == "__main__":
    unittest.main()
