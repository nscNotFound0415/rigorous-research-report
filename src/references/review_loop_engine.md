# 对抗复核循环引擎协议手册 (Adversarial Review Loop Protocol)

本协议定义跨边界通用对抗复核循环的标准执行规程、隔离要求、缺陷四档分流准则、定性留人原则、四层回读复验算法与降级阶梯出口红线。本协议在三个关键产出边界（数据底表、章节大纲、合稿全文）复用执行。

---

## 1. 架构定位与标准复核五步循环

系统在关键工件跨入下一阶段前，必须 [SHALL] 组织独立对抗复核，防止事实性缺陷、引用漂移与自洽盲区向下游级联传导。

```text
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │  产生候选产物  │ ──> │  独立异族审查  │ ──> │  四档分流评级  │ ──> │ 人类裁决与改稿 │ ──> │ 四层回读复验 │
 └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                                            │
                                                       [D0 > 0 或回读失败: 打回返工]            │
                                                       ▲────────────────────────────────────┘
                                                       │
                                                       ▼ [D0 = 0 且回读全过 且 G 门禁放行]
                                              ┌──────────────────┐
                                              │ 允许跨入下游下一阶段 │
                                              └──────────────────┘
```

### 1.1 五步循环操作定义
1. **第一步：产生候选产物 (Generate Candidate Artifact)**
   - 撰写节点完成当前边界任务后，产出候选物料（`datatable.csv` / `outline.md` / `draft_full.md`）。
   - 调度器锁定候选物料，计算并记录二进制 `content_sha256`。
2. **第二步：独立异族审查 (Independent Adversarial Review)**
   - 调度器唤醒与撰写节点完全隔离的独立审查实例。
   - 审查者必须 [SHALL] 运行于严格只读沙箱，严禁 [SHALL NOT] 拥有对受审物料的写权限。
   - 复核调用证明必须 [SHALL] 记录于 `review-reports/<boundary>_provenance.json`。
3. **第三步：四档分流评级 (Four-Tier Defect Triage)**
   - 审查者仅依据“一手原文比对”与“纯代码算术复算”判定缺陷实锤。
   - 审查者必须 [SHALL] 将检出问题分流为 D0、D1、D2、D3 四档，输出 `review-reports/<boundary>_review.md`，附带阅读覆盖声明与盲区说明。
4. **第四步：人类裁决与改稿 (Human Gate Adjudication & Patching)**
   - 调度器基于复核报告生成《纠错对照稿》（`correction-diff.md`）与 G2 放行申请（`gates/G2-request.md`）。
   - 定性裁决权严格归人类所有，严禁 [SHALL NOT] 由 Agent 代裁数据是删除还是降级。
   - 仅当 [ONLY WHEN] 获得人类在 `gates/G2-approval.md` 签署批准后，指定写入节点方可 [THEN] 执行局部精准替换。
5. **第五步：四层回读复验 (Four-Layer Readback Verification)**
   - 写入完成后，系统必须 [SHALL] 调用 `scripts/verify_readback.py` 验证新句在位、旧句零残留、结构块数一致及双哈希匹配。
   - 仅当 [ONLY WHEN] D0 缺陷数为 0、回读复验四层全部通过且人类签署放行时，方可 [THEN] 跨入下游阶段。

---

## 2. 审者隔离要求与防伪证明规范 (Provenance)

### 2.1 隔离性硬约束
1. **会话互斥铁律**：复核者会话 ID 与撰写者会话 ID 必须 [SHALL] 严格不同（`writer.session ≠ reviewer.session`）。严禁 [SHALL NOT] 由撰写正文的同一个 Sub-agent 会话实例自我复核。
2. **模型异族优先**：系统必须 [SHALL] 优先采用跨厂商前缀的异族模型通道（如 Claude 与 DeepSeek / GPT / Gemini 交叉互审）。
3. **同族零记忆隔离**：仅当 [ONLY WHEN] 异族通道受限时，方可 [THEN] 降级至同族模型；但复核子进程必须 [SHALL] 彻底清空全部历史上下文（`context_reset = true`），采用全新临时 session，严禁 [SHALL NOT] 继承撰写阶段的对话历史或思考缓存（Thinking Cache）。
4. **只读沙箱保障**：复核者权限必须 [SHALL] 强制设为只读沙箱，复核者产出物仅限复核报告与证明文件，禁止 [SHALL NOT] 直接写回被审物料。

