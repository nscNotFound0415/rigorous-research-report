# 快速上手与使用指南 (User Guide)

本文档面向希望使用本流水线产出高质量、可审计研报的分析师与工程师。系统支持两种使用形态：
*   **模式 A（Agent 驱动装配流）**：由大模型 Agent 全程闭环驱动，人类在关键节点审核签字。
*   **模式 B（独立质检工具箱 Standalone Toolkit）**：无需任何 Agent，人类分析师直接在终端调用确定性 Python 脚本质检自己的研究材料。

---

## 一、双模式运行指南

### 模式 A：Agent 协同调研流（设计原意）

#### 1. 唤醒技能
在支持 Skill 扩展的终端（如 Claude Code, ZCode 等）中输入：
```text
/rigorous-research-report
```
或直接指令：
> “请启动严谨调研报告流水线，对《全球人形机器人灵巧手供应链成熟度与关键零部件成本效益》开展可行性深度研报。”

#### 2. 流水线阶段与人机交互节点
流水线将自律推进六个阶段，并在四道门禁前主动中断等待人类签字：

```text
[用户输入议题]
   │
   ▼
[P1 落地澄清] ──> Agent 生成 brief.md + gates/G0-request.md
   │            │ (停机等待人类确认)
   │            ▼
   ├────────── [人审门 G0] ── 人类签署 gates/G0-approval.md
   │
   ▼
[P2 治理协议] ──> 初始化 progress-log.md (15项任务全为 [ ])
   │
   ▼
[P3 课题拆分] ──> 视角枚举生成 task.json，校验 DAG 无环与 guidelines
   │
   ▼
[P4 事实调研] ∥ [P5 章节大纲] ── 并行推进：
   │                  │ (P4 采信一手快照，构建 datatable.csv)
   │                  │ (P5 规划论证骨架，生成 outline.md)
   │                  ▼
   ├────────────── [人审门 G1] ── 人类审查大纲并签署 G1-approval.md
   │
   ▼
[跨产物复核] ──> 调度异族/隔离 Agent 审查，产出 D0-D3 缺陷单
   │            │ (P4底表复核、P5大纲复核、P6全文复核)
   │            ▼
   ├────────── [人审门 G2] ── 人类在 correction-diff.md 中定性裁决并签署 G2
   │
   ▼
[P6 统一合稿] ──> 单次成型 draft_full.md ──> 一致性清洗 ──> 直写 OOXML ──> 目录回填
   │            │ (产出 delivery/output.docx 与 delivery/output.pdf)
   │            ▼
   └────────── [人审门 G3] ── 人类核验版式，签署 G3-approval.md 放行交付
```

---

### 模式 B：独立质检工具箱（无 Agent 纯本地运行）

即使脱离大模型 Agent，本项目提供的 14 个 Python 脚本也是一套开箱即用的专业研报质检脚手架。人类分析师可在写报告全流程中随时调用：

#### 1. 自动复算财务/成本底表（杜绝算术倒挂与跨口径乱相减）
```bash
# 验证底表内所有公式单元格（在容差范围内纯代码复算）：
python3 src/scripts/audit_calc.py my_datatable.csv

# 结合证据索引，检验是否每一个数值都有出处，且所有预估数都有假设 tag：
python3 src/scripts/audit_calc.py my_datatable.csv --evidence-index my_evidence_index.md

# 开启严格模式，严禁自建成本(A)与外部租用价(B)在同一算式中跨口径直接相减：
python3 src/scripts/audit_calc.py my_datatable.csv --strict-tolerance
```

#### 2. 全文文本卫生与违禁词扫描（消除 AI 腔与元叙述）
```bash
# 扫描正文，精准揪出“如前所述”、“本报告不给出”、“第一性原理”等写作自述词，
# 同时保护合法的 9 类严谨性声明（如“不得跨口径相减”、“不构成法律意见”）零误报：
python3 src/scripts/audit_text_hygiene.py my_draft.md --rules src/templates/forbidden_terms.json

# 跨章节去重检查（检测是否存在跨章节复制粘贴 >= 30 字符的冗余片段）：
python3 src/scripts/audit_text_hygiene.py my_draft.md --rules src/templates/forbidden_terms.json --check-dedup
```

#### 3. 引用索引与图表连续性核查
```bash
# 确保正文中所有引用的表号、图号连续无断号，所有 [EVD-xxx] 均能在索引中找到实体：
python3 src/scripts/citation_check.py my_draft.md --evidence-index my_evidence_index.md
```

