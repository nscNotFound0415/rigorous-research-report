# G3 门禁审批签署件 (G3 Approval Sign-off)

> 【人类决策者审阅专有凭单 - 严禁机器代理代签或预填】
> 本文件为 G3（最终交付物放行门禁：Word/PDF 标准成件与回读报告）人审凭单模板。
> 必须由人类项目负责人/决策者在审阅 delivery 产物（核查目录与正文标题双向差集全空、两遍法页码回填准确、无非白名单元叙述）后手工填写并保存为 `gates/G3-approval.md`。

---
gate: G3
decision: <MUST_BE_FILLED_BY_HUMAN: APPROVED | REJECTED | CHANGES_REQUESTED>
signed_by: <MUST_BE_FILLED_BY_HUMAN: 人类决策者真实标识，禁止包含 agent/ai/bot/自动 等机器词汇>
signed_at: <MUST_BE_FILLED_BY_HUMAN: ISO8601时间戳，例如 2026-11-23T17:00:00Z>
artifact_sha256: <MUST_BE_FILLED_BY_HUMAN: delivery/output.docx 的 64 位 SHA-256 哈希值>
signature: <MUST_BE_FILLED_BY_HUMAN: 人类现场确认口令原文，例如 CONFIRMED_PROCEED_G3>
approver_role: human_decision_maker
comments: <OPTIONAL: 人类对交付包质量与正式发版许可的批注>
---
