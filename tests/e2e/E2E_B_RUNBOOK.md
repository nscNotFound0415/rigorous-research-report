# E2E-b 真人实操跑一次 · 可执行操作手册 (Human-in-the-Loop Runbook)

> 本文件是 **E2E-b 轨道的可执行骨架**，不是已完成的测试记录。
> 本轮自动化只能完成 E2E-a（门禁桩）与 E2E-c（离线夹具）；E2E-b 必须由一名真实人类操作者完整跑一次。
> **任何 Agent 不得代签、不得预填本手册涉及的签署件、不得把 E2E-a 的 `stub: true` 桩件复制进本工作区。**

---

## 0. 适用对象、目标与硬性禁止

- **实操课题**：《中国算力与大模型企业出海样例法域建设云节点的可行性、合规壁垒与全生命周期成本效益深度调研报告（2026 年）》
- **操作者角色**：人类项目总监 / 独立评测法官（Human Decision Maker / Judge）。必须为自然人本人。
- **环境**：Linux/macOS，`python3`（3.10+），`soffice` 可用；工作区为本仓库根目录下的脚本与夹具。
- **硬性禁止**：
  1. Agent 或任何自动化工具不得填写 `decision`、`signed_by`、`signature`、`artifact_sha256` 等署名/确认字段。
  2. 不得使用 `tests/e2e/gates/*.template.md` 之外的任何“预填签署件”。
  3. 不得把含 `stub: true` 或「本件为演练桩，非真实人类签署」的文件放进本实操工作区；此类文件只属于 E2E-a。
  4. 不得跳过门禁先写后续阶段文件；不得让 Agent 代勾 `progress-log.md` 的 `[x]`。

### 0.1 只能由真人完成的 E2E 判据（本手册的存在理由）

| 判据 | 真人必须完成的动作 | 为什么机器不能替代 |
|---|---|---|
| **E2E-01** | 审阅 `brief.md` 全部 11 节/八项澄清/宪法五原则/REQ-ID，亲笔签署 `gates/G0-approval.md` | G0 是项目基准的唯一人类放行点；Agent 自签被 `gate_guard.py` 以 `AGENT_SIGNATURE_PROHIBITED` 阻断 |
| **E2E-02** | 在 `progress-log.md` 中对已核实任务写 `[x]`，并在 `decision-log.md` 写 `approved_by: human` 与正确 `artifact_sha256` | 勾选权排他归人类；`storage_guard.py` 会回滚未经人类签署授权的 `[x]` |
| **E2E-04** | 审阅章间论证拓扑与每章 `evidence_ref`，确认 PENDING 清零后签署 `gates/G1-approval.md` | 大纲取舍属人类判断，G1 必须真人放行 |
| **E2E-06** | 对复核报告中的 D1（证据不足）/D2（信源冲突）做保留、降级、补证或删除的定性裁决，并签署 `gates/G2-approval.md` | 宪法「定性裁决权归人类」；机器只能整理对照稿 |
| **E2E-07** | 打开 `delivery/output.docx` 与 `output.pdf` 目检版式、断号、溢出，确认三差集为空后签署 `gates/G3-approval.md` | 版式质量与对外交付许可属人类判断 |
| **E2E-08** | 审阅《指示处置对照表》、母本备份与零漂移声明，签署 `gates/change-01-approval.md` | 变更范围授权必须由真人行使 |
| **E2E-b** | 记录每一步的人类审阅人时与机器运行耗时，填写第 8 节记录表 | 无人值守环境无法采集真实人时与人类决策过程 |

---

## 1. 准备一个全新的实操工作区

不要复用 `e2e_run/`（该目录由其他演练占用），也不要在 `tests/e2e_fixtures/` 原地签署。请新建独立目录：

```bash
export WS="$HOME/e2e_b_workspace_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WS"/{gates,delivery,backup,fact-store,review-reports}
cd "$WS"

# 复制离线夹具作为实操输入（只读来源，签署与改写都发生在新工作区）
cp /home/ubuntu/workspace/词元出海汇报_接手项目_2026-11-18/skill-build/tests/e2e_fixtures/{brief.md,task.json,datatable.csv,evidence-index.md,outline.md,draft_full.md,correction-diff.md,draft_corrected.md,change-table.md,progress-log.md,baseline_draft_for_change.md,patched_draft_c01.md} .
cp -r /home/ubuntu/workspace/词元出海汇报_接手项目_2026-11-18/skill-build/tests/e2e_fixtures/backup/* backup/
cp /home/ubuntu/workspace/词元出海汇报_接手项目_2026-11-18/skill-build/src/schemas/task.schema.json .
```

