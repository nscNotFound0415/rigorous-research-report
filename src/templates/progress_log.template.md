# [模板规范] 项目治理总控台账 (Progress & Governance Ledger)

<!--
  说明：
  1. 本台账为调研项目唯一的执行进度、授权边界与决策汇总控制台。
  2. 变量统一使用双大括号占位符 {{VARIABLE_NAME}}。
  3. 铁律：复选框 [x] 仅人类或依据人类在 gates/*.md 签署放行单方可填入；Agent 严禁自评打勾！
-->

## 1. 授权边界 (Authorization Boundaries)
- active_session_id: {{SESSION_ID}}
- authorized_operations:                      # 本轮人类明确下达并授权之动作
  - "{{AUTH_OP_1}}"
  - "{{AUTH_OP_2}}"
- prohibited_operations:                      # 未经授权严禁擅自执行之动作
  - "未经 G0 签署擅自启动后续调研规划"
  - "未经 G1 签字启动正文合稿"
  - "未经 G2 裁决静默覆盖线上或本地母本"
  - "未经 G3 终审对外正式提交文件"
  - "Agent 擅自修改任务完成复选框 [x]"

## 2. 状态四分铁律 (State Axiom) 与 STALE 失效语义
> **状态公理**：材料存在 != 已复核 != 已同步 != 已审定。
> 严禁仅因文件存在而推断其内容正确或已经审定。
> 
> - **存在**：工件已在文件系统生成，但未经历对抗复核或人审。
> - **已复核**：工件已通过独立审者复核（达到 D0=0 或校验无环），但未获人类签批或未向外设同步。
> - **已同步**：工件已镜像到在线文档或外设端，但未获最终决策人审定签批。
> - **已审定**：已获得人类在对应门禁签署件（G0-G3 / change-<id>）正式签名批准，具备最高权威。签署件可以是人类直接签署（`human_signed`），也可以是人类会话授权后由 Agent 代录（`session_transcribed`）；后者须在台账「依据签署件与哈希」列同时登记其 `authorization_turn`，使打勾依据可回溯到人类具体授权。
> 
> ### STALE 标记语义与清除规则
> - **STALE 标记语义**：当发生 brief 变更、一手新事实输入或重大口径颠覆时，受影响的任务行或门禁行状态被标记为 STALE（如 `已审定 [STALE]` 或 `存在 [STALE]`），表示前序阶段结论或产物受新信息波及而失效，必须重新执行对应动作与复核。
> - **谁可清除 STALE [铁律]**：STALE 标记与对应门禁的清除/重核权**严格归人类所有**，Agent 严禁擅自清除 STALE 标记，严禁擅自复位或修改复选框 `[x]`。

## 3. 阶段流水线任务清单 (Pipeline Checklist)
> **勾选权公理**：状态列 [x] 仅人类有权写入。Agent 严禁自评放行！Agent 仅可更新「agent_建议」列。
> 校验以 gates/*.md 签署件为准，恢复执行时以首个未勾选项为断点。

| 阶段 | 任务 ID | 任务内容与目标 | 任务完成 | 四分状态 | 责任角色 | agent_建议 | 产出物路径与 content_sha256 | 依据签署件与哈希 |
|---|---|---|:---:|:---:|---|:---:|---|---|
| P1 | T-P1-01 | grill-me 八项澄清访谈 | [ ] | 存在 | Agent/Human | 建议放行 | `brief.md` ({{BRIEF_HASH}}) | 等待 G0 门禁签字 |
| P2 | T-P2-01 | 治理台账与存储契约初始化 | [ ] | 已审定 | Agent | 建议放行 | `progress-log.md` ({{PROGRESS_LOG_HASH}}) | 人类初始确认 |
| P3 | T-P3-01 | 视角枚举与调研任务分解 | [ ] | 存在 | Agent | 建议放行 | `task.json` ({{TASK_JSON_HASH}}) | 启动 M4/M5 |
| P4 | T-P4-01 | 并行调研与数据底表重构 | [ ] | 存在 | Sub-agents | 待复核 | `datatable.csv` ({{DATATABLE_HASH}}) | 待触发边界 1 复核 |
| P4 | T-P4-02 | 边界 1 底表对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/datatable_review.md` ({{DATATABLE_REV_HASH}}) | D0=0 且代码复算通过 |
| P5 | T-P5-01 | 章节架构规划与契约制定 | [ ] | 存在 | Agent/Human | 建议放行 | `outline.md` ({{OUTLINE_HASH}}) | 等待 G1 门禁签字 |
| -  | T-G1-01 | G1 大纲人审门禁签署 | [ ] | 已审定 | Human | - | `gates/G1-approval.md` ({{G1_APPROVAL_HASH}}) | G1 签署放行件 |
| P5 | T-P5-02 | 边界 2 大纲对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/outline_review.md` ({{OUTLINE_REV_HASH}}) | 引用回指与 REQ 覆盖 |
| P6 | T-P6-01 | 调研并行、单次全文合稿 | [ ] | 存在 | Agent | 待复核 | `draft_full.md` ({{DRAFT_HASH}}) | 待触发边界 3 复核 |
| P6 | T-P6-02 | Polish 一致性与交付物构建 | [ ] | 存在 | Agent | 待人审 | `delivery/output.docx` ({{DELIVERY_HASH}}) | 待 G2 裁决与 G3 放行 |
| -  | T-G2-01 | G2 纠错定性裁决签署 | [ ] | 已审定 | Human | - | `gates/G2-approval.md` ({{G2_APPROVAL_HASH}}) | G2 裁决件 |
| P6 | T-P6-03 | 边界 3 全文对抗复核 | [ ] | 已复核 | Reviewer | 建议放行 | `review-reports/draft_full_review.md` ({{DRAFT_REV_HASH}}) | D0=0 且卫生扫描通过 |
| P6 | T-P6-04 | 交付回读与两遍法验证 | [ ] | 已复核 | Agent | 建议放行 | `delivery_readback.json` ({{DELIVERY_READBACK_HASH}}) | 目录与标题差集为空 |
| -  | T-G3-01 | G3 最终成稿交付放行 | [ ] | 已审定 | Human | - | `gates/G3-approval.md` ({{G3_APPROVAL_HASH}}) | G3 终审放行件 |
| M  | T-M8-01 | 变更处置与零漂移维护 | [ ] | 存在 | Agent/Human | 待事件触发 | `change-table.md` ({{CHANGE_TABLE_HASH}}) | 动态回路响应 |

## 4. 决策日志 (Decision Log)
记录项目全生命周期所有重大取舍、口径选择与定性裁决。

| 决策 ID | 时间戳 | 触发事件/争议点 | 权衡选项 (Tradeoffs) | 最终裁决结论 | 裁决人 | 影响产物与生效范围 |
|---|---|---|---|---|---|---|
| {{DECISION_ID}} | {{TIMESTAMP}} | {{TRIGGER_EVENT}} | {{TRADEOFFS}} | {{CONCLUSION}} | {{DECIDER}} | {{IMPACT_SCOPE}} |
