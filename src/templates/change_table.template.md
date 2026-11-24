# [模板规范] 变更管理与指示处置对照表 (Change & Dispatch Ledger)

> **治理铁律 (Governance Axioms)**：
> 1. **母本冻结原则**：未获得人类在 `gates/change-{{CHANGE_ID}}-approval.md` 的有效签署前，严禁直接触碰或修改既有正式母本文件；变更前必须生成只读快照归档并存证母本 `parent_baseline_sha256`。
> 2. **零漂移验收原则**：变更实施后，除显式声明修改的章节与段落外，非声明区域的未声明漂移数（`undeclared_drift`）必须严格为 0。
> 3. **待核事项只标注不改数**：外部新事实未完成交叉验证前，一律仅能标注 `PENDING` 待核，严禁擅自修改正式研报结论与底表数据。
> 4. **定性裁决权归人类**：涉及口径重构、数据删除或降级判定的重大分歧，由人类操作者裁决，严禁 Agent 代裁。

---

## 1. 变更元信息 (Change Meta)
- change_id: "{{CHANGE_ID}}"                          # 变更唯一标识符 (如 change-01)
- change_nature: "{{CHANGE_NATURE}}"                  # 枚举: directive | new_evidence | scope_tweak | architecture_shift
- source_instruction_raw: "{{SOURCE_INSTRUCTION_RAW}}"# 来源指示与外部输入原文
- proposed_by: "{{PROPOSED_BY}}"                      # 变更提出人 (如: 用户 / 评审专家 / 业务主管)
- created_at: "{{CREATED_TIME}}"                      # 变更提出时间 (ISO-8601, 如: 2026-11-23T10:00:00Z)
- priority: "{{PRIORITY}}"                            # 优先级枚举: P0 (紧急阻断) | P1 (重要口径) | P2 (普通微调) | P3 (措辞润色)
- parent_baseline_file: "{{PARENT_BASELINE_FILE}}"    # 变更前母本文件相对路径 (默认: draft_full.md)
- parent_baseline_sha256: "{{PARENT_SHA256}}"        # 变更前母本文件完整 content_sha256 哈希
- approval_signoff: "gates/change-{{CHANGE_ID}}-approval.md" # 必须绑定的门禁审批签署件路径

---

## 2. 变更分级与流程升轨 (Ceremony Triage & Escalation)
- ceremony_level: "{{CEREMONY_LEVEL}}"                # 枚举: LIGHTWEIGHT (默认轻量对照表) | MAJOR (重大变更提案)
- enhanced_openspec_enabled: {{ENHANCED_OPENSPEC}}    # 布尔: true | false (是否显式启用 OpenSpec 可选增强层)
- ceremony_rationale: "{{CEREMONY_RATIONALE}}"        # 分级判定依据说明
- impacted_sections:                                 # 受影响章节范围列表
  - "{{IMPACTED_SECTION_1}}"
  - "{{IMPACTED_SECTION_2}}"
- affected_evidence_ids:                             # 受影响之一手证据/图表 ID 列表
  - "{{AFFECTED_EVIDENCE_ID_1}}"
  - "{{AFFECTED_EVIDENCE_ID_2}}"

---

## 3. 指示与变更逐条处置矩阵 (Directive & Patch Matrix)
> 规则：未获得人类在 `gates/change-{{CHANGE_ID}}-approval.md` 签署批准前，严禁触碰母本。

| 条目 ID | 外部指示/输入原文 | 涉及章节与定位 | 涉及图表/证据 ID | 现状表述/旧口径 | 拟修订表述/新方案 | 修改前后对比与处置方案 | 待核标记与修订依据 | 人审状态 (PENDING / APPROVED / REJECTED) |
|---|---|---|---|---|---|---|---|:---:|
| C-01 | "{{DIRECTIVE_TEXT_1}}" | {{SECTION_LOC_1}} | {{EVIDENCE_FIG_ID_1}} | "{{OLD_TEXT_1}}" | "{{NEW_TEXT_1}}" | {{DIFF_SUMMARY_1}} | {{PENDING_OR_VERIFIED_1}} | [{{APPROVAL_STATUS_1}}] |
| C-02 | "{{DIRECTIVE_TEXT_2}}" | {{SECTION_LOC_2}} | {{EVIDENCE_FIG_ID_2}} | "{{OLD_TEXT_2}}" | "{{NEW_TEXT_2}}" | {{DIFF_SUMMARY_2}} | {{PENDING_OR_VERIFIED_2}} | [{{APPROVAL_STATUS_2}}] |

---

## 4. 执行留痕与四层回读审计 (Execution & Readback Audit)
- execution_timestamp: "{{EXEC_TIME}}"                # 实施修改完成时间戳
- backup_archive_path: "{{BACKUP_PATH}}"              # 变更前母本只读归档目录路径
- target_modified_file: "{{TARGET_FILE}}"            # 变更实施之目标母本文件路径
- new_baseline_content_sha256: "{{NEW_SHA256}}"      # 变更实施后新文件全文 content_sha256
- new_baseline_nettext_sha256: "{{NEW_NETTEXT}}"      # 变更实施后新文件净文本 nettext_sha256
- approval_signoff_path: "{{APPROVAL_PATH}}"          # 核验通过之人类签署放行件路径
- undeclared_drift_count: {{UNDECLARED_DRIFT_COUNT}}  # 未声明漂移数 (整数，必须严格为 0)

### 4.1 四层回读验证结果 (Four-Layer Readback Results)
- layer_1_new_sentence_present: {{LAYER_1_RESULT}}    # 布尔: 新拟表述是否已 100% 准确在位
- layer_2_old_sentence_residuals: {{LAYER_2_RESULT}}  # 整数: 淘汰旧句/旧口径残留数，必须为 0
- layer_3_block_count_valid: {{LAYER_3_RESULT}}       # 布尔: 文档骨架块数与章节结构是否完整合规
- layer_4_undeclared_drift: {{LAYER_4_RESULT}}        # 整数: 非声明区域未声明漂移数，必须为 0
  - diff_summary: "{{DIFF_SUMMARY_TEXT}}"             # 差异简要说明 (如: 仅第 1.2 节声明行存在变更，其余区域逐字节一致)
