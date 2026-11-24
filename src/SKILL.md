---
name: rigorous-research-report
description: 严谨复杂调研报告写作流水线。用于商业分析、产业研判、合规审计、技术选型等事实核验成本高的长篇调研报告。典型触发场景包括：调研报告、可行性报告、行业研判、尽调报告，以及对既有报告做事实复核与修订。默认不触发，必须由用户显式调用。
when_to_use: 默认不触发。仅在用户显式调用 /rigorous-research-report 或当轮明确要求按本流水线执行时使用；普通问答、数据查询、单文件润色一律不使用。
license: MIT
metadata:
  version: "2.1.0"
  framework: "openspec-v1.14"
  mode: "rigorous-pipeline"
  source_of_truth: "brief.md"
  default_storage: "local-git"
---

# 严谨复杂调研报告写作系统 (rigorous-research-report)

## 1. 触发控制硬规则

本技能的启动前提是用户显式调用 /rigorous-research-report 或当轮明确要求按本流水线执行；若无该显式调用，立即输出「本技能需显式调用 /rigorous-research-report 启动」并停止，不得发起任何澄清提问、不得创建任何文件。

## 2. 项目核心宪法

本项目执行全流程必须遵守五项底线常量，禁止任何形式改写：
1. **事实判锤唯二通路**：一手原文比对与代码算术复算，禁止任何模型凭空臆测。
2. **定性裁决权归人类**：对于争议表述之存废与降级，机器禁止自作主张，定性裁决权归人类。
3. **无隐藏状态**：材料存在 != 已复核 != 已同步 != 已审定；台账状态必须真实、无未声明的中间态。
4. **非同族对抗复核且审者只读**：复核者必须与生成者实现模型或通道级隔离，审者权限严格设为只读，禁止直接修改受审文本。
5. **严禁跨口径相减**：不同口径、不同币种、不同周期的指标必须设立分栏对比，禁止直接执行加减运算。

治理台账与存储纪律约束：
- **勾选权公理**：状态列 `[x]` 仅人类有权写入，Agent 禁止自评打勾，仅可更新独立的 `agent_建议` 列。
- **唯一事实源**：`brief.md` 为唯一权威事实源，后续大纲、调研与撰写均由此派生；口径冲突时以其为准。
- **存储受控**：工作区受控目录必须以本地 Git 为主载体；未经 `manifest.json` 登记的文件写入必须强制拦截。

## 3. 状态机路由与人审门禁

流水线按六阶段与动态维护回路 (6 + 1 结构) 执行，设四道不可省略的人审门禁与变更门禁：

```text
P1 落地澄清 ──[G0 门禁]──> P2 治理适配 ──> P3 课题拆分
                                               │
                        ┌──────────────────────┴──────────────────────┐
                        ▼                                             ▼
             P4 并行调研与底表重构                         P5 章节规划与大纲审批
                        │                                             │
                        └─────────────► Join 2 ◄──────────────────────┘
                                     [G1 门禁]
                                         │
                                         ▼
                               P6 统一合稿与交付层
                          [G2 纠错裁决] ──> [G3 终审交付]
                                         ▲
                                         │ (贯穿全程，事件驱动)
                                   M 变更管理回路
                                  [change 门禁]
```

门禁卡点与签署件路径契约（未获签署或校验失败时由 `scripts/gate_guard.py` 返回退出码 1 阻断）：
- **G0 澄清放行门 (Join 1)**：卡在 P1 唯一事实源 `brief.md` 生成后、P2/P3 启动前。申请件：`gates/G0-request.md`；签署件：`gates/G0-approval.md`。11 个小节齐全是硬结构；八项澄清（2.1–2.8）为建议澄清清单，不是准入条件，每项必须登记 `clarification_status`（CLARIFIED / NOT_CLARIFIED / NOT_APPLICABLE），未澄清或不适用项按协议默认行为执行并登记 `unclarified_reason`；未获 G0 批准禁止在工作区生成后续阶段文件。
- **G1 大纲审批门 (Join 2)**：卡在 P5 章节规划完成、Join 2 汇合前。申请件：`gates/G1-request.md`；签署件：`gates/G1-approval.md`。必须待补数据 PENDING 归零且 100% 锚定一手事实；未获 G1 批准禁止启动正文合稿。
- **G2 纠错裁决门**：卡在 P6 全文合稿与边界 3 复核后。申请件：`gates/G2-request.md`；签署件：`gates/G2-approval.md`。定性争议存废与口径分栏降级必须由人类签署裁决。
- **G3 交付终审门 (Join 3)**：卡在 P6 交付物构建与交付回读验证通过后。申请件：`gates/G3-request.md`；签署件：`gates/G3-approval.md`。未获 G3 人类有效签署授权，禁止向外正式交付。
- **变更审批门 (change-<id>)**：卡在外部指示引发母本修改前。申请件：`change-table.md`；签署件：`gates/change-<change_id>-approval.md`。未获签署前母本严格只读冻结，禁止直接覆盖母本。

