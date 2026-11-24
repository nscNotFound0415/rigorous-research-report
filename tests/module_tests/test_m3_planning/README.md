# M3 课题拆分与调研规划 模块测试与法官验收手册

本目录包含 M3 模块（`research-decomposition`）的独立黑箱验收测试套件、测试夹具及执行规范。
供独立验收法官（Independent Reviewer）在沙箱环境中开展黑箱验收。

---

## 一、法官黑箱执行命令原文 (Judge Execution Commands)

验收法官可在工作区根目录（`skill-build/`）复制并直接执行以下命令：

### 1. 自动化全量测试运行命令 (Automated Suite)
```bash
pytest tests/module_tests/test_m3_planning/test_m3_planning.py -v
```
或直接运行一键脚本：
```bash
./tests/module_tests/test_m3_planning/run_tests.sh
```
- **期望结果**：10 项测试全部通过（`10 passed in <1s`），退出码为 `0`。

---

### 2. 黑箱核心判据独立执行指令与期望值

#### 场景 A：正向 Schema 与 DAG 无环性校验（CRITERION M3-1 & M3-2）
```bash
python3 src/scripts/task_schema_check.py tests/module_tests/test_m3_planning/fixtures/valid_task.json --schema src/schemas/task.schema.json
```
- **期望退出码**：`0`
- **期望 stdout JSON**：
  ```json
  {"errors": [], "guidelines_validated": true}
  ```

#### 场景 B：阴性对照 - 包含循环依赖的 task.json 阻断（Scenario: cyclic DAG）
```bash
python3 src/scripts/task_schema_check.py tests/module_tests/test_m3_planning/fixtures/cyclic_dep_task.json --schema src/schemas/task.schema.json
```
- **期望退出码**：`1`
- **期望 stdout JSON**：包含循环依赖节点路径与错误原因
  ```json
  {"errors": ["Circular dependency detected in tasks: T-01 -> T-02 -> T-01"], "cycle": ["T-01", "T-02", "T-01"]}
  ```

#### 场景 C：正向 REQ-ID 100% 覆盖率核验（CRITERION M3-3）
```bash
python3 src/scripts/task_schema_check.py tests/module_tests/test_m3_planning/fixtures/valid_task.json --req-index tests/module_tests/test_m3_planning/fixtures/valid_brief.md --coverage
```
- **期望退出码**：`0`
- **期望 stdout JSON**：
  ```json
  {"uncovered_req_ids": [], "coverage_ratio": 1.0}
  ```

#### 场景 D：阴性对照 - 遗漏诉求索引报错阻断（Scenario: uncovered REQ-ID）
```bash
python3 src/scripts/task_schema_check.py tests/module_tests/test_m3_planning/fixtures/uncovered_req_task.json --req-index tests/module_tests/test_m3_planning/fixtures/valid_brief.md --coverage
```
- **期望退出码**：`1`
- **期望 stdout JSON**：明确列出遗漏的 REQ-ID 列表及未达 100% 的覆盖率
  ```json
  {"uncovered_req_ids": ["REQ-02", "REQ-03"], "coverage_ratio": 0.3333, "errors": ["Uncovered REQ-IDs: REQ-02, REQ-03"]}
  ```

#### 场景 E：正向 Guidelines 数据三要素核查
```bash
python3 src/scripts/task_schema_check.py tests/module_tests/test_m3_planning/fixtures/valid_task.json --guidelines-check
```
- **期望退出码**：`0`
- **期望 stdout JSON**：
  ```json
  {"errors": [], "guidelines_validated": true}
  ```

#### 场景 F：阴性对照 - Guidelines 缺失数据三要素阻断（Scenario: missing guidelines）
```bash
python3 src/scripts/task_schema_check.py tests/module_tests/test_m3_planning/fixtures/missing_guidelines_task.json --guidelines-check
```
- **期望退出码**：`1`
- **期望 stdout JSON**：明确输出违规任务 ID 与缺失的三要素字段
  ```json
  {"errors": ["Task 'T-01' guidelines missing essential assertion(s): source_provenance, pricing_date, metric_unit"], "guidelines_validated": false, "offending_tasks": [{"task_id": "T-01", "missing_essentials": ["source_provenance", "pricing_date", "metric_unit"]}]}
  ```

---

## 二、测试夹具清单与拓扑

```text
tests/module_tests/test_m3_planning/
├── README.md                      # 本验收手册
├── run_tests.sh                   # 一键测试运行入口
├── test_m3_planning.py            # 10 项全量自动化测试套件
└── fixtures/                      # 离线黑箱夹具
    ├── valid_brief.md             # 包含 REQ-01..03 索引的合法简报
    ├── valid_task.json            # 满足全量规范之合规调研任务清单
    ├── uncovered_req_task.json    # (a) 阴性对照：遗漏 REQ-02 与 REQ-03 覆盖
    ├── cyclic_dep_task.json       # (b) 阴性对照：T-01 与 T-02 构成循环依赖
    ├── missing_guidelines_task.json # (c) 阴性对照：guidelines 缺失数据三要素
    └── schema_violation_task.json # (d) 阴性对照：source_type 非法枚举值
```
