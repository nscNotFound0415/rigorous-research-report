# 项目简报 (Project Brief)

> **权威派生声明**：本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准。

## 1. 元数据 (Metadata)
- project_id: SAMPLE-AI-CLOUD-2026
- version: 1.0.0
- created_at: 2026-03-01T10:00:00Z
- brief_content_sha256: "67458ca822572c6d339ad24011c57ea9dd3669c764850e6f8e6dfcd91b9b7c92"
- status: APPROVED
- authoritative_declaration: "本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准。"

## 2. 澄清八项与基准清单 (Clarifications & Baselines)

### 2.1 报告受众 (Target Readers)
- primary_readers: [企业出海决策委员会, 战略投资总监, 云计算合规法务总监]
- reader_preferences: 偏好一手实证数据、公式可穿透复算与口径分栏对比，拒绝泛泛而谈

### 2.2 研究标的与对象 (Subject Entity)
- subject_name: 中国大模型与算力企业出海样例法域建设云节点
- scope_boundaries: 涵盖样例法域样例市 IDC 自建与租用成本、SCA 监管牌照与外资准入、SDO 跨境数据本地化法规；明确排除无监管的大模型跨境公网纯 API 调用场景

### 2.3 风格与基调 (Tone & Style)
- style_mode: 严谨审计与商业尽调风格 (Rigorous Audit & Commercial Due Diligence)
- perspective: 独立第三方战略咨询与合规审计专家

### 2.4 背景与历史上下文 (Background Context)
- context_summary: 2026年样例法域加速推进「数字基建蓝图」与国家人工智能战略，中资大模型企业密集调研样例法域算力中心落地可行性。
- inherited_materials: [SCA_Cloud_Regulations_2026.pdf, SDO_样例数据保护法_Executive_Rules.pdf]

### 2.5 交付目的地 (Delivery Path)
- target_local_dir: /home/ubuntu/workspace/sample_cloud_report
- target_delivery_dir: /home/ubuntu/workspace/sample_cloud_report/delivery

### 2.6 交付形态与格式约定 (Format Contract)
- primary_format: Word (.docx) 及 PDF (.pdf) 双格式交付，附带单源母本 Markdown (.md)
- pagination_limit: 40-50页
- structural_requirements:
  - numbering_system: "中文规范三级编号"
  - reference_style: "文末显式索引与一手出处锚定"

### 2.7 在线载体基准判定 (Online Baseline Rule)
- online_enabled: false
- source_of_truth: LOCAL_GIT
- sync_policy: 本地优先，无在线覆盖

### 2.8 人机交互与问询模式 (Interaction Mode)
- interaction_mode: 终端交互式决策树
- interruption_threshold: "仅 G 级门禁与定性裁决主动中断，其余自主闭环推进"

### 2.9 诉求与实体索引 (Requirements & Entities Index)
- REQ-01: 样例法域 IDC 自建与租用成本测算 | 核心实体: 样例法域样例市数据中心 | 权衡维度: CapEx vs OpEx
- REQ-02: SCA 云计算合规牌照与外资准入 | 核心实体: 样例通信管理局 (SCA) | 权衡维度: Tier 1/2/3 资质与合规周期
- REQ-03: SDO 数据出境安全与跨境推理评估 | 核心实体: 样例法域样例数据办公室 (SDO) | 权衡维度: 数据本地化审计与 TCO 模型

### 2.10 术语与口径 (Glossary & Metric Standards)
- PUE: 电能使用效率 (Power Usage Effectiveness) | 基准口径: 工业数据中心全年综合能效
- TCO: 全生命周期总拥有成本 (Total Cost of Ownership) | 基准口径: 包含机柜租金、算力卡时、合规审计与电力运维

## 3. 项目宪法（本文件内嵌章节，唯一权威，禁止外置）
1. **事实判锤唯二通路**：一手原文比对与代码算术复算，严禁任何模型凭空臆测。
2. **定性裁决权归人类**：对于争议表述之存废与降级，机器严禁自作主张，定性裁决权严格归人类。
3. **无隐藏状态**：材料存在 != 已复核 != 已同步 != 已审定；台账状态必须真实、无未声明的中间态。
4. **非同族对抗复核且审者只读**：复核者必须与生成者实现模型或通道级隔离，审者权限严格设为只读，禁止直接修改受审文本。
5. **严禁跨口径相减**：不同口径、不同币种、不同周期的指标必须设立分栏对比，严禁直接执行加减运算。
