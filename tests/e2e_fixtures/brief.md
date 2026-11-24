# 项目简报 (Project Brief)

> **权威派生声明**：本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准。

## 1. 元数据 (Metadata)
- project_id: PRJ-SAMPLE-CLOUD-2026
- version: 1.0.0
- created_at: 2026-11-23T10:00:00Z
- brief_content_sha256: "9812d94fded46946993e1d528dc22fbd3d57104b0ef01b10610cb6a66606c89d"
- status: APPROVED
- authoritative_declaration: "本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准。"

## 2. 澄清八项与基准清单 (Clarifications & Baselines)

### 2.1 报告受众 (Target Readers)
- clarification_status: CLARIFIED
- primary_readers: [企业出海战略决策委员会, 首席技术官, 基础设施投资总监]
- reader_preferences: 偏好一手实证数据、公式可穿透复算与口径分栏对比，拒绝泛泛而谈与未标假设的裸数字

### 2.2 研究标的与对象 (Subject Entity)
- clarification_status: CLARIFIED
- subject_name: 中国算力与大模型企业出海样例法域建设云节点可行性调研
- scope_boundaries: 聚焦样例市与样例港两地 IDC 建设、合规牌照与用电成本，明确排除无监管的大模型跨境公网纯 API 调用场景

### 2.3 风格与基调 (Tone & Style)
- clarification_status: CLARIFIED
- style_mode: rigorous_analytical
- perspective: third_party_neutral

### 2.4 背景与历史上下文 (Background Context)
- clarification_status: CLARIFIED
- context_summary: 2026年样例法域加速推进「数字基建蓝图」与国家人工智能战略，中资大模型企业密集调研样例法域算力中心落地可行性与成本效益。
- inherited_materials: [mock_regulator_framework_2026.html, mock_utility_tariff_2026.pdf]

### 2.5 交付目的地 (Delivery Path)
- clarification_status: CLARIFIED
- target_local_dir: /home/ubuntu/workspace/sample_cloud_report
- target_delivery_dir: /home/ubuntu/workspace/sample_cloud_report/delivery

### 2.6 交付形态与格式约定 (Format Contract)
- clarification_status: CLARIFIED
- primary_format: DOCX
- pagination_limit: 40-50页
- structural_requirements:
  - numbering_system: "中文规范三级编号"
  - reference_style: "文末显式索引与一手出处锚定"

### 2.7 在线载体基准判定 (Online Baseline Rule)
- clarification_status: CLARIFIED
- online_enabled: false
- source_of_truth: LOCAL_AUTHORITATIVE
- sync_policy: 本地优先，无在线覆盖
- delivery_channel: LOCAL_ONLY

### 2.8 人机交互与问询模式 (Interaction Mode)
- clarification_status: CLARIFIED
- interaction_mode: minimal_interruption
- interruption_threshold: "仅 G 级门禁与定性裁决主动中断，其余自主闭环推进"

### 2.9 诉求与实体索引 (Requirements & Entities Index)
- REQ-01: 样例法域样例市自建 IDC 与租用云节点成本效益测算 | 核心实体: 样例市数据中心 | 权衡维度: CapEx vs OpEx
- REQ-02: SCA 云计算合规牌照与外资准入壁垒分析 | 核心实体: 样例通信管理局 (SCA) | 权衡维度: Tier 1/2/3 牌照资质要求
- REQ-03: 样例电网高压工业电价与汇率敏感性分析 | 核心实体: 样例电网 (SPC) 与样例央行 (SCB) | 权衡维度: 0.18 XDS/kWh 与固定汇率测算

### 2.10 术语与口径 (Glossary & Metric Standards)
- SCA 牌照: 样例通信管理局颁发的云计算服务提供商注册资质 | 基准口径: SCA Cloud Computing Regulatory Framework 2026
- PUE (Power Usage Effectiveness): 数据中心总能耗与 IT 设备能耗之比 | 基准口径: 工业数据中心全年综合能效
- CapEx: 算力中心自建机房、机柜与电力变压设备之初始资本性支出 | 基准口径: 2026 年样例法域本地施工采购均价

### 2.11 继承声明与人工裁决 (Inherited Claims & Human Adjudication)
| 条目 ID | 继承说法 (claim) | 来源文件 (source_path) | 来源 SHA256 (source_sha256) | 人工裁决 (human_decision) |
|---|---|---|---|---|
| IC-01 | SCA 牌照申请审批基准周期为 6 个月 | mock_regulator_framework_2026.html | eb5468e3f7666e0dcc8136ebaaa57f8b63138d32621e20fdc3c3fc9383dc4882 | CONFIRMED |
| IC-02 | 样例市高压重工业电价统一按 0.18 XDS/kWh 计收 | mock_utility_tariff_2026.pdf | c5c252f5ab566d55a346054c758ca064928d6c534ba7ff085d5619a1470661b5 | CONFIRMED |

## 3. 项目宪法（本文件内嵌章节，唯一权威，禁止外置）
1. **事实判锤唯二通路**：一手原文比对与代码算术复算，严禁任何模型凭空臆测。
2. **定性裁决权归人类**：对于争议表述之存废与降级，机器严禁自作主张，定性裁决权严格归人类。
3. **无隐藏状态**：材料存在 != 已复核 != 已同步 != 已审定；台账状态必须真实、无未声明的中间态。
4. **非同族对抗复核且审者只读**：复核者必须与生成者实现模型或通道级隔离，审者权限严格设为只读，禁止直接修改受审文本。
5. **严禁跨口径相减**：不同口径、不同币种、不同周期的指标必须设立分栏对比，严禁直接执行加减运算。
