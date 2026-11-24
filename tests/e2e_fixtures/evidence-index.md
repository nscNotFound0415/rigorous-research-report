# 事实与证据索引主表 (Evidence Index)

> 本文件为全项目证据与信源唯一索引表，由单写者维护。记录一手证据快照、SHA-256存证与采信状态。

## 1. 证据清单 (Evidence Registry)

### EVID-001
- evidence_id: EVID-001
- source_url: https://regulator.example.invalid/framework-2026
- publisher: SCA (Sample Communications Authority, fictional)
- title: Sample Cloud Computing Regulatory Framework 2026
- pricing_date: 2026-01-15
- access_date: 2026-02-01
- snapshot_path: tests/e2e_fixtures/raw_evidence/mock_regulator_framework_2026.html
- content_sha256: eb5468e3f7666e0dcc8136ebaaa57f8b63138d32621e20fdc3c3fc9383dc4882
- evidence_type: 一手文件
- directly_admissible: YES
- description: 样例法域云计算监管框架 CCRF 3.1 版，明确 Tier 1/2/3 三类牌照准入与外资控股红线

### EVID-002
- evidence_id: EVID-002
- source_url: https://utility.example.invalid/tariff-2026
- publisher: SPC (Sample Power Company, fictional)
- title: High Voltage Industrial Electricity Tariff Schedule
- pricing_date: 2026-01-10
- access_date: 2026-02-02
- snapshot_path: tests/e2e_fixtures/raw_evidence/mock_utility_tariff_2026.pdf
- content_sha256: c5c252f5ab566d55a346054c758ca064928d6c534ba7ff085d5619a1470661b5
- evidence_type: 公开挂牌
- directly_admissible: YES
- description: 样例电网高压工业用电阶梯电价公报，标准电价 0.18 XDS/kWh

### EVID-003
- evidence_id: EVID-003
- source_url: https://telco.example.invalid/gpu-quote-2026
- publisher: Sample Telco Cloud
- title: Enterprise Dedicated GPU Cluster Pricing Quote
- pricing_date: 2026-01-20
- access_date: 2026-02-03
- snapshot_path: tests/e2e_fixtures/raw_evidence/mock_telco_pricing_2026.pdf
- content_sha256: 3fe1a48a10b8c99fc0db75c12f6c72eabe4722be807385c9082a6aed2392d3a3
- evidence_type: 供应商陈述
- directly_admissible: CONDITIONAL
- description: 样例法域电信云企业专用 GPU 集群租赁年度报价单（含网络专线开销）

### EVID-004
- evidence_id: EVID-004
- source_url: https://centralbank.example.invalid/rates-2026-01-01
- publisher: SCB (Sample Central Bank, fictional)
- title: Official USD to XDS Exchange Rate Fixing
- pricing_date: 2026-01-01
- access_date: 2026-02-01
- snapshot_path: tests/e2e_fixtures/raw_evidence/mock_centralbank_fx_2026.html
- content_sha256: 02441debba78643fa60e91b6ae1119451e964463e7c29112f6aed68b74f5da47
- evidence_type: 一手文件
- directly_admissible: YES
- description: 样例央行美元兑示例币官方固定汇率公告（1 USD = 3.75 XDS）

### EVID-005
- evidence_id: EVID-005
- source_url: https://research.example.invalid/datacenter-benchmark-2026
- publisher: Sample Research Institute
- title: Sample Region Datacenter Market Benchmark 2026
- pricing_date: 2026-01-05
- access_date: 2026-02-05
- snapshot_path: tests/e2e_fixtures/raw_evidence/mock_market_benchmark_2026.pdf
- content_sha256: 56ea943976b37fc4f0be4edcd83e8c8e4869a2bd253a2cada0d380284d247347
- evidence_type: 公开报道
- directly_admissible: CONDITIONAL
- description: 样例区域数据中心机柜市场月租基准与三年复合年均增长率预测报告

### EVID-006
- evidence_id: EVID-006
- source_url: internal://e2e_fixtures/raw_evidence/mock_internal_cost_model_2026.xlsx
- publisher: Internal Model
- title: Sample Cloud Financial Projection Model 2026
- pricing_date: 2026-02-01
- access_date: 2026-02-10
- snapshot_path: tests/e2e_fixtures/raw_evidence/mock_internal_cost_model_2026.xlsx
- content_sha256: 46d8fd9d7b8aed8856bed95cbb58be4e2c18bbc18aa837aede73f1808de50cb3
- evidence_type: 一手文件
- directly_admissible: YES
- description: 中资云厂商出海样例法域自建云节点全生命周期财务测算模型及综合推导

## 2. 信源快照完整性总表
| 证据编号 | 发布机构 | 文件类型 | 取价基准日 | 快照 SHA-256 前8位 | 采信结论 |
|---|---|---|---|---|---|
| EVID-001 | SCA | HTML | 2026-01-15 | eb5468e3 | 直接采信 |
| EVID-002 | SPC | PDF | 2026-01-10 | c5c252f5 | 直接采信 |
| EVID-003 | Sample Telco Cloud | PDF | 2026-01-20 | 3fe1a48a | 条件采信 (需交叉验证) |
| EVID-004 | SCB | HTML | 2026-01-01 | 02441deb | 直接采信 |
| EVID-005 | Sample Research Institute | PDF | 2026-01-05 | 56ea9439 | 条件采信 (第三方预测) |
| EVID-006 | Internal Model | XLSX | 2026-02-01 | 46d8fd9d | 内部基准模型 |
