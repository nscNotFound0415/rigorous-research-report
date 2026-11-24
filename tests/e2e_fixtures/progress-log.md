# 项目治理总控台账 (E2E 离线夹具 · 机器阶段冻结态)

> 本文件为 E2E-c 离线夹具的治理台账快照，仅代表「机器已完成、人类尚未授权勾选」的中间态。
> 铁律：复选框 `[x]` 仅人类有权写入。本夹具中全部任务保持 `[ ]`，任何 `[x]` 均由测试用例构造为负例并断言被回滚。

## 1. 授权边界 (Authorization Boundaries)
- active_session_id: e2e-c-ledger-fixture
- authorized_operations:
  - "执行离线确定性夹具 E2E-c（M3→M7）"
- prohibited_operations:
  - "未经 G0 签署擅自启动后续调研规划"
  - "未经 G1 签字启动正文合稿"
  - "未经 G2 裁决静默覆盖母本"
  - "未经 G3 终审对外正式提交文件"
  - "Agent 擅自修改任务完成复选框 [x]"

## 2. 状态四分铁律 (State Axiom)
> 材料存在 != 已复核 != 已同步 != 已审定。本夹具仅使用 `存在` 与 `已复核` 两种机器可自证状态，绝不使用 `已审定`（该状态必须由人类签署授予）。

## 3. 阶段流水线任务清单 (Pipeline Checklist)

| 阶段 | 任务 ID | 任务内容与目标 | 任务完成 | 四分状态 | 责任角色 | agent_建议 | 产出物路径与 content_sha256 | 依据签署件与哈希 |
|---|---|---|:---:|:---:|---|:---:|---|---|
| P1 | T-P1-01 | grill-me 八项澄清访谈 | [ ] | 存在 | Agent/Human | 建议放行 | `brief.md` (91deff94f842ab9c92274f75d496834d2a6196c83a0442bc86971e5cd121dfed) | 等待 G0 门禁签字 |
| P2 | T-P2-01 | 治理台账与存储契约初始化 | [ ] | 存在 | Agent | 建议放行 | `progress-log.md` (machine-phase-fixture) | 等待人类初始确认 |
| P3 | T-P3-01 | 视角枚举与调研任务分解 | [ ] | 存在 | Agent | 建议放行 | `task.json` (bebcce89e5b9865c6e97c0557771db8f578272589b4f914659864a6b86971ee5) | 启动 M4/M5 |
| P4 | T-P4-01 | 并行调研与数据底表重构 | [ ] | 存在 | Sub-agents | 待复核 | `datatable.csv` (7cd88271e69c8e67951fd421102915b48ada2d47763f416cda2279342d4bdffc) | 待边界 1 复核 |
| P4 | T-P4-02 | 边界 1 底表对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/datatable_review.md` (not-produced-in-fixture) | D0=0 且代码复算通过 |
| P5 | T-P5-01 | 章节架构规划与契约制定 | [ ] | 存在 | Agent/Human | 建议放行 | `outline.md` (cfade7dee3bd6f857b82ed41802601098457e940d48635d7f3de5d1a6bcca1c8) | 等待 G1 门禁签字 |
| -  | T-G1-01 | G1 大纲人审门禁签署 | [ ] | 存在 | Human | - | `gates/G1-approval.md` (not-produced-in-fixture) | 等待真人签署 |
| P5 | T-P5-02 | 边界 2 大纲对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/outline_review.md` (not-produced-in-fixture) | 引用回指与 REQ 覆盖 |
| P6 | T-P6-01 | 调研并行、单次全文合稿 | [ ] | 存在 | Agent | 待复核 | `draft_full.md` (6e7e4a42ab6f9bfdb9b836beee3f13374609c75a3f8b33076857252e93e25e12) | 待边界 3 复核 |
| P6 | T-P6-02 | Polish 一致性与交付物构建 | [ ] | 存在 | Agent | 待人审 | `delivery/output.docx` (built-at-runtime) | 待 G2 裁决与 G3 放行 |
| -  | T-G2-01 | G2 纠错定性裁决签署 | [ ] | 存在 | Human | - | `gates/G2-approval.md` (not-produced-in-fixture) | 等待真人裁决 |
| P6 | T-P6-03 | 边界 3 全文对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/draft_full_review.md` (not-produced-in-fixture) | D0=0 且卫生扫描通过 |
| P6 | T-P6-04 | 交付回读与两遍法验证 | [ ] | 已复核 | Agent | 建议放行 | `delivery_readback.json` (built-at-runtime) | 目录与标题差集为空 |
| -  | T-G3-01 | G3 最终成稿交付放行 | [ ] | 存在 | Human | - | `gates/G3-approval.md` (not-produced-in-fixture) | 等待真人签署 |
| M  | T-M8-01 | 变更处置与零漂移维护 | [ ] | 存在 | Agent/Human | 待事件触发 | `change-table.md` (33d895cb894e45698b161e9936ae07def3b7c1eab0ffd5fe3cc23fe17deb8f29) | 等待变更门禁真人签署 |

## 4. 决策日志 (Decision Log)

| 决策 ID | 时间戳 | 触发事件/争议点 | 权衡选项 (Tradeoffs) | 最终裁决结论 | 裁决人 | 影响产物与生效范围 |
|---|---|---|---|---|---|---|
| none | - | 机器阶段无人类定性裁决事项 | - | 等待 G0-G3 真人裁决 | - | - |
