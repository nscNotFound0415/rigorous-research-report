# 项目治理总控台账 (Progress & Governance Ledger)

## 1. 授权边界 (Authorization Boundaries)
- active_session_id: test_session_tampered_02
- authorized_operations:
  - "课题拆分中"
- prohibited_operations:
  - "未经 G1 签字启动正文合稿"
  - "未经 G2 裁决静默覆盖线上或本地母本"
  - "对外正式提交文件"
  - "Agent 擅自修改任务完成复选框 [x]"

## 2. 状态四分铁律 (State Axiom)
> **状态公理**：材料存在 != 已复核 != 已同步 != 已审定。

## 3. 阶段流水线任务清单 (Pipeline Checklist)

| 阶段 | 任务 ID | 任务内容与目标 | 任务完成 | 四分状态 | 责任角色 | agent_建议 | 产出物路径与 content_sha256 | 依据签署件与哈希 |
|---|---|---|:---:|:---:|---|:---:|---|---|
| P1 | T-P1-01 | grill-me 八项澄清访谈 | [ ] | 存在 | Agent/Human | 建议放行 | `brief.md` (hash) | 等待 G0 门禁签字 |
| P2 | T-P2-01 | 治理台账与存储契约初始化 | [ ] | 已审定 | Agent | 建议放行 | `progress-log.md` (hash) | 人类初始确认 |
| P3 | T-P3-01 | 视角枚举与调研任务分解 | [x] | 存在 | Agent | 自行标记完成（非法） | `task.json` (hash) | 无签署件 |
| P4 | T-P4-01 | 并行调研与数据底表重构 | [ ] | 存在 | Sub-agents | 待复核 | `datatable.csv` (hash) | 待触发边界 1 复核 |
| P4 | T-P4-02 | 边界 1 底表对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/datatable_review.md` (hash) | D0=0 且代码复算通过 |
| P5 | T-P5-01 | 章节架构规划与契约制定 | [ ] | 存在 | Agent/Human | 建议放行 | `outline.md` (hash) | 等待 G1 门禁签字 |
| -  | T-G1-01 | G1 大纲人审门禁签署 | [ ] | 已审定 | Human | - | `gates/G1-approval.md` (hash) | G1 签署放行件 |
| P5 | T-P5-02 | 边界 2 大纲对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/outline_review.md` (hash) | 引用回指与 REQ 覆盖 |
| P6 | T-P6-01 | 调研并行、单次全文合稿 | [ ] | 存在 | Agent | 待复核 | `draft_full.md` (hash) | 待触发边界 3 复核 |
| P6 | T-P6-02 | Polish 一致性与交付物构建 | [ ] | 存在 | Agent | 待人审 | `delivery/output.docx` (hash) | 待 G2 裁决与 G3 放行 |
| -  | T-G2-01 | G2 纠错定性裁决签署 | [ ] | 已审定 | Human | - | `gates/G2-approval.md` (hash) | G2 裁决件 |
| P6 | T-P6-03 | 边界 3 全文对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/draft_full_review.md` (hash) | D0=0 且卫生扫描通过 |
| P6 | T-P6-04 | 交付回读与两遍法验证 | [ ] | 存在 | Agent | 待运行 | `delivery_readback.json` | 待构建后校验 |
| -  | T-G3-01 | G3 最终成稿交付放行 | [ ] | 已审定 | Human | - | `gates/G3-approval.md` (hash) | G3 终审放行件 |
| M  | T-M8-01 | 变更处置与零漂移维护 | [ ] | 存在 | Agent/Human | 待事件触发 | `change-table.md` (hash) | 动态回路响应 |

## 4. 决策日志 (Decision Log)

| 决策 ID | 时间戳 | 触发事件/争议点 | 权衡选项 (Tradeoffs) | 最终裁决结论 | 裁决人 | 影响产物与生效范围 |
|---|---|---|---|---|---|---|
| D-001 | 2026-11-23T10:00:00Z | 方案选型 | 方案 A vs 方案 B | 采纳方案 A | human_operator_01 | 架构设计 |
