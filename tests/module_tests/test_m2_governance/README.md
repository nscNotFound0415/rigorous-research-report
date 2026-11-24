# M2 治理协议与载体适配 模块测试与法官验收指南

本目录包含 M2 模块（`governance-ledger`）的独立黑箱验收测试套件与测试夹具。
定义 15 项完整任务清单，断言严格包含 15 项标准化任务（包含 T-P6-04 交付回读与两遍法验证）。

---

## 一、法官执行命令原文 (Judge Execution Commands)

独立验收法官可直接在工作区根目录（`skill-build/`）复制并执行以下命令进行验收：

### 1. 自动化全量测试运行命令
```bash
pytest tests/module_tests/test_m2_governance/test_m2_governance.py -v
```
**期望结果**：15 项测试全部通过（`15 passed in <1s`），退出码为 0。

> **写盘型命令铁律（必读）**：凡命令行会修改文件系统（`--check-ledger` 会回滚 `[x]` 并追加 `violations.log`；`--snapshot` 会创建 `backup/` 归档），**必须先将夹具 `cp -r` 到 `/tmp` 下的临时工作区再执行**，严禁直接对仓库内夹具运行。否则夹具会被消费掉，后续法官复跑与 pytest 基线都会失真。夹具复原方法见本文件末尾「四、夹具被消费后的复原方法」。

---

### 2. 黑箱场景独立验证命令

#### 场景 A：向受控目录写入未在 manifest 登记的文件被拦截拒绝（CRITERION M2-3，只读）
```bash
python3 src/scripts/storage_guard.py --root tests/module_tests/test_m2_governance/fixtures/unregistered_write_workspace --manifest tests/module_tests/test_m2_governance/fixtures/unregistered_write_workspace/manifest.json --probe-unregistered-write
```
- **期望退出码**：`0`（代表拒绝拦截成功）
- **期望 stdout**：
  ```json
  {"rejected": true, "path": "unregistered_leak.txt", "unregistered_count": 1, "reason": "Unregistered file write attempt to 'unregistered_leak.txt' was intercepted and rejected"}
  ```

#### 场景 B：合规受控工作区自检通过（只读；已登记模式文件与 15 项台账）
```bash
python3 src/scripts/storage_guard.py --root tests/module_tests/test_m2_governance/fixtures/valid_workspace --check
```
- **期望退出码**：`0`
- **期望 stdout**：
  ```json
  {"valid": true, "registered": 4, "workspace_files": 3, "unregistered": [], "mismatched": [], "missing_registered": [], "ledger_valid": true, "reverted_tasks": []}
  ```

#### 场景 C：Agent 试图自评勾选 [x] 被检出并强制回滚（台账防篡改，覆盖 T-P3-01 / T-P6-04）
> **会写盘**：先复制到 `/tmp`，可反复执行且不污染仓库夹具。
```bash
rm -rf /tmp/m2_tampered && cp -r tests/module_tests/test_m2_governance/fixtures/tampered_ledger_workspace /tmp/m2_tampered && \
python3 src/scripts/storage_guard.py --root /tmp/m2_tampered --check-ledger
```
- **期望退出码**：`1`（阻断非人类签名修改）
- **期望 stdout**：
  ```json
  {"ledger_valid": false, "reverted_tasks": ["T-P3-01"], "reason": "Unauthorized checkbox [x] detected in task(s) ['T-P3-01']; reverted to [ ] and logged to violations.log"}
  ```
- **副作用位置**：仅 `/tmp/m2_tampered/progress-log.md` 与 `/tmp/m2_tampered/violations.log`；仓库内夹具保持不变。

#### 场景 C2：台账 [x] 行与人类决策日志绑定校验（CRITERION M2-4，只读）
```bash
python3 src/scripts/storage_guard.py --root tests/module_tests/test_m2_governance/fixtures/decision_log_workspace --check-decision-log
```
- **期望退出码**：`0`
- **期望 stdout**：
  ```json
  {"decision_log_valid": true, "violations": []}
  ```
- **阴性对照**：`rm -rf /tmp/m2_dl && cp -r tests/module_tests/test_m2_governance/fixtures/decision_log_workspace /tmp/m2_dl && printf '\n' >> /tmp/m2_dl/brief.md && python3 src/scripts/storage_guard.py --root /tmp/m2_dl --check-decision-log`，期望退出码 `1`，`violations[0].task_id == "T-P1-01"` 且 `reason` 含 `artifact_sha256 mismatch`（并报告台账行号 `line`）。

#### 场景 D：计算文件双哈希（content_sha256 与 nettext_sha256，只读）
```bash
python3 src/scripts/adapter_git_sync.py --hash tests/module_tests/test_m2_governance/fixtures/drift_workspace/old_draft.md
```
- **期望退出码**：`0`
- **期望 stdout**：包含 64 位十六进制 content_sha256 与 nettext_sha256。

