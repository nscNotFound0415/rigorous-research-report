# G2 门禁审批签署件 (G2 Approval Sign-off)

> 【人类决策者审阅专有凭单 - 严禁机器代理代签或预填】
> 本文件为 G2（对抗复核定性裁决与纠错对照稿 correction-diff.md 审批门禁）人审凭单模板。
> 必须由人类项目负责人/决策者在审阅 review-reports 与 correction-diff.md（针对 D1/D2 争议项行使人类排他定性拍板权）后手工填写并保存为 `gates/G2-approval.md`。

---
gate: G2
decision: <MUST_BE_FILLED_BY_HUMAN: APPROVED | REJECTED | CHANGES_REQUESTED>
signed_by: <MUST_BE_FILLED_BY_HUMAN: 人类决策者真实标识，禁止包含 agent/ai/bot/自动 等机器词汇>
signed_at: <MUST_BE_FILLED_BY_HUMAN: ISO8601时间戳，例如 2026-11-23T16:00:00Z>
artifact_sha256: <MUST_BE_FILLED_BY_HUMAN: correction-diff.md 的 64 位 SHA-256 哈希值>
signature: <MUST_BE_FILLED_BY_HUMAN: 人类现场确认口令原文，例如 CONFIRMED_PROCEED_G2>
approver_role: human_decision_maker
comments: <OPTIONAL: 人类对争议表述存废、降级或补证的定性裁决记录>
---
