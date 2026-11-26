# 变更管理与动态维护回路协议手册 (Change Circuit & Maintenance Protocol)

本协议定义研究报告全生命周期中由外部指示、新事实输入或重大口径变动所引发的维护回路规程。涵盖外部输入三类分流响应、变更分级机制、母本冻结原则、签署件防伪、零漂移回读核验与载体抽象规范。

---

## 1. 架构定位与核心原则 (Architecture & Core Principles)

维护回路（M Loop: Change Circuit）是流水线动态适应外部变化的唯一受控接口。任何非初次生成的母本修改，均必须 [SHALL] 纳入本回路纳管。

```text
 ┌────────────────┐
 │ 外部输入 / 指示 │
 └───────┬────────┘
         │
         ▼
 ┌────────────────────────────────────────────────────────┐
 │ 1. 输入分类与分流 (Triage: new_evidence / directive / shift)│
 └───────┬────────────────────────────────────────────────┘
         │
         ▼
 ┌────────────────────────────────────────────────────────┐
 │ 2. 变更分级判定 (Ceremony: LIGHTWEIGHT vs MAJOR)          │
 └───────┬────────────────────────────────────────────────┘
         │
         ▼
 ┌────────────────────────────────────────────────────────┐
 │ 3. 母本冻结与归档 (Baseline Freeze: parent_baseline_sha256)│
 └───────┬────────────────────────────────────────────────┘
         │
         ▼
 ┌────────────────────────────────────────────────────────┐
 │ 4. 门禁签署审批 (Human Signoff: change-<id>-approval.md) │
 └───────┬────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────────┐
         ▼ [未批准: exit 1, 严禁触碰母本]             ▼ [人类批准: 放行]
 ┌──────────────────┐                     ┌──────────────────────────────┐
 │ 阻断写入保持原样 │                     │ 5. 受控局部改写实施          │
 └──────────────────┘                     └──────────────┬───────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │ 6. 零漂移四层回读复验        │
                                          │    (verify_readback diff-mode)│
                                          └──────────────┬───────────────┘
                                                         │
                                  ┌──────────────────────┴──────────────────────┐
                                  ▼ [undeclared_drift > 0]                      ▼ [undeclared_drift == 0]
                         ┌──────────────────┐                          ┌──────────────────────────┐
                         │ 阻断并告警回滚   │                          │ 归档快照并更新留痕台账   │
                         └──────────────────┘                          └──────────────────────────┘
```

### 1.1 载体抽象与单源母本 (Storage Abstraction)
1. **本地 Git 优先原则**：系统必须 [SHALL] 将本地 Git 工作区（Markdown 文件系统）视为全局唯一权威事实母本。
2. **外设只读镜像原则**：外部在线协同平台（如云文档平台）在读取端仅作为只读快照拉取源；在写入端复杂成品一律以离线编译产出的标准 Word (`.docx`) / PDF 文件通过整文件附件形式覆盖同步，严禁 [SHALL NOT] 依赖在线富文本 API 逆向改写本地母本。

---

## 2. 外部输入分类与分流响应路径 (Three-Way External Input Triage)

系统接收到外部输入时，必须 [SHALL] 首先调用 `scripts/change_dispatch.py --classify` 按以下三类通道分流处置：

### 2.1 类型 A：新的背景/事实信息 (new_evidence)
- **判定标准**：外部补充了行业一手政策、财报数据、企业访谈等新信源，但并未直接推翻现有逻辑结构。
- **响应路径**：
  1. 系统必须 [SHALL] 提取新信源要素并归档至 `fact-store/` 与 `evidence-index.md`。
  2. **待核事项只标注不改数原则**：在新信源尚未完成数据底表交叉复算与人类确认前，研报正文与大纲对应位置必须 [SHALL] 显式标注 `PENDING` 待核标记，严禁 [SHALL NOT] 直接修改既有定稿数值或结论。
  3. 当且仅当人类在后续审查中签署放行后，方可启动数据底表重新核算（`audit_calc.py`）。

### 2.2 类型 B：领导与业务微调指示 (directive / scope_tweak)
- **判定标准**：针对特定段落、章节措辞、图表排版或局部需求评级的微调（例如：“将目标市场某模式的市场需求评级由中高调整为高”）。
- **响应路径**：
  1. 系统必须 [SHALL] 生成《变更管理与指示处置对照表》（`change-table.md`），登记指示原文、涉及定位、现状表述与拟修订方案。
  2. 系统必须 [SHALL] 自动检索受影响图表与引用证据（如 `E-01`, `S-05`），生成条目 ID（如 `C-01`）。
  3. 进入微调轻流程（LIGHTWEIGHT）。

