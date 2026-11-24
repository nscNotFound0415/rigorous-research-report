# 变更门禁审批签署件 (change-<id> Approval Sign-off)

> 【人类决策者审阅专有凭单 - 严禁机器代理代签或预填】
> 本文件为变更维护回路（change-table.md 指示处置与母本局部修订）人审凭单模板。
> 必须由人类项目负责人/决策者在审阅《指示处置对照表》（核对受影响章节范围、母本只读备份及零漂移声明）后手工填写并保存为 `gates/change-<id>-approval.md`。

---
gate: change-01
decision: <MUST_BE_FILLED_BY_HUMAN: APPROVED | REJECTED | CHANGES_REQUESTED>
signed_by: <MUST_BE_FILLED_BY_HUMAN: 人类决策者真实标识，禁止包含 agent/ai/bot/自动 等机器词汇>
signed_at: <MUST_BE_FILLED_BY_HUMAN: ISO8601时间戳，例如 2026-11-23T18:00:00Z>
artifact_sha256: <MUST_BE_FILLED_BY_HUMAN: change-table.md 的 64 位 SHA-256 哈希值>
signature: <MUST_BE_FILLED_BY_HUMAN: 人类现场确认口令原文，例如 CONFIRMED_PROCEED_CHANGE_01>
parent_baseline_sha256: <MUST_BE_FILLED_BY_HUMAN: 变更前母本文件 draft_full.md 的 SHA-256 哈希值>
approver_role: human_decision_maker
comments: <OPTIONAL: 人类对本次指示处置与局部改写范围的批准说明>
---
