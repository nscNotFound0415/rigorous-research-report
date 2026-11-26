# P1 落地澄清与决策树协议手册 (P1 Grill-me Elicitation Protocol)

## 0. 协议元定义与适用范围
本协议定义严谨复杂调研报告写作系统第一阶段（P1 落地澄清与简报构建）的可执行规则。
Agent 与人类操作者之间的交互必须严格遵循本协议。

---

## 1. 核心前置原则与触发控制

### 1.1 触发控制铁律
1. **启动前置检查**：仅当人类用户显式输入命令 `/rigorous-research-report` 或在当轮对话中明确要求“按严谨调研报告流水线执行”时，Agent 方可启动本协议。
2. **静默退出规则**：若无上述显式调用指令，Agent 必须立即输出“本技能需显式调用 /rigorous-research-report 启动”并无条件终止执行；禁止向人类提出任何澄清问题，禁止在工作区创建或修改任何文件。

### 1.2 能自查事实禁止提问铁律
1. **自查前置义务**：在向人类抛出任何问题前，Agent 必须穷尽本地工作区既有材料、已提供的前情文档及系统环境进行自查。
2. **禁止无效打扰**：凡可通过本地文件读取或工具调用确证的事实，禁止向人类提问；仅当自查无结果或存在多重不可调和冲突时，该要素方可进入待澄清队列。

### 1.3 一次一问与选项规范
1. **单步交互约束**：Agent 必须严格执行“一次一问”原则，禁止在单次回复中合并提出多个维度的澄清问题。
2. **推荐选项约束**：每个提问必须提供 2 至 4 个明确的推荐选项，并在末尾固定附带 `[Other] 自定义输入` 选项供人类补充。
3. **句式断言约束**：本协议全文采用“必须 [SHALL]”、“禁止 [SHALL NOT]”、“仅当……方可 [ONLY WHEN... THEN...]”等绝对断言句式。

### 1.4 交接材料与历史设定继承约束铁律
1. **交接材料仅作候选答案**：交接包、历史文件、既有报告中的任何项目设定必须仅作为候选答案，必须标注来源文件路径与 SHA256，并在 brief §2.11 逐条由人类在 G0 门禁给出 `CONFIRMED` 或 `REVISED` 裁决；未决条目严禁写入 brief 正文。
2. **禁止以继承材料自动充当答案**：交接包、历史文件与既有材料不得自动充当八项建议澄清清单中任何一项的答案；人类未答的项一律按协议默认行为执行，并登记 `NOT_CLARIFIED` 与 `unclarified_reason`，严禁以继承材料掩填。
3. **搜索核实须人确认**：搜索子代理仅用于核实外部可查事实，其核实结果同样必须经人类确认后方可写入 brief。
4. **交接物料只读与历史标签不继承**：交接包一律作为只读输入并记录 SHA256 哈希；交接材料中携带的历史标签（如“已核验”、“A级”、“定案”）一律禁止继承，必须在本流水线内重新核验。

---

## 2. 八项建议澄清清单的决策树拓扑与 Frontier 计算规则

八项澄清的用途是帮助把研究对象与交付形态明确下来，不是 G0 准入条件。八项全部澄清有利于一次成型，但缺项不得阻断流程：未澄清项只须登记状态与原因，并按默认行为执行。

### 2.1 决策树依赖拓扑 (DAG)
八项建议澄清项存在如下推荐提问顺序（前置依赖仅决定提问次序，不构成阻断条件）：

```text
[D1 研究标的与对象] (根节点)
  │
  ├──────────────────────────────────┐
  ▼                                  ▼
[D2 项目背景与历史上下文]           [D3 报告受众]
  │                                  │
  └──────────────────┬───────────────┘
                     ▼
              [D4 风格与基调]
                     │
                     ▼
          [D5 交付形态与格式约定]
                     │
                     ▼
              [D6 交付目的地]
                     │
                     ▼
          [D7 在线载体基准判定]
                     │
                     ▼
          [D8 人机交互与问询模式]
```

