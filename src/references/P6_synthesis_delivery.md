# P6 统一合稿与多格式交付协议手册 (P6 Monolithic Drafting & Multi-format Delivery Protocol)

## 0. 协议元定义与适用范围
本协议定义严谨复杂调研报告写作系统第六阶段（P6 统一合稿与多格式交付）的可执行规范。
Agent 与人类操作者在组织全文合稿、执行一致性打磨、清除 AI 痕迹、直写 OOXML 构建 Word 与 PDF 交付物、执行 TOC 两遍法及交付回读校验时，必须严格遵守本协议。
本协议全文采用“必须 [SHALL]”、“禁止 [SHALL NOT]”、“仅当……方可 [ONLY WHEN... THEN...]”等绝对断言句式。

---

## 1. 调研并行与单次合稿铁律 (Monolithic Drafting)

### 1.1 单次成型原则
1. **单次全文合稿铁律 [SHALL]**：事实调研与分视角探究允许并行开展，但最终合稿必须由统一的写者模型执行单次成型（Monolithic Draft），输出全篇唯一母本 `draft_full.md`。
2. **严禁分节拼接 [SHALL NOT]**：严禁调度多个子 Agent 各自撰写章节后再进行简单文件拼接（Concatenation）。历史教训证实，分节拼接必然引发各章文风割裂、口径自相矛盾、退役数值残留与交叉引用断号。
3. **前置门禁约束 [ONLY WHEN... THEN...]**：仅当数据底表 `datatable.csv` 经 M6 对抗复核达到 D0=0，且大纲 `outline.md` 获人类签署 `gates/G1-approval.md`（Join 2 汇合）后，方可启动 P6 单次合稿流程。

---

## 2. STORM 式 Polish 全文一致性遍历协议

### 2.1 全文数据与术语一致性
1. **术语全篇统一 [SHALL]**：全文必须维护统一的专业名词术语表。禁止在同一报告中对同一概念混用不同命名（例如对“单卡吞吐”与“卡时产出率”等概念必须统一术语与符号）。
2. **摘要与正文数据绝对吻合 [SHALL]**：执行摘要（Executive Summary）与各章节导语中出现的所有核心指标、测算金额与结论评级，必须与正文及底表数据逐字逐句逐位吻合，严禁摘要出现正文未支撑的数字。
3. **交叉引用与编号闭环 [SHALL]**：全篇正文中引用的所有一手证据 ID 必须在 `evidence-index.md` 中完全存在；所有插图与表格必须连续编号，严禁断号或悬空引用。

### 2.2 章节间去重判据 (Section Deduplication)
1. **去重判据约束 [SHALL]**：整份报告任意两个独立章节（Section）之间，共享的连续字符子串长度必须严格小于 30 字符。
2. **严禁复读式堆砌 [SHALL NOT]**：严禁在后文章节复制粘贴前文的背景陈述、论证过程或分析段落；重复表述必须通过正规交叉引用（如“参见第 X.Y 节”）替代。

---

## 3. AI 痕迹清理与文本卫生扫描协议

### 3.1 三类 AI 痕迹穷尽清理
1. **臆测数字与过程占位符清理 [SHALL]**：必须彻底清除所有“待填”、“待核”、“母稿”、“过程稿”等草稿标识，以及历史已废弃的臆测数值。
2. **元叙述类表述清理 [SHALL]**：必须彻底清除指向文档外前置材料或报告写作过程的元叙述（如“如前所述”、“本报告下一阶段”、“前面已经分析”、“前轮内部测算采用的…”、“不再作为本报告参照”、“项目历史材料”）。报告的职责是给出客观结论，严禁把修订历史当成正文陈述。
3. **自述型表述清理 [SHALL]**：必须彻底清除以报告姿态代替结论的主观表述（如“我们认为”、“经我核查”、“我已确认”、“本报告不下…”、“本报告不给出…”、“本章不重复论证”）。此类句子不提供任何事实增量，必须改写为基于事实证据的直接陈述。
4. **AI 腔空洞黑话清理 [SHALL]**：清除“第一性原理”、“赋能”、“抓手”、“打通底层逻辑”等泛化词汇；对“闭环”等词汇，仅在具备严密控制工程或业务流程闭环上下文时方可保留。

