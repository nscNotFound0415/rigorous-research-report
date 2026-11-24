# 独立对抗复核报告 (Adversarial Review Report)

> **复核引擎约束与治理红线 (Review Axioms)**：
> 1. 本报告由独立只读审查实例产出，审者严禁直接改动受审工件。
> 2. 缺陷严格执行四档分流（D0 已证实错误、D1 证据不足、D2 材料冲突、D3 待核 T 项）。
> 3. 事实判锤只走三条确定性通路：纯代码算术复算 (ARITH)、一手原文比对 (QUOTE_MISMATCH) 与确定性词法扫描器 (LEXICAL_RULE)；证据不足≠事实错误。
> 4. 出口红线：D0 缺陷数必须强制清零（D0 == 0），且完成四层回读复验并获人类门禁批准后，方可跨入下游阶段。

---

## 1. 复核元信息与隔离声明 (Review Meta & Isolation Declaration)

- boundary: {{BOUNDARY}}                         # 枚举: datatable | outline | draft_full
- reviewed_artifact: "{{REVIEWED_ARTIFACT_PATH}}" # 被审工件相对路径
- artifact_content_sha256: {{ARTIFACT_SHA256}}   # 被审工件全文 SHA-256
- review_timestamp: {{REVIEW_TIMESTAMP}}          # ISO 8601 标准时间戳
- provenance_file: "{{PROVENANCE_FILE_PATH}}"     # 机器可读复核证明路径，例: review-reports/{{BOUNDARY}}_provenance.json
- reviewer_channel: {{REVIEWER_CHANNEL}}          # 枚举: 异族 | 同族-零记忆隔离
- read_only_verified: true                        # 审者沙箱只读状态核验
- isolation_statement: "复核者运行于严格隔离只读沙箱，与撰写者会话分离（session 互斥），无历史思考缓存继承；调用证明详见 {{PROVENANCE_FILE_PATH}}。"

---

## 2. 复核覆盖度与盲区声明 (Coverage Declaration)

> 规则：审者必须明示阅读深度，杜绝假装全量阅读。

### 2.1 全文深读物料清单 (Deep-read Materials)
- 逐行比对与全文精读文件：
  - `{{DEEP_READ_ITEM_1}}`
  - `{{DEEP_READ_ITEM_2}}`

### 2.2 定向扫描物料清单 (Targeted Scan Materials)
- 依据特定关键词、公式列、引用 ID 进行定向核查的文件：
  - `{{TARGETED_SCAN_ITEM_1}}`
  - `{{TARGETED_SCAN_ITEM_2}}`

### 2.3 未读/盲区声明 (Unread Materials & Blind Spots)
- 本次复核未覆盖或因环境受限未能接入的外部信源与工件：
  - `{{UNREAD_ITEM_1}}`
  - `{{UNREAD_ITEM_2}}`

---

## 3. 缺陷统计与出口门禁判定 (Defect Statistics & Gate Status)

| 缺陷级别 | 级别定义与处置原则 | 检出数量 | 阻断状态 (BLOCKED / PASS) |
|:---:|---|:---:|:---:|
| **D0** | **已证实错误**（仅限 ARITH 算术复算错误 / QUOTE_MISMATCH 原文不一致 / LEXICAL_RULE 确定性词法扫描）：**必须清零** | {{D0_COUNT}} | {{D0_STATUS}} |
| **D1** | **证据不足**（方向性逻辑相反、未声明的主观臆测、缺乏一手信源等）：列出两个选项（补证 ｜ 降级为推测/待证实）供 G2 人类裁决，禁止自动降级改写 | {{D1_COUNT}} | PASS (需裁决) |
| **D2** | **材料冲突**（多个权威信源对同一指标冲突）：设立分栏对比，禁止主观取舍 | {{D2_COUNT}} | PASS (需分栏) |
| **D3** | **待核 T 项**（调研范围外未闭环事项、企业未披露项）：只标注不改数，挂牌留存 | {{D3_COUNT}} | PASS (留存) |
| **总计** | 全部分类缺陷汇总 | {{TOTAL_COUNT}} | {{OVERALL_STATUS}} |

**出口门禁初步判定 (Exit Assessment)**:
- D0 缺陷清零判定: {{D0_ZERO_ASSERTION}} (必须为 true 方可放行)
- 降级阶梯级别: {{DEGRADATION_LEVEL}} (Level 1: 异族 / Level 2: 同族零记忆 / Level 3: 规则扫描补充态)
- 门禁状态: {{GATE_STATE}} (例: PENDING_CORRECTION | BLOCKED_NO_REVIEWER | READY_FOR_G2)

---

## 4. 缺陷明细清单 (Defect Details)

### 4.1 D0: 已证实错误 (Confirmed Errors - 必须清零，仅限 ARITH / QUOTE_MISMATCH / LEXICAL_RULE)

#### [D0-{{DEFECT_INDEX_01}}] {{DEFECT_TITLE_01}}
- **定位 (Location)**: {{DEFECT_LOCATION_01}}
- **原文 (Original Text)**:
  > {{DEFECT_ORIGINAL_TEXT_01}}
