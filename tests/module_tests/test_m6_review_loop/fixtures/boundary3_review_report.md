# 独立对抗复核报告 (Adversarial Review Report)

> **复核引擎约束与治理红线 (Review Axioms)**：
> 1. 本报告由独立只读审查实例产出，审者严禁直接改动受审工件。
> 2. 缺陷严格执行四档分流（D0 已证实错误、D1 证据不足、D2 材料冲突、D3 待核 T 项）。
> 3. 事实判锤只走确定性通路：纯代码算术复算 (ARITH)、一手原文比对 (QUOTE_MISMATCH) 与确定性词法扫描器 (LEXICAL_RULE)；证据不足≠事实错误。
> 4. 出口红线：D0 缺陷数必须强制清零（D0 == 0），且完成四层回读复验并获人类门禁批准后，方可跨入下游阶段。

---

## 1. 复核元信息与隔离声明 (Review Meta & Isolation Declaration)

- boundary: draft_full
- reviewed_artifact: "tests/module_tests/test_m6_review_loop/fixtures/injected_defects_draft.md"
- artifact_content_sha256: dbae2992b48ae4f593403550223750de47e2b4072e96a7beb678a89f48f47c79
- review_timestamp: 2026-11-23T18:00:00Z
- provenance_file: "tests/module_tests/test_m6_review_loop/fixtures/valid_heterogeneous_provenance.json"
- reviewer_channel: 异族
- read_only_verified: true
- isolation_statement: "复核者运行于严格隔离只读沙箱，与撰写者会话分离（session 互斥），无历史思考缓存继承；调用证明详见 tests/module_tests/test_m6_review_loop/fixtures/valid_heterogeneous_provenance.json。"

---

## 2. 复核覆盖度与盲区声明 (Coverage Declaration)

### 2.1 全文深读物料清单 (Deep-read Materials)
- 逐行比对与全文精读文件：
  - `tests/module_tests/test_m6_review_loop/fixtures/injected_defects_draft.md`
  - `fact-store/raw_evidence/sample_cloud_market_2026.md`

### 2.2 定向扫描物料清单 (Targeted Scan Materials)
- 依据特定关键词、公式列、引用 ID 进行定向核查的文件：
  - `src/templates/forbidden_terms.json` (扫描自述词与元叙述)
  - `datatable.csv` (底表 CapEx/OpEx 核对)

### 2.3 未读/盲区声明 (Unread Materials & Blind Spots)
- 本次复核未覆盖或因环境受限未能接入的外部信源与工件：
  - `样例法域国家信息中心 (NIC) 内部专网接入细则非公开文档`

---

## 3. 缺陷统计与出口门禁判定 (Defect Statistics & Gate Status)

| 缺陷级别 | 级别定义与处置原则 | 检出数量 | 阻断状态 (BLOCKED / PASS) |
|:---:|---|:---:|:---:|
| **D0** | **已证实错误**（仅限 ARITH 算术复算 / QUOTE_MISMATCH 原文不一致 / LEXICAL_RULE 确定性词法扫描，每条必带 route）：**必须清零** | 2 | BLOCKED |
| **D1** | **证据不足**（缺乏一手信源、二手转述无考证、缺基准日或单位）：列出两个选项（补证 ｜ 降级为推测/待证实）供 G2 人类裁决 | 1 | PASS (需裁决) |
| **D2** | **材料冲突**（多个权威信源对同一指标冲突）：设立分栏对比，禁止主观取舍 | 0 | PASS |
| **D3** | **待核 T 项**（调研范围外未闭环事项、企业未披露项）：只标注不改数，挂牌留存 | 0 | PASS |
| **总计** | 全部分类缺陷汇总 | 3 | BLOCKED (D0 > 0) |

**出口门禁初步判定 (Exit Assessment)**:
- D0 缺陷清零判定: false (检出 2 处 D0 错误，严禁放行)
- 降级阶梯级别: Level 1 (异族通道对抗复核)
- 门禁状态: BLOCKED_D0_PRESENT (需提交 correction-diff.md 修订并经 G2 门禁人类裁决)

---

## 4. 缺陷明细清单 (Defect Details)

### 4.1 D0: 已证实错误 (Confirmed Errors - 必须清零，仅限 ARITH / QUOTE_MISMATCH / LEXICAL_RULE)

