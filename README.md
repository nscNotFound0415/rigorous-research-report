# rigorous-research-report

![CI](https://github.com/nscNotFound0415/rigorous-research-report/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.12-3.14](https://img.shields.io/badge/Python-3.12--3.14%20(stdlib%20only)-blue.svg)](#-系统与运行依赖)

**严谨复杂调研报告写作流水线** — 一套给 AI agent 读的调研报告写作行为协议。

不是散文操作手册，是**可判定、可执行、可机检**的规则集：每条规则要么能被脚本验证，要么能被人类一眼判真伪。

> 📖 **完整文档索引**：
> - [📘 快速上手与使用手册 (User Guide)](docs/USER_GUIDE.md)：涵盖模式 A（Agent 驱动流水线）与模式 B（人类独立质检工具箱）、门禁签署实操、变更维护回路等。
> - [⚙️ 环境与系统依赖指南 (Prerequisites)](docs/PREREQUISITES.md)：跨平台安装命令（Linux/macOS/Windows）、CJK 字体配置、Agent 宿主工具权限与单模型降级策略。
> - [🏗️ 架构设计与踩坑清单 (Design)](docs/DESIGN.md)：四大层级 40 余条“典型失效 → 为什么发生 → 本流水线如何拦截”实测经验。

---

## ⚡ 极速安装与唤醒

```bash
# 复制到 Agent 技能目录（Claude Code）
cp -r src/ ~/.claude/skills/rigorous-research-report/

# 复制到 Agent 技能目录（ZCode）
cp -r src/ ~/.zcode/skills/rigorous-research-report/
```

在 Agent 对话中调用：`/rigorous-research-report`，或当轮明确说明“请按严谨调研流水线执行”。**默认不自动触发**，避免普通闲聊产生侵入性问答。

---

## 🛠️ 系统与运行依赖

本流水线坚持**“运行时极轻、质检高确定、环境可降级”**原则：

*   **Python 运行时（零依赖！）**：全部 14 个核心脚本（`src/scripts/*.py`）**100% 基于 Python 3.12–3.14 标准库**实现，**无需任何 `pip install`**。
*   **文档渲染引擎（LibreOffice `soffice`）**：负责将 `.docx` 转换为矢量 `.pdf` 并抽取打印页码。若环境未安装，Word 仍可完整生成，PDF 与目录回填将显式降级跳过，绝不崩溃伪造。
*   **中文字体（必须）**：PDF 生成依赖系统 CJK 字体以确保字符流映射正确。
    *   **Debian/Ubuntu**：`sudo apt-get install -y --no-install-recommends libreoffice-writer fonts-noto-cjk`
    *   **macOS / Windows**：系统原生自带中文字体，无需额外配置。
    *   *若缺少字体，流水线会主动报错 `pdf_text_layer_lost_cjk` 并阻断目录回填，坚决不写入虚假猜测页码。*

详细的跨平台安装指令与环境自检请参考 [环境与依赖说明文档 (docs/PREREQUISITES.md)](docs/PREREQUISITES.md)。

---

## 🎯 为什么存在

调研报告的失效很少是因为“写得不认真”，更多是因为这几件事在多轮对话中悄悄发生了：

| 典型失效场景 | 本流水线的防护机制 |
|---|---|
| **算术写反、毛利分母混用、单位相减** | 标准底表**三口径隔离分栏** ＋ 纯代码复算（`audit_calc.py`），跨口径相减直接报错阻断。 |
| **“看起来有出处”的数实为上一轮臆测** | 每个数值必须有 `evidence_ref` 强回指一手索引；估算数（`estimated`）强制带假设标签。 |
| **挂牌价被当成可采购、媒体转述升格为许可** | 证据类型严格分级（挂牌／报道／一手文件／陈述），“挂牌≠可采购，报道≠行政许可”写入铁律。 |
| **已推翻的旧结论依然残留在核心论点** | 跨口径禁算 ＋ 全库文本残留扫描；旧口径必须显式退役或降级为情景假设。 |
| **通篇 AI 腔、自述型“我们认为”、元叙述** | 确定性词表扫描（`audit_text_hygiene.py`），同时保护 9 类严谨性声明（白名单）零误报。 |
| **目录页码与正文对不上却没人发现** | 目录两遍法从实际渲染流定位；**生成侧与校验侧各自独立实现**，杜绝“自己证明自己正确”。 |
| **“已核验”“定案”等历史标签被盲目继承** | 唯一事实源声明 ＋ 历史材料继承声明必须逐条人工裁决（`CONFIRMED`/`REVISED`）。 |
| **人审门禁被大模型自己悄悄代签** | 门禁防伪引擎：机器签名、模拟桩件（`stub: true`）、工件哈希不符一律退出码 1 拦截。 |

---

## 🔄 流程骨架与人审门禁

```text
P1 落地澄清（grill-me 决策树：八项建议澄清，未澄清按默认行为登记，不卡死推进）
   ↓
P2 治理协议（brief.md 唯一背景源 / progress-log.md 台账 / change-table.md 变更对照表）
   ↓
P3 课题拆分（多视角枚举 → task.json：数据三要素 guidelines、REQ-ID 全覆盖、DAG 无环）
   ↓
P4 并行事实调研  ∥  P5 章节规划与大纲（G1 前置）
   ↓  （三边界复用同一复核循环：底表边界 / 大纲边界 / 全文边界）
P6 统一合稿（单次成型 → 一致性清洗 → 直写 OOXML → 目录两遍法 → 双向回读 → G3）
   ↑
M  变更回路（外部输入 → 失效传播 → 对照表 → 局部改写 → 零漂移回读）
```

### 1. 通用复核循环引擎 (Adversarial Review Loop)
在数据底表、章节大纲、合稿全文三个产物边界，复用完全相同的标准复核闭环：
```text
产出候选物 ──> 独立对抗审查 (异族模型/零记忆隔离沙箱) ──> D0-D3 四档分流 ──> 局部改写 ──> 四层回读复验 ──> 放行出口
```
*   **D0 已证实错误**：仅限三大客观判定通路（`ARITH` 代码复算、`QUOTE_MISMATCH` 原文比对、`LEXICAL_RULE` 确定性机器扫描），P0 缺陷未清零严禁放行。
*   **D1 证据不足**：必须列出“补证”与“降级为假设”两个选项供人类裁决，**机器严禁擅自做定性降级**。
*   **判实锤唯二通路**：一手原文比对 / 纯算术代码复算。

### 2. 四道刚性人审门禁 (Human Gates)
*   **G0 简报定稿**：签署 `gates/G0-approval.md`，确认研究对象、边界与宪法五原则。
*   **G1 大纲放行**：签署 `gates/G1-approval.md`，锁定论证拓扑与章节契约，未批准严禁动笔合稿。
*   **G2 纠错定性**：在 `correction-diff.md` 中对争议条目拍板定性（删除 vs 降级），签署 G2 放行。
*   **G3 终审交付**：核验最终排版与双向回读报告，签署 `gates/G3-approval.md` 正式放行交付件。

---

## 📂 仓库目录规范

```text
├── src/                         # 技能交付物源码（复制此目录即完成安装）
│   ├── SKILL.md                 # 核心入口协议（严格 <200 行，仅含宿主安全键与路由）
│   ├── references/              # 9 份条目化、断言化可执行规程手册
│   ├── templates/               # 14 份标准模板规范（含治理三件套、数据底表、违禁词库等）
│   ├── schemas/                 # task.json 的 JSON Schema 校验模式
│   └── scripts/                 # 14 个确定性 Python 校验与构建脚本（纯标准库）
├── specs/                       # 8 个能力规格契约（OpenSpec 规范体系，49 个可判定 Scenario）
├── tests/                       # 147 项模块单元/黑箱测试 + 55 项端到端线束（全离线合成数据）
│   ├── module_tests/            # M1–M9 模块级独立验收测试套件
│   └── e2e/                     # E2E-a 门禁矩阵校验 + E2E-c 离线闭环线束
└── docs/                        # 完整设计与实操文档库
    ├── USER_GUIDE.md            # 快速上手与双模式使用指南
    ├── PREREQUISITES.md         # 依赖分级、字体配置与 Agent 宿主环境说明
    └── DESIGN.md                # 架构设计权衡与 40+ 真实踩坑清单
```

---

## 🧪 自动化测试与质量检验

本仓库配有全自动化的本地离线测试套件：

```bash
# 1. 运行 147 项模块测试（纯标准库 + pytest 运行器，秒级完成）
python3 -m pytest tests/ -q

# 2. 运行 55 项端到端全链路闭环测试（覆盖 5 门禁 x 5 场景矩阵 + 交付全流程）
bash tests/e2e/run_e2e.sh
```

所有测试用例与端到端测试均采用手写合成夹具（Synthetic Fixtures），**完全不依赖外部网络与任何商业 API**，可在隔离的持续集成（GitHub Actions CI）环境中稳定跑通。

---

## ⚖️ 协议与开源声明

本项目基于 [MIT 许可证](LICENSE) 开源。欢迎各类研究机构、咨询团队与开发者基于本协议二次开发研报流水线。