### 2.3 类型 C：既有事实被推翻或架构口径颠覆 (architecture_shift / fact_refutation)
- **判定标准**：底层关键核算数据被证伪、法律合规政策发生实质性逆转、或核心报告框架被要求重组。
- **响应路径**：
  1. 系统必须 [SHALL] 在事实库中立刻将对应事实项标记为 `REFUTED`，在报告草稿中对受波及段落标红警示。
  2. **定性裁决归人类原则**：对于推翻事实后的业务走向（是完全删除该业务板块，还是降级为审慎观察或补充附录），必须 [SHALL] 由人类操作者在审批签署件中裁定，严禁 [SHALL NOT] 由 Agent 擅自替人类作出战略定性决策。
  3. 系统建议升轨至重大变更流程（MAJOR）。

### 2.4 失效传播规则与影响矩阵 (Invalidation Propagation Rules)
当外部新信息输入（无论是 brief 变更、一手新事实、领导文本指示还是口径颠覆）到达时，系统必须 [SHALL] 依据下表确定失效范围，并在治理台账中将受影响的任务行与门禁行标记为 `STALE`：

| 输入类型 | 判定 | 失效范围 | 必须执行的动作 | 门禁后果 |
|---|---|---|---|---|
| brief 字段变更（背景/读者/格式/权威载体） | 母本变更 | G0 失效；M2–M7 全部标 STALE | 回到 M1 重签 G0 | G0 之前不得继续下游 |
| 新一手事实（新增或修正 fact-store 条目） | 影响数值 | 受影响底表行标 STALE；M5b 与 G1 失效；M7 失效 | 局部重跑 M4 → 边界 1 复核 → 重签 G1 | 边界 1 与 G1 须重出 |
| 领导指示（不改数） | 文本层 | 命中章节块 | 生成对照表 → 人审 → 局部写入 → 边界 3 局部复核 | 边界 3 须重过 |
| 口径重构（结构/结论级别） | 架构层 | 全部 | 建 OpenSpec 变更提案（可选增强层） | 全部门禁重走 |

**STALE 标记与勾选权铁律 [CRITERION M8-4]**：
1. STALE 标记写入治理台账 `progress-log.md` 对应任务行的「四分状态」列（格式为 `已审定 [STALE]` 或 `存在 [STALE]`）。
2. **复选框绝对锁定**：Agent 严禁 [SHALL NOT] 自行复位或改写台账复选框 `[x]`，`[x]` 的数量必须保持不变，清除 STALE 标记与复选框变更的排他权限严格属于人类。
3. **只标记不改写原则**：调用 `change_dispatch.py --propagate` 模式仅向台账注入 STALE 标记并输出失效清单，严禁自动执行母本文件的改写。母本改写必须且仅能由 `--apply` 模式在人类签署 `gates/change-<id>-approval.md` 后方可执行。

---

## 3. 变更分级与流程升轨机制 (Ceremony Triage & Escalation)

变更处置严格区分轻量微调与重大变更，避免过度流程化或失控裸奔：

### 3.1 LIGHTWEIGHT 微调流程（默认基线通道）
- **适用场景**：词句润色、图表修补、独立段落评级调整、局部数值勘误。
- **执行规程**：
  1. 以 `src/templates/change_table.template.md` 实例化生成 `change-table.md`。
  2. 生成审批放行申请 `gates/change-<id>-request.md`。
  3. 待人类签署 `gates/change-<id>-approval.md` 后，执行局部改写与四层回读复验。
  4. 无需生成整套 OpenSpec 规范文件。

### 3.2 MAJOR 重大变更提案（可选增强层 ENHANCED_OPENSPEC）
- **适用场景**：全局口径重构、整章结构重组、分析模型替换、结论颠覆性变更。
- **执行规程**：
  1. 默认基线仍必须 [SHALL] 维持 `change-table.md` 与人类门禁签署。
  2. 仅当 [ONLY WHEN] 用户或调度器显式声明 `--ceremony MAJOR` 或开启 `ENHANCED_OPENSPEC` 时，方可 [THEN] 挂载 `changes/<change-id>/`（包含 `proposal.md`、`design.md`、`specs/` 与 `tasks.md`）。
  3. 重大变更通过后，主规范同步并归档入 `openspec/changes/archive/`。
  4. **工具限制（实测，OpenSpec v1.14.1）**：归档命令**忽略增量中的 `## Purpose`**（主规格 Purpose 不会被 delta 覆盖，须人工最小修正并披露）；**不支持 Scenario 级改名**——把改名后的 Scenario 直接放进 `## MODIFIED Requirements` 会报 `omits scenario(s) the current spec still has`，等价做法是三段式：`## RENAMED Requirements`（原名 → 临时名 `(Superseded)`）→ `## REMOVED Requirements`（删临时名）→ `## ADDED Requirements`（以原名重加整块，WHEN/THEN/AND 逐字不变）。副作用：被重命名的 Requirement 在主规格中会移到末尾（纯顺序变化）。

---

## 4. 母本冻结与只读快照原则 (Baseline Freeze & Snapshot Axiom)

