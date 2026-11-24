# P3 课题拆分与调研规划协议手册 (P3 Research Decomposition & Planning Protocol)

## 0. 协议元定义与适用范围
本协议定义严谨复杂调研报告写作系统第三阶段（P3 课题拆分与调研规划）的可执行规则。
Agent 必须严格依据本协议开展多视角枚举、任务分解、DAG 拓扑构建与 Guidelines 注入。
本协议全文采用条目化、断言化句式，杜绝模糊建议词，统一使用“必须 [SHALL]”、“禁止 [SHALL NOT]”、“仅当……方可 [ONLY WHEN... THEN...]”。

---

## 1. 核心底线宪法原则

### 1.1 事实判锤与数字真实性原则
1. **禁止凭空捏造数字 [SHALL NOT]**：Agent 在拆解任务单元与规划数据指标时，禁止自行发明、估算或伪造任何具体数值；所有数值必须且仅能在 M4 阶段通过一手证据搜集或严格复算产出。
2. **严禁将待核事项作为既定事实写入任务 [SHALL NOT]**：在编写 `sub_topic`、`guidelines` 或调研目标时，严禁使用预设确定性立场的陈述句（如「论证目标市场 IDC 租用成本显著低于自建」），必须采用中立核验句式（如「核查目标市场 IDC 自建与租用机柜全生命周期成本差异」）。
3. **未定事项显式标注 [SHALL]**：凡属于外部未经证实的假设、传闻或初步线索，必须在任务中显式标注为 `待核事项`，严禁作为公理传递至下游。

### 1.2 权威事实源与归属铁律
1. **唯一输入源约束 [SHALL]**：课题拆分的唯一合法输入事实源为通过 G0 门禁放行的 `brief.md`。
2. **诉求覆盖权威归属 [SHALL]**：`target_req_ids` 的权威归属与自动化校验基准唯独处于 `task.json` 中；`research-breakdown.md` 仅作为展示与交叉引用载体，禁止作为诉求覆盖判据的判定源。

---

## 2. STORM 式多视角枚举（Persona / Perspective）驱动机制

### 2.1 视角学出与枚举前置规则
1. **同类报告先导调研 [SHALL]**：在展开任何具体课题拆分前，Agent 必须首先检索并参考 2-3 篇同领域高水平专业研报（行业行研、投行研报或技术白皮书），分析其章节组织所蕴含的切入视角。
2. **多视角正交性要求 [SHALL]**：拆解出的专家视角（Persona/Perspective）数量不得少于 3 个，且必须覆盖至少以下三个正交维度：
   - **技术与基础设施视角 (Technical / Infrastructure Perspective)**：如基础设施架构师、技术总监，重点审视技术可行性、网络拓扑、算力卡时与物理参数。
   - **合规与法律风控视角 (Regulatory / Compliance Perspective)**：如中东数据跨境合规律师、牌照审计顾问，重点审视外资准入、数据出境、牌照等级与违规罚则。
   - **商业与财务成本视角 (Commercial / Financial Perspective)**：如首席财务官、出海投资分析师，重点审视 CapEx/OpEx 拆分、ROI、现金流周期与 TCO 模型。
3. **视角对抗与盲区覆盖 [SHALL]**：各视角之间必须设立张力对照（如技术最优方案与合规阻力的冲突、自建 IDC 资本支出与租赁灵活性之间的取舍），确保无单一视角盲区。

---

## 3. 任务拆解颗粒度判据与 DAG 拓扑规范

### 3.1 拆分颗粒度判定三准则
1. **准则一：独立一手信源可达性 [SHALL]**：
   每个调研单元必须且仅能对应一组特定的一手信源族（例如一组特定的法规条文、一份公开价目表或一套官方统计公报），禁止将需跨越完全不相干信源的议题合并为一个大任务。
2. **准则二：单任务产物隔离性 [SHALL]**：
   每个任务项必须具备唯一的 `output_path`（格式规范为 `fact-store/<task_id>_*.json`），其调研结论与一手证据快照必须完全落盘于该独立路径，禁止多任务向同一文件执行并发写操作。
