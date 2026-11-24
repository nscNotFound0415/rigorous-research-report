# M8 模块变更管理与维护回路独立验收测试指南 (Reviewer Judge Guide)

本目录为 M8 模块（变更管理与动态维护回路，M Loop: Change Circuit）的独立黑箱验收测试套件与测试夹具库。
独立验收法官（Independent Reviewer Judge）可在不查看内部代码实现的前提下，直接通过标准 CLI 命令执行确定性黑箱判定。

---

## 1. 契约与规范绑定
- **OpenSpec 规范**: `openspec/changes/add-rigorous-research-report/specs/change-circuit/spec.md`
- **建设方案 (v2.1)**: §1.2 M8, §1.3 (CRITERION M8-1, M8-2, M8-3), §3.2, §5.3, §8.1, §8.2 E2E-08, §9.1
- **审查裁决 2**: D-7 (阴性对照夹具闭环 `undeclared_drift_patch.md`), D-14 (变更门禁已登记 CLI 契约)

---

## 2. 独立法官黑箱执行命令契约与期望输出一览

> **写盘型命令铁律**：`change_dispatch.py` 的 `--root` 为**必填**参数，且严禁指向 `src/`（脚本与模板为只读资产）。
> - 本节 2.1 / 2.2 / 2.3 / 2.4.1 命令均为**只读**，可反复执行；
> - `--apply` 与 `--propagate` 会写盘（改写目标稿 / 写 STALE 台账），必须先 `cp -r` 夹具到 `/tmp` 临时工作区并显式传 `--root /tmp/xxx`，严禁直接对仓库夹具运行。

### 2.1 变更指示分类与分级判定 (Scenario: Change table records directive and target sections)

#### 命令 2.1.1: 微调指示输入（评级调整）判定为 LIGHTWEIGHT
- **执行命令**:
  ```bash
  python3 src/scripts/change_dispatch.py \
    --root . \
    --instruction-file tests/module_tests/test_m8_change_circuit/fixtures/instruction_lightweight.md \
    --classify
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "change_id": "change-01",
    "ceremony_level": "LIGHTWEIGHT",
    "impacted_sections": ["第1.2节", "第4.2节", "表4-2", "模式二", "1.2", "4.2", "第 1.2 节 业务模式评级与概览", "第 4.2 节 表 4-2 需求测算底表"],
    "affected_evidence_ids": ["S-05", "E-01"],
    "requires_human_signoff": true
  }
  ```

#### 命令 2.1.2: 重大重构指示输入（战略架构颠覆）判定为 MAJOR
- **执行命令**:
  ```bash
  python3 src/scripts/change_dispatch.py \
    --root . \
    --instruction-file tests/module_tests/test_m8_change_circuit/fixtures/instruction_major.md \
    --classify
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "change_id": "change-02",
    "ceremony_level": "MAJOR",
    "impacted_sections": ["全文受影响小节"],
    "affected_evidence_ids": [],
    "requires_human_signoff": true
  }
  ```

---

### 2.2 门禁防伪与母本冻结校验 (CRITERION M8-1 & Scenario: Modification without change signoff is blocked)

#### 命令 2.2.1: 未获审批签署时门禁阻断 (M8-1 Check-Only 契约)
- **执行命令**:
  ```bash
  python3 src/scripts/gate_guard.py --gate change-01 --check-only --root .
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "gate": "change-01",
    "state": "PENDING",
    "blocked": true,
    "artifact_sha256": null
  }
  ```
- **母本存证硬线**: 母本 `draft_full.md` 的 `content_sha256` 绝对保持不变。

#### 命令 2.2.2: Agent 伪造自签时无条件拦截阻断 (Anti-forgery Rule)
- **执行命令**:
  ```bash
  python3 src/scripts/gate_guard.py \
    --gate change-01 \
    --verify \
    --artifact tests/module_tests/test_m8_change_circuit/fixtures/valid_change_table.md \
    --approval tests/module_tests/test_m8_change_circuit/fixtures/approval_fake_agent_negative.md
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "gate": "change-01",
    "state": "AGENT_SIGNATURE_PROHIBITED",
    "blocked": true
  }
  ```