## 4. 阶段手册与脚本 CLI 索引

每个阶段必须查阅对应的 `references/` 相对路径手册，并严格调用对应的脚本 CLI 契约：

| 阶段 | 必读 references/ 相对路径 | 环节 / 任务 | 必用脚本 CLI 契约 | 模块状态 |
|---|---|---|---|---|
| P1 落地澄清 | `references/P1_grill_me_protocol.md` | 简报规范核验（8 项澄清状态＋11 小节结构） | `python3 scripts/gate_guard.py --verify-brief brief.md` | 已建 |
| P1 落地澄清 | `references/P1_grill_me_protocol.md` | G0 门禁状态探测 | `python3 scripts/gate_guard.py --gate G0 --check-only` | 已建 |
| P1 落地澄清 | `references/P1_grill_me_protocol.md` | G0 门禁放行校验 | `python3 scripts/gate_guard.py --gate G0 --verify --artifact brief.md --approval gates/G0-approval.md` | 已建 |
| P2 治理适配 | `references/P2_governance_protocol.md` | 治理台账合规核验 | `python3 scripts/storage_guard.py --check-ledger` | 已建 |
| P2 治理适配 | `references/storage_adapters.md` | 未登记写入拦截探测 | `python3 scripts/storage_guard.py --root <dir> --manifest manifest.json --probe-unregistered-write` | 已建 |
| P2 治理适配 | `references/storage_adapters.md` | 本地 Git 快照与同步 | `python3 scripts/adapter_git_sync.py --snapshot --target <dir>` | 已建 |
| P3 课题拆分 | `references/P3_decomposition_guidelines.md` | 任务 Schema 与无环校验 | `python3 scripts/task_schema_check.py task.json --schema schemas/task.schema.json` | 已建 |
| P3 课题拆分 | `references/P3_decomposition_guidelines.md` | 诉求 REQ-ID 覆盖率校验 | `python3 scripts/task_schema_check.py task.json --req-index brief.md --coverage` | 已建 |
| P3 课题拆分 | `references/P3_decomposition_guidelines.md` | 课题拆分准则合规校验 | `python3 scripts/task_schema_check.py task.json --guidelines-check` | 已建 |
| P4 事实底表 | `references/P4_fact_finding_datatable.md` | 底表公式纯代码复算 | `python3 scripts/audit_calc.py datatable.csv` | 已建 |
| P4 事实底表 | `references/P4_fact_finding_datatable.md` | 证据索引映射与假设 tag | `python3 scripts/audit_calc.py datatable.csv --evidence-index evidence-index.md` | 已建 |
| P4 事实底表 | `references/P4_fact_finding_datatable.md` | 跨口径隔离与严格容差 | `python3 scripts/audit_calc.py datatable.csv --strict-tolerance` | 已建 |
| P5 章节大纲 | `references/P5_outline_gate.md` | 大纲证据引用与待补登记 | `python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md` | 已建 |
| P5 章节大纲 | `references/P5_outline_gate.md` | 章节结构与论证目的校验 | `python3 scripts/outline_check.py outline.md --check-sections` | 已建 |
| P5 章节大纲 | `references/P5_outline_gate.md` | Join 2 证据全量锚定校验 | `python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md --require-resolved` | 已建 |
| P5 章节大纲 | `references/P5_outline_gate.md` | G1 门禁状态探测 | `python3 scripts/gate_guard.py --gate G1 --check-only` | 已建 |
| P5 章节大纲 | `references/P5_outline_gate.md` | G1 门禁放行校验 | `python3 scripts/gate_guard.py --gate G1 --verify --artifact outline.md --approval gates/G1-approval.md` | 已建 |
| 跨阶段复核 | `references/review_loop_engine.md` | 独立复核证明 provenance 校验 | `python3 scripts/gate_guard.py --check-provenance review-reports/<boundary>_provenance.json` | 已建 |
| 跨阶段复核 | `references/review_loop_engine.md` | 局部替换四层回读复验 | `python3 scripts/verify_readback.py --plan correction-diff.md --target draft_full.md` | 已建 |
| 跨阶段复核 | `references/review_loop_engine.md` | G2 门禁定性裁决放行 | `python3 scripts/gate_guard.py --gate G2 --verify --artifact correction-diff.md --approval gates/G2-approval.md` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | 文本卫生扫描 (带白名单保护) | `python3 scripts/audit_text_hygiene.py draft_full.md --rules templates/forbidden_terms.json` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | 章节跨度去重判据核验 | `python3 scripts/audit_text_hygiene.py draft_full.md --check-dedup` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | 全文图表编号与文献引用核查 | `python3 scripts/citation_check.py draft_full.md --evidence-index evidence-index.md` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | Markdown 直写 OOXML 生成 Word | `python3 scripts/build_docx.py draft_full.md --out delivery/output.docx --manifest build_manifest.json` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | 无损转交付 PDF | `python3 scripts/build_pdf.py delivery/output.docx --out delivery/output.pdf` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | TOC 目录两遍法页码回填 | `python3 scripts/toc_two_pass.py delivery/output.docx delivery/output.pdf` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | 交付物目录标题双向回读校验 | `python3 scripts/delivery_readback.py --docx delivery/output.docx --pdf delivery/output.pdf --source draft_full.md --out delivery_readback.json` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | G3 终审门禁状态探测 | `python3 scripts/gate_guard.py --gate G3 --check-only` | 已建 |
| P6 合稿交付 | `references/P6_synthesis_delivery.md` | G3 终审放行校验 | `python3 scripts/gate_guard.py --gate G3 --verify --artifact delivery/output.docx --approval gates/G3-approval.md` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 外部指示三通道分流 | `python3 scripts/change_dispatch.py --root <workspace> --classify --instruction-file <file>` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 变更门禁状态探测 | `python3 scripts/gate_guard.py --gate change-<id> --check-only` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 变更审批签署校验 | `python3 scripts/gate_guard.py --gate change-<id> --verify --artifact change-table.md --approval gates/change-<id>-approval.md` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 变更实施与零漂移回读 | `python3 scripts/change_dispatch.py --root <workspace> --apply --change-table change-table.md` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 变更执行审计与备份核验 | `python3 scripts/change_dispatch.py --root <workspace> --audit --change-table change-table.md` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 变更后零漂移比对 | `python3 scripts/verify_readback.py --diff-mode --old backup/… --new … --declared C-01` | 已建 |
| M 变更回路 | `references/change_circuit.md` | 变更前母本快照备份核验 | `python3 scripts/verify_readback.py --verify-backup backup/ --change-table change-table.md` | 已建 |