#### 4. 高质量 Word 直写、PDF 转换与精准目录回填
```bash
# 1. 由单源 Markdown 直接生成标准 OOXML Word 文档并输出部件哈希清单（无 pandoc 依赖）：
python3 src/scripts/build_docx.py my_draft.md --out output.docx --manifest build_manifest.json

# 2. 转换为 PDF：
python3 src/scripts/build_pdf.py output.docx --out output.pdf

# 3. 目录两遍法：从 PDF 真实打印流中抽取物理页码，精确回填到 Word 目录中：
python3 src/scripts/toc_two_pass.py output.docx output.pdf

# 4. 双向回读校验：验证 Word 目录项与正文 H1/H2 标题 100% 对应且页码无误：
python3 src/scripts/delivery_readback.py --docx output.docx --pdf output.pdf --source my_draft.md --out readback.json
```

---

## 二、人审门禁 (G0–G3) 实操指引

流水线设置了 G0（简报定稿）、G1（大纲审批）、G2（定性纠错裁决）、G3（终审放行）四道刚性人审门。门禁具有严格的**代码级防伪机制**：

### 1. 门禁文件结构与职责
*   **申请单（由 Agent 生成）**：路径为 `gates/G*-request.md`。Agent 会将当前待审核物料的路径、生成的 SHA-256 哈希、核心决策摘要填写在申请单中，然后停止推进。
*   **签署件（必须由人类操作者写入）**：路径为 `gates/G*-approval.md`。只有存在该文件且字段合法、哈希一致时，门禁检查脚本 `gate_guard.py` 才会放行。

### 2. 合法签署件标准模板示例

以 G0 门禁为例，人类操作者在确认 `brief.md` 无误后，在项目根目录下创建 `gates/G0-approval.md`：

```markdown
---
gate: G0
decision: APPROVED
signed_by: human:chief_analyst_zhang
signed_at: 2026-11-24T10:00:00Z
artifact_sha256: 053865462b1dc7fbb8320ecb2c5020a6cfb610c0382c0f0fe1b4d739fdbbdf67
signature: 确认项目简报与宪法五原则，同意进入下一阶段
approver_role: human_decision_maker
---

已审阅 brief.md，核心诉求与研究范围界定明确，同意启动调研规划。
```

### 3. 三大防伪铁律（违规将直接被 exit 1 阻断）

1.  **拒绝机器与代签（Anti-Agent-Sign）**：  
    `signed_by` 或 `signature` 中若包含 `agent`、`ai`、`bot`、`模型`、`自动`、`脚本` 等词汇，`gate_guard.py` 会返回 `AGENT_SIGNATURE_PROHIBITED` 并退出码 1。
2.  **拒绝演练桩件（Anti-Stub）**：  
    若签署件中标记了 `stub: true`，会被判为演练模拟桩件，系统返回 `STUB_REJECTED` 并退出码 1。**门禁只接受真实人类授权**。
3.  **哈希强绑定（Hash-Binding）**：  
    签署件中的 `artifact_sha256` 必须与被放行文件（如 `brief.md` 或生成的 `output.docx`）的实际 SHA-256 逐位吻合。若人类签字后文件又被 Agent 篡改，哈希失效，门禁自动锁死。

---

## 三、P1 落地澄清八项的心智模型

在报告启动初期，系统会围绕 8 个维度展开问询。**请牢记：这 8 项是帮助你厘清思路的“思考罗盘”，绝非刁难你的“考试准入题”**。

### 1. 状态分类机制
每项均包含 `clarification_status` 标识：
*   `CLARIFIED`（已澄清）：你给出了明确要求，系统会严格按你的要求执行，并开启严格格式与枚举校验。
*   `NOT_CLARIFIED`（未澄清）：你当前不确定或暂不关心，允许留空，但系统会**自动落入安全完备的协议默认行为**，绝不阻断流水线。
*   `NOT_APPLICABLE`（不适用）：本次课题不涉及该维度（如学术研究不涉及对外商务格式）。

### 2. 八项维度的协议默认行为 (Fallback Defaults)