### 2.2 复核证明数据契约 (`review-reports/<boundary>_provenance.json`)
每次复核必须 [SHALL] 产出合规 JSON 记录：
```json
{
  "boundary": "datatable|outline|draft_full",
  "review_timestamp": "ISO8601",
  "target_artifact": "path/to/artifact",
  "target_artifact_sha256": "64_char_hex",
  "writer": {
    "model": "model_identifier",
    "session": "session_id",
    "agent": "agent_role_or_id"
  },
  "reviewer": {
    "model": "model_identifier",
    "session": "distinct_session_id",
    "agent": "reviewer_agent_role",
    "channel": "异族|同族-零记忆隔离",
    "context_reset": true
  },
  "read_only_verified": true
}
```
**判定断言契约 [CRITERION M6-2]**：
- `writer.session ≠ reviewer.session`；
- 当 `channel = "异族"` 时，`writer.model` 与 `reviewer.model` 的厂商前缀（如 `gpt-`、`claude-`、`deepseek-`、`gemini-`、`minimax-`、`qwen-` 等）必须 [SHALL] 不同；
- 当 `channel = "同族-零记忆隔离"` 时，`reviewer.context_reset` 必须 [SHALL] 为 `true`，且 `reviewer.session` 为新建独立会话；
- 仅在 Markdown 报告中文字声明“已隔离”不构成通过依据；必须通过 `scripts/gate_guard.py --check-provenance <file>`（或 `verify_readback.py --check-provenance <file>`）验证。任一条件不满足，退出码为 1。

---

## 3. 事实判锤通路与四档分流体系

### 3.1 事实判锤唯二通路与 D0 严格判定契约
评判报告内容是否存在事实性错误，只允许走以下两条客观通路，严禁 [SHALL NOT] 基于大模型主观“语感”或“常识常理”空泛挑刺；**D0 级已证实错误严格仅限以下两类，每条检出记录必须 [SHALL] 包含非空的 `route` 字段**：
1. **通路一：一手原文比对 (`route: QUOTE_MISMATCH`)**
   - 将文中断言与 `fact-store/` 中留存的一手原始文献/网页快照逐句比对。若数字、单位、主体、时间范围与一手原文不符，判定为实锤错误。每条记录必须附原文 chunk ID 与不一致片段；若引用的 chunk ID 在 fact-store 中不存在，亦记为 `QUOTE_MISMATCH` 且标 `NOT_FOUND`。
2. **通路二：纯代码算术复算 (`route: ARITH`)**
   - 提取文中所涉公式、合计值、毛利率、比率变动，通过纯 Python 代码执行数学算术复算。若复算结果超出容差声明（`tolerance`），判定为实锤错误。每条记录必须附复算命令与输出行。
3. **不可判定项降级禁令 [SHALL NOT]**：
   - 「方向性逻辑相反」、「未声明的主观臆测」等无法由上述两条通路客观判定的主观逻辑争议，**严禁 [SHALL NOT] 列为 D0 错误**，必须 [SHALL] 降为 D1（证据不足）或 D3（待核 T 项）。

### 3.2 证据不足≠事实错误与 D1 定性留人公理
- 审查者必须 [SHALL] 严格区分“证实有错”与“证据不足”。
- 凡无法证明为假、但缺乏一手信源或仅有二手转述的断言，禁止 [SHALL NOT] 直接当作 D0 错误删除，而必须 [SHALL] 归类为 **D1（证据不足）**。
- **D1 处置定性留人铁律**：
  - 对于 D1 缺陷，审查单与《纠错对照稿》必须 [SHALL] 同时列出两个选项（选项 A：补证；选项 B：降级为推测/待证实并在正文加注 `[假设: 待一手证实]`），并标注倾向性推荐项。
  - **最终处置由 G2 门禁人类操作者排他裁决，机器严禁 [SHALL NOT] 自行决定降级、严禁擅自自动改写**。

