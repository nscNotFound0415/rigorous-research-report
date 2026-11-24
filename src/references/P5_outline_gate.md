# P5 章节架构规划与 G1 人审门禁协议手册 (P5 Outline Structuring & Human Gate Protocol)

## 0. 协议元定义与适用范围
本协议定义严谨复杂调研报告写作系统第五阶段（P5 章节架构规划与 G1 人审门禁）的可执行规范。
Agent 与人类操作者在规划章节拓扑、管理前置数据引用、编制章节写作契约及执行 G1 门禁时，必须严格遵守本协议。
本协议全文采用“必须 [SHALL]”、“禁止 [SHALL NOT]”、“仅当……方可 [ONLY WHEN... THEN...]”等绝对断言句式。

---

## 1. 章节结构设计规则

### 1.1 论证拓扑与逻辑递进
1. **逻辑递进铁律 [SHALL]**：章节排布必须遵循“宏观研判 → 现状与壁垒 → 量化对比与成本拆解 → 落地路径与合规策略 → 综合结论与建议”的严密递进拓扑，禁止逻辑前后倒挂。
2. **避免重复与发散 [SHALL NOT]**：各章节之间必须保持正交性，严禁在不同章节就同一事实或同一论题进行重叠论证；跨章交叉引用必须以显式“参见第 X.Y 节”标注。
3. **章首判断句规范 [SHALL]**：每个二级章节（H2）的首段第一句必须为明确的论证判断句（Thesis Statement），直接陈述该章核心调研结论，禁止使用无信息量的寒暄或背景泛论铺垫。
4. **章末结论规范 [SHALL]**：每个二级章节末尾必须包含明确的「核心结论」或总结论述，提炼 2 至 3 条量化或确定性研判。

### 1.2 标题层级严谨性
1. **严格三级骨架 [SHALL]**：大纲正文骨架必须细化到三级标题（章 H2 → 节 H3 → 小节 H4）。
2. **禁止层级跳级 [SHALL NOT]**：大纲各级标题必须连续递进，严禁发生层级跳跃（如从 `# 一级文档标题` 直接跳至 `### 三级节标题`，或从 `## 二级章标题` 直接跳至 `#### 四级子项`）。跳级的大纲文件将被 `scripts/outline_check.py --check-sections` 判定为非法并阻断。
3. **论证目的行必备 [SHALL]**：每个二级章（H2）和三级节（H3）必须具备显式的 `论证目的:` 声明行，明确回答该节在整体论证拓扑中的战略意图。

---

## 2. REQ-ID 诉求全覆盖与事实锚定规则

### 2.1 诉求索引全覆盖
1. **100% 映射铁律 [SHALL]**：大纲章节规划必须基于 `brief.md` 中的「2.9 诉求与实体索引」，将其中声明的全部 `REQ-ID` 100% 映射到具体章节或小节。
2. **禁止遗漏诉求 [SHALL NOT]**：严禁遗漏任何一条 `REQ-ID`；大纲第 0 节必须明文列示「诉求索引覆盖表」，标明每个 `REQ-ID` 的承载章节。
3. **禁止无锚点章节 [SHALL NOT]**：所有章节设计必须具有来自 `brief.md` 的明确需求来源，严禁脱离委托目标随意堆砌无关背景章节。

### 2.2 事实边界锚定
1. **唯二通路约束 [SHALL]**：大纲规划引用的每一个核心论据、关键指标与数据支撑，必须来源于 M4 调研沉淀的一手事实快照或数据底表 `datatable.csv`。
2. **严禁凭空拟造 [SHALL NOT]**：大纲中规划的图表、数据引用必须有据可循，禁止在大纲中预设缺乏信源支撑的虚构结论。

---

## 3. 并行期证据引用与 PENDING 登记机制

