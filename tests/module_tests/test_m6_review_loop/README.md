# M6 模块对抗复核循环引擎独立验收测试指南 (Reviewer Judge Guide)

本目录为 M6 模块（对抗复核循环引擎，三边界复用）的独立黑箱验收测试套件与测试夹具库。
独立验收法官（Independent Reviewer Judge）可在不查看内部代码实现的前提下，直接通过标准 CLI 命令执行确定性黑箱判定。

> **写盘型命令铁律**：本节所有 M6 命令（`--plan/--target`、`--check-provenance`、`--diff-mode`、`--verify-backup`）均为**只读**，不会修改或消费夹具，可反复执行。
> 若后续新增任何会写盘（生成/回滚/归档）的命令，必须先 `cp -r` 夹具到 `/tmp` 临时工作区再执行，严禁直接对仓库夹具运行。

---

## 1. 独立法官黑箱执行命令契约与期望输出一览

### 1.1 四层回读复验命令 (CRITERION M6-3)

#### 用例 1.1.1: 纠错后目标稿完全满足四层回读 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --plan tests/module_tests/test_m6_review_loop/fixtures/correction_diff.md \
    --target tests/module_tests/test_m6_review_loop/fixtures/draft_full_corrected.md
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "layer1": true,
    "layer2_residuals": 0,
    "layer3_match": true,
    "layer4_hash_match": true,
    "actual_content_sha256": "3eafa980d603e0b79f28e6c43746282eb4f990c2273fa2208bfbf721b46c8215",
    "actual_nettext_sha256": "1892f8bd2b168fc3b90bdae3c3e1defccfd4fa323c251b53b7e28e048e969d78",
    "errors": []
  }
  ```

#### 用例 1.1.2: 目标稿包含 D0 旧句残留 (阴性对照 1 - 旧句零残留失败)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --plan tests/module_tests/test_m6_review_loop/fixtures/correction_diff.md \
    --target tests/module_tests/test_m6_review_loop/fixtures/negative_control_residual_d0.md
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "layer2_residuals": 1,
    "layer4_hash_match": false
  }
  ```

#### 用例 1.1.3: 目标稿遗漏批准的新句 (阴性对照 2 - 新句在位失败)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --plan tests/module_tests/test_m6_review_loop/fixtures/correction_diff.md \
    --target tests/module_tests/test_m6_review_loop/fixtures/negative_control_missing_new.md
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "layer1": false,
    "layer4_hash_match": false
  }
  ```

---

### 1.2 复核调用证明隔离核验 (CRITERION M6-2)

#### 用例 1.2.1: 异族模型通道隔离核验 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --check-provenance tests/module_tests/test_m6_review_loop/fixtures/valid_heterogeneous_provenance.json
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "provenance_valid": true,
    "channel": "异族",
    "isolated": true,
    "errors": []
  }
  ```

#### 用例 1.2.2: 同族零记忆隔离通道核验 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --check-provenance tests/module_tests/test_m6_review_loop/fixtures/valid_isolated_provenance.json
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "provenance_valid": true,
    "channel": "同族-零记忆隔离",
    "isolated": true,
    "errors": []
  }
  ```

#### 用例 1.2.3: 相同 session ID 伪造隔离 (阴性对照 1 - 会话互斥失败)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --check-provenance tests/module_tests/test_m6_review_loop/fixtures/unisolated_provenance_same_session.json
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "provenance_valid": false,
    "isolated": false
  }
  ```

#### 用例 1.2.4: 同族模型但 context_reset 为 false (阴性对照 2 - 上下文未重置)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --check-provenance tests/module_tests/test_m6_review_loop/fixtures/unisolated_provenance_no_reset.json
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "provenance_valid": false,
    "isolated": false
  }
  ```

#### 用例 1.2.5: 同厂商模型冒充异族通道 (阴性对照 3 - 厂商前缀相同)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --check-provenance tests/module_tests/test_m6_review_loop/fixtures/unisolated_provenance_same_vendor.json
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "provenance_valid": false,
    "isolated": false
  }
  ```

