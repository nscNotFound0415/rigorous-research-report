# M1 落地澄清与简报构建 (brief-elicitation) 模块测试夹具与法官执行手册

本手册供独立验收法官（Independent Reviewer）开展全黑箱验证。
法官无需审阅内部实现，仅需在宿主终端按本手册所列命令黑箱执行，比对进程退出码与标准输出（stdout）中的 JSON 字段。

---

## 1. 夹具清单与测试拓扑

```text
tests/module_tests/test_m1_elicitation/
├── README.md                                  # 本手册（法官黑箱执行唯一指南）
├── run_tests.sh                               # 一键全套测试运行脚本
├── test_m1.py                                 # 模块标准自动化测试套件 (31 项断言)
├── elicitation_evaluator.py                   # 决策树推算与 Frontier 计算器
└── fixtures/                                  # 确定性黑箱物料
    ├── input_missing_two_dimensions.json      # (a) 故意缺失「格式约定」「落盘地址」的输入
    ├── expected_frontier.json                 # 预期 Active Frontier 结构与推荐选项
    ├── sample_brief_draft.md                  # 满足 M1-1/M1-2/M2-2 标准之 brief 样卷 (八项均 CLARIFIED)
    ├── brief_unclarified_soft_item_positive.md        # 正例：软项 NOT_CLARIFIED + 合法 reason 放行
    ├── brief_unclarified_missing_reason_negative.md   # 阴性：NOT_CLARIFIED 缺 unclarified_reason 阻断
    ├── brief_invalid_clarification_status_negative.md # 阴性：clarification_status 取值非法阻断
    ├── brief_clarified_pending_term_negative.md       # 阴性：CLARIFIED 项内容含「待定」阻断
    ├── brief_unclarified_content_marker_positive.md   # 正例防误报：未澄清项内容含「未澄清」放行
    ├── brief_clarified_invalid_source_of_truth_negative.md # 阴性：CLARIFIED 但 source_of_truth 越界阻断
    ├── brief_unclarified_source_of_truth_not_default_negative.md # 阴性：未澄清项未落默认行为值阻断 (M1-6)
    ├── provenance_valid_heterogeneous.json    # 异族跨厂商对抗复核证明 (有效放行)
    ├── provenance_valid_homologous_reset.json # 同族-零记忆隔离且 context_reset=True (有效放行)
    ├── unisolated_provenance.json             # 阴性对照：伪造隔离但 session 相同 (阻断拦截)
    ├── provenance_invalid_same_vendor.json    # 阴性对照：异族但相同厂商前缀 (阻断拦截)
    ├── provenance_invalid_no_reset.json       # 阴性对照：同族但 context_reset=false (阻断拦截)
    ├── empty_workspace/                       # 场景 2 空白工作区（不含 gates/G0-approval.md）
    └── gates/                                 # 门禁凭据夹具
        ├── G0-request.md                      # G0 人审放行申请单
        ├── G0-approval-valid.md               # 有效人类签署放行件 (decision: APPROVED)
        ├── G0-approval-pending.md             # (b) 未获 G0 签署件 (decision: PENDING)
        ├── G0-approval-fake-agent.md          # 阴性对照：Agent 自签放行件 (signed_by: agent:*)
        ├── G0-approval-hash-mismatch.md       # 阴性对照：哈希被篡改/不符的放行件
        └── G0-approval-changes-requested.md   # 驳回要求修改件 (decision: CHANGES_REQUESTED)
```

---

## 2. 法官黑箱逐项执行指令与期望值

以下所有命令在 `skill-build/` 根目录或任意指定绝对路径下均可直接执行。

### 场景 1：缺失「格式约定」与「落盘地址」输入，计算 Frontier
- **被测目标**：`P1_grill_me_protocol.md` 规定的 DAG 与一次一问规则。
- **输入文件**：`tests/module_tests/test_m1_elicitation/fixtures/input_missing_two_dimensions.json`
- **执行命令**：
  ```bash
  python3 tests/module_tests/test_m1_elicitation/elicitation_evaluator.py \
    --input tests/module_tests/test_m1_elicitation/fixtures/input_missing_two_dimensions.json
  ```
