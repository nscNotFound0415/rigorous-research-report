# M7 模块统一合稿与多格式交付独立验收测试指南 (Reviewer Judge Guide)

本目录为 M7 模块（统一合稿与多格式交付，Monolithic Drafting & Multi-format Delivery）的独立黑箱验收测试套件与测试夹具库。
独立验收法官（Independent Reviewer Judge）可在不查看内部代码实现的前提下，直接通过标准 CLI 命令执行确定性黑箱判定。

---

## 1. 独立法官黑箱执行命令契约与期望输出一览

### 1.1 文本卫生与元叙述扫描核验 (CRITERION M7-1)

#### 用例 1.1.1: 干净草稿扫描通过且 9 类严谨性声明零误报 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/audit_text_hygiene.py \
    tests/module_tests/test_m7_delivery/fixtures/draft_full_clean.md \
    --rules src/templates/forbidden_terms.json
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 单行输出**:
  ```json
  {"violations":[]}
  ```

#### 用例 1.1.2: 历史缺陷旧稿精准捕获全部 5 处违规元叙述 (阴性对照 a - D-15 闭环)
- **执行命令**:
  ```bash
  python3 src/scripts/audit_text_hygiene.py \
    tests/module_tests/test_m7_delivery/fixtures/dirty_meta_draft.md \
    --rules src/templates/forbidden_terms.json
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 判定**:
  违规计数严格等于 5，精准定位全部注入项，且 9 类严谨性声明被 allowlist 保护零误报：
  ```json
  {"violations":[{"line":5,"rule_id":"F-01","matched_text":"如前所述","sentence":"如前所述，海外算力中心选址需综合评估电费与网络出境通道","description":"元叙述类：指向文档外前置材料、修订历史或报告写作流程的表述"},{"line":13,"rule_id":"F-01","matched_text":"前轮内部测算","sentence":"前轮内部测算表明单卡成本为 40.2 元每卡时","description":"元叙述类：指向文档外前置材料、修订历史或报告写作流程的表述"},{"line":15,"rule_id":"F-02","matched_text":"本报告不给出","sentence":"本报告不给出最终毛利率结论，待商务洽谈后定案","description":"自述型：以报告自身写作姿态代替结论、或带有主观第一人称自述的表述"},{"line":30,"rule_id":"F-02","matched_text":"本节不引述","sentence":"本节不引述未经核实的非公开口头沟通信息","description":"自述型：以报告自身写作姿态代替结论、或带有主观第一人称自述的表述"},{"line":32,"rule_id":"F-03","matched_text":"第一性原理","sentence":"第一性原理推导显示分布式节点具备更优网络弹性","description":"AI 腔空泛词：缺乏具体事实支撑的空洞行业黑话"}]}
  ```

#### 用例 1.1.3: 跨章节连续 30 字符重复去重检测 (去重判据 - D-8 闭环)
- **正向命令**:
  ```bash
  python3 src/scripts/audit_text_hygiene.py \
    tests/module_tests/test_m7_delivery/fixtures/draft_full_clean.md \
    --rules src/templates/forbidden_terms.json \
    --check-dedup
  ```
  - **期望退出码**: `0`
  - **期望 stdout**: `{"violations":[],"shared_substrings":[]}`
- **阴性对照命令**:
  ```bash
  python3 src/scripts/audit_text_hygiene.py \
    tests/module_tests/test_m7_delivery/fixtures/redundant_sections_draft.md \
    --rules src/templates/forbidden_terms.json \
    --check-dedup
  ```
  - **期望退出码**: `1`
  - **期望 stdout 包含共享子串**:
    ```json
    {"violations":[],"shared_substrings":[{"section_a":"1. 行业背景与出海动因","section_b":"2. 算力成本对比与口径分析","length":32,"shared_text":"海外算力中心选址需综合评估本地电费基准与网络出境通道等关键要素。"}]}
    ```

---

### 1.2 图表编号与文献引用一致性核查 (CRITERION M7-2)

#### 用例 1.2.1: 引用闭环且图表连续无断号 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/citation_check.py \
    tests/module_tests/test_m7_delivery/fixtures/draft_full_clean.md \
    --evidence-index tests/module_tests/test_m7_delivery/fixtures/evidence-index.md
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 单行输出**:
  ```json
  {"dangling_refs":[],"unnumbered_figs":[],"dangling_tables":[]}
  ```

#### 用例 1.2.2: 捕获悬空引用与断号图表 (阴性对照 b - D-7 闭环)
- **执行命令**:
  ```bash
  python3 src/scripts/citation_check.py \
    tests/module_tests/test_m7_delivery/fixtures/broken_citation_draft.md \
    --evidence-index tests/module_tests/test_m7_delivery/fixtures/evidence-index.md
  ```
- **期望退出码**: `1`
- **期望 stdout JSON 判定**:
  ```json
  {"dangling_refs":["EVD-999_FICTIONAL"],"unnumbered_figs":["图表编号断号: 缺少 图 2 (存在 图 3)"],"dangling_tables":["正文引用了未定义的表号: 表 9"]}
  ```

---

### 1.3 OOXML 构建、两遍法与交付回读校验 (CRITERION M7-3)

#### 用例 1.3.1: 单源直写 Word 交付件与构建幂等性校验
- **执行命令**:
  ```bash
  python3 src/scripts/build_docx.py \
    tests/module_tests/test_m7_delivery/fixtures/draft_full_clean.md \
    --out /tmp/delivery/output.docx \
    --manifest /tmp/delivery/build_manifest.json
  ```
- **期望退出码**: `0`
- **幂等性核验断言**:
  连续构建两次，生成的 `build_manifest.json` 中各部件（`document.xml`, `styles.xml`, `numbering.xml` 等 8 项）SHA256 哈希值逐项一致，且 docx 二进制 SHA256 完全相同。

#### 用例 1.3.2: 无损转 PDF 与两遍法页码回填
- **执行命令**:
  ```bash
  python3 src/scripts/build_pdf.py /tmp/delivery/output.docx --out /tmp/delivery/output.pdf
  python3 src/scripts/toc_two_pass.py /tmp/delivery/output.docx /tmp/delivery/output.pdf
  ```
- **期望退出码**: `0`
- **期望 toc_two_pass stdout**:
  ```json
  {"toc_backfilled":true,"entries_count":3,"updated_count":3,"toc_pages":1,"body_start_page":2,"total_pages":3,"pages":{"1. 行业背景与出海动因":2,"2. 算力成本对比与口径分析":2,"3. 合规壁垒与实施路线":3}}
  ```
- **页码判定规则**: `toc_pages` 为实测的目录实际页数（从第 1 页起含点前导页码行的连续页），正文起始页 = `toc_pages + 1`；每个标题只在正文区域内定位，不使用任何固定页偏移。

#### 用例 1.3.3: 交付物双向回读差集与页码零倒挂校验 (CRITERION M7-3)
- **执行命令**:
  ```bash
  python3 src/scripts/delivery_readback.py \
    --docx /tmp/delivery/output.docx \
    --pdf /tmp/delivery/output.pdf \
    --source tests/module_tests/test_m7_delivery/fixtures/draft_full_clean.md \
    --out /tmp/delivery/delivery_readback.json
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 单行输出**:
  ```json
  {"toc_minus_headings":[],"headings_minus_toc":[],"page_mismatch":[],"toc_heading_order_mismatch":[],"page_bounds_violations":[],"unresolved_page_entries":[],"toc_page_integrity_errors":[],"toc_pages":[1]}
  ```
