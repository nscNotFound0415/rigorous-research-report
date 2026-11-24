# [模板规范] 证据与信源唯一索引表 (Evidence & Citation Master Index)

> [!NOTE]
> **维护规则与单写者约束**:
> 1. 本文件为全项目唯一证据事实源索引表（单写者模式，由 M4 事实调研子代理独占写入维护）。
> 2. 每完成一个子任务（task_id）的调研，必须立即向本文件追加条目并刷新增量快照，供并行中的 M5 章节大纲只读消费。
> 3. **一手证据优先铁律**：二手转述报道严禁直接作为底层数据来源，必须穿透至权威机构原始公文、监管牌照公报或公司财报一手原文。
> 4. **引用不得升格铁律**：商业挂牌 ≠ 可实际采购落地；公开新闻报道 ≠ 行政许可/牌照获批；意向备忘录 (MOU) ≠ 约束性法律合同；供应商宣传文案 ≠ 第三方实测性能。
> 5. **快照哈希存证**：凡采信之一手证据，其原始文件/网页快照必须留存于 `fact-store/` 并准确登记 `content_sha256`。

---

## 1. 证据类型与采信层级标准 (Evidence Taxonomy)

| 证据类型 (Type) | 证据属性定义 | 采信权限与要求 | 是否可直接采信默认值 |
|---|---|---|---|
| **一手文件** | 政府公报、监管机构法案/牌照批文、上市公司审计财报、官方技术规范白皮书 | 最高权威事实源，核心数值第一依据 | `YES` (直接采信) |
| **公开挂牌** | 官方电力局公用事业资费表、云厂商官方公开发布的价格表单 (Pricing API/Calculator) | 商业基准参考，须核验是否含税及可用区折扣 | `YES` (直接采信，注明牌价) |
| **公开报道** | 权威主流财经科技媒体的新闻深度调查、行业研讨会公开报道 | 仅限作为背景引线，不得作为独立数值唯一定论 | `CONDITIONAL` (须交叉印证) |
| **供应商陈述** | 设备/IDC 服务商销售报价单、BD 提案 PPT、产品宣传手册 | 存在商业夸大倾向，必须核查折让条款与交付条件 | `CONDITIONAL` (仅作上限/下限情景) |
| **会议线索** | 专家访谈纪要、行业闭门研讨发言、口头调研线索 | 未公开一手原件前仅限登记为线索，禁止定稿采信 | `NO` (不可直接采信，须转证) |

---

## 2. 证据主索引条目清单 (Evidence Ledger Entries)

### EVID-{{EVID_ID_01}}
- **evidence_id**: `EVID-{{EVID_ID_01}}`
- **source_identity**:
  - publisher: "{{PUBLISHER_01}}"                # 发布机构/主体（如：目标市场通信监管机构）
  - title: "{{TITLE_01}}"                        # 文档/网页标题
  - uri_or_path: "{{URI_OR_PATH_01}}"            # 原始访问 URL 或归档相对文件路径
- **pricing_date**: "{{PRICING_DATE_01}}"        # 取价日 / 事实发生基准日期 (YYYY-MM-DD)
- **access_date**: "{{ACCESS_DATE_01}}"          # 检索抓取日期 (YYYY-MM-DD)
- **snapshot_path**: "{{SNAPSHOT_PATH_01}}"      # 原始快照落盘路径 (如: fact-store/snapshots/regulator_2026.html)
- **content_sha256**: "{{CONTENT_SHA256_01}}"    # 快照文件 UTF-8 全文 SHA256 哈希
- **evidence_type**: "{{EVIDENCE_TYPE_01}}"      # 枚举: 一手文件 | 公开挂牌 | 公开报道 | 会议线索 | 供应商陈述
- **directly_admissible**: {{DIRECTLY_ADMISSIBLE_01}} # 枚举: YES | NO | CONDITIONAL
- **admissibility_rationale**: "{{RATIONALE_01}}" # 采信评估理由（落实不得升格原则）
- **mapped_items**:
  - `{{MAPPED_ITEM_ID_01}}`                      # 映射底表 item_id

---

### EVID-{{EVID_ID_02}}
- **evidence_id**: `EVID-{{EVID_ID_02}}`
- **source_identity**:
  - publisher: "{{PUBLISHER_02}}"
  - title: "{{TITLE_02}}"
  - uri_or_path: "{{URI_OR_PATH_02}}"
- **pricing_date**: "{{PRICING_DATE_02}}"
- **access_date**: "{{ACCESS_DATE_02}}"
- **snapshot_path**: "{{SNAPSHOT_PATH_02}}"
- **content_sha256**: "{{CONTENT_SHA256_02}}"
- **evidence_type**: "{{EVIDENCE_TYPE_02}}"
- **directly_admissible**: {{DIRECTLY_ADMISSIBLE_02}}
- **admissibility_rationale**: "{{RATIONALE_02}}"
- **mapped_items**:
  - `{{MAPPED_ITEM_ID_02}}`

---

## 3. 证据索引表格汇总视图 (Tabular Master View)

| evidence_id | 一手来源标识 (机构/标题/URL) | 取价日 | 访问日期 | 证据类型 | 是否直接采信 | 快照路径与 content_sha256 | 映射底表指标 |
|---|---|---|---|---|:---:|---|---|
| EVID-{{EVID_ID_01}} | {{PUBLISHER_01}} / {{TITLE_01}} | {{PRICING_DATE_01}} | {{ACCESS_DATE_01}} | {{EVIDENCE_TYPE_01}} | [{{DIRECTLY_ADMISSIBLE_01}}] | `{{SNAPSHOT_PATH_01}}`<br>`{{CONTENT_SHA256_01}}` | `{{MAPPED_ITEM_ID_01}}` |
| EVID-{{EVID_ID_02}} | {{PUBLISHER_02}} / {{TITLE_02}} | {{PRICING_DATE_02}} | {{ACCESS_DATE_02}} | {{EVIDENCE_TYPE_02}} | [{{DIRECTLY_ADMISSIBLE_02}}] | `{{SNAPSHOT_PATH_02}}`<br>`{{CONTENT_SHA256_02}}` | `{{MAPPED_ITEM_ID_02}}` |