#### 命令 2.2.3: 未获签署件时 `--apply` 严格拒绝执行
> **前置条件**：`--apply` 必须先定位目标母本 `draft_full.md`，因此必须在**含 `draft_full.md` 的工作区间**执行。
> 在清洁根目录（无 `draft_full.md`）下执行时，`reason` 会是 `Target baseline file not found: ...`（文件缺失）而非 `missing_change_approval`，这属于预期行为，不代表门禁逻辑失效。
- **执行命令**:
  ```bash
  rm -rf /tmp/m8_apply_ws && mkdir -p /tmp/m8_apply_ws && \
  cp tests/module_tests/test_m8_change_circuit/fixtures/baseline_draft_full.md /tmp/m8_apply_ws/draft_full.md && \
  cp tests/module_tests/test_m8_change_circuit/fixtures/valid_change_table.md /tmp/m8_apply_ws/change-table.md && \
  python3 src/scripts/change_dispatch.py \
    --root /tmp/m8_apply_ws \
    --apply \
    --change-table change-table.md
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "applied": false,
    "blocked": true,
    "reason": "missing_change_approval"
  }
  ```

---

### 2.3 零漂移比对与阴性对照拦截 (CRITERION M8-2 & Scenario: Diff verification confirms zero undeclared drift)

#### 命令 2.3.1: 仅声明区域改写，非声明区域 0 漂移 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --diff-mode \
    --old tests/module_tests/test_m8_change_circuit/fixtures/baseline_draft_full.md \
    --new tests/module_tests/test_m8_change_circuit/fixtures/clean_corrected_draft.md \
    --declared C-01
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "undeclared_drift": 0,
    "declared_id": "C-01",
    "drift_details": []
  }
  ```

#### 命令 2.3.2: 阴性对照：包含未声明章节篡改的旧料被强制拦截 (D-7 强制要求)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --diff-mode \
    --old tests/module_tests/test_m8_change_circuit/fixtures/baseline_draft_full.md \
    --new tests/module_tests/test_m8_change_circuit/fixtures/undeclared_drift_patch.md \
    --declared C-01
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "undeclared_drift": 140,
    "declared_id": "C-01",
    "drift_details": [
      {
        "tag": "replace",
        "drift_chars": 140
      }
    ]
  }
  ```

---

### 2.4 快照归档与审计核验 (CRITERION M8-3 & M8-Audit)

