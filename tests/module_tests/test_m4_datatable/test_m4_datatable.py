#!/usr/bin/env python3
"""
test_m4_datatable.py - M4 并行事实调研与底表重构 模块黑箱与单元测试套件

测试对象:
  1. src/references/P4_fact_finding_datatable.md (协议断言与无禁词检查)
  2. src/templates/datatable.template.md (底表模板与列名契约)
  3. src/templates/evidence_index.template.md (证据索引模板契约)
  4. src/scripts/audit_calc.py (纯代码 AST 复算、容差判定、口径隔离与证据索引核验)
  5. tests/module_tests/test_m4_datatable/fixtures/ (全场景测试夹具与阴性对照)

符合标准:
  - 纯 Python 3 标准库 / pytest 框架无缝兼容
  - 100% 覆盖 CRITERION M4-1, M4-2, M4-3 及 fact-verification spec.md 全部 Scenarios
"""

import ast
import json
import os
import re
import subprocess
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

SRC_SCRIPTS = os.path.join(MODULE_ROOT, "src", "scripts")
if SRC_SCRIPTS not in sys.path:
    sys.path.insert(0, SRC_SCRIPTS)

SRC_TEMPLATES = os.path.join(MODULE_ROOT, "src", "templates")
SRC_REFERENCES = os.path.join(MODULE_ROOT, "src", "references")
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")

AUDIT_CALC_PY = os.path.join(SRC_SCRIPTS, "audit_calc.py")


