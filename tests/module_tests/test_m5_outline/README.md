# M5 章节架构规划与 G1 人审门禁 模块测试与法官验收指南

本指南供独立验收法官（Independent Reviewer）开展全黑箱验证。
法官无需审阅内部实现代码，仅需在工作区根目录（`skill-build/`）复制并执行本指南所列的命令，比对进程退出码与标准输出（stdout）中的 JSON 字段。

---

## 一、夹具清单与测试拓扑

```text
tests/module_tests/test_m5_outline/
├── README.md                                       # 本手册（法官黑箱执行唯一指南）
├── run_tests.sh                                    # 一键全套测试运行脚本
├── test_m5_outline.py                              # 模块标准自动化测试套件 (16 项断言)
└── fixtures/                                       # 确定性黑箱测试夹具
    ├── evidence-index.md                           # 证据索引快照 (含 EVD-001..EVD-005)
    ├── valid_outline_parallel.md                   # 并行期合规大纲 (含已声明 PENDING-01)
    ├── valid_outline_resolved.md                   # Join 2 闭环大纲 (全量回指，0 PENDING)
    ├── empty_workspace/gates/                      # (c) 未签署 G1 的空白工作区
    ├── negative_controls/                          # 阴性对照测试旧料夹具集
    │   ├── missing_refs_outline.md                 # (a) 包含 2 条悬空引用的旧大纲 (EVD-998, EVD-999)
    │   ├── unlisted_pending_outline.md             # (b) 包含 PENDING 但未在待补数据节登记的旧大纲
    │   ├── dangling_evidence_outline.md            # (d) §8.1 规定未锚定引用的旧大纲
    │   ├── skipped_heading_outline.md              # 标题层级跳级旧大纲 (H2 直接跳至 H4)
    │   ├── missing_objective_outline.md            # 缺失明确「论证目的」行的旧大纲
    │   └── no_evidence_outline.md                  # 章节缺失 evidence_ref 的旧大纲
    └── gates/                                      # G1 门禁测试凭据夹具
        ├── G1-request.md                           # G1 人审放行申请单
        ├── G1-approval-valid.md                    # 有效人类签署放行件 (decision: APPROVED)
        ├── G1-approval-pending.md                  # 未获签署件 (decision: PENDING)
        ├── G1-approval-rejected.md                 # 驳回件 (decision: REJECTED)
        ├── G1-approval-fake-agent.md               # 阴性对照：Agent 自签放行件 (signed_by: agent:*)
        └── G1-approval-hash-mismatch.md            # 阴性对照：哈希被篡改的放行件
```

---

## 二、法官执行命令原文与判定标准 (Judge Execution Commands)

所有命令均以 `skill-build/` 为当前工作目录直接执行。

### 1. 自动化全量测试运行命令
```bash
pytest tests/module_tests/test_m5_outline/test_m5_outline.py -v
```
- **期望退出码**：`0`
- **期望输出**：`15 passed in <2s`

---

### 2. 黑箱场景独立验证命令

#### 场景 1：并行期大纲证据引用与显式 PENDING 登记放行 (CRITERION M5-1a)
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/valid_outline_parallel.md --evidence-index tests/module_tests/test_m5_outline/fixtures/evidence-index.md
```
- **期望退出码**：`0`
- **期望 stdout JSON 关键字段**：
  - `"missing_refs": []`
  - `"pending_refs": ["PENDING-01"]`
  - `"pending_declared": true`
  - `"refs_total": 4`

---

#### 场景 2：阴性对照 (a) - 2 条 evidence_ref 指向不存在的证据 (CRITERION M5-1a 阴性)
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/negative_controls/missing_refs_outline.md --evidence-index tests/module_tests/test_m5_outline/fixtures/evidence-index.md
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"missing_refs"` 包含 `["EVD-998", "EVD-999"]`
  - 阻断并报错

---

#### 场景 3：阴性对照 (b) - outline 有 PENDING 但「待补数据」小节未登记
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/negative_controls/unlisted_pending_outline.md --evidence-index tests/module_tests/test_m5_outline/fixtures/evidence-index.md
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"pending_declared": false`
  - `"pending_refs"` 包含 `["PENDING-99"]`

---

#### 场景 4：Join 2 汇合门禁清零校验 (CRITERION M5-1b)
##### 4.1 含 PENDING 的大纲在 Join 2 汇合核验中被不可豁免阻断
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/valid_outline_parallel.md --evidence-index tests/module_tests/test_m5_outline/fixtures/evidence-index.md --require-resolved
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"pending_count": 1` 或 `"pending_refs"` 非空