- **问题类型 (Problem Type)**: {{DEFECT_SUBTYPE_01}} # 严格仅限三条确定性通路之一
- **route**: {{D0_ROUTE_01}} # 枚举: ARITH (附复算命令与输出行) | QUOTE_MISMATCH (附原文 chunk ID 与不一致片段; chunk ID 不存在时标 NOT_FOUND) | LEXICAL_RULE (附机器扫描器命令与输出行，用于元叙述/悬空引用/图表断号等确定性扫描)
- **证据来源 (Evidence Source)**: {{DEFECT_EVIDENCE_SOURCE_01}}
- **影响范围 (Impact Scope)**: {{DEFECT_IMPACT_SCOPE_01}}
- **建议处置 (Recommended Disposition)**: {{DEFECT_DISPOSITION_01}} # 倾向性建议: 修正计算 / 剔除错误结论
- **仍待核事项 (Pending Items)**: {{DEFECT_PENDING_ITEMS_01}}

---

### 4.2 D1: 证据不足 (Insufficient Evidence - 列出选项供 G2 人类裁决，禁止自动改写)

#### [D1-{{DEFECT_INDEX_02}}] {{DEFECT_TITLE_02}}
- **定位 (Location)**: {{DEFECT_LOCATION_02}}
- **原文 (Original Text)**:
  > {{DEFECT_ORIGINAL_TEXT_02}}
- **问题类型 (Problem Type)**: {{DEFECT_SUBTYPE_02}} # 枚举: 缺乏一手信源 | 二手转述未考证 | 方向性逻辑相反 | 未声明的主观臆测 | 缺失取价日 | 缺失统计单位
- **证据来源 (Evidence Source)**: {{DEFECT_EVIDENCE_SOURCE_02}}
- **影响范围 (Impact Scope)**: {{DEFECT_IMPACT_SCOPE_02}}
- **处置选项与推荐 (Disposition Options & Recommendation)**:
  - 选项 A (补证): 限期补充一手原始文献/网页快照并完成交叉核验
  - 选项 B (降级为推测/待证实): 降级为推测/待证实，并在正文显式加注 `[假设: 待一手证实]` 标识
  - 推荐项 (Recommendation): {{D1_RECOMMENDED_OPTION_02}} # 标注倾向性推荐选项，由 G2 门禁人类裁决；机器严禁自动降级或自动改写
- **建议处置 (Recommended Disposition)**: "列出两个选项（补证｜降级为推测/待证实）并标注推荐项，由 G2 人类裁决。机器严禁自动降级或自动改写。"
- **仍待核事项 (Pending Items)**: {{DEFECT_PENDING_ITEMS_02}}

---

### 4.3 D2: 材料冲突 (Conflicting Sources - 设立分栏对比)

#### [D2-{{DEFECT_INDEX_03}}] {{DEFECT_TITLE_03}}
- **定位 (Location)**: {{DEFECT_LOCATION_03}}
- **原文 (Original Text)**:
  > {{DEFECT_ORIGINAL_TEXT_03}}
- **问题类型 (Problem Type)**: {{DEFECT_SUBTYPE_03}} # 枚举: 多权威信源口径冲突 | 统计维度差异 | 汇率/财年折算冲突
- **证据来源 (Evidence Source)**: {{DEFECT_EVIDENCE_SOURCE_03}}
- **影响范围 (Impact Scope)**: {{DEFECT_IMPACT_SCOPE_03}}
- **建议处置 (Recommended Disposition)**: {{DEFECT_DISPOSITION_03}} # 倾向性建议: 保留双重口径并在正文设立对比表格
- **仍待核事项 (Pending Items)**: {{DEFECT_PENDING_ITEMS_03}}

---

### 4.4 D3: 待核 T 项 (Unverified Pending Items - 挂牌留存)

#### [D3-{{DEFECT_INDEX_04}}] {{DEFECT_TITLE_04}}
- **定位 (Location)**: {{DEFECT_LOCATION_04}}
- **原文 (Original Text)**:
  > {{DEFECT_ORIGINAL_TEXT_04}}
- **问题类型 (Problem Type)**: {{DEFECT_SUBTYPE_04}} # 枚举: 超出当前调研边界 | 涉及未披露商业机密 | 外部监管细则未出台
- **证据来源 (Evidence Source)**: {{DEFECT_EVIDENCE_SOURCE_04}}
- **影响范围 (Impact Scope)**: {{DEFECT_IMPACT_SCOPE_04}}
- **建议处置 (Recommended Disposition)**: {{DEFECT_DISPOSITION_04}} # 建议: 只标注不改数，列入待核追踪清单并在正文打 PENDING 标签
- **仍待核事项 (Pending Items)**: {{DEFECT_PENDING_ITEMS_04}}

---

## 5. 后续流转指引 (Downstream Action Items)

1. 若检出 D0 缺陷：立即阻断流水线向下游流转，调度撰写节点编制《纠错对照稿》（`correction-diff.md`）。
2. 将定性裁决权交由人类操作者在 G2 门禁（`gates/G2-approval.md`）行使。
3. 纠错写入后，必须运行 `python3 scripts/verify_readback.py --plan correction-diff.md --target <target_file>` 执行四层回读复验。