### 2.2 Frontier 队列动态计算算法
1. **状态定义**：
   每个维度具备且仅具备三种登记状态：`CLARIFIED`（人类已明确回答且字段非空）、`NOT_CLARIFIED`（人类选择跳过或未答，已按默认行为执行并登记原因）、`NOT_APPLICABLE`（本次议题不涉及该项，已登记原因）。`NOT_CLARIFIED` 与 `NOT_APPLICABLE` 均视为已收敛，必须登记 `unclarified_reason`。
2. **准入规则**：
   仅当某维度的所有直接前置依赖节点均已收敛（登记为 `CLARIFIED`／`NOT_CLARIFIED`／`NOT_APPLICABLE` 之一），且该维度自身尚未登记时，该维度方可进入待澄清活跃队列（Active Frontier）。
3. **入队优先级**：
   Active Frontier 队列必须严格按 DAG 拓扑偏序排列。存在多个就绪节点时，按 `D1 -> D2 -> D3 -> D4 -> D5 -> D6 -> D7 -> D8` 的确定性序号出队。
4. **出队执行**：
   Agent 必须从 Active Frontier 头部取出且仅取出 1 个维度，调用对应的提问模板向人类发问。
5. **状态跃迁**：
   人类完成有效回复且 Agent 成功提取字段后，该维度登记为 `CLARIFIED`；人类明确选择跳过或不再回答时，Agent 必须按该维度默认行为填充可执行值并登记为 `NOT_CLARIFIED`＋`unclarified_reason`；两者均触发下一轮 Frontier 重算。

### 2.3 必须问与可默认的两类问题
1. **必须问（禁止默认）**：① 工作区或任务中确实存在在线文档时，「本地与在线以哪个为准」（2.7 权威载体）；② 任何一旦答错会导致整篇返工的关键事实（如研究对象本身搞错）。若人类明确选择跳过，登记 `NOT_CLARIFIED`＋`unclarified_reason`「用户选择跳过」，不阻断流程。
2. **可默认（问一次即可）**：2.1 读者、2.2 对象、2.3 风格、2.4 背景、2.5 落盘地址、2.6 格式、2.7 权威载体（仅当无在线文档时）、2.8 交互模式。人类未答或选择不答时，必须按 §3 各自默认行为执行，并登记 `NOT_CLARIFIED`＋`unclarified_reason`。

---

## 3. 八项建议澄清项逐项提问模板、字段与默认行为规范

### 3.1 D1: 研究标的与对象 (Subject Entity)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认由议题文本可确定的范围界定（`subject_name` 与 `scope_boundaries` 同步给出）；议题文本仍无法确定时登记 `NOT_CLARIFIED`＋`unclarified_reason`。
- **前置依赖**：无（根节点）。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `subject_name`: 字符串，核心企业、行业、技术或政策标的。
  - `scope_boundaries`: 字符串，调研涵盖与明确排除的业务/地域/时间边界。
- **自查准则**：自查用户初始提示词及上下文，提取提及的目标实体与范围。
- **提问模板**：
  ```text
  【澄清 1/8 · 研究标的与边界】
  请确认本篇调研报告的核心研究标的与范围边界：
  [选项 A] 标的：{{RECOMMENDED_SUBJECT_A}}；边界：{{RECOMMENDED_BOUNDARY_A}}
  [选项 B] 标的：{{RECOMMENDED_SUBJECT_B}}；边界：{{RECOMMENDED_BOUNDARY_B}}
  [选项 C] 标的：{{RECOMMENDED_SUBJECT_C}}；边界：{{RECOMMENDED_BOUNDARY_C}}
  [Other] 自定义输入研究标的与明确的边界排除项。
  ```

