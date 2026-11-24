# rigorous-research-report

**严谨复杂调研报告写作流水线** — 一套给 AI agent 读的调研报告写作行为协议。

不是散文操作手册，是**可判定、可执行、可机检**的规则集：每条规则要么能被脚本验证，要么能被人类一眼判真伪。

```bash
# 安装（Claude Code）
cp -r src/ ~/.claude/skills/rigorous-research-report/

# 安装（ZCode）
cp -r src/ ~/.zcode/skills/rigorous-research-report/
```

调用：`/rigorous-research-report`，或当轮明确说「按调研流水线执行」。**默认不自动触发**。

## 系统要求

`src/scripts/` 全部是纯 Python 3 标准库实现（Python 3.12+），不需要任何第三方包、不联网。但 **PDF 交付链路依赖两个系统件**：

- `soffice`（LibreOffice headless），用于 docx → pdf 无损转换。缺失时 `build_pdf.py` 输出 `{"pdf":false,"reason":"soffice_unavailable"}`，不会伪造 PDF。
- **CJK 字体（必须）**。PDF 生成环境必须安装中文字体：
  - Debian/Ubuntu：`sudo apt-get install -y --no-install-recommends libreoffice-writer fonts-noto-cjk`
  - macOS / Windows：系统自带中文字体，通常无需额外安装
  - Docker / CI：务必在镜像或工作流里显式装上 `fonts-noto-cjk`

  缺中文字体时，soffice 用替代字形渲染，**PDF 文本层会丢失中文字形**（页数与字符映射都与本地不同），目录页码无法定位。此时脚本会明确报错 `pdf_text_layer_lost_cjk` 并给出 `diagnostic.hint`（提示安装 CJK 字体），**不会写入任何猜测页码**；`build_pdf.py` 也会在 PDF 生成成功后返回 `text_layer_warning` 提示文本层不可靠。

---

## 为什么存在

调研报告的失效很少是因为「写得不认真」，更多是因为这几件事悄悄发生了：

| 典型失效 | 本流水线的防线 |
|---|---|
| 数字方向写反、毛利分母混用、单位不同却相减 | 底表**三口径分栏**＋纯代码复算（`audit_calc.py`），跨口径相减直接报错退出码 1 |
| 「看起来有出处」的数其实是上一轮臆测 | 每个数字必须有 `evidence_ref` 回指证据索引；`estimated` 必须带假设标签 |
| 挂牌价被说成可采购价、媒体转述被升格为许可 | 证据类型分级（公开挂牌／公开报道／一手文件／供应商陈述），引用不得升格写进协议 |
| 已排除的旧口径仍在核心论点里 | 跨口径禁算 ＋ 全库残留扫描；旧口径必须显式退役或降级为情景 |
| AI 腔、元叙述、自述型表述混进正文 | 确定性词表扫描（`audit_text_hygiene.py`），带严谨性声明白名单保护 |
| 目录页码与正文对不上却没人发现 | 生成侧与校验侧**各自独立**定位页码；共用同一个假设＝自证清白 |
| 「已核验」「A级」这类标签被跨项目继承 | 唯一事实源声明＋继承声明须逐条人工裁决（`human_decision`） |
| 人审门被机器自己签掉 | 机器签名、桩件（`stub: true`）、哈希不符一律退出码 1 |

## 流程骨架

```
P1 落地澄清（grill-me 决策树：八项建议澄清，未澄清按默认行为登记）
   ↓
P2 治理协议（brief.md 唯一背景源 / progress-log.md 台账 / change-table.md 变更对照表）
   ↓
P3 课题拆分（视角枚举 → task.json：数据三要素 guidelines、REQ-ID 全覆盖、DAG 无环）
   ↓
P4 并行事实调研  ∥  P5 章节规划与大纲（G1 前置）
   ↓  （三边界共用同一个复核循环）
P6 合稿与交付（单次成型 → 一致性 pass → 直写 OOXML → 目录两遍法 → 双向回读 → G3）
   ↑
M  变更回路（外部输入 → 失效传播 → 对照表 → 局部改写 → 零漂移回读）
```