### 3.2 9 类必要严谨性声明白名单保护
1. **白名单保护机制 [SHALL]**：运行 `scripts/audit_text_hygiene.py` 时，必须加载 `src/templates/forbidden_terms.json` 中的 `allowlist`，对项目既有的 9 类必要严谨性声明实施零误报保护：
   - A-01: 不得跨口径相减（跨口径隔离声明）
   - A-02: 不是发布数据 / 不是厂商或平台发布的数据（非官方发布数据声明）
   - A-03: 不构成法律意见（法务免责声明）
   - A-04: 情景假设，非预测 / 情景测算（测算性质声明）
   - A-05: 不构成对全部品类与全部时点的普遍结论（样本局限性声明）
   - A-06: 不得以数量拆分规避（合规界限声明）
   - A-07: 不构成降价或涨价的事实（价格事实界定声明）
   - A-08: 不能与单一输出挂牌价相减得出毛利（毛利核算禁止相减声明）
   - A-09: 不重复正文叙述 / 仅供参考，不作为承诺（范围与文风界定声明）
2. **严谨性声明完好铁律 [SHALL]**：文本清洗严禁伤及上述 9 类严谨性声明；任何因机械过滤导致严谨性声明缺失的草稿均判定为不合格。

### 3.3 阴性对照要求 (Negative Control)
1. **强制阴性对照机制 [SHALL]**：系统每新增或维护一项文本校验规则，必须同时配备至少一条阴性对照用例（传入包含已知历史缺陷的旧料，断言新校验脚本必须精确报错并阻断）。
2. **测试夹具要求 [SHALL]**：`tests/module_tests/test_m7_delivery/fixtures/` 必须常态化固化 `dirty_meta_draft.md`（注入 5 处违规元叙述且含 9 类白名单声明）与 `broken_citation_draft.md`（含虚构引用与断号图表）。

---

## 4. 交付文档构建引擎与 TOC 两遍法规范

### 4.1 单源母本与直写 OOXML
1. **唯一母源铁律 [SHALL]**：全报告交付物必须以 `draft_full.md` 为唯一数据母源。
2. **禁止 pandoc 直出 [SHALL NOT]**：严禁使用 pandoc 直出 docx 或 pdf（防止复杂表格、自适应页边距与多级标题样式坍塌）。
3. **标准库直写 OOXML [SHALL]**：Word 交付件必须由 `scripts/build_docx.py` 纯标准库直写标准 Office Open XML（document.xml, styles.xml, numbering.xml 等），并同时产出各部件 SHA256 清单 `build_manifest.json`。

### 4.2 无损转 PDF 与优雅降级
1. **系统预装调用 [SHALL]**：PDF 构建必须通过 `scripts/build_pdf.py` 调用系统预装之 `soffice --headless --convert-to pdf` 执行无损导出。
2. **优雅降级原则 [SHALL]**：若系统环境未预装 soffice，脚本必须输出 JSON `{"pdf":false,"reason":"soffice_unavailable"}` 并返回退出码 0，严禁通过任何手段伪造假 PDF。降级时退出码为 0，调用方必须解析 JSON 字段 `pdf` 判定，禁止仅凭退出码判定成功。
3. **CJK 字体依赖 [SHALL]**：PDF 生成环境必须安装中文字体（Debian/Ubuntu：`fonts-noto-cjk`；macOS/Windows 自带中文字体）。缺字体时 soffice 以替代字形渲染，PDF 文本层将丢失中文字形，目录两遍法与回读校验均无法定位标题。CI 与容器镜像必须显式安装该字体。
4. **文本层预检与风险提示 [SHALL]**：`build_pdf.py` 在 PDF 生成成功后必须比对「源 docx 文本」与「生成 PDF 文本层」的 CJK 字符占比。若源文本含 CJK 而 PDF 文本层几乎不含 CJK，则 PDF 已生成（`pdf:true`）但必须附加
   `"text_layer_warning":"pdf_text_layer_lost_cjk"` 与含 `hint` 的 `text_layer_diagnostic`。严禁把文本层不可靠的产物静默当作正常成功交付。