### 3.2 D2: 项目背景与历史上下文 (Background Context)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认只保留本次会话与工作区中可核实的背景；继承材料一律不得自动充当答案（沿用 §1.4 规则），无继承材料时填 `["NONE"]`。
- **前置依赖**：D1 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `context_summary`: 字符串，项目成因、前情与业务决策目标。
  - `inherited_materials`: 字符串列表，继承的前序材料清单与初始可信度评级（无继承材料时填 `["NONE"]`）。
- **自查准则**：检查工作区是否存在历史交接文档、会议纪要或前期调研快照。
- **提问模板**：
  ```text
  【澄清 2/8 · 背景与前情资料】
  关于本课题的前情背景与已有资料沉淀：
  [选项 A] 既有业务面临落地决策，需全新一手论证；无前序继承资料。
  [选项 B] 继承既有前期方案，需针对最新市场/合规变动进行深度复核与增量重构。
  [选项 C] 应对外部审计或高层审阅，需对历史推论进行事实穿透核验。
  [Other] 自定义补充项目背景及已掌握的材料清单。
  ```

### 3.3 D3: 报告受众与偏好 (Target Readers)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认「公司内部决策层阅示」，并在 `reader_preferences` 标注该值为假设；人类跳过时登记 `NOT_CLARIFIED`。
- **前置依赖**：D1、D2 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `primary_readers`: 字符串列表，核心决策者或评审人职能角色。
  - `reader_preferences`: 字符串，受众关注的决策维度偏好（如成本效益、合规风险、技术壁垒）。
- **自查准则**：若用户指令中已指定“向 CEO 汇报”或“供合规委员会审查”，直接提取填入。
- **提问模板**：
  ```text
  【澄清 3/8 · 核心受众与关切偏好】
  本份报告的核心阅读对象与决策偏好为：
  [选项 A] 受众：公司高层/CEO/投资人；偏好：投资回报测算、战略竞争格局、终局可行性。
  [选项 B] 受众：业务与合规专委会/法务总监；偏好：监管牌照合规、数据出境风险、罚则红线。
  [选项 C] 受众：工程架构师/技术技术总监；偏好：技术路线选型、性能指标压测、系统集成成本。
  [Other] 自定义受众角色与关注的核心评价指标。
  ```

### 3.4 D4: 风格与基调 (Tone & Style)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认「正式研报体：章首判断句、一段一个意思、先结论后依据」，即 `style_mode: rigorous_analytical`、`perspective: third_party_neutral`。
- **前置依赖**：D3 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `style_mode`: 枚举值，严格限定为 `rigorous_analytical`（严谨深度剖析） | `executive_brief`（高管决策摘要） | `adversarial_audit`（红蓝对抗审计）。
  - `perspective`: 枚举值，严格限定为 `third_party_neutral`（独立第三方中立） | `strategic_advisor`（战略参谋建议）。
- **自查准则**：依据 D3 受众类型自动计算最佳推荐组合。
- **提问模板**：
  ```text
  【澄清 4/8 · 报告基调与行文风格】
  请选定本报告的分析基调与视角立场：
  [选项 A] 严谨深度剖析 + 独立第三方中立立场 (rigorous_analytical + third_party_neutral)
  [选项 B] 高管决策导向 + 战略参谋建议立场 (executive_brief + strategic_advisor)
  [选项 C] 风险穿透审计 + 红蓝对抗审查立场 (adversarial_audit + third_party_neutral)
  [Other] 自定义风格模式与视角立场。
  ```

### 3.5 D5: 交付形态与格式约定 (Format Contract)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认 Markdown ＋ docx ＋ PDF 三件交付，`primary_format: MARKDOWN`，并写明另两件由 Markdown 母本派生。
- **前置依赖**：D4 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `primary_format`: 枚举值，严格限定为 `DOCX` | `PDF` | `MARKDOWN`。
  - `pagination_limit`: 字符串，报告篇幅预算约束（如“30页以内”、“2万字精简版”、“不限篇幅以论证完整为准”）。
  - `structural_requirements`: 映射字典，固定包含 `numbering_system: "中文规范三级编号"` 与 `reference_style: "文末显式索引与一手出处锚定"`。