| 澄清维度 | 关注的核心问题 | 若未明确时的默认行为 |
|---|---|---|
| **2.1 报告受众** | 报告主要给谁看？（高管/投资人/技术专家） | 默认按**“公司内部决策层阅示”**定位，结论前置，突出条件式权衡。 |
| **2.2 研究标的** | 核心调研对象与边界是什么？ | 默认直接从你的初始意图文本中提取核心关键词作为研究边界。 |
| **2.3 风格基调** | 正式公文体、深度研报体还是商业推介体？ | 默认采用**“正式中立研报体”**（章首判断句、一段一个核心论点、先结论后依据）。 |
| **2.4 项目背景** | 有无历史沿革或交接材料？ | 默认仅以本次对话提供的事实为准，**严禁将历史交接材料的旧结论当既成事实**。 |
| **2.5 交付路径** | 最终文件保存在本地哪个目录？ | 默认写入 `<当前工作区>/research/<议题名称>/` 相对路径下。 |
| **2.6 交付形态** | 需要什么格式的文件？ | 默认交付**“Markdown 终稿 + 标准 Word (.docx) + 打印排版 PDF”**三件套。 |
| **2.7 载体基准** | 若有在线协作文档，以谁为准？ | **唯一条件硬约束**：若存在在线文档，必须人工指定权威归属；**若无在线文档，默认“本地为唯一母本（`LOCAL_AUTHORITATIVE`）”**。 |
| **2.8 交互模式** | 希望 Agent 怎么跟你沟通？ | 默认采用**“关键节点一次一问、前沿决策收敛后集中确认”**。 |

---

## 四、变更维护回路 (M Loop) 实操

调研报告定稿后，若领导提出微调（如“修改某章措辞”），或外部出现重大新事实（如“某竞品大幅降价”），**严禁直接在母本上推倒重写**。流水线提供分级变更响应：

### 1. 轻量微调流程 (LIGHTWEIGHT)
*   **适用**：文字润色、个别数字修正、评级从“中高”微调为“高”。
*   **操作**：
    1. 生成《指示处置对照表》（`change-table.md`），列出修改前后文字比对与影响章节。
    2. 自动调用 `adapter_git_sync.py --snapshot` 对旧母本进行快照哈希存证（归档至 `backup/`）。
    3. 人类签署 `gates/change-<id>-approval.md`。
    4. 实施改写并运行 `verify_readback.py --diff-mode` 验证**非声明区域 0 字符漂移**。

### 2. 重大口径颠覆流程 (MAJOR)
*   **适用**：调研核心假设被证伪、法律红线彻底翻转、分析模型重构。
*   **操作**：触发失效传播规则（`change_dispatch.py --propagate`），受影响的章节在治理台账中被标记为 `STALE`（失效）。前序复核报告作废，必须局部重跑调研与复核，重签 G1/G2 门禁。

---

## 五、完整项目工件清单与归宿

运行完一次完整的调研流水线后，你的研究工作区将沉淀为以下清晰、可追溯的资产树：

```text
my-research-workspace/
├── brief.md                     # [权威母本] 项目简报唯一事实源（内嵌宪法五原则与诉求索引）
├── progress-log.md              # [治理台账] 15 项流水线任务进度与人类决策审计日志
├── task.json                    # [拆分规划] 机器可校验的调研任务依赖图（DAG）
├── research-breakdown.md        # [拆分架构] 多视角分析与任务映射树
├── fact-store/                  # [事实金库] 抓取的一手网页快照/数据文件（只读存证，不可篡改）
│   ├── T-01_idc_evidence.html
│   └── snapshots_manifest.md    # 证据快照 SHA-256 哈希清单
├── evidence-index.md            # [证据索引] 证据条目元数据总表（含机构、日期、可采信度）
├── datatable.csv                # [数据底表] 标准化数据底表（含公式、容差、口径隔离标注）
├── outline.md                   # [章节架构] 经 G1 人审批准的完整章节大纲与证据回指表
├── draft_full.md                # [报告正文] 单次成型、经过文本卫生清洗的完整 Markdown 正文
├── gates/                       # [门禁存证] G0、G1、G2、G3 四道人审申请单与人类签署放行单
│   ├── G0-approval.md
│   ├── G1-approval.md
│   ├── G2-approval.md
│   └── G3-approval.md
└── delivery/                    # [最终交付] 面向最终读者的正式出版级报告物料
    ├── output.docx              # 依据标准样式直写的 Word 正式报告（目录页码已精准回填）
    ├── output.pdf               # 高清排版 PDF 文档
    ├── build_manifest.json      # OOXML 8 个底层部件哈希清单（保证构建幂等性）
    └── delivery_readback.json   # 目录与正文实际页码 0 误差回读审计证明
```
