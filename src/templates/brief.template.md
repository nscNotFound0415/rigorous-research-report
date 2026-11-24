# 项目简报 (Project Brief)

> **权威派生声明**：本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准。

## 1. 元数据 (Metadata)
- project_id: {{PROJECT_ID}}
- version: {{VERSION}}
- created_at: {{CREATED_TIME}}
- brief_content_sha256: {{CONTENT_SHA256}}
- status: {{STATUS}}
- authoritative_declaration: "本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准。"

## 2. 澄清八项与基准清单 (Clarifications & Baselines)

> 八项为**建议澄清清单**：它们的作用是帮助把研究对象与交付形态明确下来，不是 G0 准入条件。
> 每项必须登记 `clarification_status`（CLARIFIED / NOT_CLARIFIED / NOT_APPLICABLE）；未澄清或不适用项必须登记 `unclarified_reason`，并按协议默认行为执行。

### 2.1 报告受众 (Target Readers)
- clarification_status: {{CLARIFICATION_STATUS_2_1}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_1}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- primary_readers: [{{READER_LIST}}]
- reader_preferences: {{READER_PREFERENCES}}

<!-- 默认行为：读者默认「公司内部决策层阅示」，须在 reader_preferences 标注为假设并登记 reason -->

### 2.2 研究标的与对象 (Subject Entity)
- clarification_status: {{CLARIFICATION_STATUS_2_2}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_2}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- subject_name: {{SUBJECT_NAME}}
- scope_boundaries: {{SCOPE_BOUNDARIES}}

<!-- 默认行为：默认由议题文本可确定的范围界定；无法确定则记 NOT_CLARIFIED -->

### 2.3 风格与基调 (Tone & Style)
- clarification_status: {{CLARIFICATION_STATUS_2_3}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_3}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- style_mode: {{STYLE_MODE}}
- perspective: {{PERSPECTIVE}}

<!-- 默认行为：默认「正式研报体：章首判断句、一段一个意思、先结论后依据」 -->

### 2.4 背景与历史上下文 (Background Context)
- clarification_status: {{CLARIFICATION_STATUS_2_4}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_4}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- context_summary: {{CONTEXT_SUMMARY}}
- inherited_materials: [{{INHERITED_FILES}}]

<!-- 默认行为：默认只保留本次会话与工作区中可核实的背景；继承材料一律不得自动充当答案 -->

### 2.5 交付目的地 (Delivery Path)
- clarification_status: {{CLARIFICATION_STATUS_2_5}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_5}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- target_local_dir: {{LOCAL_DIR_PATH}}
- target_delivery_dir: {{DELIVERY_DIR_PATH}}

<!-- 默认行为：可由默认行为填充；默认 `<当前工作区>/research/<议题简称>/`，执行方必须写出绝对路径 -->

### 2.6 交付形态与格式约定 (Format Contract)
- clarification_status: {{CLARIFICATION_STATUS_2_6}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_6}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- primary_format: {{PRIMARY_FORMAT}}
- pagination_limit: {{PAGE_BUDGET}}
- structural_requirements:
  - numbering_system: "中文规范三级编号"
  - reference_style: "文末显式索引与一手出处锚定"

<!-- 默认行为：默认 Markdown ＋ docx ＋ PDF 三件 -->

### 2.7 在线载体基准判定 (Online Baseline Rule)
- clarification_status: {{CLARIFICATION_STATUS_2_7}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_7}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- online_enabled: {{IS_ONLINE_ENABLED}}
- source_of_truth: {{SOURCE_OF_TRUTH}}
- sync_policy: {{SYNC_POLICY}}
- delivery_channel: {{DELIVERY_CHANNEL}}

<!-- 默认行为：可由默认行为填充；无在线文档时默认 LOCAL_AUTHORITATIVE 并登记 reason；存在在线文档时必须人工澄清，禁止默认 -->

### 2.8 人机交互与问询模式 (Interaction Mode)
- clarification_status: {{CLARIFICATION_STATUS_2_8}}  # 枚举: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE
- unclarified_reason: {{UNCLARIFIED_REASON_2_8}}  # 仅当 status != CLARIFIED 时必填，写明未澄清原因
- interaction_mode: {{INTERACTION_MODE}}
- interruption_threshold: "仅 G 级门禁与定性裁决主动中断，其余自主闭环推进"

<!-- 默认行为：默认「逐项确认，一次一问」即 synchronous_frontier -->

### 2.9 诉求与实体索引 (Requirements & Entities Index)
- REQ-01: {{REQ_01_NAME}} | 核心实体: {{ENTITY_1}} | 权衡维度: {{DIMENSION_1}}
- REQ-02: {{REQ_02_NAME}} | 核心实体: {{ENTITY_2}} | 权衡维度: {{DIMENSION_2}}
- REQ-03: {{REQ_03_NAME}} | 核心实体: {{ENTITY_3}} | 权衡维度: {{DIMENSION_3}}

### 2.10 术语与口径 (Glossary & Metric Standards)
- {{TERM_1}}: {{DEFINITION_1}} | 基准口径: {{METRIC_STANDARD_1}}
- {{TERM_2}}: {{DEFINITION_2}} | 基准口径: {{METRIC_STANDARD_2}}

### 2.11 继承声明与人工裁决 (Inherited Claims & Human Adjudication)
<!-- 交接包、历史文件与既有报告中的设定仅作为候选答案；未决条目（无 human_decision）严禁写入 brief 正文 -->
| 条目 ID | 继承说法 (claim) | 来源文件 (source_path) | 来源 SHA256 (source_sha256) | 人工裁决 (human_decision: CONFIRMED / REVISED) |
|---|---|---|---|---|
| IC-01 | {{CLAIM_1}} | {{SOURCE_PATH_1}} | {{SOURCE_SHA256_1}} | {{HUMAN_DECISION_1}} |

## 3. 项目宪法（本文件内嵌章节，唯一权威，禁止外置）
<!-- 5 条宪法字符串为全局系统常量，禁止任意重构或使用改写变体 -->
1. **事实判锤唯二通路**：一手原文比对与代码算术复算，严禁任何模型凭空臆测。
2. **定性裁决权归人类**：对于争议表述之存废与降级，机器严禁自作主张，定性裁决权严格归人类。
3. **无隐藏状态**：材料存在 != 已复核 != 已同步 != 已审定；台账状态必须真实、无未声明的中间态。
4. **非同族对抗复核且审者只读**：复核者必须与生成者实现模型或通道级隔离，审者权限严格设为只读，禁止直接修改受审文本。
5. **严禁跨口径相减**：不同口径、不同币种、不同周期的指标必须设立分栏对比，严禁直接执行加减运算。
