# [模板规范] 标准化数据底表 (Datatable Ledger Template)

> [!NOTE]
> **使用说明与填写契约**:
> 1. 本底表为项目中全部核心数值与测算指标的唯一权威基准台账，所有章节正文引用的数据必须 100% 溯源至本底表。
> 2. 底表强制实施 A/B/C 三口径分栏列示。
> 3. **核心宪法红线**：必须严格遵循「严禁跨口径相减」底线原则。不同口径（如 A 自建私有 IDC vs B 租用公有云）的成本、单价、利润严禁在任何公式中直接加减或混合计算，必须在底表中以分栏或显式分隔列并列呈现。
> 4. **同一指标多来源口径冲突时并列呈现、严禁求平均或主观裁决**。
> 5. 纯代码复算要求：凡包含计算关系的数值必须声明 `expected_expression` 与 `tolerance`（整数默认 0；浮点默认 1e-9 并须带舍入模式声明）。
> 6. 假设与出处要求：凡 `source_type=estimated` 者其 `assumption_tag` 必须非空，严禁任何未注假设 tag 的裸数字；每一个数值必须能回指 `evidence-index.md` 中的有效条目。

---

## 1. 口径分栏与分类体系定义 (Caliber Architecture)

| 口径代码 (Caliber) | 口径名称 | 成本/效益核算范畴 | 适用场景说明 |
|---|---|---|---|
| **A** | 自建私有 IDC 口径 | CapEx 资本性支出驱动（机房土建/租赁、机柜电力、自购服务器折旧、自有运维） | 长期持有、规模化算力中心、主权合规要求极高 |
| **B** | 租用公有云/算力租赁口径 | OpEx 运营性支出驱动（按卡时/Token/按月计费、包含厂商网络带宽与托管服务） | 轻资产起步、弹性业务负载、快速上线出海 |
| **C** | 行业公允市场口径 | 市场挂牌公允参考价（公开发布报告、第三方研究机构行业基准） | 宏观市场比照、行业平均水位评估 |
| **COMMON** | 通用常数与换算基准 | 汇率、法定税率、物理常数（如 PUE 基准、电费换算比例） | 跨口径通用基准换算参数 |

> [!WARNING]
> **跨口径相减禁止铁律 (Cross-Scope Arithmetic Ban)**:
> 严禁在公式中直接计算 `A - B` 或 `B - A` 宣称“成本节约额”！因自建含沉没折旧且未含软件层运维，公有云含利润与全托管弹性溢价，直接相减属于严重口径混淆。如需比对，必须列明完整生命周期 TCO 并行比较表。

---

## 2. 字段字典与约束规范 (Schema Definitions)

| 字段名称 (Column) | 必填性 | 字段约束与合法取值 | 说明与示例 |
|---|---|---|---|
| `item_id` | 必须 | 字符串，唯一标识符，格式 `ITM-[A-Za-z0-9_-]+` | 示例: `ITM-A01`, `ITM-REV-2026` |
| `label` | 必须 | 字符串，指标中文规范全称 | 示例: `目标市场自建节点年总收入 (口径A)` |
| `value` | 必须 | 数值（整数或浮点数，正负数均可） | 示例: `8.04`, `5.32`, `33.83` |
| `unit` | 必须 | 计量单位与币种代码 | 示例: `USD_M`, `LOCAL_CUR`, `PERCENT`, `KW`, `TCO` |
| `source_type` | 必须 | 枚举值: `measured` \| `derived` \| `estimated` \| `quoted` | `measured`: 实测/财报; `derived`: 纯公式推导; `estimated`: 预测/推算; `quoted`: 权威引述 |
| `source_ref` | 必须 | 字符串，指向 `evidence-index.md` 中的 `evidence_id` | 示例: `EVID-001`, `EVID-REG-01` |
| `expected_expression` | 条件 | 公式单元格必填，纯算术表达式（支持 + - * / % ** // 与 item_id 变量代入） | 示例: `ITM-A01 - ITM-A02` 或 `(8.04-5.32)/8.04*100` |
| `tolerance` | 必须 | 容差与舍入规则声明 | 整数: `0`；浮点: `1e-9` 或 `0.01;round=half_up` |
| `caliber` | 必须 | 枚举值: `A` \| `B` \| `C` \| `COMMON` | 声明数值所属口径 |
| `assumption_tag` | 条件 | 当 `source_type=estimated` 时必须非空；其余可选 | 示例: `ASM-GPU-UTIL-85PCT`, `ASM-PUE-1.25` |