- **期望落盘产物**: 生成 `/tmp/delivery/delivery_readback.json`，记录完整的 `headings` 与 `toc_entries` 结构。
- **校验独立性**: 本工具的 PDF 抽取、目录页实测与正文标题定位均在本文件内独立实现，与 `toc_two_pass.py` 不共享任何「跳过第几页」的常量或函数。

#### 用例 1.3.4: 缺失 PDF 时的显式跳过标记
- **执行命令**:
  ```bash
  python3 src/scripts/delivery_readback.py \
    --docx /tmp/delivery/output.docx \
    --pdf /tmp/delivery/nonexistent.pdf \
    --source tests/module_tests/test_m7_delivery/fixtures/draft_full_clean.md \
    --out /tmp/delivery/delivery_readback.json
  ```
- **期望退出码**: `0`
- **期望 stdout JSON 单行输出**:
  ```json
  {"toc_minus_headings":[],"headings_minus_toc":[],"page_mismatch":"skipped_no_pdf","toc_heading_order_mismatch":[],"page_bounds_violations":[],"unresolved_page_entries":[],"toc_page_integrity_errors":[],"toc_pages":[]}
  ```

#### 用例 1.3.5: 目录占多页时逐条页码等于正文真实页（新增回归 1）
- **夹具**: `fixtures/toc_multipage.md`（43 条目录项，实测目录占 2 页）
- **执行链路**: `build_docx.py` → `build_pdf.py` → `toc_two_pass.py`
- **断言**: 目录条目数 `>= 40`；实测目录页数 `>= 2`；`toc_two_pass` 报告的 `toc_pages` / `body_start_page` 与测试侧独立实测一致；**逐条**比对 docx 目录记录页码与 PDF 正文真实页码，全部相等；所有真实页码均落在目录页之后。
- **对应函数**: `test_toc_multipage_entries_match_real_body_pages`

