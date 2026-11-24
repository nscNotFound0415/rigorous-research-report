# 存储载体抽象契约与适配器规范 (Storage Adapter Specification)

本规范定义调研报告流水线的存储分层拓扑、工作区受控登记清单（`manifest.json`）以及在线协同载体抽象适配器接口。

---

## 1. 核心架构原则：双分支权威基准与平台抽象中立

流水线不预设单一绝对的权威存储载体，权威归属必须严格由 `brief.md` §2.7 中的 `source_of_truth` 必填枚举决定（仅限 `ONLINE_AUTHORITATIVE` 或 `LOCAL_AUTHORITATIVE`），且该字段为空或待定时 G0 门禁严禁放行。

### 1.1 双分支权威定义
1. **分支 A：`ONLINE_AUTHORITATIVE`（在线协同文档为权威事实基准）**：
   - 在线协同文档为全局内容基准与唯一事实源；本地文件系统为带双哈希（`content_sha256` 与 `nettext_sha256`）的只读工作镜像。
   - 本地产生的一切改写或修正，必须 [SHALL] 先通过适配器回写同步至在线平台，并回读重新校验哈希与一致性后，方可 [THEN] 视为落地生效。
2. **分支 B：`LOCAL_AUTHORITATIVE`（本地 Git 文件系统为权威事实母本）**：
   - 本地文件系统结合 Git 版本控制为全局唯一母本（Markdown 原文、数据底表与一手证据快照）；在线协同端仅作为单向发布目标与阅读镜像。
   - 本地修改提交后向目标发布通道推送，发布后执行回读校验确认一致。

### 1.2 平台抽象中立性
协议与接口定义中禁止 [SHALL NOT] 绑定特定平台专用 API 或专有私有数据结构。所有协同载体读写必须通过抽象适配器（`OnlineStorageAdapter`）执行。

---

## 2. 读写契约、同步策略与投递通道

### 2.1 读取端契约
1. 当从在线协同载体拉取内容时（无论是 ONLINE_AUTHORITATIVE 模式的主源拉取，还是 LOCAL_AUTHORITATIVE 模式的只读镜像参考），适配器必须 [SHALL] 转换为标准 Markdown/结构化文件并落盘至工作区。
2. 落盘后必须 [SHALL] 计算其 `content_sha256` 并登记快照索引。

### 2.2 写入端与交付投递通道契约
写入端根据 `brief.md` 中声明的 `delivery_channel` 字段选择匹配通道（整文件原地覆盖投递为可选通道之一，严禁写成全局默认）：
1. **整文件原地覆盖投递通道 (`FILE_OVERWRITE_PUSH`) [可选通道]**：
   - 仅当 `brief.md` 中 `delivery_channel` 配置为整文件投递时启用。对于交付物成品（如标准排版 Word `.docx`、最终版 PDF `.pdf`），采用整文件覆盖上传模式。
2. **局部更新适配接口 (`API_CHUNK_SYNC`) [可选通道]**：
   - 对于支持结构化块更新的协同文档，通过统一适配器 `OnlineStorageAdapter.patch_block(target_id, old_anchor, new_text)` 执行受控局部写入与回读验证。
3. **本地独占通道 (`LOCAL_ONLY`) [可选通道]**：
   - 纯本地文件系统落盘，不执行任何外部协同推送。

### 2.3 异常处理与防回滚保护
1. **同步未完成标记**：当在线载体网络中断、鉴权失效、API 速率受限或写入返回非 200 时，适配器必须 [SHALL] 将台账中对应状态标记为「同步未完成」或状态保持为「已复核」，禁止 [SHALL NOT] 伪造「已同步」状态。
2. **禁止以旧母本回滚线上**：若在线同步失败，严禁 [SHALL NOT] 提取本地旧版本快照强制覆盖或回滚线上载体，避免线上并发编辑内容发生灾难性丢失；必须 [SHALL] 记录错误堆栈并等待重新同步或人工介入。

---

## 3. 工作区受控清单 (`manifest.json`) 规范

工作区根目录下必须 [SHALL] 存在受控登记清单 `manifest.json`，用于实施写操作受控准入控制。

### 3.1 字段架构 Schema
```json
{
  "manifest_version": "1.0.0",
  "project_id": "rigorous-research-report",
  "managed_files": [
    {
      "path": "brief.md",
      "category": "contract",
      "allowed_roles": ["M1_elicitation", "Human"],
      "content_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    {
      "path": "progress-log.md",
      "category": "governance",
      "allowed_roles": ["M2_governance", "Human"],
      "content_sha256": null
    },
    {
      "path": "src/schemas/task.schema.json",
      "category": "schema_definition",
      "allowed_roles": ["M3_agent"],
      "writer": "M3_agent",
      "content_sha256": null
    }
  ],
  "ignored_patterns": [
    "backup/**",
    ".git/**",
    "__pycache__/**",
    "*.log"
  ]
}
```

### 3.2 准入拦截规则
1. **未登记写入强制拦截**：工作区受控目录中任何新文件的创建或修改，必须 [SHALL] 预先在 `manifest.json` 的 `managed_files` 中完成路径登记。
2. **探针自检契约**：调用 `storage_guard.py --root <dir> --manifest manifest.json --probe-unregistered-write` 时，守护程序必须 [SHALL] 扫描所有非忽略路径。若探测到未经登记的文件写入，必须 [SHALL] 拦截并输出 `{"rejected":true,"path":"..."}`，退出码为 0。

---

## 4. 抽象适配器接口 (OnlineStorageAdapter Interface)

适配器实现必须 [SHALL] 遵循以下抽象接口契约：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class OnlineStorageAdapter(ABC):
    """在线载体通用抽象基类 (平台无关)"""

    @abstractmethod
    def pull_snapshot(self, remote_doc_id: str, local_dest_path: str) -> Dict[str, Any]:
        """
        拉取在线文档镜像至本地，计算 SHA-256 并返回元数据字典:
        {"remote_doc_id": "...", "local_path": "...", "content_sha256": "...", "success": True}
        """
        pass

    @abstractmethod
    def deliver_binary(self, local_file_path: str, remote_folder_id: str) -> Dict[str, Any]:
        """
        将本地生成的 Word / PDF 交付件以物理整文件原地覆盖投递至在线协同端:
        {"file_name": "...", "remote_file_id": "...", "delivered_at": "...", "success": True}
        """
        pass

    @abstractmethod
    def patch_block(self, remote_doc_id: str, anchor_id: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """
        局部块精准更新。仅当旧文本锚点严格匹配时更新，更新失败时抛出异常或返回 success=False，
        严禁静默忽略失败或用本地旧快照覆写线上。
        """
        pass
```
