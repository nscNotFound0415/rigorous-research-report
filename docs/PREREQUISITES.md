# 环境与依赖完整指南 (Prerequisites)

本文档面向希望在本地安装、运行或二次开发 `rigorous-research-report` 的分析师与开发者，详细说明跨平台依赖要求、安装命令、降级行为与 Agent 宿主环境配置。

---

## 一、依赖分级总览 (Dependency Matrix)

本项目的架构原则是**“运行时极简、质检确定性、环境可降级”**：

| 依赖类别 | 具体依赖项 | 作用范围 | 必要性 | 缺少时的降级行为 |
|---|---|---|:---:|---|
| **Python 运行时** | **Python 3.12 – 3.14 标准库** | 核心脚本（`src/scripts/` 14 个工具） | **强制** | **零第三方依赖**。完全基于标准库实现（`json`, `ast`, `csv`, `re`, `zipfile`, `xml.etree` 等），无需任何 `pip install`。 |
| **文档渲染引擎** | **LibreOffice (`soffice`)** | 将生成的 `.docx` 转换为 `.pdf` | 推荐 | 若缺失，`build_docx.py` 仍可生成高质量 Word 文档，PDF 生成与目录回填将显式降级跳过（输出 `{"pdf": false, "reason": "soffice_unavailable"}`），**绝不报错崩溃，亦绝不伪造成功**。 |
| **多语言字形** | **中文字体 (CJK Fonts)** | 保证 PDF 文本层字形映射正确 | 强制（针对中文研报） | 若缺少中文字体，LibreOffice 会使用西文字体替换，导致生成的 PDF 文本层丢失中文字形（例如繁简错位或乱码），`toc_two_pass.py` 会触发安全中断并报错 `pdf_text_layer_lost_cjk`，**绝不回填不可靠的猜测页码**。 |
| **测试框架** | **`pytest`** | 执行单元测试与模块黑箱用例 | 可选（仅开发者） | 仅在运行 `tests/` 目录下的 147 项自动化测试时需要。**普通用户仅使用技能撰写报告时完全无需安装**。 |
| **规格治理工具** | **`openspec` CLI (v1.14+)** | 维护/演进 `specs/` 核心能力契约 | 可选（仅核心开发者） | 仅在修改能力规格、创建变更提案或归档主规格时需要。终端执行调研流程完全无需安装。 |
| **Agent 宿主能力** | **具备标准工具集的大模型 Agent** | 驱动端到端流水线自律运行 | 模式 A 必需 | 若无 Agent 宿主，人类分析师亦可直接在终端中手动调用脚本作为**独立质检工具箱**（模式 B）。 |

---

## 二、操作系统与环境安装一条龙

### 1. Ubuntu / Debian (推荐部署环境)

```bash
# 1. 基础编译与字体环境
sudo apt-get update && sudo apt-get install -y --no-install-recommends \
  python3 \
  libreoffice-writer \
  fonts-noto-cjk

# 2. 验证字体与 LibreOffice 就绪
fc-list :lang=zh | head -n 3
soffice --version

# 3. (可选) 仅二次开发者需要安装测试运行器
python3 -m pip install pytest
```

### 2. macOS (原生环境)

macOS 原生自带高质量中文字体（如苹方 `PingFang SC` 与宋体 `Songti SC`），文本层兼容性极佳：

```bash
# 1. 使用 Homebrew 安装 LibreOffice
brew install --cask libreoffice

# 2. 配置终端 soffice 别名/软链接（以便 scripts/ 可在 PATH 中直接调用）
sudo ln -sf /Applications/LibreOffice.app/Contents/MacOS/soffice /usr/local/bin/soffice

# 3. 验证命令行可用
soffice --version
```

### 3. Windows / WSL2 (推荐使用 WSL2)