#### 用例 1.3.6: 标题同时出现在目录页与正文页时不取目录页（新增回归 2）
- **夹具**: `fixtures/toc_multipage.md`
- **断言**: 每个标题都确实出现在目录页文本中（前提成立）；回填页码等于正文真实页，既不等于目录首页，也不落入任何目录页。
- **对应函数**: `test_toc_heading_present_in_toc_page_does_not_win`

#### 用例 1.3.7: 目录含正文不存在的标题时显式失败（新增回归 3）
- **构造**: 在正常交付物 docx 的目录区注入一条正文不存在的 TOC 条目。
- **期望退出码**: `1`
- **期望 stdout**: `{"toc_backfilled":false,"reason":"unresolved_toc_entries",...,"unresolved_toc_entries":["幽灵章节：正文中并不存在"]}`
- **附加断言**: 失败时 docx 目录页码保持第一遍占位值，证明没有静默写入猜测页码。
- **对应函数**: `test_toc_unresolved_entry_fails_loudly`

#### 用例 1.3.8: 人为篡改目录页码后回读必须报错（新增回归 4）
- **构造**: 把回填后的 docx 目录首条页码改为错误页码（1 或 2），PDF 保持真实。
- **期望退出码**: `1`
- **期望 stdout**: `page_mismatch` 非空，且包含该条目的 `docx_page`（篡改值）与 `pdf_page`（真实页）。
- **附加断言**: 落盘的 `delivery_readback.json` 中 `page_mismatch` 同样非空。
- **对应函数**: `test_delivery_readback_detects_tampered_toc_page`

---

### 1.4 G3 终审门禁校验与机器签名拦截 (CRITERION M7-4)

#### 用例 1.4.1: 人类授权签署放行 G3 门禁 (正向用例)
- **执行命令**:
  ```bash
  python3 src/scripts/gate_guard.py \
    --gate G3 \
    --verify \
    --artifact tests/module_tests/test_m7_delivery/fixtures/delivery/output.docx \
    --approval tests/module_tests/test_m7_delivery/fixtures/gates/G3-approval-valid.md
  ```
- **期望退出码**: `0`
- **期望 stdout**:
  ```json
  {"gate":"G3","state":"APPROVED","blocked":false,"artifact_sha256":"8afef4627ded3e2dbc480b4dcb76a02b93b4c4bcc40b973386866fe668714ea5","reason":"Gate G3 successfully verified and approved by human:delivery_lead"}
  ```

#### 用例 1.4.2: 机器/AI 自签拦截 (阴性对照 c - R1 闭环)
- **执行命令**:
  ```bash
  python3 src/scripts/gate_guard.py \
    --gate G3 \
    --verify \
    --artifact tests/module_tests/test_m7_delivery/fixtures/delivery/output.docx \
    --approval tests/module_tests/test_m7_delivery/fixtures/gates/G3-approval-machine-signed.md
  ```
- **期望退出码**: `1`
- **期望 stdout**:
  ```json
  {"gate":"G3","state":"AGENT_SIGNATURE_PROHIBITED","blocked":true,"artifact_sha256":"8afef4627ded3e2dbc480b4dcb76a02b93b4c4bcc40b973386866fe668714ea5","reason":"Agent self-signing is strictly prohibited; signed_by must be a human identifier (contains machine token 'ai'), got 'AI-Agent-Claude (自动复核代理)'"}
  ```

---

## 2. 自动化一键测试运行

法官可直接运行自动化测试脚本：
```bash
bash tests/module_tests/test_m7_delivery/run_tests.sh
```
该脚本将依次执行 Pytest 单元与集成测试（22 项用例），并直接执行正向与阴性对照 CLI 断言。

---

## 3. 测试夹具说明 (Fixture Inventory)