#### [D0-01] 初期 CapEx 加总纯代码复算倒挂
- **定位 (Location)**: 第 1. 项目概况与投资测算 第 1 段 [C-01]
- **原文 (Original Text)**:
  > 在样例市可用区算力基础设施前期测算中，初期部署 CapEx 总计为 1200 万美元，其中服务器硬件支出 800 万美元，网络与配套机电设施 500 万美元。
- **问题类型 (Problem Type)**: 算术复算错误
- **route**: ARITH
- **证据来源 (Evidence Source)**: 复算命令 `python3 -c "print(f'800 + 500 = {800+500}; expected 1200; match={800+500==1200}')"`，输出行：`800 + 500 = 1300; expected 1200; match=False`（即 800 + 500 = 1300 != 1200）
- **影响范围 (Impact Scope)**: 导致投资预算总额与分项直接矛盾，影响财务模型准确性
- **建议处置 (Recommended Disposition)**: 倾向性建议更正总额为 1300 万美元，并同步修订底表
- **仍待核事项 (Pending Items)**: 无，算术逻辑确定

#### [D0-02] 违规大模型自指与自述元叙述
- **定位 (Location)**: 第 3. 合规审查与技术路线 第 1 段 [C-03]
- **原文 (Original Text)**:
  > 作为一名专业的大模型 AI 语言助手，我在本章节中将为读者全面梳理上述合规要素与跨境数据安全要求。
- **问题类型 (Problem Type)**: 违规自述元叙述
- **route**: LEXICAL_RULE
- **证据来源 (Evidence Source)**: 扫描器命令 `grep -n "作为一名专业的大模型 AI 语言助手" tests/module_tests/test_m6_review_loop/fixtures/injected_defects_draft.md`，输出行：`15:作为一名专业的大模型 AI 语言助手，我在本章节中将为读者全面梳理上述合规要素与跨境数据安全要求。`
- **影响范围 (Impact Scope)**: 破坏报告学术严谨性与严肃商业调研基调，显露 AI 生成痕迹
- **建议处置 (Recommended Disposition)**: 彻底删除自指语句，重写为以被动/客观视角表达的合规梳理陈述
- **仍待核事项 (Pending Items)**: 无，元叙述属纯违规项

---

### 4.2 D1: 证据不足 (Insufficient Evidence - 降级或补证)

#### [D1-01] 二手自媒体转述电力成本下调缺乏一手信源与基准
- **定位 (Location)**: 第 2. 外部政策与电力成本研判 第 1 段 [C-02]
- **原文 (Original Text)**:
  > 据某行业自媒体博主非公开转述，样例法域电力成本在未来三年将无条件大幅下调 50% 以上，这将极大释放云端算力利润空间。
- **问题类型 (Problem Type)**: 二手转述未考证
- **证据来源 (Evidence Source)**: 缺乏一手信源，且未检索到样例法域 SERA 或能源部官方官方降价法令
- **影响范围 (Impact Scope)**: 电力敏感度与运营成本测算可能产生过度乐观偏差
- **建议处置 (Recommended Disposition)**: 列出两个选项供 G2 人类裁决——补证（限期补充 SERA 官方一手降价法令或受限电价文件）｜ 降级为推测/待证实（正文加注 `[假设: 待一手证实]`，并采用 SERA 现行工业电价基准 0.18 示例币/kWh）
- **仍待核事项 (Pending Items)**: 后续跟踪样例法域水电监管局官方公告确认是否有调价试点

---

### 4.3 D2: 材料冲突 (Conflicting Sources - 设立分栏对比)
*无检出项目。*

---

### 4.4 D3: 待核 T 项 (Unverified Pending Items - 挂牌留存)
*无检出项目。*

---

## 5. 后续流转指引 (Downstream Action Items)

1. 检出 2 处 D0 缺陷：当前边界严格阻断向下游流转。
2. 调度撰写节点编制《纠错对照稿》（`correction-diff.md`），将 D1 定性选项（补证 ｜ 降级为推测/待证实）提交人类在 G2 门禁（`gates/G2-approval.md`）裁决。
3. 获得人类签署后执行局部替换，并运行 `python3 scripts/verify_readback.py --plan correction-diff.md --target draft_full.md` 完成四层回读复验。