### 3.1 消费 M4 增量快照
1. **并行推进机制 [SHALL]**：M5 与 M4 调研并行启动。M5 模块只读消费 M4 维护的单写者证据索引快照 `evidence-index.md`。
2. **证据引用标记规范 [SHALL]**：
   - 凡所引数据已在当前 `evidence-index.md` 中存在，必须在对应条目声明 `evidence_ref: EVD-XXX`。
   - 凡因 M4 调研任务尚在推进而未完成入库的数据，允许标注为 `evidence_ref: PENDING`（或 `PENDING-XX`）。

### 3.2 「待补数据」集中登记铁律
1. **显式登记义务 [SHALL]**：凡在正文各章节中出现的任何 `PENDING` 引用，必须立即且无条件在大纲文末设立的「## 待补数据（PENDING）」专用小节中进行集中登记。
2. **严禁隐式挂起 [SHALL NOT]**：严禁仅在章节局部随意写 `PENDING` 却不在「待补数据」小节列出。未登记的 PENDING 属于严重违规，`scripts/outline_check.py` 必须返回退出码 1 阻断流程。
3. **登记要素齐备 [SHALL]**：待补数据登记项必须明确写明：待补标识（如 `PENDING-01`）、数据内容描述、关联章节、责任模块（M4）及清零时限要求。

---

## 4. Join 2 汇合门禁清零判据 (CRITERION M5-1b)

### 4.1 Join 2 不可豁免闭环
1. **PENDING 必须归零 [SHALL]**：在 Batch 2 汇合点（Join 2）及 G1 门禁人类签署前，大纲全文中的所有待补数据必须完成全量证据回指，`PENDING` 引用计数必须严格为 0。
2. **全量锚定检验 [SHALL]**：所有 `evidence_ref` 必须 100% 成功映射到 `evidence-index.md` 中的有效条目。
3. **自动化阻断指令 [SHALL]**：执行命令：
   ```bash
   python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md --require-resolved
   ```
   若返回的 `pending_refs` 非空，或存在未入库的 `missing_refs`，脚本必须退出码 1 阻断流水线，绝不可豁免放行。

---

## 5. 章节撰写契约规范 (`section-contracts.md`)

### 5.1 编制目标与下发原则
1. **合稿硬约束集 [SHALL]**：M5 必须编制完整的章节撰写契约手册 `section-contracts.md`，作为向 M7 合稿引擎下发的机器/人工写作指令集。
2. **复核判据基准 [SHALL]**：本契约手册同时作为 M6 对抗复核引擎在执行全文审查时的判断基准。

### 5.2 章节契约七要素
每个章节的撰写契约必须且仅能包含以下 7 项要素：
1. **必须回答的核心命题 (Mandatory Propositions)**：明确定量或定性解答的 2-3 个核心问题。
2. **必须使用的底表口径与字段 (Datatable Scopes & Fields)**：明确该章使用 A自建 / B采购 / C市场何种口径，列明核算字段，重申严禁跨口径相减。
3. **禁用词表引用 (Forbidden Terms)**：显式引用 `templates/forbidden_terms.json`，列出章节特异性禁用自述词，声明保护的 9 类严谨性免责语句。
4. **边界限定与禁言红线 (Boundary Constraints)**：明确限定论证边界，明令禁止越界断言的内容。
5. **证据要求 (Evidence Requirements)**：明确规定该章最小 `evidence_ref` 数量，要求重要判断句必须闭环引用。
6. **长度与风格基线 (Length & Style Baseline)**：规定字数区间、客观陈述基调、章首判断句与章末结论要求。
7. **交付到 M7 的写作指令 (Synthesis Instructions)**：按条目给出向 M7 引擎的直接起草指令。

---

## 6. G1 门禁流程与防伪阻断

### 6.1 G1 门禁标准流转步骤
1. **前置自检通过 [SHALL]**：仅当 `outline_check.py outline.md --check-sections` 与 `outline_check.py outline.md --evidence-index evidence-index.md --require-resolved` 均返回退出码 0 时，方可启动 G1 门禁流程。
2. **生成申请单 [SHALL]**：Agent 生成 `gates/G1-request.md`，完整填写大纲结构摘要、底表覆盖分析及哈希值。
3. **人类离线签署 [SHALL]**：人类操作者在场审查大纲与章节契约，手工填写并签署 `gates/G1-approval.md`。
4. **门禁核验放行 [SHALL]**：调用 `gate_guard.py` 核验签署凭单：
   ```bash
   python3 scripts/gate_guard.py --gate G1 --verify --artifact outline.md --approval gates/G1-approval.md
   ```
   仅当返回 `state: APPROVED` 且退出码为 0 时，才允许启动 M7 合稿模块。

