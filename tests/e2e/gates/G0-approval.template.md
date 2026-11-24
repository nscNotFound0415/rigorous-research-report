# G0 门禁审批签署件 (G0 Approval Sign-off)

> 【人类决策者审阅专有凭单 - 严禁机器代理代签或预填】
> 本文件为 G0（项目落地简报 brief.md 放行门禁）人审凭单模板。
> 必须由人类项目负责人/决策者在审阅 brief.md（核对 11 个小节、诉求索引 REQ-ID 与项目宪法）后手工填写并保存为 `gates/G0-approval.md`。

---
gate: G0
decision: <MUST_BE_FILLED_BY_HUMAN: APPROVED | REJECTED | CHANGES_REQUESTED>
signed_by: <MUST_BE_FILLED_BY_HUMAN: 人类决策者真实标识，禁止包含 agent/ai/bot/自动 等机器词汇>
signed_at: <MUST_BE_FILLED_BY_HUMAN: ISO8601时间戳，例如 2026-11-23T14:30:00Z>
artifact_sha256: <MUST_BE_FILLED_BY_HUMAN: brief.md 的 64 位 SHA-256 哈希值>
signature: <MUST_BE_FILLED_BY_HUMAN: 人类现场确认口令原文，例如 CONFIRMED_PROCEED_G0>
approver_role: human_decision_maker
comments: <OPTIONAL: 人类决策者批注与指导意见>
---