- **期望退出码**：`0`
- **期望 JSON 关键字段断言**：
  - `"is_complete": false`
  - `"unresolved_count": 2`
  - `"all_unresolved_dimensions"` 包含 `D5_format` 与 `D6_delivery_path`
  - `"active_frontier"[0]["id"] == "D5"`（D5 依赖已满足，优先出队；D6 依赖 D5 暂不入 active 队列）
  - `"recommended_options"` 长度为 4（包含 3 个推荐方案 + `[Other]` 自定义选项）

---

### 场景 2：未获 G0 签署时，门禁阻断下游流转 (CRITERION M1-3)
- **被测脚本**：`src/scripts/gate_guard.py`
- **黑箱场景**：工作区不存在 `gates/G0-approval.md` 时执行常规检查。
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --gate G0 --check-only --root tests/module_tests/test_m1_elicitation/fixtures/empty_workspace
  ```
- **期望退出码**：`1` (Operation Blocked)
- **期望 stdout JSON**：
  ```json
  {"gate": "G0", "state": "PENDING", "blocked": true, "artifact_sha256": null, "reason": "Approval file not found: tests/module_tests/test_m1_elicitation/fixtures/empty_workspace/gates/G0-approval.md"}
  ```

---

### 场景 3：签署件处于 PENDING 状态时阻断流转
- **被测脚本**：`src/scripts/gate_guard.py`
- **输入文件**：工件 `sample_brief_draft.md`，签署件 `G0-approval-pending.md`
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --gate G0 --verify \
    --artifact tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md \
    --approval tests/module_tests/test_m1_elicitation/fixtures/gates/G0-approval-pending.md
  ```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"gate": "G0"`
  - `"state": "PENDING"`
  - `"blocked": true`

---

### 场景 4：具备合规人类签名且哈希一致，放行进入 M2 (CRITERION M1-3 通过态)
- **被测脚本**：`src/scripts/gate_guard.py`
- **输入文件**：工件 `sample_brief_draft.md`，签署件 `G0-approval-valid.md`
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --gate G0 --verify \
    --artifact tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md \
    --approval tests/module_tests/test_m1_elicitation/fixtures/gates/G0-approval-valid.md
  ```
- **期望退出码**：`0` (Unblocked / Success)
- **期望 stdout JSON**：
  ```json
  {"gate": "G0", "state": "APPROVED", "blocked": false, "artifact_sha256": "a90276b06291a2e859f2369c7adca60ad2c3f246a41e6a8e9e88542834117d7d", "reason": "Gate G0 successfully verified and approved by operator_huang"}
  ```

---

### 场景 5 [阴性对照]：Agent 伪造签署件自签放行，断言强制拦截
- **被测脚本**：`src/scripts/gate_guard.py`
- **输入文件**：签署件 `G0-approval-fake-agent.md` (`signed_by: agent:subagent-gemini-session-999`)
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --gate G0 --verify \
    --artifact tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md \
    --approval tests/module_tests/test_m1_elicitation/fixtures/gates/G0-approval-fake-agent.md
  ```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"gate": "G0"`
  - `"state": "AGENT_SIGNATURE_PROHIBITED"`
  - `"blocked": true`
  - `"reason"` 包含 `"Agent self-signing is strictly prohibited"`

---

### 场景 6 [阴性对照]：工件哈希与签署单声明不符，断言强制拦截
- **被测脚本**：`src/scripts/gate_guard.py`
- **输入文件**：签署件 `G0-approval-hash-mismatch.md` (`artifact_sha256: 00000...`)
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --gate G0 --verify \
    --artifact tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md \
    --approval tests/module_tests/test_m1_elicitation/fixtures/gates/G0-approval-hash-mismatch.md
  ```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"gate": "G0"`
  - `"state": "HASH_MISMATCH"`
  - `"blocked": true`

---

### 场景 7：brief 宪法五原则与派生声明校验 (CRITERION M1-1, M1-2, M2-2)
- **被测脚本**：`src/scripts/gate_guard.py`
- **输入文件**：`tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md`
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py \
    --verify-brief tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md
  ```
- **期望退出码**：`0`
- **期望 stdout JSON**：
  ```json
  {"valid": true, "brief_content_sha256": "3fb41b37ac28054f9fa3e571b83457e79894c7d5512fd0b2679f32487d4f8f32", "errors": []}
  ```

---

### 场景 8：通用变更门禁 (change-<id>) 校验支持 (AL-08)
- **被测脚本**：`src/scripts/gate_guard.py`
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --gate change-01 --check-only
  ```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"gate": "change-01"`
  - `"state": "PENDING"`
  - `"blocked": true`
  - `"artifact_sha256": null`

---

### 场景 9：对抗复核证明异族隔离性校验放行 (AL-06 / CRITERION M6-2)
- **被测脚本**：`src/scripts/gate_guard.py`
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --check-provenance tests/module_tests/test_m1_elicitation/fixtures/provenance_valid_heterogeneous.json
  ```
