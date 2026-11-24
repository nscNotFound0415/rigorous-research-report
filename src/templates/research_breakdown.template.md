# 课题视角枚举与多维拆解架构 (Research Decomposition & Breakdown)

> **权威映射与归属声明**：
> 1. 本文档为人类可读之课题多维拆分架构说明书，重点呈现基于多视角（Persona/Perspective）的拆分推导逻辑。
> 2. `target_req_ids` 诉求覆盖与机器判定之唯一权威位置为 `task.json`；本文档中呈现的映射矩阵仅作为展示与交叉引用，不作为机器判定的权威事实源。
> 3. 严禁把待核事项作为既定事实写入任务单元，所有预设指标必须通过 M4 独立调研与一手证据采信予以核验。

---

## 1. 拆解元信息 (Decomposition Metadata)
- project_id: {{PROJECT_ID}}
- baseline_brief_sha256: {{BRIEF_CONTENT_SHA256}}
- created_at: {{CREATED_TIME}}
- author_role: "M3_planner_agent"
- task_json_ref: "task.json"

---

## 2. 视角枚举与角色设定 (Persona & Perspective Enumeration)

> **注记**：依据 STORM 多视角展开范式，在拆解调研任务前，必须系统性枚举针对本课题具有深度切入能力的专家角色视角，防止单一技术或单一商业视角带来的认知盲区。

### 2.1 视角清单与核心审视边界
| 视角 ID | 专家角色名称 (Persona) | 核心关切问题与研判边界 | 覆盖盲区与对抗焦点 |
|---|---|---|---|
| P-01 | {{PERSPECTIVE_1_NAME}} | {{PERSPECTIVE_1_CORE_FOCUS}} | {{PERSPECTIVE_1_BLIND_SPOT}} |
| P-02 | {{PERSPECTIVE_2_NAME}} | {{PERSPECTIVE_2_CORE_FOCUS}} | {{PERSPECTIVE_2_BLIND_SPOT}} |
| P-03 | {{PERSPECTIVE_3_NAME}} | {{PERSPECTIVE_3_CORE_FOCUS}} | {{PERSPECTIVE_3_BLIND_SPOT}} |

### 2.2 视角交叉互验逻辑
- **技术 vs 成本**：{{TECH_VS_COST_RATIONALE}}
- **商业收益 vs 合规阻力**：{{BIZ_VS_REGULATORY_RATIONALE}}

---

## 3. 调研任务树与拓扑依赖 (Research Task Tree & DAG)

> **注记**：所有任务单元必须构成严格的有向无环图（DAG），严禁任何环状闭环依赖。依赖关系直接决定 M4 并行调度拓扑。

```text
{{TASK_TREE_ASCII_OR_MERMAID}}
```

### 3.1 任务执行批次规划
- **首批无依赖并行项 (Roots)**: [{{ROOT_TASK_IDS}}]
- **次批汇聚依赖项 (Intermediate)**: [{{INTERMEDIATE_TASK_IDS}}]
- **终批全景测算项 (Leaves)**: [{{LEAF_TASK_IDS}}]

---

## 4. 诉求与实体映射矩阵 (REQ-ID Cross-reference Matrix)

> **注记**：本矩阵直观呈现 `brief.md` §2.9 中全部 `REQ-ID` 在各任务单元中的承接分布。机器校验通过 `python3 scripts/task_schema_check.py task.json --req-index brief.md --coverage` 执行 100% 覆盖闭环判定。

| 诉求编号 (REQ-ID) | 简报诉求名称与核心实体 | 承接任务 ID (`task_id`) | 承接视角 (`perspective`) | 交付物期望路径 |
|---|---|---|---|---|
| REQ-01 | {{REQ_01_NAME}} | {{TASK_1_ID}} | {{PERSPECTIVE_1_NAME}} | `fact-store/{{TASK_1_ID}}_evidence.json` |
| REQ-02 | {{REQ_02_NAME}} | {{TASK_2_ID}} | {{PERSPECTIVE_2_NAME}} | `fact-store/{{TASK_2_ID}}_evidence.json` |
| REQ-03 | {{REQ_03_NAME}} | {{TASK_3_ID}} | {{PERSPECTIVE_3_NAME}} | `fact-store/{{TASK_3_ID}}_evidence.json` |

---

## 5. 任务单元详单与 Guidelines 注入 (Task Specification & Injected Guidelines)

> **注记**：每个任务单元必须注入数据三要素（来源出处、取价日/基准时间、统计口径与单位）硬约束断言。

### 5.1 任务单元 1: {{TASK_1_ID}} - {{TASK_1_SUB_TOPIC}}
- **负责视角**: {{TASK_1_PERSPECTIVE}}
- **承接诉求**: [{{TASK_1_REQ_ID}}]
- **前置依赖**: []
- **产出文件**: `{{TASK_1_OUTPUT_PATH}}`
- **注入 Guidelines (数据三要素断言)**:
  1. **来源出处**: 必须采信 {{TASK_1_SOURCE_PROVENANCE}}，严禁引用二手未经核实之转述。
  2. **基准时间**: 取价日与时间窗口必须限定于 {{TASK_1_BENCHMARK_DATE}}。
  3. **统计口径**: 统计口径与单位必须严格统一为 {{TASK_1_METRIC_UNIT}}。
- **数据需求与来源分类 (Data Requirements)**:
  - 核心指标: {{TASK_1_METRIC_NAME}} | 类型: `{{TASK_1_SOURCE_TYPE}}` | 假设 Tag: `{{TASK_1_ASSUMPTION_TAG}}`

### 5.2 任务单元 2: {{TASK_2_ID}} - {{TASK_2_SUB_TOPIC}}
- **负责视角**: {{TASK_2_PERSPECTIVE}}
- **承接诉求**: [{{TASK_2_REQ_ID}}]
- **前置依赖**: [{{TASK_1_ID}}]
- **产出文件**: `{{TASK_2_OUTPUT_PATH}}`
- **注入 Guidelines (数据三要素断言)**:
  1. **来源出处**: 必须采信 {{TASK_2_SOURCE_PROVENANCE}}，严禁使用未披露非公开传闻。
  2. **基准时间**: 取价日与时间窗口必须限定于 {{TASK_2_BENCHMARK_DATE}}。
  3. **统计口径**: 统计口径与单位必须严格统一为 {{TASK_2_METRIC_UNIT}}。
- **数据需求与来源分类 (Data Requirements)**:
  - 核心指标: {{TASK_2_METRIC_NAME}} | 类型: `{{TASK_2_SOURCE_TYPE}}` | 假设 Tag: `{{TASK_2_ASSUMPTION_TAG}}`
