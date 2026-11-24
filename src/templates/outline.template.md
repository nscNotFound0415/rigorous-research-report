# {{REPORT_TITLE}} 章节架构规划大纲 (Outline)

> **大纲架构设计与使用说明 (Outline Design & Usage Guidelines)**：
> 1. 本大纲为整个长篇研究报告的骨架母本，严格由 M5 模块独占写入，供 M7 统一单次合稿时唯一依凭。
> 2. 章节规划必须保证对 `brief.md` 中声明的全部 `REQ-ID` 达到 100% 覆盖。
> 3. 严格遵循三级标题层级（章 H2 → 节 H3 → 子项 H4），**严禁标题层级跳级**。
> 4. 每章必须具备明确的「论证目的」行与至少 1 条 `evidence_ref` 数据引用。
> 5. **并行期引用规则**：若数据已入库，必须使用确定的 `evidence_ref`（如 `EVD-001`）；若 M4 事实调研仍在并行推进尚未完成入库，允许标记为 `PENDING`（如 `PENDING-01`），但**必须在文末「待补数据（PENDING）」小节集中登记**。
> 6. **Join 2 汇合门禁**：在 G1 门禁签署前，文内所有 `PENDING` 引用必须清零并闭环映射到 `evidence-index.md`，否则门禁脚本无条件阻断流转。

---

## 0. 大纲元信息与诉求覆盖索引 (Meta & REQ Coverage)

- **报告课题 (Topic)**: {{RESEARCH_TOPIC}}
- **目标读者 (Audience)**: {{TARGET_AUDIENCE}}
- **基调与风格 (Tone & Style)**: {{REPORT_TONE_AND_STYLE}}
- **事实底表关联 (Datatable Ref)**: {{DATATABLE_PATH}}
- **诉求索引覆盖 (REQ-ID Coverage)**:
  - {{REQ_ID_1}}: {{REQ_ID_1_DESCRIPTION}} (覆盖于: 第 1 章、第 2 章)
  - {{REQ_ID_2}}: {{REQ_ID_2_DESCRIPTION}} (覆盖于: 第 3 章)
  - {{REQ_ID_3}}: {{REQ_ID_3_DESCRIPTION}} (覆盖于: 第 4 章)

---

## 第一章：{{CHAPTER_1_TITLE}}

- **论证目的**: {{CHAPTER_1_ARGUMENTATION_OBJECTIVE}}
- **章首判断句**: {{CHAPTER_1_OPENING_THESIS_STATEMENT}}
- **本章核心结论**: {{CHAPTER_1_CLOSING_CONCLUSION}}

### 1.1 {{SECTION_1_1_TITLE}}
- **节摘要**: {{SECTION_1_1_SUMMARY}}
- **论证目的**: {{SECTION_1_1_ARGUMENTATION_OBJECTIVE}}
- **核心论据与数据引用**:
  - 核心论点 1: {{POINT_1_1_1_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_1_1_1}}
  - 核心论点 2: {{POINT_1_1_2_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_1_1_2}}
- **图表规划**:
  - 图 1-1: {{CHART_1_1_TITLE}} (数据源: {{CHART_1_1_SOURCE}}, 口径: {{CHART_1_1_SCOPE}})

#### 1.1.1 {{SUBSECTION_1_1_1_TITLE}}
- **要点陈述**: {{SUBSECTION_1_1_1_CONTENT}}
- **数据支撑**: {{SUBSECTION_1_1_1_DATA_POINT}}
  - evidence_ref: {{EVIDENCE_REF_1_1_1_A}}

### 1.2 {{SECTION_1_2_TITLE}}
- **节摘要**: {{SECTION_1_2_SUMMARY}}
- **论证目的**: {{SECTION_1_2_ARGUMENTATION_OBJECTIVE}}
- **核心论据与数据引用**:
  - 关键论据: {{POINT_1_2_1_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_1_2_1}}