- **推荐方案（WSL2 Ubuntu）**：按照上述 [Ubuntu / Debian](#1-ubuntu--debian-推荐部署环境) 指南直接在 WSL2 内安装 `libreoffice-writer` 与 `fonts-noto-cjk`，与 Linux 完全一致。
- **Windows 原生 PowerShell 方案**：
  1. 从官网下载并安装 [LibreOffice for Windows](https://www.libreoffice.org/)。
  2. 将安装路径（默认 `C:\Program Files\LibreOffice\program`）加入系统的系统环境变量 `Path`。
  3. Windows 自带中文字体（中易宋体 `SimSun`、微软雅黑 `Microsoft YaHei`），无需额外安装字体包。
  4. 验证 PowerShell 中可直接运行：`soffice --version`。

---

## 三、中文字体与 PDF 文本层的关键技术细节

调研报告交付物通常要求“文档目录上的页码与最终导出的 PDF 打印页码必须 100% 逐页吻合”。许多同类工具常在此处踩坑，产生“目录写第 5 页，翻过去发现标题在第 7 页”的低级失误。

本流水线采用 **“目录两遍法 (Two-Pass TOC Backfill)”** 解决此问题：
1. 第一遍构建出不含页码的完整 `.docx`；
2. 调用系统 `soffice` 将其渲染成真实的矢量 `.pdf`；
3. `toc_two_pass.py` 深入解析 PDF 内部底层矢量文字流（Content Stream），定位正文各标题实际落入的物理页码，精确回填到 Word 目录中；
4. `delivery_readback.py` 独立抽取文本层，反向校验目录与正文实际页码的差集。

> **⚠️ 为什么必须安装 CJK 字体？**  
> 当环境缺少中文字体时，LibreOffice 无法找到匹配字形，会将中文字符投影到默认等宽西文字体上。这会导致两大致命后果：  
> 1. 字符宽度计算严重失真，排版发生剧烈位移（例如原本 40 页的研报被压缩成 13 页）；  
> 2. PDF 的 `ToUnicode` 映射表损坏，导出的文本流无法被正确解码（例如简体“评估”被映射成了繁体“評估”甚至十六进制不可读序列）。  
> 
> 当本流水线检测到此现象时，**绝不妥协去填猜测数字**，而是会返回：  
> `{"toc_backfilled": false, "reason": "pdf_text_layer_lost_cjk", "diagnostic": {"hint": "PDF 文本层未包含中文字形：系统缺少 CJK 字体..."}}`  
> 安装中文字体包后重试即可恢复 100% 精确页码回填。

---

## 四、Agent 宿主环境配置要求

若将本流水线作为 Agent Skill 调度，宿主环境（如 Claude Code, ZCode, OpenCode 等）需满足以下契约：

### 1. 必需工具权限 (Tool Privileges)

*   **`Bash` / 命令行终端**：用于执行 `src/scripts/*.py` 确定性校验工具及测试套件。
*   **`Read` / 读取文件**：用于读取本仓库的 `references/` 协议手册、`templates/` 模板规范及搜集的事实快照。
*   **`Write` / `Edit` / 写入文件**：用于编写简报、大纲、数据底表和最终正文。
*   **`AskUserQuestion` / 终端交互**（强烈建议）：用于在 G0 至 G3 四道关键人审门禁前向人类决策者发起核验交互。

### 2. 多模型通道与异族复核要求 (Adversarial Review)

流水线的核心设计原则是**“严禁自编自审”**（防止大模型出现逻辑幻觉时自我背书）：

*   **最佳方案（跨厂商异族对抗）**：  
    撰写 Agent 采用厂商 A（例如 Claude 族系或 DeepSeek 族系），复核 Agent 采用厂商 B（例如 Gemini 族系或 GPT 族系）。复核证明文件 `provenance.json` 会由 `gate_guard.py --check-provenance` 自动判定不同厂商前缀与非同一 Session。
*   **单模型降级方案（零记忆独立沙箱）**：  
    若使用者仅拥有单一模型 API Key，复核阶段**必须彻底清空上下文，开启独立的无上下文子会话（Subagent / CoVe 模式）**，且在 `provenance.json` 中声明 `context_reset: true`。
*   **离线保底防火墙**：  
    即使在缺乏任何二审模型的最恶劣离线环境下，流水线内置的 14 个确定性 Python 脚本仍能提供底层安全网（代码纯算术复算、数据三要素缺失检查、违禁词扫描、图表连续性断链扫描、四层回读哈希比对），确保机械级事实错误 100% 无法溜入最终成稿。

---

## 五、离线安全性与保密声明

*   **100% 本地离线**：所有 14 个核心工具脚本未引入任何网络请求库（如 `requests`, `urllib.request`），代码中不含任何 Telemetry 打点、日志外发或远程分析代码。
*   **保密机开箱即用**：在完全断网（Air-gapped）、具备高保密要求的政府内网机或金融离线工作站上，只要预置了 Python 3 与 LibreOffice，即可完整运行。
*   **数据合规提示**：当驱动外部大模型 Agent 进行公开网络信息调研时，用户应遵守所在机构的涉密数据脱敏规范，严禁将未公开的内部底稿、保密底表直接传入公有云商业模型。