| 夹具文件名 | 用途与特征 | 对应判据 / 阻断项 |
|---|---|---|
| `fixtures/evidence-index.md` | 标准归档一手证据索引表，含 EVD-001/002/003, REF-01/02, S31 | M7-2 信源基准 |
| `fixtures/draft_full_clean.md` | 合规单次合稿母本，含 3 章正文、合规图表、完整一手引用及全部 9 类严谨性声明 | M7-1, M7-2, M7-3 正向基准 |
| `fixtures/dirty_meta_draft.md` | 阴性对照旧料：注入 5 处元叙述/自述词，含 9 类严谨性声明白名单 | M7-1 阴性对照 (D-15) |
| `fixtures/broken_citation_draft.md` | 阴性对照旧料：注入虚构引用 EVD-999、图 1 跳至图 3 缺少图 2、未定义表 9 | M7-2 阴性对照 (D-7) |
| `fixtures/redundant_sections_draft.md` | 阴性对照旧料：注入跨章节共享 >= 30 字符重复文本 | D-8 去重判据阴性对照 |
| `fixtures/inline_violation_with_allowlist.md` | 阴性对照：单行内同行并存违禁元叙述与严谨性声明 | R2 句粒度判据阴性对照 |
| `fixtures/toc_multipage.md` | 43 条目录项的合稿母本，实测目录占 2 页、正文标题跨多页 | 目录页码回归 1/2/4（多页目录、标题同时在目录与正文、篡改页码） |
| `fixtures/delivery/output.docx` | 标准 Word 交付物工件，用于 G3 终审门禁校验 | M7-4 工件基准 |
| `fixtures/gates/G3-approval-valid.md` | G3 人类有效授权签署凭单（含 approver_role: human_decision_maker） | M7-4 正向放行 |
| `fixtures/gates/G3-approval-machine-signed.md` | G3 机器签名伪造件（AI-Agent-Claude 自动复核代理） | R1 / M7-4 机器签名阻断 |
| `fixtures/gates/G3-approval-invalid-role.md` | G3 非法角色审批件（非 human_decision_maker） | M7-4 角色违规阻断 |
| `fixtures/gates/G3-approval-hash-mismatch.md` | G3 哈希不匹配审批件 | M7-4 哈希防伪阻断 |

---

## 4. OpenSpec 需求与 Scenario 映射表

| OpenSpec Requirement | Scenario 名称 | 映射验证函数 / CLI 用例 | 状态 |
|---|---|---|---|
| **Monolithic Drafting and Synthesis Consistency Pass** | `Section deduplication verification passes` | `test_audit_text_hygiene_section_deduplication` / 用例 1.1.3 | **通过 (PASS)** |
| **Text Hygiene Audit with Allowlist Protection** | `Prohibited meta-narrative outside allowlist triggers rejection` | `test_audit_text_hygiene_negative_control_dirty_meta_draft` / 用例 1.1.2 | **通过 (PASS)** |
| **Text Hygiene Audit with Allowlist Protection** | `Allowlisted rigor declarations pass without false positives` | `test_audit_text_hygiene_positive_control` / 用例 1.1.1 | **通过 (PASS)** |
| **Dual Document Build and Delivery Readback Verification** | `Delivery readback confirms zero heading and page mismatches` | `test_toc_two_pass_and_delivery_readback_pipeline` / 用例 1.3.3 | **通过 (PASS)** |
| **Dual Document Build and Delivery Readback Verification** | `Idempotent build produces identical component hashes` | `test_build_docx_idempotency_and_component_hashes` / 用例 1.3.1 | **通过 (PASS)** |
| **Dual Document Build and Delivery Readback Verification** | `Delivery readback confirms zero heading and page mismatches`（多页目录逐条页码） | `test_toc_multipage_entries_match_real_body_pages` / 用例 1.3.5 | **通过 (PASS)** |
| **Dual Document Build and Delivery Readback Verification** | `Delivery readback confirms zero heading and page mismatches`（目录页干扰） | `test_toc_heading_present_in_toc_page_does_not_win` / 用例 1.3.6 | **通过 (PASS)** |
| **Dual Document Build and Delivery Readback Verification** | `Delivery readback confirms zero heading and page mismatches`（无法定位显式失败） | `test_toc_unresolved_entry_fails_loudly` / 用例 1.3.7 | **通过 (PASS)** |
| **Dual Document Build and Delivery Readback Verification** | `Delivery readback confirms zero heading and page mismatches`（篡改页码捕获） | `test_delivery_readback_detects_tampered_toc_page` / 用例 1.3.8 | **通过 (PASS)** |

---

## 桩签署件硬拒绝（加固项 G）

门禁 `gate_guard.py` 对含 `stub: true`（或 `stub:true`）的签署件一律硬拒绝：`state=STUB_REJECTED`、`blocked=true`、退出码 1，即使 `artifact_sha256` 完全吻合。G0/G1/G2/G3/change-<id> 五门共用该校验。

- 本目录用于正向放行路径的签署件夹具均为**符合人类签署格式且不含 stub 标记**的测试夹具；该夹具仅用于验证放行路径，**不代表真实人类签署**。
- 真实人类签署件必须由人类本人亲笔填写，不得由任何自动流程代签。