### 4.3 TOC 两遍法 (TOC Two-Pass)
1. **两遍法执行流程 [SHALL]**：
   - 第一遍：`build_docx.py` 解析全篇章节标题，生成带有标准 TOC 目录样式与占位页码的初版 docx；
   - 转换：调用 `build_pdf.py` 生成物理排版 PDF；
   - 第二遍：`scripts/toc_two_pass.py` 提取 PDF 物理页面文本，精准确定各标题首现的物理页码，回填至 docx 目录项中。
2. **消除目录与页码漂移 [SHALL]**：回填后，docx 目录展示页码与 PDF 实际页码必须 100% 逐字逐项吻合。

---

## 5. 交付回读核验与构建确定性规范

### 5.1 双向回读差集校验
1. **双向差集全空铁律 [SHALL]**：运行 `python3 scripts/delivery_readback.py --docx <docx> --pdf <pdf> --source draft_full.md --out delivery_readback.json`：
   - `toc_minus_headings` 必须为空数组 `[]`；
   - `headings_minus_toc` 必须为空数组 `[]`；
   - 系统判定标准为“有序集合完全一致”，严禁仅以“条目数量相等”作为放行依据。
2. **页码零倒挂 [SHALL]**：PDF 可用时，`page_mismatch` 必须为空数组 `[]`；PDF 缺失时，必须显式标为 `"skipped_no_pdf"`，退出码为 0，严禁虚假放行。降级时退出码为 0，调用方必须解析 JSON 字段 `page_mismatch` 判定，禁止仅凭退出码判定成功。
3. **标题无法定位的归因 [SHALL]**：当存在无法定位的目录条目时，`toc_two_pass.py` 必须区分两类失败：目录条目 CJK 占比 >= 0.05 而 PDF 正文文本层 CJK 占比 < 0.01 时，返回 `reason:"pdf_text_layer_lost_cjk"` 并附带 `diagnostic.hint`（提示安装 CJK 字体）；其余情况返回 `reason:"unresolved_toc_entries"` 且同样附带 `diagnostic`（含两侧 CJK 占比）。两种情形均退出码 1，且严禁写入猜测页码。
4. **回读侧同源诊断 [SHALL]**：`delivery_readback.py` 遇到同一征候时，必须在 `page_mismatch` 之外输出 `text_layer_diagnostic`（含 `hint`）并退出码 1，使「N 条目录项找不到」的报错可归因于缺字体而非正文缺失。

### 5.2 构建幂等性验证 (Idempotency)
1. **部件哈希一致性 [SHALL]**：对同一份单源草稿 `draft_full.md` 连续执行两次完整构建，生成的 `build_manifest.json` 中各 OOXML 部件 SHA256 哈希值必须 100% 逐字节相同。任何含有随机数、未受控时间戳漂移的构建器一律判定为不合格。

---

## 6. G3 交付放行门禁与交付参数规范

### 6.1 G3 交付终审门禁
1. **人类排他裁决 [SHALL]**：G3 交付放行单 `gates/G3-approval.md` 的放行裁决必须由人类作出，包含确认口令与被放行文件实际哈希，Agent 严禁自行裁决或伪造放行单。签署件有两种记录方式：人类直接手工签署；或人类在会话中明确授权后由 Agent 依授权原话代录，并在签署件中留下 `authorization_quote`、`authorization_turn`、`authorization_at`、`authorized_by`、`recorded_by` 五个溯源字段。
2. **放行前置条件 [ONLY WHEN... THEN...]**：仅当满足下列全部条件时，方可提请 G3 终审放行：
   - M6 全文复核报告 `review-reports/draft_full_review.md` 确认 D0=0；
   - 文本卫生扫描 `audit_text_hygiene.py` 确认 violations 违规计数为 0；
   - 引用核验 `citation_check.py` 确认悬空引用与断号计数为 0；
   - 交付回读 `delivery_readback.py` 确认双向差集全空且页码匹配；
   - 连续两次构建 `build_manifest.json` 部件哈希 100% 一致。

### 6.2 交付参数显式约定
1. **交付目的地与形式 [SHALL]**：在 `brief.md` 与交付申请件中必须显式登记交付包落盘路径（默认 `delivery/` 目录）、交付形式（正式汇报版 Word 与只读审阅版 PDF）及版本命名标识。