### 3.3 四档缺陷分流标准 (D0 - D3)
缺陷级别统一采用 D0 至 D3 编码（消解与阶段 P1-P6 编号冲突）：

| 缺陷级别 | 级别名称 | 严格判定条件 | 标准处置动作 | 门禁阻断效力 |
|:---:|:---:|---|---|:---:|
| **D0** | **已证实错误**<br>(Confirmed Error) | 严格仅限两类客观通路（必带 `route` 字段）：<br>1. 纯代码算术复算错误（`ARITH`）；<br>2. 篡改或曲解一手原文引用，或 chunk 缺失（`QUOTE_MISMATCH`）。 | 强制纳入《纠错对照稿》，必须局部更正或彻底删除。 | **强阻断**：D0 > 0 时严禁跨入下游阶段。 |
| **D1** | **证据不足**<br>(Insufficient Evidence) | 1. 结论逻辑自洽但无一手信源存证；<br>2. 引用二手媒体转述未核查母源；<br>3. 方向性逻辑相反或未声明的主观臆测；<br>4. 缺乏取价日、时间范围或统计单位。 | 列出两个选项（补证｜降级为推测）并标注推荐项，由 G2 人类裁决；机器严禁自动降级或改写。 | **条件放行**：经 G2 人类裁决放行。 |
| **D2** | **材料冲突**<br>(Conflicting Sources) | 两个或多个权威信源对同一指标给出相互矛盾的数字或统计口径（如 IDC 与 Gartner 数据偏差）。 | 严禁主观二选一或擅自取平均数；必须设立分栏对比，列示各自出处与口径差异。 | **条件放行**：完成分栏对比并经人类确认后放行。 |
| **D3** | **待核 T 项**<br>(Unverified Items) | 超出当前既定调研边界的未闭环事项、企业未披露信息或政府尚未出台之监管细则。 | **只标注不改数**；正文保留占位并统一录入待核 T 项清单挂牌留存。 | **放行**：记入台账挂牌追踪。 |

---

## 4. 覆盖声明与盲区披露规范

复核报告必须 [SHALL] 包含显式的阅读覆盖度与盲区声明，审者必须真实披露：
1. **全文深读物料 (Deep-read)**：审者逐行审阅、比对代码与快照的核心物料列表。
2. **定向扫描物料 (Targeted Scan)**：审者仅依据正则、关键词或断言表进行局部探针扫描的物料。
3. **未读与盲区物料 (Unread / Blind Spots)**：因权限、上下文窗口或信源不可达而未能核验的领域。
严禁 [SHALL NOT] 产出未经覆盖声明的虚假全能复核报告。

---

## 5. 定性裁决权留给人类与 G2 门禁

1. **定性裁决人类排他原则**：
   - 项目宪法原则明确规定“定性裁决权归人类”。当遇到数据争议、信源缺失或敏感推论时，处理方式究竟是“彻底删除”、“降级为假设”、“设立上限情景”还是“列入附录”，定性裁决权归人类，人类操作者拥有排他裁决权。
   - Agent 仅可 [ONLY WHEN] 在《纠错对照稿》（`correction-diff.md`）中给出倾向性分析与处置建议，严禁 [SHALL NOT] 越权擅自替人类拍板定性。
2. **G2 门禁防伪放行流程**：
   - 调度器生成 `gates/G2-request.md`，汇总待裁决条目与哈希；
   - 人类操作者作出裁决，并在 `gates/G2-approval.md` 中填写裁决口令与决策（`APPROVED`）；亦可在会话中明确授权，由 Agent 依授权原话代录签署件，并留下 `authorization_quote`、`authorization_turn`、`authorization_at`、`authorized_by`、`recorded_by` 五个溯源字段；
   - `scripts/gate_guard.py --gate G2 --verify --artifact correction-diff.md --approval gates/G2-approval.md` 校验通过后，纠错写入方获合法授权。