class TestM4DatatableLedger(unittest.TestCase):

    def setUp(self):
        self.assertTrue(os.path.exists(AUDIT_CALC_PY), f"Missing audit_calc.py at {AUDIT_CALC_PY}")
        self.assertTrue(os.path.exists(FIXTURES_DIR), f"Missing fixtures dir at {FIXTURES_DIR}")

    def test_p4_protocol_assertions_and_forbidden_terms(self):
        """
        [P4 协议规范检验]
        1. 必须使用断言句式（必须/禁止/仅当...方可）。
        2. 严禁使用模糊词汇（尽量/应当/注意）。
        3. 必须包含项目宪法五原则常量字符串（逐字一致）。
        4. 包含核心事实调研原则（一手证据优先、引用不得升格、单写者、数据三要素、口径分栏等）。
        """
        protocol_path = os.path.join(SRC_REFERENCES, "P4_fact_finding_datatable.md")
        self.assertTrue(os.path.exists(protocol_path), f"Protocol missing: {protocol_path}")

        with open(protocol_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 断言句式检查
        self.assertIn("必须", content)
        self.assertIn("禁止", content)
        self.assertIn("仅当", content)

        # 禁用词扫描
        forbidden = ["尽量", "应当", "注意"]
        for word in forbidden:
            self.assertNotIn(word, content, f"Forbidden word '{word}' found in P4 protocol")

        # 宪法五原则常量字符串逐字检验
        constitution_rules = [
            "事实判锤唯二通路",
            "定性裁决权归人类",
            "无隐藏状态",
            "非同族对抗复核且审者只读",
            "严禁跨口径相减",
        ]
        for rule in constitution_rules:
            self.assertIn(rule, content, f"Missing constitutional rule in P4: {rule}")

        # 核心采信与底表规则检验
        self.assertIn("一手证据优先", content)
        self.assertIn("引用不得升格", content)
        self.assertIn("单写者", content)
        self.assertIn("数据三要素", content)
        self.assertIn("expected_expression", content)
        self.assertIn("tolerance", content)
        self.assertIn("assumption_tag", content)
        self.assertIn("禁止求平均", content)
        self.assertIn("禁止主观裁决", content)

    def test_datatable_template_schema_and_columns(self):
        """
        [底表模板规范检验]
        1. 必须包含全部 10 项标准化表头列名。
        2. 包含口径分栏定义（A, B, C, COMMON）。
        3. 包含红线警示（严禁跨口径相减、禁止求平均或主观裁决）。
        4. 变量占位符统一采用 Mustache {{VARIABLE_NAME}}。
        """
        template_path = os.path.join(SRC_TEMPLATES, "datatable.template.md")
        self.assertTrue(os.path.exists(template_path), f"Missing template: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 表头 10 列
        expected_cols = [
            "item_id", "label", "value", "unit", "source_type",
            "source_ref", "expected_expression", "tolerance", "caliber", "assumption_tag"
        ]
        for col in expected_cols:
            self.assertIn(col, content, f"Missing column {col} in datatable template")

        # 口径定义
        self.assertIn("口径 A", content)
        self.assertIn("口径 B", content)
        self.assertIn("口径 C", content)
        self.assertIn("COMMON", content)

        # 核心红线警示
        self.assertIn("严禁跨口径相减", content)
        self.assertIn("同一指标多来源口径冲突时并列呈现、严禁求平均或主观裁决", content)

        # Mustache 占位符
        self.assertRegex(content, r"\{\{[A-Za-z0-9_]+\}\}")

    def test_evidence_index_template_schema_and_fields(self):
        """
        [证据索引模板规范检验]
        1. 必须包含必填字段：evidence_id, source_identity, pricing_date, access_date,
           snapshot_path, content_sha256, evidence_type, directly_admissible, admissibility_rationale.
        2. 包含单写者与一手证据优先声明。
        3. 包含引用不得升格铁律。
        4. 占位符统一采用 Mustache {{VARIABLE_NAME}}。
        """
        template_path = os.path.join(SRC_TEMPLATES, "evidence_index.template.md")
        self.assertTrue(os.path.exists(template_path), f"Missing template: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        expected_fields = [
            "evidence_id", "source_identity", "pricing_date", "access_date",
            "snapshot_path", "content_sha256", "evidence_type", "directly_admissible",
            "admissibility_rationale"
        ]
        for field in expected_fields:
            self.assertIn(field, content, f"Missing field {field} in evidence_index template")

        self.assertIn("单写者", content)
        self.assertIn("一手证据优先", content)
        self.assertIn("引用不得升格", content)
        self.assertRegex(content, r"\{\{[A-Za-z0-9_]+\}\}")

    def test_criterion_m4_1_valid_formula_calculation_within_tolerance(self):
        """
        [CRITERION M4-1 & Scenario: Formula calculation within declared tolerance passes]
        运行 python3 scripts/audit_calc.py datatable.csv:
        - 进程退出码为 0
        - stdout JSON 为 {"checked_cells": N, "mismatches": []}，其中 mismatches 为空
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "valid_datatable.csv")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0, got {proc.returncode}. Stderr: {proc.stderr}")
        data = json.loads(proc.stdout.strip())
        self.assertIn("checked_cells", data)
        self.assertGreater(data["checked_cells"], 0)
        self.assertEqual(data["mismatches"], [])

    def test_criterion_m4_2_evidence_index_mapping_and_assumptions(self):
        """
        [CRITERION M4-2 & Schema Check: Estimated cells have assumption_tag and valid evidence]
        运行 python3 scripts/audit_calc.py datatable.csv --evidence-index evidence-index.md:
        - 底表中每一个数值单元格必须映射到 evidence-index.md 中的有效条目
        - 凡 source_type=estimated 者其 assumption_tag 必须非空
        - 进程退出码为 0
        - stdout JSON 为 {"unlinked_cells": [], "missing_assumption_tags": []}
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "valid_datatable.csv")
        evidence_index_md = os.path.join(FIXTURES_DIR, "valid_evidence_index.md")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv, "--evidence-index", evidence_index_md],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0, got {proc.returncode}. Stderr: {proc.stderr}")
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data["unlinked_cells"], [])
        self.assertEqual(data["missing_assumption_tags"], [])

    def test_criterion_m4_3_scope_isolation_and_cross_scope_ban(self):
        """
        [CRITERION M4-3: Scope isolation check]
        运行 python3 scripts/audit_calc.py datatable.csv --strict-tolerance:
        - 进程退出码为 0
        - stdout JSON 为 {"checked_cells": N, "cross_scope_violations": []}
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "valid_datatable.csv")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv, "--strict-tolerance"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Expected 0, got {proc.returncode}. Stderr: {proc.stderr}")
        data = json.loads(proc.stdout.strip())
        self.assertIn("checked_cells", data)
        self.assertEqual(data["cross_scope_violations"], [])

    def test_scenario_calculation_mismatch_fails_and_reports_coordinates(self):
        """
        [Scenario: Calculation mismatch triggers failure and coordinate output]
        输入算术矛盾底表（毛利率分母混用与倒挂）：
        - 进程退出码为 1
        - stdout JSON 报告 row 与 col 冲突单元格坐标，包含 item_id、期望值、实际值与差值
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "arithmetic_contradiction_datatable.csv")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 1, f"Expected exit code 1 on mismatch, got {proc.returncode}")
        data = json.loads(proc.stdout.strip())
        self.assertGreater(len(data.get("mismatches", [])), 0)
        mismatch = data["mismatches"][0]
        self.assertEqual(mismatch["item_id"], "ITM_MARGIN_CONFLICT")
        self.assertEqual(mismatch["col"], "value")
        self.assertIn("row", mismatch)
        self.assertIn("expected", mismatch)
        self.assertIn("actual", mismatch)
        self.assertIn("diff", mismatch)

    def test_scenario_cross_caliber_arithmetic_blocked(self):
        """
        [Scenario: Direct arithmetic across incompatible scopes is blocked]
        输入自建口径与采购口径直接相减的底表：
        - 运行 audit_calc.py 返回退出码 1
        - stdout JSON 标记 cross_caliber / scope isolation violation 错误及单元格坐标
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "cross_caliber_datatable.csv")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv, "--strict-tolerance"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 1, f"Expected exit code 1 on cross-caliber, got {proc.returncode}")
        data = json.loads(proc.stdout.strip())
        self.assertGreater(len(data.get("cross_scope_violations", [])), 0)
        violation = data["cross_scope_violations"][0]
        self.assertEqual(violation["error"], "cross_caliber")
        self.assertEqual(violation["item_id"], "ITM_CROSS_DIFF")
        self.assertIn("Scope isolation violation", violation["message"])

    def test_scenario_estimated_cell_without_assumption_tag_rejected(self):
        """
        [Scenario: Estimated cell without assumption tag is rejected]
        输入 source_type=estimated 且 assumption_tag 为空的底表：
        - 运行 audit_calc.py 返回退出码 1
        - stdout JSON 报告 bare_estimate 错误及冲突单元格坐标
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "bare_estimate_datatable.csv")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 1, f"Expected exit code 1 on bare estimate, got {proc.returncode}")
        data = json.loads(proc.stdout.strip())
        self.assertGreater(len(data.get("missing_assumption_tags", [])), 0)
        item = data["missing_assumption_tags"][0]
        self.assertEqual(item["item_id"], "ITM_01")
        self.assertEqual(item["col"], "assumption_tag")
        self.assertEqual(item["error"], "bare_estimate")

    def test_scenario_unlinked_evidence_rejected(self):
        """
        [Scenario: Unlinked evidence reference or missing source_ref is rejected]
        输入包含未在索引登记的虚构 evidence_id 或 source_ref 为空的底表：
        - 运行 audit_calc.py --evidence-index 返回退出码 1
        - stdout JSON 报告 unlinked_cells
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "missing_source_datatable.csv")
        evidence_index_md = os.path.join(FIXTURES_DIR, "valid_evidence_index.md")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv, "--evidence-index", evidence_index_md],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 1, f"Expected exit code 1 on unlinked evidence, got {proc.returncode}")
        data = json.loads(proc.stdout.strip())
        self.assertGreater(len(data.get("unlinked_cells", [])), 0)

    def test_negative_control_bad_calc_datatable(self):
        """
        [阴性对照: §8.1 注入已知缺陷旧料 bad_calc_datatable.csv 必须报错]
        喂入已知倒挂、跨口径与裸数字旧料，断言 audit_calc.py 必须报错（退出码 1）
        """
        datatable_csv = os.path.join(FIXTURES_DIR, "bad_calc_datatable.csv")
        proc = subprocess.run(
            [sys.executable, AUDIT_CALC_PY, datatable_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.assertEqual(proc.returncode, 1, f"Negative control MUST fail with exit code 1, got {proc.returncode}")
        data = json.loads(proc.stdout.strip())
        # 必须检出算术倒挂
        self.assertGreater(len(data.get("mismatches", [])), 0)
        # 必须检出跨口径相减
        self.assertGreater(len(data.get("cross_scope_violations", [])), 0)
        # 必须检出裸数字
        self.assertGreater(len(data.get("missing_assumption_tags", [])), 0)

    def test_ast_safe_evaluator_blocks_code_execution(self):
        """
        [安全审计检验: AST 白名单严格杜绝代码注入与任意函数调用]
        注入含 __import__ 或函数调用的恶意表达式，断言纯 AST 白名单求值直接拦截，严禁执行。
        """
        try:
            from src.scripts.audit_calc import safe_eval_ast
        except ImportError:
            from audit_calc import safe_eval_ast

        dangerous_expressions = [
            "__import__('os').system('ls')",
            "open('/etc/passwd').read()",
            "eval('1 + 2')",
            "(lambda x: x + 1)(2)",
        ]

        for expr in dangerous_expressions:
            try:
                tree = ast.parse(expr, mode="eval")
                with self.assertRaises(ValueError):
                    safe_eval_ast(tree, {})
            except SyntaxError:
                pass


if __name__ == "__main__":
    unittest.main()