- **期望退出码**：`0`
- **期望 stdout JSON**：
  ```json
  {"provenance_valid": true, "isolated": true, "channel": "异族", "errors": []}
  ```

---

### 场景 10 [阴性对照]：对抗复核伪造隔离但 session 相同阻断 (AL-06 阴性对照)
- **被测脚本**：`src/scripts/gate_guard.py`
- **执行命令**：
  ```bash
  python3 src/scripts/gate_guard.py --check-provenance tests/module_tests/test_m1_elicitation/fixtures/unisolated_provenance.json
  ```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"provenance_valid": false`
  - `"isolated": false`
  - `"status": "BLOCKED_NO_REVIEWER"`
  - `"errors"` 包含 `"Writer session and reviewer session must be distinct"`

### 场景 11：八项澄清状态登记与默认行为 (CRITERION M1-1 / M1-4 / M1-6)
- **被测脚本**：`src/scripts/gate_guard.py`
- **语义**：八项澄清为建议澄清清单，不是准入条件。每项必须登记 `clarification_status`；`CLARIFIED` 项内容非空且无占位符/待定词；非 `CLARIFIED` 项必须有 `unclarified_reason`，正文豁免扫描且必须落出默认行为值。
- **正例命令（未澄清项放行）**：
  ```bash
  python3 src/scripts/gate_guard.py --verify-brief tests/module_tests/test_m1_elicitation/fixtures/brief_unclarified_soft_item_positive.md
  ```
  期望退出码 `0`，`{"valid": true, "errors": []}`。
- **正例命令（未澄清项不误报）**：
  ```bash
  python3 src/scripts/gate_guard.py --verify-brief tests/module_tests/test_m1_elicitation/fixtures/brief_unclarified_content_marker_positive.md
  ```
  期望退出码 `0`，`{"valid": true, "errors": []}`。
- **阴性命令（缺 reason / 非法状态 / CLARIFIED 含待定 / 枚举越界）**：
  ```bash
  python3 src/scripts/gate_guard.py --verify-brief tests/module_tests/test_m1_elicitation/fixtures/brief_unclarified_missing_reason_negative.md
  python3 src/scripts/gate_guard.py --verify-brief tests/module_tests/test_m1_elicitation/fixtures/brief_invalid_clarification_status_negative.md
  python3 src/scripts/gate_guard.py --verify-brief tests/module_tests/test_m1_elicitation/fixtures/brief_clarified_pending_term_negative.md
  python3 src/scripts/gate_guard.py --verify-brief tests/module_tests/test_m1_elicitation/fixtures/brief_clarified_invalid_source_of_truth_negative.md
  ```
  期望退出码均为 `1`，`errors` 分别提及 `unclarified_reason`、`clarification_status`、`待定`、`source_of_truth`。

---

## 3. 一键全量自动化验收指令

独立法官可直接运行以下任意一条命令，执行全量自动化验收：

```bash
# 方式 A: 执行自带运行脚本
bash tests/module_tests/test_m1_elicitation/run_tests.sh

# 方式 B: 调用 Python 原生测试框架
python3 tests/module_tests/test_m1_elicitation/test_m1.py

# 方式 C: 调用 pytest 框架
pytest tests/module_tests/test_m1_elicitation/test_m1.py -v
```

**合格判据**：31 项测试全部通过（`31 passed`），退出码为 `0`。

---

## 桩签署件硬拒绝（加固项 G）

门禁 `gate_guard.py` 对含 `stub: true`（或 `stub:true`）的签署件一律硬拒绝：`state=STUB_REJECTED`、`blocked=true`、退出码 1，即使 `artifact_sha256` 完全吻合。G0/G1/G2/G3/change-<id> 五门共用该校验。

- 本目录用于正向放行路径的签署件夹具均为**符合人类签署格式且不含 stub 标记**的测试夹具；该夹具仅用于验证放行路径，**不代表真实人类签署**。
- 真实人类签署件必须由人类本人亲笔填写，不得由任何自动流程代签。