#### 命令 2.4.1: 备份快照核验 (CRITERION M8-3)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --verify-backup tests/module_tests/test_m8_change_circuit/fixtures/audit_workspace/backup \
    --change-table tests/module_tests/test_m8_change_circuit/fixtures/audit_workspace/change-table.md
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "backup_valid": true,
    "hash_matched": true
  }
  ```

#### 命令 2.4.2: 维护回路编排审计命令 (--audit)
- **执行命令**（`--root` 指向随库 workspace 夹具，`--change-table` 相对 `--root` 解析）:
  ```bash
  python3 src/scripts/change_dispatch.py \
    --root tests/module_tests/test_m8_change_circuit/fixtures/audit_workspace \
    --audit \
    --change-table change-table.md
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "audit_present": true,
    "backup_present": true,
    "undeclared_drift": 0
  }
  ```

---

> **签署件哈希绑定口径（重要）**：变更门禁的 `artifact_sha256` 绑定的是**变更对照表 `change-table.md` 的哈希**，不是母本 `draft_full.md` 的哈希。
> 实测：签署件若绑定母本哈希，`gate_guard.py --gate change-01` 会以 `HASH_MISMATCH` 拒绝；绑定 `change-table.md` 哈希后，签署校验、快照归档、局部改写与零漂移核验全流程成功。

---

## 3. 测试夹具清单 (Fixtures Manifest)

| 文件名 | 类型 | 说明与契约对应 |
|---|---|---|
| `instruction_lightweight.md` | 正向输入 | 样例法域出海模式二评级微调指示（中高→高），用于测试 LIGHTWEIGHT 分级与章节/证据提取 |
| `instruction_major.md` | 正向输入 | 推翻私有IDC可行性并重组报告结构之重大指示，用于测试 MAJOR 分级 |
| `baseline_draft_full.md` | 母本草稿 | 变更前样例法域算力出海调研报告母本全文，包含 5 章 10 节，第 1.2 节带有评级旧文 |
| `clean_corrected_draft.md` | 正向物料 | 仅第 1.2 节声明行替换为「高」，其余非声明章节逐字节一致的合规产物 |
| `undeclared_drift_patch.md` | **阴性对照** | 包含对未声明之第 3.1 节电价篡改的旧料（D-7），断言 `diff-mode` 退出码 1 |
| `valid_change_table.md` | 对照表格 | 实例化变更对照表，包含 `parent_baseline_sha256` 存证与处置矩阵 |
| `approval_signed_positive.md` | 人类门禁 | 包含真实人类签名与工件哈希匹配的放行签署件 |
| `approval_fake_agent_negative.md` | **阴性对照** | 包含 `signed_by: agent:autonomous_worker_07` 的伪造签名件，断言门禁阻断 |
| `audit_workspace/` | 随库 workspace | 含 `draft_full.md`、`change-table.md`（`parent_baseline_sha256` 与快照一致）、`backup/20261123_baseline_rev/draft_full.md`、`change-audit.md`（`undeclared_drift: 0`），供 §2.4.1/§2.4.2 直接执行 |

---

## 4. 与 OpenSpec Scenario 契约对照表

| OpenSpec Requirement / Scenario | 对应判据 / 规格 | 关联测试函数 / CLI 命令 | 验证状态 |
|---|---|---|:---:|
| **Requirement**: Change Matrix Dispatch and Ceremony Triage<br>**Scenario**: Change table records directive and target sections | 方案 §1.2 M8<br>§5.3 对照表定义 | `test_classify_lightweight_rating_instruction`<br>`test_change_table_template_schema_and_placeholders`<br>`python3 scripts/change_dispatch.py --classify` | **100% 覆盖** |
| **Requirement**: Baseline Freeze and Signoff Gate<br>**Scenario**: Modification without change signoff is blocked | **CRITERION M8-1**<br>§1.3 追溯矩阵 | `test_m8_1_blocked_without_approval_and_parent_baseline_unmodified`<br>`test_m8_1_blocked_when_agent_attempts_forged_self_sign`<br>`python3 scripts/gate_guard.py --gate change-01 --check-only` | **100% 覆盖** |
| **Requirement**: Zero-Drift Readback and Snapshot Archival<br>**Scenario**: Diff verification confirms zero undeclared drift | **CRITERION M8-2**<br>**CRITERION M8-3**<br>审查裁决 2: D-7 / D-14 | `test_m8_apply_success_with_human_signoff_and_zero_drift`<br>`test_m8_2_negative_control_undeclared_drift_intercepted`<br>`python3 scripts/verify_readback.py --diff-mode`<br>`python3 scripts/change_dispatch.py --apply` | **100% 覆盖** |

---

## 5. 一键复测执行命令

法官可直接在工作区根目录下执行以下测试命令验证：
```bash
# 1. 运行 pytest 完整测试套件 (12 项用例)
pytest tests/module_tests/test_m8_change_circuit/test_m8_change_circuit.py -v

# 2. 运行集成 Shell 批处理黑箱断言
tests/module_tests/test_m8_change_circuit/run_tests.sh
```

---

## 桩签署件硬拒绝（加固项 G）

门禁 `gate_guard.py` 对含 `stub: true`（或 `stub:true`）的签署件一律硬拒绝：`state=STUB_REJECTED`、`blocked=true`、退出码 1，即使 `artifact_sha256` 完全吻合。G0/G1/G2/G3/change-<id> 五门共用该校验。

- 本目录用于正向放行路径的签署件夹具均为**符合人类签署格式且不含 stub 标记**的测试夹具；该夹具仅用于验证放行路径，**不代表真实人类签署**。
- 真实人类签署件必须由人类本人亲笔填写，不得由任何自动流程代签。
