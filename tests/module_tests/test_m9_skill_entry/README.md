# M9 模块 SKILL.md 主入口契约独立黑箱验收指南 (Reviewer Judge Guide)

本目录为技能主入口路由与触发控制层（`src/SKILL.md`）的独立黑箱验收测试套件。
独立验收法官（Independent Reviewer Judge）可在不查看内部实现的前提下，直接通过标准 CLI 命令执行确定性黑箱判定。

---

## 1. 独立法官黑箱执行命令契约与期望输出一览

### 1.1 主入口综合黑箱校验命令 (CRITERION M9-Entry)

- **被测对象**: `src/SKILL.md`
- **执行命令**:
  ```bash
  python3 tests/module_tests/test_m9_skill_entry/entry_validator.py \
    --skill src/SKILL.md \
    --src-root src
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "valid": true,
    "line_count": 120,
    "frontmatter_keys": [
      "description",
      "license",
      "metadata",
      "name",
      "when_to_use"
    ],
    "safe_keys_valid": true,
    "trigger_rule_valid": true,
    "negative_phrasing_valid": true,
    "constitution_constants_valid": true,
    "references_count": 9,
    "references_indexed": [
      "references/P1_grill_me_protocol.md",
      "references/P2_governance_protocol.md",
      "references/P3_decomposition_guidelines.md",
      "references/P4_fact_finding_datatable.md",
      "references/P5_outline_gate.md",
      "references/P6_synthesis_delivery.md",
      "references/review_loop_engine.md",
      "references/change_circuit.md",
      "references/storage_adapters.md"
    ],
    "unbuilt_references": [],
    "scripts_indexed": [
      "scripts/adapter_git_sync.py",
      "scripts/audit_calc.py",
      "scripts/audit_text_hygiene.py",
      "scripts/build_docx.py",
      "scripts/build_pdf.py",
      "scripts/citation_check.py",
      "scripts/delivery_readback.py",
      "scripts/gate_guard.py",
      "scripts/outline_check.py",
      "scripts/storage_guard.py",
      "scripts/task_schema_check.py",
      "scripts/toc_two_pass.py",
      "scripts/verify_readback.py"
    ],
    "unbuilt_scripts": [],
    "forbidden_words_found": [],
    "specific_instances_found": [],
    "platform_names_found": [],
    "gates_valid": true,
    "review_loop_exit_valid": true,
    "enhancement_layers_valid": true,
    "errors": []
  }
  ```

---

### 1.2 阴性对照命令与反向拦截验证 (Negative Controls)

#### 用例 1.2.1: Frontmatter 包含未知/非安全字段 (阻断装载)
- **输入物料**: `tests/module_tests/test_m9_skill_entry/fixtures/bad_frontmatter_disallowed_keys.md`
- **执行命令**:
  ```bash
  python3 tests/module_tests/test_m9_skill_entry/entry_validator.py \
    --skill tests/module_tests/test_m9_skill_entry/fixtures/bad_frontmatter_disallowed_keys.md
  ```
- **期望退出码**: `1`
- **期望 stdout 诊断字段**: `"safe_keys_valid": false`, `"valid": false`

#### 用例 1.2.2: 行数超标 (Line count >= 200 lines)
- **输入物料**: `tests/module_tests/test_m9_skill_entry/fixtures/bad_overlong.md`
- **执行命令**:
  ```bash
  python3 tests/module_tests/test_m9_skill_entry/entry_validator.py \
    --skill tests/module_tests/test_m9_skill_entry/fixtures/bad_overlong.md
  ```
- **期望退出码**: `1`
- **期望 stdout 诊断字段**: `"line_count": 220`, `"valid": false`

#### 用例 1.2.3: 缺失首部触发控制硬规则
- **输入物料**: `tests/module_tests/test_m9_skill_entry/fixtures/bad_first_rule.md`
- **执行命令**:
  ```bash
  python3 tests/module_tests/test_m9_skill_entry/entry_validator.py \
    --skill tests/module_tests/test_m9_skill_entry/fixtures/bad_first_rule.md
  ```
- **期望退出码**: `1`
- **期望 stdout 诊断字段**: `"trigger_rule_valid": false`, `"valid": false`

#### 用例 1.2.4: 包含禁用模糊词 ("应当/尽量/注意")
- **输入物料**: `tests/module_tests/test_m9_skill_entry/fixtures/bad_forbidden_words.md`
- **执行命令**:
  ```bash
  python3 tests/module_tests/test_m9_skill_entry/entry_validator.py \
    --skill tests/module_tests/test_m9_skill_entry/fixtures/bad_forbidden_words.md
  ```
- **期望退出码**: `1`
- **期望 stdout 诊断字段**: `"forbidden_words_found": ["应当", "尽量", "注意"]`, `"valid": false`

#### 用例 1.2.5: 包含具体项目实例词 ("样例法域/词元")
- **输入物料**: `tests/module_tests/test_m9_skill_entry/fixtures/bad_specific_instance.md`
- **执行命令**:
  ```bash
  python3 tests/module_tests/test_m9_skill_entry/entry_validator.py \
    --skill tests/module_tests/test_m9_skill_entry/fixtures/bad_specific_instance.md
  ```
- **期望退出码**: `1`
- **期望 stdout 诊断字段**: `"specific_instances_found": ["样例法域", "词元"]`, `"valid": false`

---

## 2. 一键自动化验证与 Pytest 套件

法官可直接运行目录内配备的 `run_tests.sh` 或使用 `pytest`:

```bash
# 方式 A: 执行一键测试脚本
bash tests/module_tests/test_m9_skill_entry/run_tests.sh

# 方式 B: pytest 标准调用
pytest tests/module_tests/test_m9_skill_entry/test_m9_skill_entry.py -v
```

**期望结果**: 13 项测试全部 PASS，耗时 < 1 秒。
