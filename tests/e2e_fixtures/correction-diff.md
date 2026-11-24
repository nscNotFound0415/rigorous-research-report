# 纠错与修改对照稿 (Correction Diff Plan)

## 1. 纠错元信息与门禁关联
- plan_id: PLAN-M6-EVAL-01
- boundary: draft_full
- target_artifact_path: "tests/module_tests/test_m6_review_loop/fixtures/draft_full_corrected.md"
- source_review_report: "tests/module_tests/test_m6_review_loop/fixtures/boundary3_review_report.md"
- created_at: 2026-11-23T18:00:00Z
- approval_signoff: "gates/G2-approval.md"
- target_baseline_sha256: "0000000000000000000000000000000000000000000000000000000000000000"

## 2. 结构块数与双哈希期望声明
- declared_block_ids: ["C-01", "C-02", "C-03"]
- expected_headings: 4
- expected_tables: 1
- expected_paragraphs: 3
- expected_content_sha256: "3eafa980d603e0b79f28e6c43746282eb4f990c2273fa2208bfbf721b46c8215"
- expected_nettext_sha256: "78997d2f8d9b8e0bd692fcb1c9f5d8a31216616996c7afe9c285dea89ecd447c"

## 3. 逐条纠错对照矩阵
| 条目 ID | 缺陷级别 | 涉及章节与块 ID | 原文 | 拟改为 | 处置类型 | 证据与理由 | 人审裁决 |
|---|:---:|---|---|---|:---:|---|:---:|
| DIFF-01 | D0 | 第 1 节 [C-01] | 初期部署 CapEx 总计为 1200 万美元，其中服务器硬件支出 800 万美元，网络与配套机电设施 500 万美元。 | 初期部署 CapEx 总计为 1300 万美元，其中服务器硬件支出 800 万美元，网络与配套机电设施 500 万美元。 | 纠正算术 | 纯代码复算 800+500=1300 万美元，纠正加总倒挂 | [APPROVED] |
| DIFF-02 | D1 | 第 2 节 [C-02] | 据某行业自媒体博主非公开转述，样例法域电力成本在未来三年将无条件大幅下调 50% 以上，这将极大释放云端算力利润空间。 | 依据样例能源监管局（SERA）现行工业电价基准，样例法域重工业与数据中心电价保持在每千瓦时 0.18 示例币基准水平 [假设: 待一手证实未来调价预期]，这将极大释放云端算力利润空间。 | 降级为假设 | 二手自媒体无出处，替换为 SERA 权威基准日电价并加注假设 tag | [APPROVED] |
| DIFF-03 | D0 | 第 3 节 [C-03] | 作为一名专业的大模型 AI 语言助手，我在本章节中将为读者全面梳理上述合规要素与跨境数据安全要求。 | 本章节基于样例法域样例数据办公室（SDO）跨境数据流动监管条例，系统梳理关键合规要素与安全控制基线。 | 删除元叙述 | 违反文本卫生禁令，删除自指元叙述并重写为客观学术陈述 | [APPROVED] |
