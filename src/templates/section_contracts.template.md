# {{REPORT_TITLE}} 章节撰写契约手册 (Section Writing Contracts)

> **章节撰写契约规范说明 (Section Contracts Specification)**：
> 1. 本契约由 M5 章节规划模块编制，作为向 M7 合稿引擎下发的硬性写作指令集。
> 2. 合稿引擎（M7）在起草各章节正文时，必须逐条遵守对应章节的约束契约，严禁越界发挥或违反口径隔离。
> 3. 对抗复核引擎（M6）在合稿全文复核（边界 3）时，将本契约作为独立审查的判据基准。

---

## 0. 全局通用撰写底线约束 (Global Writing Constraints)

- **唯一母源与事实源**: 所有数据、断言必须锚定到 `brief.md` 与 `datatable.csv` / `evidence-index.md`，严禁虚构或引用未登记一手信源。
- **宪法常量条款遵从**:
  1. 事实判锤唯二通路：必须且仅能来自一手采集快照或纯代码算术复算。
  2. 定性裁决权归人类：争议事实与倾向性定性严禁 Agent 独断，必须上浮由人类拍板。
  3. 无隐藏状态：所有假设、推算逻辑、口径差异必须明文声明并注记。
  4. 非同族对抗复核且审者只读：合稿过程审写隔离，合稿全文必须经由异族模型进行 D0-D3 独立复核。
  5. 严禁跨口径相减：不同统计口径（A自建 / B采购 / C市场）数值严禁直接进行算术加减比较。
- **禁用词表通用规则**:
  - 全局遵守 `src/templates/forbidden_terms.json` 规则，严禁出现“本报告旨在”、“如前文所述”、“经过深入分析表明”等 AI 痕迹与自述词。
  - 允许且保护项目既有的 9 类严谨性声明（如口径免责声明、法务免责声明）。

---

## 第一章 撰写契约：{{CHAPTER_1_TITLE}}

### 1. 必须回答的核心命题 (Mandatory Propositions)
- 命题 1: {{CHAPTER_1_MANDATORY_PROPOSITION_1}}
- 命题 2: {{CHAPTER_1_MANDATORY_PROPOSITION_2}}
- 命题 3: {{CHAPTER_1_MANDATORY_PROPOSITION_3}}

### 2. 必须使用的底表口径与字段 (Datatable Scopes & Fields)
- **指定底表范围**: `{{CHAPTER_1_DATATABLE_PATH}}`
- **使用口径**: {{CHAPTER_1_DATA_SCOPE}} (例如: A自建口径 / B采购口径 / C第三方市场口径)
- **口径隔离红线**: {{CHAPTER_1_SCOPE_ISOLATION_RULE}} (例如: 严禁将自建 IDC 机柜成本与公有云托管月租直接相减)
- **关键核算字段**:
  - {{CHAPTER_1_KEY_METRIC_1}} (单位: {{METRIC_1_UNIT}}, source_type: {{METRIC_1_SOURCE_TYPE}})
  - {{CHAPTER_1_KEY_METRIC_2}} (单位: {{METRIC_2_UNIT}}, source_type: {{METRIC_2_SOURCE_TYPE}})

### 3. 禁用词与表达负面清单 (Forbidden Terms & Expressions)
- **引用规则库**: `templates/forbidden_terms.json`
- **章节特异性禁用表达**:
  - 严禁使用: {{CHAPTER_1_FORBIDDEN_EXPRESSION_1}}
  - 严禁使用: {{CHAPTER_1_FORBIDDEN_EXPRESSION_2}}
- **保护性表达**: 必须保留并在注记中明示“{{CHAPTER_1_PROTECTED_DISCLAIMER}}”。

### 4. 边界限定与禁言红线 (Boundary Constraints & Prohibitions)
- **论证边界**: {{CHAPTER_1_BOUNDARY_SCOPE}}
- **严禁越界断言**:
  - 严禁在缺乏目标市场官方细则证据的情况下，断言“{{CHAPTER_1_PROHIBITED_ASSERTION_1}}”。
  - 严禁跨越至后文专属的“{{CHAPTER_1_PROHIBITED_ASSERTION_2}}”议题。

### 5. 证据要求与引用规范 (Evidence Requirements)
- **最小证据数**: 本章正文必须引用不少于 {{CHAPTER_1_MIN_EVIDENCE_COUNT}} 条已核验的 `evidence_ref`。
- **引用闭环**: 每一条关键数据点与核心定性判断句末尾必须标注形如 `[evidence_ref: EVD-XXX]` 的回指标识。
- **待补数据清零**: 合稿阶段严禁残留任何 `PENDING` 引用，所有证据 ID 必须在 `evidence-index.md` 真实存在。

### 6. 长度与风格基线 (Length & Style Baseline)
- **篇幅预算**: 建议 {{CHAPTER_1_WORD_COUNT_MIN}} - {{CHAPTER_1_WORD_COUNT_MAX}} 字。
- **章首判断句要求**: 章首第一段必须以强有力的事实陈述或研判判断句开篇，直接呈现该章核心发现。
- **章末结论要求**: 章末必须设置独立的「核心结论与业务启示」小结，提炼 2-3 条精炼行动指南。

### 7. 交付到 M7 的写作指令 (Synthesis Instructions for M7)
- 指令 1: {{CHAPTER_1_M7_INSTRUCTION_1}}
- 指令 2: {{CHAPTER_1_M7_INSTRUCTION_2}}
- 指令 3: {{CHAPTER_1_M7_INSTRUCTION_3}}

---

## 第二章 撰写契约：{{CHAPTER_2_TITLE}}

### 1. 必须回答的核心命题 (Mandatory Propositions)
- 命题 1: {{CHAPTER_2_MANDATORY_PROPOSITION_1}}
- 命题 2: {{CHAPTER_2_MANDATORY_PROPOSITION_2}}

### 2. 必须使用的底表口径与字段 (Datatable Scopes & Fields)
- **指定底表范围**: `{{CHAPTER_2_DATATABLE_PATH}}`
- **使用口径**: {{CHAPTER_2_DATA_SCOPE}}
- **口径隔离红线**: 必须使用显式对比分栏列示，严禁混同。
- **关键核算字段**:
  - {{CHAPTER_2_KEY_METRIC_1}}
  - {{CHAPTER_2_KEY_METRIC_2}}

### 3. 禁用词与表达负面清单 (Forbidden Terms & Expressions)
- 遵守全局禁词库，章节禁用词: {{CHAPTER_2_FORBIDDEN_EXPRESSIONS}}。

### 4. 边界限定与禁言红线 (Boundary Constraints & Prohibitions)
- 严禁越界断言: {{CHAPTER_2_PROHIBITED_ASSERTIONS}}。

### 5. 证据要求与引用规范 (Evidence Requirements)
- 每条核心结论必须带 `evidence_ref`，本章引用不少于 {{CHAPTER_2_MIN_EVIDENCE_COUNT}} 条。

### 6. 长度与风格基线 (Length & Style Baseline)
- 篇幅预算: {{CHAPTER_2_WORD_COUNT_MIN}} - {{CHAPTER_2_WORD_COUNT_MAX}} 字。
- 风格: 结构化量化论证，图文紧密呼应。

### 7. 交付到 M7 的写作指令 (Synthesis Instructions for M7)
- 指令 1: {{CHAPTER_2_M7_INSTRUCTION_1}}
- 指令 2: {{CHAPTER_2_M7_INSTRUCTION_2}}