3. **准则三：算式与事实的原子性 [SHALL]**：
   单一任务项涵盖的核心测算指标不得超过 5 项，超出者必须进一步拆解为“基础参数采集任务”与“上层派生复算任务”。

### 3.2 依赖拓扑与 DAG 无环性硬约束
1. **无环依赖铁律 [SHALL]**：所有任务项的 `dependencies` 字段必须构成严格的有向无环图（Directed Acyclic Graph, DAG）。
2. **禁止循环依赖 [SHALL NOT]**：禁止出现任何直接或间接的闭环依赖（如 `A -> B -> A` 或 `A -> B -> C -> A`）。一经检测出环路，`scripts/task_schema_check.py` 必须立即返回非 0 退出码并中断构建流程。
3. **无悬空依赖 [SHALL]**：任务依赖数组中的所有 `task_id` 必须存在于同一 `task.json` 任务列表中，禁止指向未定义的外部 ID。

---

## 4. 数据三要素 Guidelines 注入规范

### 4.1 任务级 Guidelines 必备要素
每个调研任务单元的 `guidelines` 列表必须具备且非空，且必须明确断言以下三项数据硬约束（数据三要素）：
1. **要素一：来源出处 (Source Provenance / URL) [SHALL]**：
   - 必须明文断言该任务采信的一手信源级别（如「必须采信目标市场通信监管机构现行规章或当地持牌运营商官方公开报价单」）。
   - 严禁模糊表述（如“参考网上公开资料”）。
   - 严禁采信未经核实的二手媒体自媒体洗稿材料。
2. **要素二：取价日与基准时间 (Reference / Pricing Date) [SHALL]**：
   - 必须明文断言时间窗口（如“取价日与基准时间必须严格锁定在 2026 年 Q1”）。
   - 禁止混入未标注年份的历史过时数据。
3. **要素三：统计口径与单位 (Metric Standard & Unit) [SHALL]**：
   - 必须明文断言数值的计量口径与法定计量单位（如“统计口径与单位必须明确区分单机柜月度租金 USD/机柜/月 及工业电价 当地货币/kWh”）。
   - 严禁跨币种混算或隐式汇率折算。

### 4.2 数据需求分类 (Data Requirements Taxonomy)
每个任务单元的 `data_requirements` 数组必须为每项指标明确标注 `source_type`：
1. **`measured`**：可直接由官方一手公布文件测量或确证的硬指标。
2. **`quoted`**：市场公开报价或权威机构公开标价。
3. **`derived`**：依据确定性算术公式由其他已采信指标推导出的指标。
4. **`estimated`**：基于特定假设前提推测的指标。
   - **铁律 [SHALL]**：仅当 `source_type == "estimated"` 时，必须提供非空的 `assumption_tag`（如 `ASSUMP_PUE_1_35`），并在正文中保留显式假设声明；禁止任何未注假设 tag 的裸数字进入数据需求。

---

## 5. 诉求与实体索引 (REQ-ID) 100% 覆盖闭环铁律

### 5.1 覆盖完整性判据
1. **100% 覆盖约束 [SHALL]**：
   `task.json` 中所有任务项的 `target_req_ids` 之并集，必须 100% 包含 `brief.md`「2.9 诉求与实体索引」小节中声明的全部 `REQ-ID`。
2. **零悬空诉求 [SHALL]**：
   差集 `(brief_req_ids - task_req_ids)` 必须严格为空集（`uncovered_req_ids == []`，`coverage_ratio == 1.0`）。
3. **机器判锤可判定性 [SHALL]**：
   运行 `python3 scripts/task_schema_check.py task.json --req-index brief.md --coverage`，必须返回退出码 0 与 `{"uncovered_req_ids":[],"coverage_ratio":1.0}`。若有任一 REQ-ID 遗漏，脚本必须返回退出码 1 并阻断流水线向 M4/M5 流转。

---

## 6. 工件产出与下游交接