脚本统一以仓库根目录为基准调用；若不在仓库根目录，请用绝对路径：

```bash
export REPO="/home/ubuntu/workspace/词元出海汇报_接手项目_2026-11-18/skill-build"
alias s='python3 "$REPO/src/scripts"'
```

> 注意：`gate_guard.py` 的默认路径是 `<root>/brief.md`、`<root>/outline.md`、`<root>/correction-diff.md`、`<root>/delivery/output.docx`、`<root>/change-table.md` 与 `<root>/gates/*.md`。因此以下命令都在 `$WS` 内执行，并使用 `--root "$WS"`（或 `cd "$WS"` 后省略）。

---

## 2. G0：审阅简报并真人签署（E2E-01）

1. 打开 `brief.md`，逐项核对：
   - 2.1–2.8 八项澄清是否完整；
   - 2.9 是否列全 `REQ-01..REQ-03`；
   - 第 3 节是否逐字包含宪法五原则；
   - 2.11 继承声明每条 `human_decision` 是否为 `CONFIRMED` 或 `REVISED`。
2. 运行简报自验（期望 `valid:true`、退出 0）：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --verify-brief "$WS/brief.md"
```

3. 计算 `brief.md` 的二进制 SHA-256：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --compute-hash "$WS/brief.md"
```

4. 复制模板并**由您本人**填写：

```bash
cp "$REPO/tests/e2e/gates/G0-approval.template.md" "$WS/gates/G0-approval.md"
```

填写要求（缺一不可，且不得含 `agent/ai/bot/自动/模型` 等机器词）：

```yaml
---
gate: G0
decision: APPROVED
signed_by: <您的真实姓名或职工代号，如 lead_evaluator_zhang>
signed_at: <当前 ISO8601 时间，如 2026-11-23T14:00:00Z>
artifact_sha256: <第 3 步得到的 64 位哈希>
signature: <您本人当场写下的确认口令，如 CONFIRMED_PROCEED_G0>
approver_role: human_decision_maker
comments: <可选：您的审阅意见>
---
```

5. 验证放行（期望 `state:APPROVED`、退出 0）：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --gate G0 --check-only --root "$WS"
```

6. 在 `progress-log.md` 中把 `T-P1-01` 的 `[ ]` 改为 `[x]`（这是您的授权动作）。为确保 `storage_guard` 能识别授权，T-P1-01 行已映射到 G0；其他没有专属门禁的任务，请在该行最后一列显式写入 `gates/G0-approval.md` 之类的已签件路径，否则会被判为未授权并回滚。
7. 在 `decision-log.md` 追加人类决策记录（`storage_guard --check-decision-log` 会逐行校验哈希）：

```markdown
- task_id: T-P1-01
  approved_by: human
  artifact_sha256: <brief.md 的 64 位 SHA-256>