**一个复核循环**，跑在三个产物边界（数据底表／章节大纲／合稿全文）：

```
产出 → 独立审（异族模型、只读、附覆盖声明）→ 四档分流 → 修订 → 四层回读复验 → 出口
```

- **四档缺陷**：D0 已证实错误／D1 证据不足／D2 材料冲突／D3 待核。D0 只允许三种确定性通路：`ARITH`（代码复算）／`QUOTE_MISMATCH`（原文比对）／`LEXICAL_RULE`（机器扫描）。D1 的处置必须**列出两个选项交人裁决**，机器不得自动降级。
- **判实锤只走两条路**：一手原文比对 / 纯算术复算。
- **四道人审门**：G0 澄清定稿 → G1 大纲放行 → G2 纠错定性裁决 → G3 交付放行。签署件必须绑定被放行工物的 sha256。

## 目录结构

```
skill/          技能本体：SKILL.md + references/×9 + templates/×14 + scripts/×14 + schemas/×1
specs/          8 个能力规格（OpenSpec 风格，49 个可判定 Scenario）
tests/          147 项模块测试 + 55 项端到端断言（全部离线，夹具均为合成数据）
docs/DESIGN.md  设计说明与踩坑清单
```

`src/scripts/` 全部**纯 Python 3 标准库**、无第三方依赖、无网络访问；PDF 转换调用系统预装 `soffice`（缺失时脚本显式降级并标记，绝不伪造成功），且要求系统已安装 CJK 字体（见「系统要求」）。

## 验证

```bash
python3 -m pytest tests/ -q      # 147 项模块测试
bash tests/e2e/run_e2e.sh         # 55 项端到端断言（门禁矩阵 + 离线闭环）
```

两者均**不联网**，可在 CI 直接跑。端到端线束覆盖五个门禁 ×（缺签署件／桩件／机器签名／哈希错绑／有效放行）矩阵，以及 M3→M8 的完整离线闭环。

规格与实现的同步用 OpenSpec 维护（`specs/` 为收敛态主规格，变更走 delta → 校验 → 归档）。

## 已知边界

- **图不渲染**：流水线产出「图题＋数据表」，没有位图插图渲染器。
- **无在线平台接入**：在线文档已抽象为「在线载体约定」（`source_of_truth` 双分支），默认本地为母本；接具体平台需另写 Adapter。
- **桩件与真人签署在文件层面无法区分**（固有极限）：已用「桩件一律拒绝」把流程约束升级为机器硬拦截，剩余防线是人审流程。
- **E2E-b（真人全程签署一次）** 需要人执行，运行手册见 `tests/e2e/E2E_B_RUNBOOK.md`。
- CI 覆盖 Python 3.12–3.14；本地验证仅在 3.14 完成。

## 设计来源

本流水线的若干机制来自公开方法论，实现时按调研报告场景做了适配：

- **STORM / Co-STORM**（stanford-oval/storm）——大纲作为显式中间产物、多视角驱动提问
- **GPT Researcher**（assafelovic/gpt-researcher）——节级「研究→审→改」循环、guidelines 可校验条目
- **LangChain open_deep_research**——调研并行＋合稿单次成型（并行分节写作会割裂，是公开记录的反例）
- **OpenSpec**（Fission-AI/OpenSpec）——主规格／在途变更／归档三级状态，变更走 delta
- **GitHub Spec Kit**——「宪法」一次定稿处处对齐；勾选权归人、agent 不得自评
- **Cline Memory Bank**——唯一事实源派生层级与开场强制读取
- **mattpocock/skills（grill-me）**——决策树访谈、frontier 分轮提问、每题附推荐答案、停机条件
- **FacTool / CoVe**——claim 拆分后按类型路由验证（数字走代码执行、引用走原文比对）
- **MT-Bench / FairEval**——异族模型互审的依据（self-enhancement 偏差）与校准要求
- **Anthropic multi-agent research system**——orchestrator-worker 与 LLM-judge rubric

## License

MIT，见 [LICENSE](LICENSE)。