3. **桩签署件硬拒绝语义（G 门禁统一）**：
   - 门禁只接受真实人类签署件。任何在签署件中声明 `stub: true`（或 `stub:true`）的演练桩、样板件、自动生成件，一律判定为 `STUB_REJECTED`、`blocked=true`、退出码 1，即使其 `artifact_sha256` 完全吻合也绝不放行。
   - 该硬校验由 G0/G1/G2/G3/change-<id> 五个门禁共用。测试夹具中被用于验证「放行路径」的签署件，必须是符合人类签署格式且**不含 stub 标记**的人类格式夹具，并在测试 README 中明确声明「该夹具仅用于验证放行路径，不代表真实人类签署」。

---

## 6. 四层回读复验算法与零漂移比对

指定写入节点根据批准的《纠错对照稿》完成局部替换后，必须 [SHALL] 立即运行确定性复验脚本：
```bash
python3 scripts/verify_readback.py --plan correction-diff.md --target <target_file>
```

### 6.1 四层回读判定算法
脚本必须 [SHALL] 串行执行以下四层校验，任一层失败即判定整体失败（退出码 1）：
- **第 1 层：新句在位 (Layer 1 - New Sentences Present)**
  - 算法：遍历对照稿中所有经批准的条目，提取 `拟改为` 文本。
  - 断言：目标文件中必须 [SHALL] 100% 检索到每一条新语句文本。
- **第 2 层：旧句零残留 (Layer 2 - Zero Old Sentence Residuals)**
  - 算法：提取对照稿中所有判定为 D0 或批准替换的 `原文` 语句。
  - 断言：目标文件中上述旧语句的出现次数必须 [SHALL] 严格为 0。
- **第 3 层：结构块数保真 (Layer 3 - Structural Block Counts)**
  - 算法：解析目标工件的 Markdown 结构块（标题总数 `^#{1,6}\s+`、表格总数、段落总数）。
  - 断言：实际块数与对照稿第 2 节中声明的期望块数（`expected_headings`、`expected_tables` 等）完全一致，确保版面结构未被破坏。
- **第 4 层：双哈希精准匹配 (Layer 4 - Dual Hash Match)**
  - 算法：计算目标工件的二进制文件哈希 `content_sha256` 与去除格式符号后的正文净文本哈希 `nettext_sha256`。
  - 断言：实际哈希与对照稿中声明的 `expected_content_sha256` 与 `expected_nettext_sha256` 逐字节吻合。

### 6.2 零漂移比对模式 (`--diff-mode`)
在版本更新或变更回路中，运行：
```bash
python3 scripts/verify_readback.py --diff-mode --old <old_file> --new <new_file> --declared <id>
```
- **判定断言**：除声明修改的块（由 `--declared <id>` 标识）外，其他所有未声明区域的字符级漂移必须 [SHALL] 为 0（`undeclared_drift == 0`）。若检出任何未声明区域被改动，退出码必须为 1，阻断发布。

---

## 7. 三级复核降级阶梯与出口红线

为应对网络波动、异族通道欠费或模型限流等极端故障，系统设立三级降级阶梯：

```text
  [第 1 级: 最优态] 跨厂商异族模型通道 (Claude + GPT/DeepSeek 交叉对抗)
         │
         ▼ (异族通道不可用)
  [第 2 级: 次优态] 同模型零记忆隔离复核 (清空上下文 + 独立临时会话 + context_reset=true)
         │
         ▼ (LLM 复核全面受阻)
  [第 3 级: 补充态] 纯 Python 规则代码扫描 (audit_calc / text_hygiene / citation_check)
         │
         ▼ (出口红线拦截)
  【硬性阻断】第 3 级不构成出口条件！工件标记 BLOCKED_NO_REVIEWER，严禁向下游放行。
```

