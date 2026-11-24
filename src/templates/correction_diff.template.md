# 纠错与修改对照稿 (Correction Diff Plan)

> **宪法底线与定性裁决公理 (Axiom on Qualitative Adjudication)**：
> 1. **定性裁决权归人类**：涉及数据点与结论是“直接删除”还是“降级为假设/设立上限”，定性裁决权严格归人类所有，AI 与自动化脚本严禁越权代裁。
> 2. **局部更新与零推倒**：必须由指定写入节点依据人类审批后的对照稿执行局部精准替换，严禁黑盒推倒重写全篇。
> 3. **回读四层必验**：替换后必须运行 `verify_readback.py` 验证新句在位、旧句零残留、结构块数一致及双哈希匹配。

---

## 1. 纠错元信息与门禁关联 (Correction Meta & Gate Binding)

- plan_id: {{CORRECTION_PLAN_ID}}               # 纠错对照稿唯一标识符
- boundary: {{BOUNDARY}}                         # 对应边界: datatable | outline | draft_full
- target_artifact_path: "{{TARGET_ARTIFACT}}"   # 待纠错目标工件相对路径
- source_review_report: "{{REVIEW_REPORT_PATH}}" # 依据的独立复核报告路径
- created_at: {{CREATED_TIMESTAMP}}              # 创建时间 ISO 8601
- approval_signoff: "gates/G2-approval.md"       # 绑定的 G2 门禁签署件
- target_baseline_sha256: {{BASELINE_SHA256}}    # 纠错前目标工件 content_sha256

---

## 2. 结构块数与双哈希期望声明 (Declared Block Counts & Target Hashes)

> 本节声明数据供 `python3 scripts/verify_readback.py --plan <this_file> --target <target_file>` 执行第 3 层与第 4 层校验。

### 2.1 结构块数期望声明 (Layer 3 Expectations)
- declared_block_ids: [{{DECLARED_BLOCK_IDS}}]   # 允许修改的块 ID 集合，例: ["C-01", "SEC-2.1-P3"]
- expected_headings: {{EXPECTED_HEADINGS}}       # 纠错后目标文档预期标题总数 (以 ^#{1,6}\\s+ 统计)
- expected_tables: {{EXPECTED_TABLES}}           # 纠错后目标文档预期表格总数 (以 Markdown 表格块统计)
- expected_paragraphs: {{EXPECTED_PARAGRAPHS}}   # 纠错后目标文档预期非空段落/块总数

### 2.2 目标文档双哈希期望声明 (Layer 4 Expectations)
- expected_content_sha256: {{EXPECTED_CONTENT_SHA256}} # 纠错完成并落盘后文件的二进制 SHA-256
- expected_nettext_sha256: {{EXPECTED_NETTEXT_SHA256}} # 纠错完成并落盘后正文净文本 SHA-256

---

## 3. 逐条纠错对照矩阵 (Itemized Patch Matrix)

> 规则说明：
> - 处置类型仅限四项：`删除` / `降级为假设` / `待核` / `保留`。
> - 人审裁决：人类操作者在 G2 签署前在下表中明确各条目裁决状态（`APPROVED` / `REJECTED` / `CHANGES_REQUESTED`）。未经批准的条目不得写入目标工件。

| 条目 ID | 缺陷级别 | 涉及章节与块 ID | 原文 | 拟改为 | 处置类型 (删除/降级为假设/待核/保留) | 证据与理由 | 人审裁决 |
|---|:---:|---|---|---|:---:|---|:---:|
| {{ITEM_ID_1}} | {{GRADE_1}} | {{LOCATION_1}} | {{OLD_TEXT_1}} | {{NEW_TEXT_1}} | {{DISPOSITION_1}} | {{RATIONALE_1}} | [{{ADJUDICATION_1}}] |
| {{ITEM_ID_2}} | {{GRADE_2}} | {{LOCATION_2}} | {{OLD_TEXT_2}} | {{NEW_TEXT_2}} | {{DISPOSITION_2}} | {{RATIONALE_2}} | [{{ADJUDICATION_2}}] |
| {{ITEM_ID_3}} | {{GRADE_3}} | {{LOCATION_3}} | {{OLD_TEXT_3}} | {{NEW_TEXT_3}} | {{DISPOSITION_3}} | {{RATIONALE_3}} | [{{ADJUDICATION_3}}] |

---

## 4. 四层回读复验指引 (Readback Verification Guide)

实施补丁后，执行以下命令验证：
```bash
python3 scripts/verify_readback.py --plan correction-diff.md --target {{TARGET_ARTIFACT}}
```
验收合格标准：
1. `layer1`: 所有批准的 `拟改为` 文本 100% 存在于目标工件。
2. `layer2_residuals`: 所有判定为 D0 或批准替换的 `原文` 在目标工件中残留次数严格为 0。
3. `layer3_match`: 实际标题数、表格数与段落数 100% 吻合上述声明。
4. `layer4_hash_match`: 实际 `content_sha256` 与 `nettext_sha256` 100% 吻合上述声明。