1. **绝对禁止在线推倒重来**：在未取得门禁放行前，系统严禁 [SHALL NOT] 对既有正式母本（如 `draft_full.md`、`outline.md`、`datatable.csv`）执行任何破坏性写入或替换。
2. **基线哈希存证**：创建变更任务时，必须 [SHALL] 计算并记录变更前母本全文的 `content_sha256` 作为 `parent_baseline_sha256`。
3. **只读快照归档**：在获准改写前，编排脚本必须 [SHALL] 先调用 `adapter_git_sync.py --snapshot change-<id> --target <file>`，将母本完整无损地归档至 `backup/<timestamp>_rev_<hash>/` 目录。
4. **快照哈希一致性**：归档快照的哈希值必须 [SHALL] 与 `change-table.md` 中的 `parent_baseline_sha256` 100% 逐字节吻合。

---

## 5. 门禁审批与签署件防伪规范 (Signoff Gate & Anti-forgery Protocol)

变更实施严格受制于专属变更门禁 `change-<id>`：

1. **凭单命名规范**：
   - 申请件：`gates/change-<id>-request.md`
   - 签署件：`gates/change-<id>-approval.md`
2. **Agent 权限边界**：
   - Agent 必须 [SHALL] 被允许生成 `request.md` 申请件。
   - 严禁 [SHALL NOT] Agent 自行作出放行裁决，严禁伪造或篡改人类授权原话。
   - 会话授权代录：人类在会话中明确授权放行本次变更后，Agent 可依授权原话代写 `approval.md`，须留下 `authorization_quote`、`authorization_turn`、`authorization_at`、`authorized_by`、`recorded_by` 五个溯源字段。
3. **防伪硬核校验**：
   - `scripts/gate_guard.py` 对签署件执行强防伪校验。
   - 若签署件中的 `signed_by` 或 `authorized_by` 字段为 `agent:*` 格式或包含 Agent 标识，必须 [SHALL] 判定为非法自签，立即阻断（退出码 1）。
   - 若代录模式下任一授权溯源字段缺失，或 `authorized_by` 与 `signed_by` 不一致，必须 [SHALL] 判定为 `AUTHORIZATION_TRACE_INCOMPLETE` 并阻断。
   - 若签署件记录的 `artifact_sha256` 与当前 `change-table.md` 实际哈希不一致，必须 [SHALL] 判定为篡改并阻断。
4. **门禁先行契约**：
   - 编排脚本 `scripts/change_dispatch.py --apply` 执行前，必须 [SHALL] 内部调用：
     `python3 scripts/gate_guard.py --gate change-<id> --check-only --root <dir>`
   - 仅当 [ONLY WHEN] 该命令返回退出码 0 且 `blocked == false` 时，方可 [THEN] 允许实施后续的母本写入操作；否则必须 [SHALL] 输出 `{"applied":false,"blocked":true,"reason":"missing_change_approval"}` 并以退出码 1 拒绝执行。

---

## 6. 零漂移回读与变更审计规范 (Zero-Drift Readback & Audit Protocol)

修改实施完成后，系统必须 [SHALL] 组织严格的回读比对与审计留痕：

### 6.1 声明作用域与精准替换
- 局部修改必须绑定条目 ID（如 `C-01`）。
- 改写目标文件中，变更必须限定在声明包含 `<!-- block: <id> -->`、`<!-- <id> -->` 或带 ID 标记的小节范围之内。

### 6.2 零漂移比对命令 (CRITERION M8-2)
- 系统必须 [SHALL] 执行：
  ```bash
  python3 scripts/verify_readback.py --diff-mode --old backup/<file> --new <file> --declared <id>
  ```
- **判定硬线**：非声明变更区域发生的任何字符级漂移，`undeclared_drift` 均必须严格等于 0，退出码为 0；若检出未声明章节被篡改，`undeclared_drift > 0` 且退出码为 1。

### 6.3 四层回读复验闭环
1. **Layer 1 (新句在位)**：`change-table.md` 中核准的“拟修订表述”必须 100% 存在于目标文本中。
2. **Layer 2 (旧句清零)**：“现状表述/旧口径”在全篇中的残留量必须严格等于 0。
3. **Layer 3 (结构完整)**：标题层级结构与核心 Markdown 语义块数量无非预期增减。
4. **Layer 4 (零未声明漂移)**：非声明章节的哈希与快照逐字节一致。

### 6.4 审计留痕与快照核验 (CRITERION M8-3)
- 系统必须 [SHALL] 执行：
  ```bash
  python3 scripts/verify_readback.py --verify-backup backup/ --change-table change-table.md
  ```
- 核验证明备份目录完整存在且与 `parent_baseline_sha256` 匹配，输出 `{"backup_valid":true,"hash_matched":true}`，退出码为 0。
- 将四层回读结果与新母本哈希回填入 `change-table.md` 的第 4 节中，完成维护回路闭环。
