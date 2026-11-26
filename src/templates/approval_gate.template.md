# 门禁申请与审批标准模板 (Gate Request & Approval Templates)

> **治理铁律 (Governance Axiom)**：
> 1. 裁决归属与记录方式分离：门禁裁决（APPROVED / REJECTED / CHANGES_REQUESTED）始终由人类作出，Agent 永不得自行裁决。
> 2. 签署件允许两种记录方式：
>    - **直接签署 (`human_signed`)**：人类操作者亲手填写并签署 `gates/<G>-approval.md`。
>    - **会话授权代录 (`session_transcribed`)**：人类在会话中明确授权后，Agent 依授权原话代写签署件。代录必须完整留下 `authorization_quote` / `authorization_turn` / `authorization_at` / `authorized_by` / `recorded_by`，供事后审计；`authorized_by` 必须是人类身份且与 `signed_by` 一致。
> 3. `scripts/gate_guard.py` 对两种方式执行同一套防伪校验：授权溯源字段缺失、授权人写成机器身份、授权人与签署人不一致、工件哈希不符、桩件标记（`stub: true`）一律阻断（退出码 1）。

---

## 1. 门禁放行申请单模板 (`gates/{{GATE_NAME}}-request.md`)

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

### 2.1 直接签署模式 (`human_signed`)

```markdown
# 门禁审批签署件 ({{GATE_NAME}} Approval Sign-off)

- gate: {{GATE_NAME}}
- decision: {{DECISION}}
- signed_by: {{HUMAN_OPERATOR_ID}}
- signed_at: {{SIGNED_TIMESTAMP_ISO8601}}
- artifact_sha256: {{ARTIFACT_SHA256}}
- signature: {{HUMAN_CONFIRMATION_PASSPHRASE}}
- comments: {{HUMAN_COMMENTS_OR_INSTRUCTIONS}}
```

### 2.2 会话授权代录模式 (`session_transcribed`)

由 Agent 依人类在会话中的授权原话代写。推荐用脚本生成，避免手填哈希漂移：

```bash
python3 scripts/gate_guard.py --record-approval --gate {{GATE_NAME}} \
  --artifact {{ARTIFACT_PATH}} --root {{WORKSPACE_ROOT}} \
  --authorized-by "{{HUMAN_OPERATOR_ID}}" \
  --authorization-quote "{{人类授权原话}}" \
  --authorization-turn "{{会话与消息引用}}" \
  --decision APPROVED --comments "{{备注}}"
```

生成后的签署件形如：

```markdown
# 门禁审批签署件 ({{GATE_NAME}} Approval Sign-off)

> 本件由 Agent 依人类在会话中的明确授权代录（authorization_mode: session_transcribed）。
> 授权原话、授权轮次与授权时间见下方字段；裁决归属仍为人类，Agent 仅忠实转写。

- gate: {{GATE_NAME}}
- decision: {{DECISION}}
- signed_by: {{HUMAN_OPERATOR_ID}}
- signed_at: {{SIGNED_TIMESTAMP_ISO8601}}
- artifact_sha256: {{ARTIFACT_SHA256}}
- signature: {{HUMAN_CONFIRMATION_PASSPHRASE}}
- authorization_mode: session_transcribed
- authorized_by: {{HUMAN_OPERATOR_ID}}
- authorization_quote: {{人类授权原话}}
- authorization_turn: {{会话与消息引用}}
- authorization_at: {{SIGNED_TIMESTAMP_ISO8601}}
- recorded_by: {{AGENT_ID}}
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
| `authorization_mode` | 否 | `human_signed` \| `session_transcribed` | 缺省按 `human_signed` 处理；取值非法即阻断 |
| `authorized_by` | 代录模式必填 | 人类身份标识，须与 `signed_by` 一致 | 写成机器身份或与签署人不一致即阻断 |
| `authorization_quote` | 代录模式必填 | 人类授权原话，不得少于 2 字符 | 缺失或过短即阻断 |
| `authorization_turn` | 代录模式必填 | 会话与消息引用 | 缺失即阻断 |
| `authorization_at` | 代录模式必填 | ISO 8601 时间戳 | 缺失即阻断 |
| `recorded_by` | 代录模式必填 | 代录者标识（可为 `agent:*`） | 缺失即阻断；本字段是代录留痕，不得为空 |
| `comments` | 否 | 人类对本阶段的批注、修改意见或裁决理由 | 留存治理台账备查 |
| `parent_baseline_sha256` | 是 (仅变更) | 变更前母本全文 SHA-256 哈希 | 仅在 `change-<id>` 门禁时为必填项 |