- **自查准则**：检查运行环境是否支持 DOCX/PDF 编译；若未指定则默认推荐排版规范。
- **提问模板**：
  ```text
  【澄清 5/8 · 交付载体与篇幅约定】
  请确认本报告的交付文件格式与篇幅预算：
  [选项 A] 格式：标准排版 DOCX (附自动生成 PDF)；篇幅：严谨详尽版（不设硬性上限，以证据闭环为准）。
  [选项 B] 格式：高管精要 PDF (单源 Markdown 直转)；篇幅：控制在 25-35 页以内。
  [选项 C] 格式：纯研发与知识库 Markdown 母本；篇幅：完整沉淀全部底表与技术细节。
  [Other] 自定义交付文件格式与页数上限。
  ```

### 3.6 D6: 交付目的地 (Delivery Path)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认 `<当前工作区>/research/<议题简称>/`，执行方必须据此写出绝对路径 `target_local_dir` 与 `target_delivery_dir`；绝对路径是结构不变量，任何状态下均不得为相对路径或空值。
- **前置依赖**：D5 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `target_local_dir`: 绝对路径字符串，本地过程物料落盘目录。
  - `target_delivery_dir`: 绝对路径字符串，最终交付件落盘目录。
- **自查准则**：自查当前所在工作区根目录路径，若已在独立项目目录下，直接解析为绝对路径作为推荐项。
- **提问模板**：
  ```text
  【澄清 6/8 · 物料与成品落盘地址】
  请确认报告过程物料与终稿交付件的落盘物理路径：
  [选项 A] 本地根目录：{{CURRENT_WORKDIR}}；交付件目录：{{CURRENT_WORKDIR}}/delivery
  [选项 B] 本地根目录：{{CURRENT_WORKDIR}}/research_output；交付件目录：{{CURRENT_WORKDIR}}/research_output/final
  [Other] 自定义指定本地根目录与最终交付目录绝对路径。
  ```

### 3.7 D7: 在线载体基准判定 (Online Baseline Rule)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：无在线文档时默认 `LOCAL_AUTHORITATIVE` 并登记原因；存在在线文档时该项属于「必须问」，禁止默认，必须由人类明确 `ONLINE_AUTHORITATIVE` 或 `LOCAL_AUTHORITATIVE`。
- **前置依赖**：D5、D6 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `online_enabled`: 布尔值，严格限定为 `true` 或 `false`。
  - `source_of_truth`: 必填枚举值，无默认值，严格限定为 `ONLINE_AUTHORITATIVE` | `LOCAL_AUTHORITATIVE`（既有规范亦指代 LOCAL_GIT_FIRST 与 REMOTE_ONLINE_FIRST）；**严禁填入“待定”、TODO 或空值**。
  - `sync_policy`: 字符串，单向只读快照拉取 / 受控局部块更新回写 / 不启用同步。
  - `delivery_channel`: 字符串，指定交付通道（如 `FILE_OVERWRITE_PUSH` | `LOCAL_ONLY` | `API_CHUNK_SYNC`）。
- **自查准则**：检查当前目录是否为 Git 仓库以及是否存在在线平台配置。
- **提问模板**：
  ```text
  【澄清 7/8 · 在线载体与事实源基准】
  请确定报告主母本的存储权威基准与在线协同策略（必填，无默认值，严禁填待定）：
  [选项 A] 本地载体绝对权威 (LOCAL_AUTHORITATIVE / LOCAL_GIT_FIRST)；本地为唯一母本，在线端为单向发布目标。
  [选项 B] 在线载体绝对权威 (ONLINE_AUTHORITATIVE)；在线文档为内容基准，本地为双哈希只读镜像，本地修改须同步线上校验后方算落地。
  [选项 C] 纯本地独占模式 (LOCAL_AUTHORITATIVE 且 online_enabled: false)；不启用任何外部协同同步。
  [Other] 自定义权威载体与发布策略（必须为 ONLINE_AUTHORITATIVE 或 LOCAL_AUTHORITATIVE，严禁声明为待定）。
  ```

