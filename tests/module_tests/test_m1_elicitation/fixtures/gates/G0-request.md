# 门禁放行申请单 (G0 Request)

## 1. 申请元信息 (Request Meta)
- gate: G0
- requested_by: session_builder_01
- requested_at: 2026-11-23T10:05:00Z
- artifact_path: tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md
- artifact_sha256: ecc06c65d94ca468e0967c20f461427a7cca5a27d4cf5540c4af598260dceb1f

## 2. 交付物摘要与人审建议 (Artifact Summary & Recommendations)
- artifact_summary: 完成八项澄清，确立样例法域算力出海调研标的，内嵌宪法五原则与 3 项 REQ-ID。
- agent_recommendation: 建议批准 G0 放行进入 M2 治理协议阶段。
- decision_points:
  - 交付形态采用 DOCX + 自动转 PDF 模式
  - 事实源基准锁定本地 Git 绝对优先 (LOCAL_GIT_FIRST)

## 3. 前置自检核对清单 (Pre-flight Verification Checklist)
- [x] 产物文件已生成且路径有效: tests/module_tests/test_m1_elicitation/fixtures/sample_brief_draft.md
- [x] 全文 SHA-256 计算完毕: ecc06c65d94ca468e0967c20f461427a7cca5a27d4cf5540c4af598260dceb1f
- [x] brief_content_sha256 置空自检校验通过
- [x] 无隐藏未决异常或内部矛盾