---

### 1.3 零漂移比对命令 (CRITERION M8-2)

#### 用例 1.3.1: 仅声明区域发生修改 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --diff-mode \
    --old tests/module_tests/test_m6_review_loop/fixtures/injected_defects_draft.md \
    --new tests/module_tests/test_m6_review_loop/fixtures/patch_only_c01.md \
    --declared "C-01"
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

#### 用例 1.3.2: 非声明区域发生篡改 (阴性对照 - 漂移阻断)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --diff-mode \
    --old tests/module_tests/test_m6_review_loop/fixtures/injected_defects_draft.md \
    --new tests/module_tests/test_m6_review_loop/fixtures/patch_undeclared_drift.md \
    --declared "C-01"
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "undeclared_drift": 38,
    "declared_id": "C-01"
  }
  ```

---

### 1.4 变更备份快照核验 (CRITERION M8-3)

#### 用例 1.4.1: 备份目录存在且哈希吻合 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --verify-backup tests/module_tests/test_m6_review_loop/fixtures/valid_backup \
    --change-table tests/module_tests/test_m6_review_loop/fixtures/change_table.md
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "backup_present": true,
    "backup_valid": true,
    "backup_files": 1,
    "hash_matched": true
  }
  ```

#### 用例 1.4.2: 备份快照缺失或空目录 (阴性对照 - 备份损坏)
- **执行命令**:
  ```bash
  python3 src/scripts/verify_readback.py \
    --verify-backup tests/module_tests/test_m6_review_loop/fixtures/corrupted_backup \
    --change-table tests/module_tests/test_m6_review_loop/fixtures/change_table.md
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 关键字段**:
  ```json
  {
    "backup_present": false,
    "backup_valid": false,
    "backup_files": 0,
    "hash_matched": false
  }
  ```

---

### 1.5 注入缺陷捕获与分级准确率评定 (CRITERION M6-1 / JUDGE M6-1)
- **判定输入**: `fixtures/injected_defects_draft.md` 与 `fixtures/boundary3_review_report.md`
- **D0 确定性通路口径（三条，全部机器可判定，每条必带 `route` 字段）**:
  1. `route: ARITH` —— 纯代码算术复算，须附复算命令与输出行；
  2. `route: QUOTE_MISMATCH` —— 一手原文比对不符，须附原文 chunk ID 与不一致片段（缺失记 `NOT_FOUND`）；
  3. `route: LEXICAL_RULE` —— 确定性词法扫描器命中，须附扫描器命令与输出行（覆盖元叙述、悬空引用、图表断号等）。
- **注入缺陷与捕获比对**:
  1. 算术错误 (800+500=1300 != 1200) -> 报告精准列入 `[D0-01]`, 级别 D0, `route: ARITH`（附复算命令 `python3 -c "print(f'800 + 500 = {800+500}; expected 1200; match={800+500==1200}')"` 与输出行 `800 + 500 = 1300; expected 1200; match=False`）
  2. 二手自媒体转述电力成本下调 -> 报告精准列入 `[D1-01]`, 级别 D1，处置选项固定为「补证 ｜ 降级为推测/待证实」，提交 G2 人类裁决
  3. 大模型违规自述元叙述 ("作为一名专业的大模型 AI 语言助手...") -> 报告精准列入 `[D0-02]`, 级别 D0, `route: LEXICAL_RULE`（附扫描器命令 `grep -n "作为一名专业的大模型 AI 语言助手" tests/module_tests/test_m6_review_loop/fixtures/injected_defects_draft.md` 与输出行 `15:作为一名专业的大模型 AI 语言助手，...`）
- **期望评判输出**:
  ```json
  {
    "adjudication": "PASS",
    "captured_ratio": 1.0,
    "grade_accuracy": 1.0,
    "missed_defects": []
  }
  ```

---

## 2. 与 OpenSpec Capability Scenario 对照表

| OpenSpec Requirement / Scenario | 方案判据编号 | 测试用例函数 | 对应测试夹具 / CLI 校验 | 状态 |
|---|---|---|---|:---:|
| **Reviewer Isolation and Machine-Readable Provenance**<br>Scenario: Non-homologous model review passes isolation check | CRITERION M6-2 | `test_m6_2_provenance_isolation_checks` | `valid_heterogeneous_provenance.json`<br>`verify_readback.py --check-provenance` | **PASS (0)** |
| **Reviewer Isolation and Machine-Readable Provenance**<br>Scenario: Unverified isolation or missing provenance fails gate | CRITERION M6-2 | `test_m6_2_provenance_isolation_checks` | `unisolated_provenance_same_session.json`<br>`unisolated_provenance_no_reset.json`<br>`unisolated_provenance_same_vendor.json` | **PASS (1 阻断)** |
| **Four-Tier Defect Triage (D0-D3)**<br>Scenario: Mandatory zero D0 defects for boundary exit | CRITERION M6-1 / JUDGE | `test_m6_1_judge_defect_injection_and_triage_accuracy`<br>`test_review_report_template_schema_and_four_tier_triage` | `boundary3_review_report.md`<br>D0=2 强阻断，D0=0 放行 | **PASS** |
| **Four-Layer Readback Verification**<br>Scenario: Clean patch replacement satisfies all four layers | CRITERION M6-3 | `test_m6_3_four_layer_readback_verification` | `correction_diff.md`<br>`draft_full_corrected.md`<br>`verify_readback.py --plan --target` | **PASS (0)** |
| **Four-Layer Readback Verification**<br>Negative Control: D0 old sentence residual fails Layer 2 | CRITERION M6-3 | `test_m6_3_four_layer_readback_verification` | `negative_control_residual_d0.md` | **PASS (1 阻断)** |
| **Four-Layer Readback Verification**<br>Negative Control: Missing new sentence fails Layer 1 | CRITERION M6-3 | `test_m6_3_four_layer_readback_verification` | `negative_control_missing_new.md` | **PASS (1 阻断)** |
| **Zero Undeclared Drift (M8 Circuit)**<br>Scenario: Clean diff within declared ID | CRITERION M8-2 | `test_diff_mode_zero_drift` | `patch_only_c01.md`<br>`verify_readback.py --diff-mode` | **PASS (0)** |
| **Zero Undeclared Drift (M8 Circuit)**<br>Negative Control: Drift outside declared ID fails | CRITERION M8-2 | `test_diff_mode_zero_drift` | `patch_undeclared_drift.md` | **PASS (1 阻断)** |
| **Backup Snapshot Verification (M8 Circuit)**<br>Scenario: Snapshot matches parent baseline hash | CRITERION M8-3 | `test_verify_backup_snapshot` | `valid_backup`<br>`change_table.md` | **PASS (0)** |
| **Backup Snapshot Verification (M8 Circuit)**<br>Negative Control: Corrupted or missing backup fails | CRITERION M8-3 | `test_verify_backup_snapshot` | `corrupted_backup` | **PASS (1 阻断)** |

---

## 3. 本地自测自动化运行说明

在项目根目录下，执行以下测试脚本即可运行完整 10 项自动化测试并复验 direct CLI：
```bash
bash tests/module_tests/test_m6_review_loop/run_tests.sh
```
或者单独调用 pytest：
```bash
pytest tests/module_tests/test_m6_review_loop/test_m6_review_loop.py -v
```

---

## 桩签署件硬拒绝（加固项 G）

门禁 `gate_guard.py` 对含 `stub: true`（或 `stub:true`）的签署件一律硬拒绝：`state=STUB_REJECTED`、`blocked=true`、退出码 1，即使 `artifact_sha256` 完全吻合。G0/G1/G2/G3/change-<id> 五门共用该校验。

- 本目录用于正向放行路径的签署件夹具均为**符合人类签署格式且不含 stub 标记**的测试夹具；该夹具仅用于验证放行路径，**不代表真实人类签署**。
- 真实人类签署件必须由人类本人亲笔填写，不得由任何自动流程代签。