### 3.8 D8: 人机交互与问询模式 (Interaction Mode)
- **状态登记**：`clarification_status: CLARIFIED | NOT_CLARIFIED | NOT_APPLICABLE`；非 `CLARIFIED` 时必须有 `unclarified_reason`。
- **默认行为**：默认「逐项确认，一次一问」，即 `interaction_mode: synchronous_frontier`。
- **前置依赖**：D3、D7 已收敛。
- **建议字段（澄清后填写，未澄清项按默认行为取值）**：
  - `interaction_mode`: 枚举值，严格限定为 `synchronous_frontier`（同步前沿提问） | `async_questionnaire`（异步问卷收集） | `minimal_interruption`（极简免打扰模式）。
  - `interruption_threshold`: 字符串，必须固定为“仅 G 级门禁与定性裁决主动中断，其余自主闭环推进”。
- **自查准则**：默认推荐 `minimal_interruption`，降低人类认知负荷。
- **提问模板**：
  ```text
  【澄清 8/8 · 流水线交互问询模式】
  请选定后续执行中的人机交互模式：
  [选项 A] 极简免打扰模式 (minimal_interruption)：仅在 G 级人审门禁与定性争议裁决时中断等候人类，中间阶段自主推进。
  [选项 B] 同步交互模式 (synchronous_frontier)：在每个阶段汇合点主动输出阶段进展简讯。
  [Other] 自定义交互问询模式与中断阈值。
  ```

---

## 4. 停机条件、决策摘要与 G0 放行收敛协议

### 4.1 停机判定条件
仅当 Active Frontier 队列元素数量为 0 时，落地澄清流程方可停机：必须问的两类问题已得到答复（或人类明确选择跳过），且所有未答项均已登记 `clarification_status`（`NOT_CLARIFIED`／`NOT_APPLICABLE`）与 `unclarified_reason`、并按默认行为填充可执行值。严禁以「填不出内容」为由无限追问，严禁以「少于八项」为由拒绝停机。

### 4.2 决策摘要输出协议
在停机时刻，Agent 必须向人类输出一份包含八项要素决议的《决策摘要 (Decision Summary)》，格式必须严格如下：

```markdown
### 落地澄清决策摘要 (Decision Summary)
> 每项后缀澄清状态；`NOT_CLARIFIED`／`NOT_APPLICABLE` 项必须附默认行为结果与未澄清原因。
1. **研究标的与对象**：{{SUBJECT_NAME}} (边界: {{SCOPE_BOUNDARIES}}) [{{STATUS_2_2}}]
2. **项目背景与前情**：{{CONTEXT_SUMMARY}} (继承材料: {{INHERITED_MATERIALS}}) [{{STATUS_2_4}}]
3. **报告受众与偏好**：{{PRIMARY_READERS}} (偏好: {{READER_PREFERENCES}}) [{{STATUS_2_1}}]
4. **风格与基调**：{{STYLE_MODE}} / {{PERSPECTIVE}} [{{STATUS_2_3}}]
5. **交付形态约定**：{{PRIMARY_FORMAT}} / 预算: {{PAGE_BUDGET}} [{{STATUS_2_6}}]
6. **物料落盘地址**：{{LOCAL_DIR_PATH}} (交付: {{DELIVERY_DIR_PATH}}) [{{STATUS_2_5}}]
7. **事实源基准**：{{SOURCE_OF_TRUTH}} (在线启用: {{ONLINE_ENABLED}}) [{{STATUS_2_7}}]
8. **交互问询模式**：{{INTERACTION_MODE}} (阈值: 仅 G 级门禁与定性裁决中断) [{{STATUS_2_8}}]
```