### 6.1 阶段产出清单与校验
仅当以下条件全部满足时，P3 阶段方可宣布构建完成并触发下游：
1. `src/schemas/task.schema.json` 语法完备且支持全部必备字段。
2. `src/templates/task_json.template.json` 具备 2-3 个符合出海研报标准的示例任务。
3. `src/templates/research_breakdown.template.md` 包含多视角推导、任务树、映射矩阵与 Guidelines 说明。
4. 运行 `python3 scripts/task_schema_check.py task.json --schema schemas/task.schema.json` 校验通过（退出码 0）。
5. 运行 `python3 scripts/task_schema_check.py task.json --req-index brief.md --coverage` 校验通过（退出码 0）。

### 6.2 触发 M4 与 M5 双轨并发
- **M4 并行事实调研线**：消费 `task.json`，调度子代理并行检索一手事实，启动底表构建与 `fact-store/` 快照归档。
- **M5 章节架构规划线**：只读消费 `task.json` 与 `brief.md`，启动大纲规划与 G1 门禁准备。

---

## 7. 子 Skill 委派接口与并发控制契约 (Sub-Skill Delegation & Concurrency Contract)

为支持将颗粒化调研单元委派给独立子代理或专用子 skill 执行，确立以下标准委派接口契约：

### 7.1 子 Skill 委派输入契约 (Input Interface)
委派给子 skill 的输入必须 [SHALL] 严格限定为以下最小必要信息包，禁止传递无约束的全局上文：
1. **单任务项声明**：`task.json` 中对应的单一任务项对象（包含 `task_id`、`sub_topic`、`perspective`、`guidelines`、`target_req_ids`）。
2. **关联 brief 片段**：`brief.md` 中与该任务声明的 `target_req_ids` 直接关联的小节切片。
3. **证据索引只读视图**：当前 `evidence-index.md` 快照只读视图（用于防止重复检索相同信源）。

### 7.2 子 Skill 产出契约 (Output Interface)
子 skill 执行完成后，必须 [SHALL] 且仅能输出以下规范产物：
1. **原始材料快照**：落盘至 `fact-store/<task_id>/` 独立子目录下的一手原始文件/网页/文献快照，并附带 SHA-256 哈希存证。
2. **结构化调研结果**：遵循统一 JSON 结构，包含提取的指标名称、数值、计量单位、取价日、一手信源 URL/页码及 `source_type`。
3. **待核与未决清单**：凡调研中无法确证或存在信源冲突的事项，必须在独立清单中显式登记，禁止隐式丢弃。

### 7.3 权限与隔离边界 (Permission Boundaries)
1. **只读权限约束**：子 skill 对 `brief.md`、`guidelines.md` 及全局 `evidence-index.md` 仅具备严格只读权限。
2. **三禁止铁律 [SHALL NOT]**：
   - 严禁 [SHALL NOT] 写入或修改治理台账 `progress-log.md`；
   - 严禁 [SHALL NOT] 直接修改主数据底表 `datatable.csv` / `datatable.md`；
   - 严禁 [SHALL NOT] 越出本任务边界改动或生成其他章节/任务文件。

### 7.4 验收与失败处理协议 (Acceptance & Error Handling)
1. **双重验收机制**：
   - 第一重：调用 `audit_calc.py` 对子 skill 输出的公式列执行代码级算术复算（tolerance 容差内）；
   - 第二重：纳入边界 1（数据底表）独立对抗复核，由隔离评审者核验一手原文 chunk 对应性。
2. **失败处理铁律**：
   - 子 skill 严禁 [SHALL NOT] 自评通过；
   - 严禁 [SHALL NOT] 静默丢弃未决项或因时限用伪造数据充数；凡未决项必须显式标为待核并抛出给主调度器处理。

### 7.5 单写入节点合并与并发互斥铁律 (Concurrency Axiom)
1. **单写入节点聚合**：所有子 skill 产出的结构化数据片段，必须 [SHALL] 汇总至主调度器的唯一单写入节点统一校验后合并入库。
2. **禁止并发写同一底表行 [SHALL NOT]**：严禁多个子代理或子 skill 并发写同一底表行。各任务必须以各自独立路径隔离输出，由主写入节点串行合并写入底表。
