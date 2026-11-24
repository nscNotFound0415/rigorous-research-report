# 门禁申请与审批标准模板 (Gate Request & Approval Templates)

> **治理铁律 (Governance Axiom)**：
> 1. Agent 仅具备生成门禁申请单（`gates/<G>-request.md`）的权限，**严禁自动生成或篡改门禁审批签署件（`gates/<G>-approval.md`）的正文与签名内容**。
> 2. 门禁审批签署件（`gates/<G>-approval.md`）必须由人类操作者在场审阅后手工填写并签署。
> 3. `scripts/gate_guard.py` 对签署件执行强防伪校验，若 `signed_by` 为 `agent:*` 格式或工件哈希不符，将无条件执行阻断（退出码 1）。

---

## 1. 门禁申请单模板 (`gates/{{GATE_NAME}}-request.md`)

```markdown
# 门禁放行申请单 ({{GATE_NAME}} Request)

## 1. 申请元信息 (Request Meta)
- gate: {{GATE_NAME}}
- requested_by: {{REQUESTER_AGENT_ID}}
- requested_at: {{REQUEST_TIMESTAMP_ISO8601}}
- artifact_path: {{ARTIFACT_PATH}}
- artifact_sha256: {{ARTIFACT_SHA256}}

## 2. 交付物摘要与人审建议 (Artifact Summary & Recommendations)
- artifact_summary: {{ARTIFACT_SUMMARY}}
- agent_recommendation: {{AGENT_RECOMMENDATION}}
- decision_points:
  - {{DECISION_POINT_1}}
  - {{DECISION_POINT_2}}

## 3. 前置自检核对清单 (Pre-flight Verification Checklist)
- [x] 产物文件已生成且路径有效: {{ARTIFACT_PATH}}
- [x] 全文 SHA-256 计算完毕: {{ARTIFACT_SHA256}}
- [x] 无隐藏未决异常或内部矛盾
- [x] 已具备对应的独立复核或自查闭环证明
```

---

## 2. 门禁审批签署件模板 (`gates/{{GATE_NAME}}-approval.md`)

```markdown
# 门禁审批签署件 ({{GATE_NAME}} Approval Sign-off)

> 提示：本文件必须由人类操作者手工签署确认。严禁 Agent 自签！

- gate: {{GATE_NAME}}
- decision: {{DECISION}}
- signed_by: {{HUMAN_OPERATOR_ID}}
- signed_at: {{SIGNED_TIMESTAMP_ISO8601}}
- artifact_sha256: {{ARTIFACT_SHA256}}
- signature: {{HUMAN_CONFIRMATION_PASSPHRASE}}
- comments: {{HUMAN_COMMENTS_OR_INSTRUCTIONS}}
```

---

## 3. 字段合法枚举与填写指引

### 3.1 字段定义表
| 字段名 | 必填 | 合法取值 / 约束规则 | 校验行为 |
|---|:---:|---|---|
| `gate` | 是 | `G0` \| `G1` \| `G2` \| `G3` \| `change-<id>` | 必须与被校验门禁完全匹配 |
| `decision` | 是 | `APPROVED` \| `REJECTED` \| `CHANGES_REQUESTED` | 仅 `APPROVED` 方可放行；其余一律阻断 (exit 1) |
| `signed_by` | 是 | 人类操作者身份标识（如 `operator_alice`, `judge_reviewer`） | **禁止以 `agent:` 开头**，否则判自签违规阻断 |
| `signed_at` | 是 | ISO 8601 标准时间戳（如 `2026-11-23T14:30:00Z`） | 必须为有效时间格式 |
| `artifact_sha256` | 是 | 64 位十六进制 SHA-256 哈希字符串 | 必须与目标工件实际文件哈希逐字节一致 |
| `signature` | 是 | 人类现场确认口令原文（如 `CONFIRMED_PROCEED_G0`） | 必须非空 |
| `comments` | 否 | 人类对本阶段的批注、修改意见或裁决理由 | 留存治理台账备查 |
| `parent_baseline_sha256` | 是 (仅变更) | 变更前母本全文 SHA-256 哈希 | 仅在 `change-<id>` 门禁时为必填项 |
