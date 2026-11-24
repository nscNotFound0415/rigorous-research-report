#!/usr/bin/env python3
"""
test_m3_planning.py - M3 课题拆分与调研规划 模块黑箱与阴性对照全量测试套件

运行方式:
    pytest tests/module_tests/test_m3_planning/test_m3_planning.py -v
    python3 -m unittest tests/module_tests/test_m3_planning/test_m3_planning.py
"""

import json
import os
import subprocess
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
SCRIPT_PATH = os.path.join(ROOT_DIR, "src/scripts/task_schema_check.py")
SCHEMA_PATH = os.path.join(ROOT_DIR, "src/schemas/task.schema.json")
FIXTURES_DIR = os.path.join(ROOT_DIR, "tests/module_tests/test_m3_planning/fixtures")


class TestM3Planning(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(SCRIPT_PATH), f"Script missing: {SCRIPT_PATH}")
        self.assertTrue(os.path.exists(SCHEMA_PATH), f"Schema missing: {SCHEMA_PATH}")
        self.assertTrue(os.path.exists(FIXTURES_DIR), f"Fixtures missing: {FIXTURES_DIR}")

    def run_cli(self, args):
        cmd = [sys.executable, SCRIPT_PATH] + args
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=ROOT_DIR
        )
        try:
            parsed_json = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
        except Exception:
            parsed_json = {}
        return proc.returncode, parsed_json, proc.stdout, proc.stderr

    # =========================================================================
    # 场景 1: 正向合法 task.json 与无环 DAG 校验 (CRITERION M3-1 & M3-2)
    # =========================================================================
    def test_m3_1_valid_task_schema_and_dag(self):
        task_file = os.path.join(FIXTURES_DIR, "valid_task.json")
        code, out, stdout, stderr = self.run_cli([task_file, "--schema", SCHEMA_PATH])

        self.assertEqual(code, 0, f"Expected exit code 0, got {code}. Stderr: {stderr}, Stdout: {stdout}")
        self.assertIn("errors", out)
        self.assertEqual(out["errors"], [])
        self.assertTrue(out.get("guidelines_validated"), "Expected guidelines_validated to be True")

    # =========================================================================
    # 场景 2: 正向 REQ-ID 100% 覆盖率校验 (CRITERION M3-3)
    # =========================================================================
    def test_m3_2_req_coverage_100_percent(self):
        task_file = os.path.join(FIXTURES_DIR, "valid_task.json")
        brief_file = os.path.join(FIXTURES_DIR, "valid_brief.md")
        code, out, stdout, stderr = self.run_cli([task_file, "--req-index", brief_file, "--coverage"])

        self.assertEqual(code, 0, f"Expected exit code 0, got {code}. Stderr: {stderr}, Stdout: {stdout}")
        self.assertEqual(out.get("uncovered_req_ids"), [])
        self.assertEqual(out.get("coverage_ratio"), 1.0)

    # =========================================================================
    # 场景 3: 阴性对照 (a) - 缺失 2 个 REQ-ID 覆盖 (uncovered_req_task.json)
    # =========================================================================
    def test_m3_3_negative_uncovered_req_ids(self):
        task_file = os.path.join(FIXTURES_DIR, "uncovered_req_task.json")
        brief_file = os.path.join(FIXTURES_DIR, "valid_brief.md")
        code, out, stdout, stderr = self.run_cli([task_file, "--req-index", brief_file, "--coverage"])

        self.assertEqual(code, 1, f"Expected exit code 1, got {code}")
        self.assertIn("uncovered_req_ids", out)
        self.assertIn("REQ-02", out["uncovered_req_ids"])
        self.assertIn("REQ-03", out["uncovered_req_ids"])
        self.assertLess(out.get("coverage_ratio", 1.0), 1.0)
        self.assertGreater(len(out.get("errors", [])), 0)

    # =========================================================================
    # 场景 4: 阴性对照 (b) - 包含环状循环依赖 (cyclic_dep_task.json)
    # =========================================================================
    def test_m3_4_negative_cyclic_dependency_dag(self):
        task_file = os.path.join(FIXTURES_DIR, "cyclic_dep_task.json")
        code, out, stdout, stderr = self.run_cli([task_file, "--schema", SCHEMA_PATH])

        self.assertEqual(code, 1, f"Expected exit code 1, got {code}")
        self.assertIn("errors", out)
        has_cycle_error = any("Circular dependency detected" in err for err in out["errors"])
        self.assertTrue(has_cycle_error, f"Expected cycle error in: {out['errors']}")
        self.assertIn("cycle", out)
        self.assertIn("T-01", out["cycle"])
        self.assertIn("T-02", out["cycle"])

    # =========================================================================
    # 场景 5: 阴性对照 (c) - guidelines 缺失数据三要素 (--guidelines-check)
    # =========================================================================
    def test_m3_5_negative_guidelines_missing_essentials(self):
        task_file = os.path.join(FIXTURES_DIR, "missing_guidelines_task.json")
        code, out, stdout, stderr = self.run_cli([task_file, "--guidelines-check"])

        self.assertEqual(code, 1, f"Expected exit code 1, got {code}")
        self.assertGreater(len(out.get("errors", [])), 0)
        self.assertIn("offending_tasks", out)
        offending_ids = [item["task_id"] for item in out["offending_tasks"]]
        self.assertIn("T-01", offending_ids)

    # =========================================================================
    # 场景 6: 阴性对照 (c2) - guidelines 缺三要素通过 --schema 亦被阻断
    # =========================================================================
    def test_m3_6_negative_guidelines_via_schema_check(self):
        task_file = os.path.join(FIXTURES_DIR, "missing_guidelines_task.json")
        code, out, stdout, stderr = self.run_cli([task_file, "--schema", SCHEMA_PATH])

        self.assertEqual(code, 1, f"Expected exit code 1, got {code}")
        self.assertGreater(len(out.get("errors", [])), 0)
        has_guidelines_err = any("guidelines missing" in err for err in out["errors"])
        self.assertTrue(has_guidelines_err, f"Expected guidelines error in: {out['errors']}")

    # =========================================================================
    # 场景 7: 阴性对照 (d) - 违反 JSON Schema 规则 (schema_violation_task.json)
    # =========================================================================
    def test_m3_7_negative_schema_violation(self):
        task_file = os.path.join(FIXTURES_DIR, "schema_violation_task.json")
        code, out, stdout, stderr = self.run_cli([task_file, "--schema", SCHEMA_PATH])

        self.assertEqual(code, 1, f"Expected exit code 1, got {code}")
        self.assertGreater(len(out.get("errors", [])), 0)
        has_schema_err = any("source_type" in err for err in out["errors"])
        self.assertTrue(has_schema_err, f"Expected source_type error in: {out['errors']}")

    # =========================================================================
    # 场景 8: 检查 task_json.template.json 模板与 Schema 兼容性
    # =========================================================================
    def test_m3_8_template_json_validity(self):
        template_file = os.path.join(ROOT_DIR, "src/templates/task_json.template.json")
        self.assertTrue(os.path.exists(template_file))
        with open(template_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("tasks", data)
        self.assertIn("_examples", data)
        self.assertGreaterEqual(len(data["_examples"]), 2, "Expected 2-3 example tasks")

    # =========================================================================
    # 场景 9: 检查 research_breakdown.template.md 必备章节
    # =========================================================================
    def test_m3_9_research_breakdown_template_sections(self):
        template_file = os.path.join(ROOT_DIR, "src/templates/research_breakdown.template.md")
        self.assertTrue(os.path.exists(template_file))
        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("视角枚举", content)
        self.assertIn("调研任务树", content)
        self.assertIn("诉求与实体映射矩阵", content)
        self.assertIn("Guidelines 注入", content)
        self.assertIn("target_req_ids", content)

    # =========================================================================
    # 场景 10: 检查 P3_decomposition_guidelines.md 包含严谨性断言
    # =========================================================================
    def test_m3_10_guidelines_reference_doc(self):
        ref_file = os.path.join(ROOT_DIR, "src/references/P3_decomposition_guidelines.md")
        self.assertTrue(os.path.exists(ref_file))
        with open(ref_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("严禁将待核事项作为既定事实写入任务", content)
        self.assertIn("禁止凭空捏造数字", content)
        self.assertIn("STORM", content)
        self.assertIn("数据三要素", content)
        self.assertIn("100% 覆盖", content)


if __name__ == "__main__":
    unittest.main()