---

## 3. 标准数据底表结构 (Datatable Content)

### 3.1 口径 A：自建私有 IDC 测算专栏 (Caliber A: Private Build)

| item_id | label | value | unit | source_type | source_ref | expected_expression | tolerance | caliber | assumption_tag |
|---|---|---|---|---|---|---|---|---|---|
| ITM-A01 | {{LABEL_A01}} | {{VALUE_A01}} | {{UNIT_A01}} | {{SOURCE_TYPE_A01}} | {{SOURCE_REF_A01}} | {{EXPRESSION_A01}} | {{TOLERANCE_A01}} | A | {{ASSUMPTION_TAG_A01}} |
| ITM-A02 | {{LABEL_A02}} | {{VALUE_A02}} | {{UNIT_A02}} | {{SOURCE_TYPE_A02}} | {{SOURCE_REF_A02}} | {{EXPRESSION_A02}} | {{TOLERANCE_A02}} | A | {{ASSUMPTION_TAG_A02}} |
| ITM-A03 | {{LABEL_A03}} | {{VALUE_A03}} | {{UNIT_A03}} | derived | {{SOURCE_REF_A03}} | ITM-A01 - ITM-A02 | 0.01;round=half_up | A | {{ASSUMPTION_TAG_A03}} |

---

### 3.2 口径 B：公有云与算力租赁测算专栏 (Caliber B: Cloud Lease)

| item_id | label | value | unit | source_type | source_ref | expected_expression | tolerance | caliber | assumption_tag |
|---|---|---|---|---|---|---|---|---|---|
| ITM-B01 | {{LABEL_B01}} | {{VALUE_B01}} | {{UNIT_B01}} | {{SOURCE_TYPE_B01}} | {{SOURCE_REF_B01}} | {{EXPRESSION_B01}} | {{TOLERANCE_B01}} | B | {{ASSUMPTION_TAG_B01}} |
| ITM-B02 | {{LABEL_B02}} | {{VALUE_B02}} | {{UNIT_B02}} | {{SOURCE_TYPE_B02}} | {{SOURCE_REF_B02}} | {{EXPRESSION_B02}} | {{TOLERANCE_B02}} | B | {{ASSUMPTION_TAG_B02}} |
| ITM-B03 | {{LABEL_B03}} | {{VALUE_B03}} | {{UNIT_B03}} | derived | {{SOURCE_REF_B03}} | ITM-B01 - ITM-B02 | 0.01;round=half_up | B | {{ASSUMPTION_TAG_B03}} |

---

### 3.3 口径 C：市场公允参考指标专栏 (Caliber C: Market Benchmark)

| item_id | label | value | unit | source_type | source_ref | expected_expression | tolerance | caliber | assumption_tag |
|---|---|---|---|---|---|---|---|---|---|
| ITM-C01 | {{LABEL_C01}} | {{VALUE_C01}} | {{UNIT_C01}} | quoted | {{SOURCE_REF_C01}} |  | 0.01;round=half_even | C |  |
| ITM-C02 | {{LABEL_C02}} | {{VALUE_C02}} | {{UNIT_C02}} | estimated | {{SOURCE_REF_C02}} |  | 0.05 | C | {{ASSUMPTION_TAG_C02}} |

---

### 3.4 跨口径对比显式分隔区 (Explicit Separator & Parallel Comparison)

> [!NOTE]
> 跨口径横向展示仅允许并列对照，严禁跨行减除！

| item_id | label | value | unit | source_type | source_ref | expected_expression | tolerance | caliber | assumption_tag |
|---|---|---|---|---|---|---|---|---|---|
| ITM-PAR-01 | 自建方案首年支出汇总 (口径A) | {{VALUE_A_TOTAL}} | USD_M | derived | {{REF_A_TOTAL}} | ITM-A01 | 0.01 | A |  |
| ITM-PAR-02 | 租赁方案首年支出汇总 (口径B) | {{VALUE_B_TOTAL}} | USD_M | derived | {{REF_B_TOTAL}} | ITM-B01 | 0.01 | B |  |
