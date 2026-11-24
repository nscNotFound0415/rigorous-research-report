# M4 并行事实调研与底表重构 模块测试与法官验收指南

本目录包含 M4 模块（`fact-verification`）的独立黑箱验收测试套件与测试夹具。

---

## 一、法官执行命令原文 (Judge Execution Commands)

独立验收法官可直接在工作区根目录（`skill-build/`）复制并执行以下命令进行黑箱验收：

### 1. 自动化全量测试运行命令
```bash
pytest tests/module_tests/test_m4_datatable/test_m4_datatable.py -v
```
**期望结果**：12 项测试全部通过（`12 passed in <1s`），退出码为 0。

---

### 2. 黑箱场景独立验证命令 (CLI Blackbox Contracts)

#### 场景 1：底表公式在 declared tolerance 内纯代码复算通过（CRITERION M4-1）
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/valid_datatable.csv
```
- **期望退出码**：`0`
- **期望 stdout**：
  ```json
  {"checked_cells":4,"mismatches":[]}
  ```

#### 场景 2：底表单元格映射到 evidence-index 且 estimated 带 tag（CRITERION M4-2）
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/valid_datatable.csv --evidence-index tests/module_tests/test_m4_datatable/fixtures/valid_evidence_index.md
```
- **期望退出码**：`0`
- **期望 stdout**：
  ```json
  {"unlinked_cells":[],"missing_assumption_tags":[]}
  ```

#### 场景 3：严格口径隔离核验与容差判定通过（CRITERION M4-3）
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/valid_datatable.csv --strict-tolerance
```
- **期望退出码**：`0`
- **期望 stdout**：
  ```json
  {"checked_cells":4,"cross_scope_violations":[]}
  ```

#### 场景 4：算术矛盾（毛利率分母混用与倒挂）精准报错并输出冲突单元格坐标
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/arithmetic_contradiction_datatable.csv
```
- **期望退出码**：`1`
- **期望 stdout**：
  ```json
  {"checked_cells":2,"mismatches":[{"row":5,"col":"value","item_id":"ITM_MARGIN_CONFLICT","expected":33.83084577,"actual":-47.0,"diff":80.83084577,"tolerance":0.01,"expression":"(ITM_A01 - ITM_A02) / ITM_A01 * 100"}],"cross_scope_violations":[],"missing_assumption_tags":[],"unlinked_cells":[],"errors":["Row 5 (ITM_MARGIN_CONFLICT): calculation mismatch! Expected 33.83084577114427, actual -47.0, diff 80.83084577114427 > tol 0.01"]}
  ```

#### 场景 5：自建与采购口径直接相减被阻断并报错 cross_caliber
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/cross_caliber_datatable.csv --strict-tolerance
```
- **期望退出码**：`1`
- **期望 stdout**：
  ```json
  {"checked_cells":1,"cross_scope_violations":[{"row":4,"col":"expected_expression","item_id":"ITM_CROSS_DIFF","error":"cross_caliber","calibers":["A","B"],"expression":"ITM_A01 - ITM_B01","message":"Scope isolation violation: cross-caliber arithmetic detected across calibers ['A', 'B'] in item ITM_CROSS_DIFF"}],"mismatches":[],"missing_assumption_tags":[],"unlinked_cells":[],"errors":["Row 4 (ITM_CROSS_DIFF): cross-caliber arithmetic between ['A', 'B']"]}
  ```

#### 场景 6：裸数字（estimated 缺失 assumption_tag）被拒绝拦截
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/bare_estimate_datatable.csv
```
- **期望退出码**：`1`
- **期望 stdout**：
  ```json
  {"checked_cells":0,"mismatches":[],"cross_scope_violations":[],"missing_assumption_tags":[{"row":2,"col":"assumption_tag","item_id":"ITM_01","error":"bare_estimate","message":"Item 'ITM_01' has source_type=estimated but assumption_tag is empty"}],"unlinked_cells":[],"errors":["Row 2 (ITM_01): bare estimate without assumption_tag"]}
  ```

#### 场景 7：虚构引用或悬空 source_ref 被拒绝拦截
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/missing_source_datatable.csv --evidence-index tests/module_tests/test_m4_datatable/fixtures/valid_evidence_index.md
```
- **期望退出码**：`1`
- **期望 stdout**：包含 `unlinked_cells` 中坐标行号与未锚定引用 ID，退出码 1。

#### 场景 8：阴性对照（喂入已知倒挂旧料 bad_calc_datatable.csv 必须报错）
```bash
python3 src/scripts/audit_calc.py tests/module_tests/test_m4_datatable/fixtures/bad_calc_datatable.csv
```
- **期望退出码**：`1`
- **期望 stdout**：同时检出算术倒挂、跨口径运算与裸数字缺陷，退出码 1。

---

## 二、测试夹具清单与设计意图

| 夹具文件路径 | 设计意图与覆盖边界 | 期望判定结果 |
|---|---|---|
| `fixtures/valid_datatable.csv` | 标准合法底表，覆盖 A/B/C/COMMON 口径、纯算术公式、容差声明、证据索引引用 | audit_calc 校验全部通过，退出码 0 |
| `fixtures/valid_evidence_index.md` | 标准合法一手证据索引表，包含一手文件、公开挂牌等完整元数据 | 映射检验通过，退出码 0 |
| `fixtures/arithmetic_contradiction_datatable.csv` | 模拟毛利率分母倒挂与混用（预期 33.83% 误写为 -47%） | 检出计算倒挂并输出单元格坐标，退出码 1 |
| `fixtures/cross_caliber_datatable.csv` | 模拟自建私有 IDC (口径A) 与租赁 (口径B) 直接相减 | 检出 cross_caliber 违规并阻断，退出码 1 |
| `fixtures/bare_estimate_datatable.csv` | 模拟 source_type=estimated 但 assumption_tag 为空 | 检出 bare_estimate 违规并输出坐标，退出码 1 |
| `fixtures/missing_source_datatable.csv` | 模拟 source_ref 为空或指向虚构不存在的 evidence_id | 检出 unlinked_cells 并阻断，退出码 1 |
| `fixtures/bad_calc_datatable.csv` | 阴性对照旧料，集中注入倒挂、跨口径与裸数字三类缺陷 | 必须全部拦截，退出码 1 |