## 5. 三边界对抗复核循环与出口条件

在数据底表（边界 1）、章节大纲（边界 2）、合稿全文（边界 3）三个产物边界统一执行异族只读对抗复核：
- **四档分流标准**：
  - **D0 已证实错误**：算术倒挂、篡改出处、方向相反。处置：必须强制清零，阻断下游流转。
  - **D1 证据不足**：缺乏一手出处或缺少取价日。处置：限期补证；未补证者降级为推测并明示。
  - **D2 材料冲突**：多源口径不一。处置：禁止主观取舍折中，必须设立分栏对比列示。
  - **D3 待核 T 项**：企业未披露信息。处置：统一登记清单，正文保留占位，只标注不改数。
- **四层回读复验**：局部精准更新后，运行 `scripts/verify_readback.py` 必须满足第 1 层新句在位、第 2 层 D0 旧句零残留、第 3 层结构块保真、第 4 层双哈希比对一致。
- **独立复核证明 (Provenance)**：每次复核必须产出机器可读记录 `review-reports/<boundary>_provenance.json`，审者与撰写者必须实现模型或通道隔离（`writer.session ≠ reviewer.session`）。
- **三级降级阶梯**：第 1 级（最优态）跨厂商异族模型通道；第 2 级（同模型零记忆隔离复核）清空上下文并开启独立子进程；第 3 级（确定性规则代码兜底）纯 Python 规则扫描。第 3 级仅为补充，严禁以此替代 D0=0 放行出口。
- **放行出口条件**：仅当 **D0 缺陷数 == 0** 且 **四层回读复验全过** 且 **具备合规独立复核 provenance 记录** 且 **人类签署放行凭单** 方可跨入下游。缺少独立复核时状态必须标记为 `BLOCKED_NO_REVIEWER`，严禁放行出口。

## 6. 可选增强层清单（默认不启用）

为保证流水线基座轻量可靠，以下能力界定为可选增强层，必须在用户显式要求时方可启用：
1. **OpenSpec 全套变更提案流程 (`changes/<change-id>/`)**：默认不启用。变更默认由《变更管理与指示处置对照表》（`change-table.md`）与签署件承载，仅在用户显式要求重构治理规格时启用。
2. **在线协同载体双向实时同步**：默认不启用。默认以本地 Git 仓库为主载体与事实源，在线文档仅作为只读镜像或整文件导出附件；双向实时块更新为扩展插件。
3. **异步问卷调研模式 (to-questionnaire)**：默认不启用。默认采用交互决策树访谈，多方异步问卷为进阶扩展。
