# G1 门禁审批签署件 (G1 Approval Sign-off)

> 【人类决策者审阅专有凭单 - 严禁机器代理代签或预填】
> 本文件为 G1（调研规划与章节架构大纲 outline.md 审批门禁）人审凭单模板。
> 必须由人类项目负责人/决策者在审阅 outline.md（核对各章论证拓扑、证据引用 evidence_ref 及待补数据清零）后手工填写并保存为 `gates/G1-approval.md`。

---
gate: G1
decision: <MUST_BE_FILLED_BY_HUMAN: APPROVED | REJECTED | CHANGES_REQUESTED>
signed_by: <MUST_BE_FILLED_BY_HUMAN: 人类决策者真实标识，禁止包含 agent/ai/bot/自动 等机器词汇>
signed_at: <MUST_BE_FILLED_BY_HUMAN: ISO8601时间戳，例如 2026-11-23T15:00:00Z>
artifact_sha256: <MUST_BE_FILLED_BY_HUMAN: outline.md 的 64 位 SHA-256 哈希值>
signature: <MUST_BE_FILLED_BY_HUMAN: 人类现场确认口令原文，例如 CONFIRMED_PROCEED_G1>
approver_role: human_decision_maker
comments: <OPTIONAL: 人类决策者对大纲结构与撰写契约的批注意见>
---