##### 4.2 全量回指清零的大纲在 Join 2 汇合核验中顺利通过
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/valid_outline_resolved.md --evidence-index tests/module_tests/test_m5_outline/fixtures/evidence-index.md --require-resolved
```
- **期望退出码**：`0`
- **期望 stdout JSON 关键字段**：
  - `"missing_refs": []`
  - `"pending_refs": []`
  - `"pending_count": 0`

---

#### 场景 5：阴性对照 (d) - §8.1 规定的未锚定引用旧料喂入严格模式
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/negative_controls/dangling_evidence_outline.md --evidence-index tests/module_tests/test_m5_outline/fixtures/evidence-index.md --strict
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"pending_count": 1`

---

#### 场景 6：章节结构、层级不跳级与论证目的校验 (--check-sections)
##### 6.1 合规大纲章节结构校验通过
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/valid_outline_parallel.md --check-sections
```
- **期望退出码**：`0`
- **期望 stdout JSON 关键字段**：
  - `"invalid_sections": []`
  - `"chapter_count": 3`

##### 6.2 标题层级跳级检出 (H2 直接跳至 H4)
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/negative_controls/skipped_heading_outline.md --check-sections
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"invalid_sections"` 包含 `"Heading level skipped from H2 ... to H4"`

##### 6.3 缺失明确「论证目的」行检出
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/negative_controls/missing_objective_outline.md --check-sections
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"invalid_sections"` 包含 `"missing explicit '论证目的' line"`

##### 6.4 章节缺少 evidence_ref（少于 1 条）检出
```bash
python3 src/scripts/outline_check.py tests/module_tests/test_m5_outline/fixtures/negative_controls/no_evidence_outline.md --check-sections
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `"invalid_sections"` 包含 `"has no evidence_ref"`

---

#### 场景 7：阴性对照 (c) - G1 门禁未签署时自动阻断 (CRITERION M5-3)
```bash
python3 src/scripts/gate_guard.py --gate G1 --check-only --root tests/module_tests/test_m5_outline/fixtures/empty_workspace
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `{"gate": "G1", "state": "PENDING", "blocked": true, "artifact_sha256": null}`

---

#### 场景 8：G1 门禁处于 REJECTED 状态时阻断向 M7 合稿流转 (CRITERION M5-3)
```bash
python3 src/scripts/gate_guard.py --gate G1 --verify --artifact tests/module_tests/test_m5_outline/fixtures/valid_outline_resolved.md --approval tests/module_tests/test_m5_outline/fixtures/gates/G1-approval-rejected.md
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `{"gate": "G1", "state": "REJECTED", "blocked": true}`

---

#### 场景 9：G1 门禁具备有效人类签署且哈希一致放行 (CRITERION M5-2)
```bash
python3 src/scripts/gate_guard.py --gate G1 --verify --artifact tests/module_tests/test_m5_outline/fixtures/valid_outline_resolved.md --approval tests/module_tests/test_m5_outline/fixtures/gates/G1-approval-valid.md
```
- **期望退出码**：`0`
- **期望 stdout JSON 关键字段**：
  - `{"gate": "G1", "state": "APPROVED", "blocked": false, "artifact_sha256": "3a8daa4de28ed6efe783fd66d8da2ead1ab0d9171f5efdf1ef1ef72e5086dcd7"}`

---

#### 场景 10：门禁防伪 - Agent 自签无条件阻断
```bash
python3 src/scripts/gate_guard.py --gate G1 --verify --artifact tests/module_tests/test_m5_outline/fixtures/valid_outline_resolved.md --approval tests/module_tests/test_m5_outline/fixtures/gates/G1-approval-fake-agent.md
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `{"gate": "G1", "state": "AGENT_SIGNATURE_PROHIBITED", "blocked": true}`

---

#### 场景 11：门禁防伪 - 工件哈希不符无条件阻断
```bash
python3 src/scripts/gate_guard.py --gate G1 --verify --artifact tests/module_tests/test_m5_outline/fixtures/valid_outline_resolved.md --approval tests/module_tests/test_m5_outline/fixtures/gates/G1-approval-hash-mismatch.md
```
- **期望退出码**：`1`
- **期望 stdout JSON 关键字段**：
  - `{"gate": "G1", "state": "HASH_MISMATCH", "blocked": true}`

---

## 桩签署件硬拒绝（加固项 G）

门禁 `gate_guard.py` 对含 `stub: true`（或 `stub:true`）的签署件一律硬拒绝：`state=STUB_REJECTED`、`blocked=true`、退出码 1，即使 `artifact_sha256` 完全吻合。G0/G1/G2/G3/change-<id> 五门共用该校验。

- 本目录用于正向放行路径的签署件夹具均为**符合人类签署格式且不含 stub 标记**的测试夹具；该夹具仅用于验证放行路径，**不代表真实人类签署**。
- 真实人类签署件必须由人类本人亲笔填写，不得由任何自动流程代签。