#### 场景 E：变更前快照备份归档
> **会写盘**：先复制到 `/tmp`。
```bash
rm -rf /tmp/m2_snapshot && cp -r tests/module_tests/test_m2_governance/fixtures/snapshot_workspace /tmp/m2_snapshot && \
python3 src/scripts/adapter_git_sync.py --root /tmp/m2_snapshot --snapshot baseline_v1
```
- **期望退出码**：`0`
- **期望 stdout**：包含 `snapshot_dir` 与 `git` 优雅降级标识。

#### 场景 F：差异零漂移核验（声明改动 vs 未声明漂移）
```bash
# 1. 声明修改放行（声明变更 C-01）
python3 src/scripts/adapter_git_sync.py --diff-mode --old tests/module_tests/test_m2_governance/fixtures/drift_workspace/old_draft.md --new tests/module_tests/test_m2_governance/fixtures/drift_workspace/clean_diff_draft.md --declared C-01
# 期望退出码: 0, stdout: {"undeclared_drift": 0, "declared": "C-01", "drift_details": []}

# 2. 未声明修改阻断（存在非声明章节篡改）
python3 src/scripts/adapter_git_sync.py --diff-mode --old tests/module_tests/test_m2_governance/fixtures/drift_workspace/old_draft.md --new tests/module_tests/test_m2_governance/fixtures/drift_workspace/dirty_diff_draft.md --declared C-01
# 期望退出码: 1, stdout: {"undeclared_drift": 1, ...}
```

---

## 二、测试夹具说明

| 夹具路径 | 设计意图 | 判定断言 |
|---|---|---|
| `fixtures/valid_workspace/` | 模拟符合规范的工作区，包含 manifest、brief、已审定 G1 门禁件与合规台账 | storage_guard 校验全部通过，退出码 0 |
| `fixtures/tampered_ledger_workspace/` | 模拟 Agent 擅自把 `T-P3-01` 勾选为 `[x]` | 检出非法勾选，回滚为 `[ ]`，写入 `violations.log`，退出码 1 |
| `fixtures/unregistered_write_workspace/` | 模拟向受控目录写入未在 manifest 登记的 `unregistered_leak.txt` | probe 探针成功拦截拒绝，退出码 0 |
| `fixtures/snapshot_workspace/` | 模拟准备进行变更前的母本工作区 | 产生带时间戳与 revision 的归档目录与元数据清单 |
| `fixtures/drift_workspace/` | 模拟变更前后 Markdown 文本比对 | 声明修改区域零漂移通过；非声明修改区域检出漂移并阻断 |
| `fixtures/decision_log_workspace/` | 模拟已勾选 `[x]` 任务且具备 `approved_by: human` 决策记录与哈希绑定 | `--check-decision-log` 通过，退出码 0；篡改产物后退出码 1 并报行号 |

---

## 四、夹具被消费后的复原方法

写盘型命令（场景 C 的 `--check-ledger`、场景 E 的 `--snapshot`）若被误直接跑在仓库夹具上，会使夹具偏离设计语义，进而污染 pytest 基线。按以下方式复原：

1. **`tampered_ledger_workspace/progress-log.md`**：其设计语义是「无签署件的非法 `[x]`」。若被回滚成 `[ ]`，将 `T-P3-01` 行恢复为：
   `| P3 | T-P3-01 | 视角枚举与调研任务分解 | [x] | 存在 | Agent | 自行标记完成（非法） | \`task.json\` (hash) | 无签署件 |`
2. **删除 `tampered_ledger_workspace/violations.log`**（由 `--check-ledger` 追加产生）。
3. **删除 `snapshot_workspace/backup/`** 整个目录（由 `--snapshot` 归档产生）。
4. **`src/templates/progress_log.template.md`** 若被 `change_dispatch.py --propagate` 写入 `[STALE]`，必须移除任务行中的 `[STALE]`，仅保留「§2 状态四分铁律与 STALE 失效语义」协议说明块（该块为有意设计，含 2 处 `[STALE]` 示例）。

复原后运行 `python3 -m pytest tests/module_tests/ -q` 应全绿。

---

## 桩签署件硬拒绝（加固项 G）

门禁 `gate_guard.py` 对含 `stub: true`（或 `stub:true`）的签署件一律硬拒绝：`state=STUB_REJECTED`、`blocked=true`、退出码 1，即使 `artifact_sha256` 完全吻合。G0/G1/G2/G3/change-<id> 五门共用该校验。

- 本目录用于正向放行路径的签署件夹具均为**符合人类签署格式且不含 stub 标记**的测试夹具；该夹具仅用于验证放行路径，**不代表真实人类签署**。
- 真实人类签署件必须由人类本人亲笔填写，不得由任何自动流程代签。