### 4.3 工件生成协议
在输出决策摘要的同时，Agent 必须在工作区生成且仅生成以下两个工件：
1. `brief.md`：
   - 必须包含元数据、八项澄清小节（2.1 至 2.8）、机读诉求索引（2.9 诉求与实体索引，带 REQ-ID）、术语与口径（2.10）、继承声明与人工裁决（2.11，每条继承项必须具备 CONFIRMED 或 REVISED 裁决）、以及内嵌的「3. 项目宪法」五原则。
   - 2.1–2.8 每项必须登记 `clarification_status`；非 `CLARIFIED` 项必须登记 `unclarified_reason` 并按协议默认行为写入可执行值（如 `target_local_dir` 绝对路径、`source_of_truth` 为 `LOCAL_AUTHORITATIVE`、`interaction_mode` 为 `synchronous_frontier`）。
   - `status` 字段值必须严格设置为 `DRAFT`。
   - 必须严格计算 `brief_content_sha256`（置空该字段后，UTF-8 LF 哈希）。
2. `gates/G0-request.md`：
   - G0 放行申请单，如实填写工件路径 `brief.md` 与实际文件 SHA-256 哈希值。

### 4.4 阻断铁律与下游保护
1. **签署前零产出铁律**：在 G0 门禁处于 APPROVED 状态（无论是人类直接签署的 `human_signed`，还是人类会话授权后由 Agent 代录的 `session_transcribed`）且 `python3 scripts/gate_guard.py --gate G0 --check-only` 返回退出码 0 之前，Agent **严禁**在工作区生成任何后续阶段的文件（包括但不限于 `progress-log.md`、`task.json`、`datatable.*`、`outline.md`、`draft_full.md` 等）。
2. **裁决归属人类，记录方式可变 [SHALL]**：门禁裁决权始终归人类，Agent 永不得自行作出 APPROVED / REJECTED / CHANGES_REQUESTED 裁决。签署件存在两种记录方式：
   - **直接签署 (`human_signed`)**：人类亲手填写 `gates/G0-approval.md`。
   - **会话授权代录 (`session_transcribed`)**：人类在会话中明确授权后，Agent 依授权原话代写签署件。代录必须留下可审计溯源：`authorization_quote`（人类授权原话）、`authorization_turn`（会话与消息引用）、`authorization_at`（授权时间）、`authorized_by`（人类身份，须与 `signed_by` 一致）、`recorded_by`（代录者）。任一字段缺失、授权人写成机器身份、授权人与签署人不一致，Agent 严禁自行补写或绕过，`gate_guard.py` 将以 `AUTHORIZATION_TRACE_INCOMPLETE` 或 `AGENT_SIGNATURE_PROHIBITED` 阻断。
   - 推荐以脚本代录，避免手填哈希漂移：
     ```bash
     python3 scripts/gate_guard.py --record-approval --gate G0 --artifact brief.md --root <dir> \
       --authorized-by "<人类身份>" --authorization-quote "<人类授权原话>" \
       --authorization-turn "<会话与消息引用>" --decision APPROVED
     ```
3. **严禁伪造授权 [SHALL NOT]**：Agent 严禁在没有人类真实授权的情况下生成任何 `session_transcribed` 签署件，严禁伪造、推测或补写人类授权原话。授权原话必须逐字取自人类在会话中的实际表述。
4. **严禁代理自签 [SHALL NOT]**：`gates/<G>-approval.md` 的 `signed_by` 与 `authorized_by` 严禁包含 `agent:*` 或任何机器标识，一经发现，`gate_guard.py` 立即阻断（退出码 1）。
5. **状态阻断响应**：若 `gate_guard.py` 退出码为 1，系统必须保持挂起等候状态，严禁擅自跳过门禁向下游流转。