```

> 若您在此步发现 brief 有误，请把 `decision` 改为 `CHANGES_REQUESTED` 并停止后续阶段，不要先写后续文件。

---

## 3. M3：调研拆分与 REQ-ID 覆盖（E2E-01 的机器部分）

1. 审阅 `task.json`：DAG 依赖、每任务 `guidelines` 是否含出处/基准日/口径三要素。
2. 运行：

```bash
python3 "$REPO/src/scripts/task_schema_check.py" "$WS/task.json" --schema "$REPO/src/schemas/task.schema.json"
python3 "$REPO/src/scripts/task_schema_check.py" "$WS/task.json" --req-index "$WS/brief.md" --coverage
```

期望：`errors:[]`、`guidelines_validated:true`、`uncovered_req_ids:[]`、`coverage_ratio:1.0`。
3. 由您决定是否勾选 `T-P3-01`；如需勾选，请按第 2 节第 6 条在行末写明所依据的已签署件，并在 `decision-log.md` 记录。

---

## 4. M4：数据底表与证据锚定（E2E-03）

1. 打开 `datatable.csv` 与 `evidence-index.md`，人工核对：
   - 口径 A（自建）/B（租赁）/C（市场）是否分栏；
   - 每个 `estimated` 单元格是否有 `assumption_tag`；
   - 每个数值是否有取价日与一手信源（`source_url` 与 `content_sha256`）。
2. 运行三项机器检查：

```bash
python3 "$REPO/src/scripts/audit_calc.py" "$WS/datatable.csv"
python3 "$REPO/src/scripts/audit_calc.py" "$WS/datatable.csv" --strict-tolerance
python3 "$REPO/src/scripts/audit_calc.py" "$WS/datatable.csv" --evidence-index "$WS/evidence-index.md"
```

期望：`checked_cells=4`、`mismatches:[]`、`cross_scope_violations:[]`、`unlinked_cells:[]`、`missing_assumption_tags:[]`。
3. 抽验一手快照哈希（应全等）：

```bash
sha256sum "$WS"/../.../raw_evidence/*   # 或对 tests/e2e_fixtures/raw_evidence/ 运行并比对 evidence-index.md
```

4. 由您决定是否勾选 `T-P4-01/T-P4-02`；勾选须遵守第 2 节第 6 条与 `decision-log.md` 规则。

---

## 5. G1：大纲锁定并真人签署（E2E-04）

1. 打开 `outline.md`，核对：
   - 章节数 ≥1，且每章至少 1 条 `evidence_ref`；
   - Join 2 前「待补数据（PENDING）」为 0；
   - 章节论证目的与写作契约是否成立。
2. 运行：

```bash
python3 "$REPO/src/scripts/outline_check.py" "$WS/outline.md" --check-sections
python3 "$REPO/src/scripts/outline_check.py" "$WS/outline.md" --evidence-index "$WS/evidence-index.md" --require-resolved
```

期望：`invalid_sections:[]`、`chapter_count:3`、`pending_count:0`、`dangling_refs:[]`、`missing_refs:[]`、`refs_total:6`。
3. 计算 `outline.md` 哈希，复制模板并由您本人签署：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --compute-hash "$WS/outline.md"
cp "$REPO/tests/e2e/gates/G1-approval.template.md" "$WS/gates/G1-approval.md"
```

字段格式同 G0，`gate: G1`，`artifact_sha256` 绑定 `outline.md`。
4. 验证并勾选 `T-G1-01`：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --gate G1 --check-only --root "$WS"
```

---

## 6. G2：对抗复核、定性裁决与真人签署（E2E-06）

1. 审阅 `review-reports/`（若本轮未生成，请先让流水线产出）与 `correction-diff.md`。
2. 核验复核隔离证明：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --check-provenance "$WS/review-reports/boundary3_provenance.json"
```

期望：`provenance_valid:true`、`isolated:true`。
3. 四层回读：

```bash
python3 "$REPO/src/scripts/verify_readback.py" --plan "$WS/correction-diff.md" --target "$WS/draft_full.md"
```

期望：`layer1:true`、`layer2_residuals:0`、`layer3:true`、`layer4:true`。
4. **由您本人**在 `correction-diff.md` 的「人审裁决」列对 D1/D2 条目写明：保留 / 降级为假设 / 补证 / 删除。机器不得替您选择。
5. 计算 `correction-diff.md` 哈希，复制模板并由您本人签署：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --compute-hash "$WS/correction-diff.md"
cp "$REPO/tests/e2e/gates/G2-approval.template.md" "$WS/gates/G2-approval.md"
```

字段格式同 G0，`gate: G2`，`artifact_sha256` 绑定 `correction-diff.md`。
6. 验证并勾选 `T-G2-01`：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --gate G2 --check-only --root "$WS"
```

---

## 7. M7：合稿、构建、交付回读与 G3 真人签署（E2E-05/06/07）

1. 文本卫生与白名单：

```bash
python3 "$REPO/src/scripts/audit_text_hygiene.py" "$WS/draft_full.md" --rules "$REPO/src/templates/forbidden_terms.json"
```

期望 `violations:[]`；同时确认 9 类严谨性声明仍在原文中（E2E-06）。
2. 图表与引用：

```bash
python3 "$REPO/src/scripts/citation_check.py" "$WS/draft_full.md" --evidence-index "$WS/evidence-index.md"
```

期望 `dangling_refs:[]`、`unnumbered_figs:[]`、`dangling_tables:[]`。
3. 构建 Word / PDF 并做两遍法：

```bash
python3 "$REPO/src/scripts/build_docx.py" "$WS/draft_full.md" --out "$WS/delivery/output.docx" --manifest "$WS/delivery/build_manifest.json"
python3 "$REPO/src/scripts/build_pdf.py" "$WS/delivery/output.docx" --out "$WS/delivery/output.pdf"
python3 "$REPO/src/scripts/toc_two_pass.py" "$WS/delivery/output.docx" "$WS/delivery/output.pdf"
```

> 若 `build_pdf` 报 `soffice conversion failed ... Write Code:16`，通常是 LibreOffice 用户配置被其他进程锁定；请关闭其他 LibreOffice 进程，或为本次转换指定独立 `HOME`（例如 `HOME="$WS/lo_home"`）。
4. 交付回读：

```bash
python3 "$REPO/src/scripts/delivery_readback.py" --docx "$WS/delivery/output.docx" --pdf "$WS/delivery/output.pdf" --source "$WS/draft_full.md" --out "$WS/delivery/delivery_readback.json"
```

期望：`toc_minus_headings:[]`、`headings_minus_toc:[]`、`page_mismatch:[]`，退出 0。
5. **由您本人打开** Word 与 PDF，目检目录页码、图表断号、排版溢出与中文字体。此步骤无法自动化。
6. 计算最终 docx 哈希，复制模板并由您本人签署：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --compute-hash "$WS/delivery/output.docx"
cp "$REPO/tests/e2e/gates/G3-approval.template.md" "$WS/gates/G3-approval.md"
```

字段格式同 G0，`gate: G3`，`artifact_sha256` 绑定 `delivery/output.docx`。
7. 验证并勾选 `T-P6-04`（已映射 G3）与 `T-G3-01`：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --gate G3 --check-only --root "$WS"
```

---

## 8. M8：中途变更、零漂移与 change-01 真人签署（E2E-08）

1. 冻结母本并备份：

```bash
cp "$WS/baseline_draft_for_change.md" "$WS/backup/sample_cloud_report_snapshot.md"
```

2. 审阅（或编制）`change-table.md`：受影响章节、母本哈希、备份路径、零漂移声明。
3. 计算 `change-table.md` 哈希；复制模板并由您本人签署：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --compute-hash "$WS/change-table.md"
cp "$REPO/tests/e2e/gates/change-01-approval.template.md" "$WS/gates/change-01-approval.md"
```

字段：`gate: change-01`、`artifact_sha256` 绑定 `change-table.md`、另填 `parent_baseline_sha256`（变更前母本哈希）。
4. 验证放行：

```bash
python3 "$REPO/src/scripts/gate_guard.py" --gate change-01 --check-only --root "$WS"
```

5. 局部改写后执行零漂移与备份核验：

```bash
python3 "$REPO/src/scripts/verify_readback.py" --diff-mode --old "$WS/backup/sample_cloud_report_snapshot.md" --new "$WS/draft_full.md" --declared C-01
python3 "$REPO/src/scripts/verify_readback.py" --verify-backup "$WS/backup" --change-table "$WS/change-table.md"
```

期望：`undeclared_drift:0`；`backup_valid:true`、`hash_matched:true`。
6. 勾选 `T-M8-01`（已映射至 `gates/change-*-approval.md`）。

---

## 9. 台账收口与人工核验

```bash
python3 "$REPO/src/scripts/storage_guard.py" --root "$WS" --ledger "$WS/progress-log.md" --check-ledger
python3 "$REPO/src/scripts/storage_guard.py" --root "$WS" --ledger "$WS/progress-log.md" --decision-log "$WS/decision-log.md" --check-decision-log
```

期望均为退出 0。若 `--check-ledger` 回滚了某行，说明该行没有可识别的已签门禁件或签署被判定为机器签名；请回到对应门禁步骤，不要绕过。

---

## 10. E2E-b 记录表（由操作者本人填写，Agent 不得预填）

| 项目 | 记录 |
|---|---|
| 操作者姓名/代号 | |
| 开始 / 结束时间（本地时区） | |
| 人类审阅总人时（分钟） | |
| 机器运行总耗时（秒，可用 `time` 包裹命令） | |
| G0 签署时间与意见 | |
| G1 签署时间与意见 | |
| G2 定性裁决条目（D1/D2）与结论 | |
| G3 目检发现的问题（若有） | |
| change-01 变更范围与批准意见 | |
| 与 E2E-a/E2E-c 期望值不一致之处 | |

完成后，请将本表与五份签署件（`gates/G0-approval.md`、`G1-approval.md`、`G2-approval.md`、`G3-approval.md`、`change-01-approval.md`）一并归档，作为 E2E-b 的唯一有效证据。**没有真人签署件，E2E-b 不得判定通过。**

---

## 11. 空白模板清单（未预填任何真人署名）

- `tests/e2e/gates/G0-approval.template.md` — 绑定 `brief.md`
- `tests/e2e/gates/G1-approval.template.md` — 绑定 `outline.md`
- `tests/e2e/gates/G2-approval.template.md` — 绑定 `correction-diff.md`
- `tests/e2e/gates/G3-approval.template.md` — 绑定 `delivery/output.docx`
- `tests/e2e/gates/change-01-approval.template.md` — 绑定 `change-table.md`

模板中的 `<MUST_BE_FILLED_BY_HUMAN: ...>` 必须由您本人替换；任何保留占位符或含 `stub: true` 的签署件都会被 `gate_guard.py` 拒绝。