### 7.1 降级阶梯出口硬红线
1. **第 3 级仅为补充，绝不构成出口条件**：
   - 纯 Python 规则扫描（算术复算、三要素检查、违禁词扫描）是机械级防线，无法替代语义级对抗复核。
   - 仅通过第 3 级规则扫描但缺失第 1 级或第 2 级 LLM 复核的工件，**严禁跨入下游阶段**。
2. **缺失审者阻断标记**：
   - 若异族与同族隔离复核均不可用，调度器必须 [SHALL] 将该边界状态显式标记为 `BLOCKED_NO_REVIEWER`，立即挂起并向人类告警。
   - 严禁 [SHALL NOT] 伪造复核证明，严禁 [SHALL NOT] 以“规则扫描全部通过”为借口自评放行。

---

## 8. 三个关键产出边界的特化执行差异

标准复核五步循环在三个关键边界复用，但检查焦点与硬门禁各有特化：

| 边界维度 | 边界 1：数据底表 (`datatable`) | 边界 2：大纲与任务 (`outline`) | 边界 3：合稿全文 (`draft_full`) |
|---|---|---|---|
| **复核工件** | `datatable.csv` / `datatable.md`<br>`fact-store/` 快照 | `outline.md`<br>`task.json`<br>`brief.md` | `draft_full.md`<br>`datatable.csv`<br>`evidence-index.md` |
| **触发时机** | M4 调研完成，底表组装完毕后 | M5 章节规划完成，合稿启动前 | M7 首次单次合稿成型与 Polish 后 |
| **复核核心焦点** | 1. 纯代码算术复算（`audit_calc.py`）；<br>2. 口径分栏严格隔离（严禁跨口径相减）；<br>3. 一手信源可溯源性与取价日完整性；<br>4. `source_type=estimated` 时 `assumption_tag` 非空。 | 1. 视角枚举完整性（100% 覆盖 brief 中的 REQ-ID）；<br>2. 章节依赖 DAG 无环；<br>3. 规划引用与底表映射（evidence_ref）；<br>4. 待补数据 PENDING 清单集中管理。 | 1. 事实一致性（正文数字 100% 契合底表）；<br>2. 文本卫生性（`audit_text_hygiene.py` 扫描元叙述且受白名单保护）；<br>3. 正文引用一手原文 chunk 精准锚定；<br>4. 图表连续无断号。 |
| **定性裁决重点** | 异常数据点是剔除、重搜还是加设上限情景 | 争议章节是合并、拆分还是降级为附录 | 敏感推论是彻底删除还是加注假设声明 |
| **出口放行硬门禁** | 1. D0 = 0；<br>2. 底表算术 0 误差；<br>3. 无出处裸数字为 0；<br>4. 有效 `datatable_provenance.json`。 | 1. G1 门禁签署完成 (`gates/G1-approval.md`)；<br>2. PENDING 待补数据归零；<br>3. 有效 `outline_provenance.json`。 | 1. D0 = 0；<br>2. 卫生扫描 0 违规；<br>3. 四层回读复验全过；<br>4. G2 与 G3 门禁签署完成；<br>5. 有效 `draft_full_provenance.json`。 |

---

## 9. 异常处置与回路反拨 (Rollback & Escalation)

1. **复核未通过反拨流程**：
   - 边界 1 复核失败：回拨至 M4 事实调研子代理，重新核实一手信源或修正计算公式。
   - 边界 2 复核失败：回拨至 M5 大纲规划节点，重构章节依赖或补齐 REQ-ID 覆盖映射。
   - 边界 3 复核失败：回拨至 M7 写入节点，编制 `correction-diff.md`，提交 G2 人审裁决并执行回读复验。
2. **回读复验失败处置**：
   - 若 `verify_readback.py` 报错（新句缺失、旧句残留、块数不符或哈希漂移），写入操作视为失败，系统必须 [SHALL] 自动以备份母本回滚，严禁带病向下游交付。