- **图表规划**:
  - 表 1-1: {{TABLE_1_2_TITLE}} (口径范围: {{TABLE_1_2_SCOPE}})

---

## 第二章：{{CHAPTER_2_TITLE}}

- **论证目的**: {{CHAPTER_2_ARGUMENTATION_OBJECTIVE}}
- **章首判断句**: {{CHAPTER_2_OPENING_THESIS_STATEMENT}}
- **本章核心结论**: {{CHAPTER_2_CLOSING_CONCLUSION}}

### 2.1 {{SECTION_2_1_TITLE}}
- **节摘要**: {{SECTION_2_1_SUMMARY}}
- **论证目的**: {{SECTION_2_1_ARGUMENTATION_OBJECTIVE}}
- **核心论据与数据引用**:
  - 论据 1 (已入库事实): {{POINT_2_1_1_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_2_1_1}}
  - 论据 2 (调研中待补事实): {{POINT_2_1_2_STATEMENT}}
    - evidence_ref: {{PENDING_REF_2_1_2}}
- **图表规划**:
  - 图 2-1: {{CHART_2_1_TITLE}} (形式: 对比柱状图)

### 2.2 {{SECTION_2_2_TITLE}}
- **节摘要**: {{SECTION_2_2_SUMMARY}}
- **论证目的**: {{SECTION_2_2_ARGUMENTATION_OBJECTIVE}}
- **核心论据与数据引用**:
  - 论据 1: {{POINT_2_2_1_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_2_2_1}}
- **图表规划**:
  - 表 2-1: {{TABLE_2_2_TITLE}} (口径: A自建 / B采购分栏隔离)

---

## 第三章：{{CHAPTER_3_TITLE}}

- **论证目的**: {{CHAPTER_3_ARGUMENTATION_OBJECTIVE}}
- **章首判断句**: {{CHAPTER_3_OPENING_THESIS_STATEMENT}}
- **本章核心结论**: {{CHAPTER_3_CLOSING_CONCLUSION}}

### 3.1 {{SECTION_3_1_TITLE}}
- **节摘要**: {{SECTION_3_1_SUMMARY}}
- **论证目的**: {{SECTION_3_1_ARGUMENTATION_OBJECTIVE}}
- **核心论据与数据引用**:
  - 论据: {{POINT_3_1_1_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_3_1_1}}
- **图表规划**:
  - 图 3-1: {{CHART_3_1_TITLE}}

### 3.2 {{SECTION_3_2_TITLE}}
- **节摘要**: {{SECTION_3_2_SUMMARY}}
- **论证目的**: {{SECTION_3_2_ARGUMENTATION_OBJECTIVE}}
- **核心论据与数据引用**:
  - 论据: {{POINT_3_2_1_STATEMENT}}
    - evidence_ref: {{EVIDENCE_REF_3_2_1}}

---

## 待补数据（PENDING）

> **待补数据登记规则 (Pending Data Registry Rules)**：
> 1. 本小节为并行期大纲引用的唯一待补数据登记处，凡在大纲正文中出现标记为 `PENDING` 的 `evidence_ref`，必须在此逐项登记。
> 2. 严禁隐式挂起；未在本节登记的 PENDING 引用将被 `outline_check.py` 视为严重未声明违规并阻断流程。
> 3. 汇合门禁判据：在 Join 2 汇合与 G1 门禁签署前，本节所有待补项必须由 M4 调研完成入库，由 M5 逐一回填正式 `EVD-*` 编号，待补项数量必须归零。

- [ ] {{PENDING_REF_ID_1}}: {{PENDING_ITEM_1_DESCRIPTION}} (关联章节: {{ASSOCIATED_SECTION_1}}, 责任模块: M4, 预定补齐节点: Join 2 前)
- [ ] {{PENDING_REF_ID_2}}: {{PENDING_ITEM_2_DESCRIPTION}} (关联章节: {{ASSOCIATED_SECTION_2}}, 责任模块: M4, 预定补齐节点: Join 2 前)