### 6.2 防伪与阻断铁律
1. **禁止 Agent 自签 [SHALL NOT]**：门禁签署件 `signed_by` 字段严禁包含 `agent:*` 标识，一经发现，`gate_guard.py` 立即阻断（退出码 1）。
2. **未签署严禁合稿 [SHALL NOT]**：若 `gates/G1-approval.md` 缺失或处于 `PENDING` 状态，流水线严禁启动 M7 合稿，向 `draft_full.md` 写入 0 字节。
3. **驳回处理机制 [SHALL]**：若人类将 `decision` 标记为 `REJECTED` 或 `CHANGES_REQUESTED`：
   - `python3 scripts/gate_guard.py --gate G1 --check-only` 必须返回退出码 1 阻断流程；
   - 系统必须无条件回退至大纲重订阶段，吸收人类修改意见重新修订大纲与章节契约，严禁强行放行。

---

## 7. 写边界与模块隔离铁律

### 7.1 M5 独占写工件
M5 模块在工作区内具备且仅具备以下 3 个文件的写入权限：
1. `outline.md`：章节骨架大纲；
2. `section-contracts.md`：章节撰写契约；
3. `gates/G1-request.md`：G1 门禁放行申请单。

### 7.2 只读与互斥红线
1. **严禁写入 M4 产物 [SHALL NOT]**：`evidence-index.md`、`datatable.csv`、`fact-store/` 为 M4 独占写入产物。M5 模块对其仅有只读权限，**严禁创建或修改 `evidence-index.md`**。
2. **严禁写入 M7 产物 [SHALL NOT]**：`draft_full.md`、`delivery/` 归 M7 独占写入，M5 严禁创建或触碰。
3. **严禁自动创建审批单 [SHALL NOT]**：`gates/G1-approval.md` 属于人类专属签署凭证，M5 严禁代签或自动生成。

---

## 8. 自动化校验脚本 CLI 契约

M5 模块的结构、引用与门禁核验严格绑定以下 CLI 契约：

| 校验目的 | 执行指令 | 期望 stdout JSON | 退出码 |
|---|---|---|:---:|
| 并行期引用校验 (CRITERION M5-1a) | `python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md` | `{"missing_refs":[],"pending_refs":[...],"refs_total":N,"pending_declared":true}` | 0 (合规) / 1 (违规) |
| 章节结构与目的校验 | `python3 scripts/outline_check.py outline.md --check-sections` | `{"invalid_sections":[],"chapter_count":N}` | 0 (合规) / 1 (违规) |
| Join 2 汇合清零校验 (CRITERION M5-1b) | `python3 scripts/outline_check.py outline.md --evidence-index evidence-index.md --require-resolved` | `{"missing_refs":[],"pending_refs":[],"refs_total":N,"pending_count":0}` | 0 (清零闭环) / 1 (存在未决) |
| G1 门禁状态检查 (CRITERION M5-3) | `python3 scripts/gate_guard.py --gate G1 --check-only` | `{"gate":"G1","state":"APPROVED/PENDING","blocked":bool}` | 0 (放行) / 1 (阻断) |
| G1 门禁核验放行 (CRITERION M5-2) | `python3 scripts/gate_guard.py --gate G1 --verify --artifact outline.md --approval gates/G1-approval.md` | `{"gate":"G1","state":"APPROVED","blocked":false,"artifact_sha256":"..."}` | 0 (放行) / 1 (阻断) |

---

## 9. 本阶段模板索引

- 本阶段模板：`templates/section_contracts.template.md`（章节撰写契约结构：论证目的、证据回指、口径隔离与禁用词红线）
