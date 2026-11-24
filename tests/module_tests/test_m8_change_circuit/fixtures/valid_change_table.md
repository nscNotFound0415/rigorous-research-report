# [模板规范] 变更管理与指示处置对照表 (Change & Dispatch Ledger)

> **治理铁律 (Governance Axioms)**：
> 1. **母本冻结原则**：未获得人类在 `gates/change-01-approval.md` 的有效签署前，严禁直接触碰或修改既有正式母本文件；变更前必须生成只读快照归档并存证母本 `parent_baseline_sha256`。
> 2. **零漂移验收原则**：变更实施后，除显式声明修改的章节与段落外，非声明区域的未声明漂移数（`undeclared_drift`）必须严格为 0。
> 3. **待核事项只标注不改数**：外部新事实未完成交叉验证前，一律仅能标注 `PENDING` 待核，严禁擅自修改正式研报结论与底表数据。
> 4. **定性裁决权归人类**：涉及口径重构、数据删除或降级判定的重大分歧，由人类操作者裁决，严禁 Agent 代裁。

---

## 1. 变更元信息 (Change Meta)
- change_id: "change-01"
- change_nature: "scope_tweak"
- source_instruction_raw: "针对样例法域算力出海调研报告，请将样例法域出海模式二的市场需求评级由中高调整为高"
- proposed_by: "业务负责人 (Director Liu)"
- created_at: "2026-11-23T10:00:00Z"
- priority: "P2"
- parent_baseline_file: "draft_full.md"
- parent_baseline_sha256: "4e3473b89620f9845e8becdf3851d23e5b480c98f65e864774cea468d8761e2a"
- approval_signoff: "gates/change-01-approval.md"

---

## 2. 变更分级与流程升轨 (Ceremony Triage & Escalation)
- ceremony_level: "LIGHTWEIGHT"
- enhanced_openspec_enabled: false
- ceremony_rationale: "评级与措辞微调，影响局部段落，按 LIGHTWEIGHT 微调对照表轻流程处置"
- impacted_sections:
  - "第1.2节"
  - "表4-2"
- affected_evidence_ids:
  - "S-05"
  - "E-01"

---

## 3. 指示与变更逐条处置矩阵 (Directive & Patch Matrix)
> 规则：未获得人类在 `gates/change-01-approval.md` 签署批准前，严禁触碰母本。

| 条目 ID | 外部指示/输入原文 | 涉及章节与定位 | 涉及图表/证据 ID | 现状表述/旧口径 | 拟修订表述/新方案 | 修改前后对比与处置方案 | 待核标记与修订依据 | 人审状态 (PENDING / APPROVED / REJECTED) |
|---|---|---|---|---|---|---|---|:---:|
| C-01 | 将样例法域出海模式二的市场需求评级由中高调整为高 | 第 1.2 节 业务模式评级与定位 | 表 4-2, 证据 S-05 | 样例法域出海模式二的市场需求评级为中高，具备稳健的商业化落地基础与现金流保障。 | 样例法域出海模式二的市场需求评级为高，具备稳健的商业化落地基础与现金流保障。 | 评级微调，替换为高并同步证据链 | VERIFIED | [APPROVED] |

---

## 4. 执行留痕与四层回读审计 (Execution & Readback Audit)
- execution_timestamp: "{{EXEC_TIME}}"
- backup_archive_path: "{{BACKUP_PATH}}"
- target_modified_file: "draft_full.md"
- new_baseline_content_sha256: "{{NEW_SHA256}}"
- new_baseline_nettext_sha256: "{{NEW_NETTEXT}}"
- approval_signoff_path: "gates/change-01-approval.md"
- undeclared_drift_count: {{UNDECLARED_DRIFT_COUNT}}

### 4.1 四层回读验证结果 (Four-Layer Readback Results)
- layer_1_new_sentence_present: {{LAYER_1_RESULT}}
- layer_2_old_sentence_residuals: {{LAYER_2_RESULT}}
- layer_3_block_count_valid: {{LAYER_3_RESULT}}
- layer_4_undeclared_drift: {{LAYER_4_RESULT}}
  - diff_summary: "{{DIFF_SUMMARY_TEXT}}"
