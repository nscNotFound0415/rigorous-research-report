#!/usr/bin/env python3
"""
gate_guard.py - 门禁防伪与签署状态校验工具 (Universal Gate Guard)

符合 OpenSpec 规格与建设方案规范。
纯 Python 3 标准库实现，零第三方依赖，无外网访问，无状态残留。

CLI 契约:
    python3 scripts/gate_guard.py --gate <G> --check-only [--root <dir>]
    python3 scripts/gate_guard.py --gate <G> --verify --artifact <file> --approval <approval_file> [--root <dir>]
    python3 scripts/gate_guard.py --compute-hash <file>
    python3 scripts/gate_guard.py --compute-brief-content-hash <file>
    python3 scripts/gate_guard.py --verify-brief <file>

门禁支持:
    G0, G1, G2, G3 (大小写不敏感)
    change-<id> (如 change-01, change-add-feature)

输出契约:
    严格输出单行 JSON 到 stdout:
    {"gate":"...","state":"...","blocked":bool,"artifact_sha256":"...","reason":"..."}
    退出码: 0 放行 / 1 阻断
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# 5 条宪法字符串为全局系统常量，禁止任意重构或使用改写变体
CONSTITUTION_RULES: Tuple[str, ...] = (
    "事实判锤唯二通路",
    "定性裁决权归人类",
    "无隐藏状态",
    "非同族对抗复核且审者只读",
    "严禁跨口径相减",
)

# 八项澄清小节为「建议澄清清单」：不要求全部填满，但每项必须登记澄清状态。
CLARIFICATION_SECTIONS: Tuple[str, ...] = (
    "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8",
)
CLARIFICATION_STATUSES: Tuple[str, ...] = (
    "CLARIFIED", "NOT_CLARIFIED", "NOT_APPLICABLE",
)

# [CRITERION M1-6] 未澄清/不适用项的协议默认行为（必须已生效并被登记）
SECTION_REQUIRED_FIELDS: Dict[str, Tuple[str, ...]] = {
    "2.1": ("primary_readers", "reader_preferences"),
    "2.2": ("subject_name", "scope_boundaries"),
    "2.3": ("style_mode", "perspective"),
    "2.4": ("context_summary", "inherited_materials"),
    "2.5": ("target_local_dir", "target_delivery_dir"),
    "2.6": ("primary_format", "pagination_limit"),
    "2.7": ("online_enabled", "source_of_truth", "sync_policy", "delivery_channel"),
    "2.8": ("interaction_mode", "interruption_threshold"),
}
DEFAULT_NOT_CLARIFIED_FIELD_VALUES: Dict[str, Dict[str, str]] = {
    "2.7": {"source_of_truth": "LOCAL_AUTHORITATIVE"},
    "2.8": {"interaction_mode": "synchronous_frontier"},
}
# 软项枚举：仅在澄清状态为 CLARIFIED 时强校验取值合法性
SOFT_ENUM_FIELDS: Dict[str, Dict[str, frozenset]] = {
    "2.3": {
        "style_mode": frozenset({"rigorous_analytical", "executive_brief", "adversarial_audit"}),
        "perspective": frozenset({"third_party_neutral", "strategic_advisor"}),
    },
    "2.6": {"primary_format": frozenset({"DOCX", "PDF", "MARKDOWN", "MD"})},
    "2.7": {"source_of_truth": frozenset({"ONLINE_AUTHORITATIVE", "LOCAL_AUTHORITATIVE"})},
    "2.8": {
        "interaction_mode": frozenset({
            "minimal_interruption", "synchronous_frontier", "async_questionnaire",
        }),
    },
}
FORBIDDEN_PENDING_TERMS: Tuple[str, ...] = ("待定", "待填", "待补", "（待确认）", "(待确认)")

# 授权模式：human_signed = 人类直接签署；session_transcribed = 人类在会话中明确授权后由 Agent 代录
AUTHORIZATION_MODES: Tuple[str, ...] = ("human_signed", "session_transcribed")
AUTHORIZATION_MODE_TRANSCRIBED = "session_transcribed"
# 会话代录模式必填的授权溯源字段
TRANSCRIBED_REQUIRED_FIELDS: Tuple[str, ...] = (
    "authorization_quote",
    "authorization_turn",
    "authorization_at",
    "authorized_by",
    "recorded_by",
)
# 授权原文最小有效长度（防止用空串或单字符敷衍授权溯源）
MIN_AUTHORIZATION_QUOTE_LEN = 2


def split_brief_clarification_sections(content: str) -> Dict[str, str]:
    """按 `### 2.N 标题` 切分八项澄清小节正文（不含标题行）。"""
    headings = list(re.finditer(r"^###\s+(2\.\d+)\s+[^\n]*$", content, re.MULTILINE))
    sections: Dict[str, str] = {}
    for idx, m in enumerate(headings):
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(content)
        sections[m.group(1)] = content[m.end():end]
    return sections


def parse_brief_section_fields(section_text: str) -> Dict[str, str]:
    """解析小节内的 `- key: value` 字段（去引号），重复键取首次出现。"""
    fields: Dict[str, str] = {}
    for line in section_text.splitlines():
        m = re.match(r"^\s*(?:-\s+)?([^:\s][^:]*?)\s*:\s*(.*)$", line)
        if not m:
            continue
        key = m.group(1).strip()
        val = m.group(2).strip().strip('"').strip("'").strip()
        fields.setdefault(key, val)
    return fields


def is_blank_field_value(val: str) -> bool:
    """空值/空列表/空引号字符串均视为未填写。"""
    return val.strip().strip('"').strip("'").strip() in ("", "[]")




def normalize_gate_name(gate_raw: str) -> str:
    """标准化学门禁名称：g0 -> G0, change-01 -> change-01"""
    g = gate_raw.strip()
    upper = g.upper()
    if upper in ("G0", "G1", "G2", "G3"):
        return upper
    if g.lower().startswith("change-"):
        return g
    return g


def get_default_gate_paths(gate: str, root_dir: str) -> Tuple[str, str]:
    """返回给定门禁的默认 (artifact_path, approval_path)"""
    norm = normalize_gate_name(gate)
    gates_dir = os.path.join(root_dir, "gates")
    if norm == "G0":
        return os.path.join(root_dir, "brief.md"), os.path.join(gates_dir, "G0-approval.md")
    elif norm == "G1":
        return os.path.join(root_dir, "outline.md"), os.path.join(gates_dir, "G1-approval.md")
    elif norm == "G2":
        return os.path.join(root_dir, "correction-diff.md"), os.path.join(gates_dir, "G2-approval.md")
    elif norm == "G3":
        # M7 交付物优先 output.docx，不存在则 fall back 到 draft_full.md
        docx_path = os.path.join(root_dir, "delivery", "output.docx")
        if os.path.exists(docx_path):
            return docx_path, os.path.join(gates_dir, "G3-approval.md")
        return os.path.join(root_dir, "draft_full.md"), os.path.join(gates_dir, "G3-approval.md")
    elif norm.lower().startswith("change-"):
        return os.path.join(root_dir, "change-table.md"), os.path.join(gates_dir, f"{norm}-approval.md")
    else:
        return os.path.join(root_dir, f"{norm}-artifact.md"), os.path.join(gates_dir, f"{norm}-approval.md")


def compute_file_sha256(file_path: str) -> str:
    """计算文件的二进制 SHA-256 哈希字符串"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_brief_content_sha256(file_path: str) -> str:
    """
    计算 brief.md 的 brief_content_sha256。
    按规范：将 brief_content_sha256 字段值置空后，全文按 UTF-8 编码、LF 换行符计算 SHA256。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 标准化换行符为 LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 匹配 - brief_content_sha256: ... 或 brief_content_sha256: ... 并将值置空
    # 替换为 `- brief_content_sha256: ""`
    pattern = r"^(\s*(?:-\s+)?brief_content_sha256\s*:\s*).*$"
    replaced_text = re.sub(pattern, r'\g<1>""', text, flags=re.MULTILINE)

    return hashlib.sha256(replaced_text.encode("utf-8")).hexdigest()


def parse_approval_file(file_path: str) -> Dict[str, str]:
    """
    解析签署件中的键值对字段。
    支持 YAML frontmatter 与 Markdown 列表键值对。
    """
    if not os.path.exists(file_path):
        return {}

    fields: Dict[str, str] = {}
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    kv_pattern = re.compile(
        r"^\s*(?:-\s+)?(?:\*\*)?([a-zA-Z0-9_-]+)(?:\*\*)?\s*:\s*(.*?)\s*$"
    )

    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean == "---":
            continue
        m = kv_pattern.match(line_clean)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            # 仅剥除成对的外层引号，内部引号原样保留（授权原文引用常含引号）
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("\"", "'"):
                val = val[1:-1]
            fields[key] = val

    return fields


def emit_json_and_exit(gate: str, state: str, blocked: bool, artifact_sha256: Optional[str], reason: str, exit_code: int):
    """严格单行输出 JSON 并退出"""
    payload = {
        "gate": gate,
        "state": state,
        "blocked": blocked,
        "artifact_sha256": artifact_sha256,
        "reason": reason,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def is_machine_identity(val: str) -> Tuple[bool, str]:
    """
    检查签署者标识或签名是否命中机器标记。
    覆盖: agent, ai, bot, 机器人, 机器, 模型, 自动, 脚本, 程序, llm, gpt, claude,
    gemini, qwen, deepseek, minimax, copilot, assistant, 自动复核, 自动签, subagent, auto.
    大小写不敏感。同时避免误伤 operator_huang, human:reviewer_lead 等合法人类标识。
    """
    if not val:
        return False, ""

    val_clean = val.strip()
    val_lower = val_clean.lower()

    # 1. 保留已有规则：agent:<session-id> 或以 agent: 开头
    if re.match(r"^agent:.*", val_lower):
        return True, f"agent self-signing prefix in '{val_clean}'"

    # 2. 中文机器标识词检测（子串匹配）
    zh_machine_terms = (
        "机器人", "机器", "模型", "自动", "脚本", "程序", "自动复核", "自动签",
    )
    for zh_term in zh_machine_terms:
        if zh_term in val_clean:
            return True, f"contains machine term '{zh_term}'"

    # 3. 英文机器标识词检测（独立 token 边界匹配）
    en_machine_terms = {
        "agent", "ai", "bot", "llm", "gpt", "claude", "gemini",
        "qwen", "deepseek", "minimax", "copilot", "assistant",
        "subagent", "auto",
    }

    # 3a. 正则检测：非英文字母数字边界（支持中文字符、符号、破折号、下划线、空白等边界）
    for term in en_machine_terms:
        pattern = rf"(?<![a-zA-Z0-9]){re.escape(term)}(?![a-zA-Z0-9])"
        if re.search(pattern, val_lower):
            return True, f"contains machine token '{term}'"

    # 3b. 针对驼峰命名（如 AutoSigner -> Auto, Signer）分词检测
    camel_tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b|\d)|[0-9]+", val_clean)
    for tok in camel_tokens:
        tok_l = tok.lower()
        if tok_l in en_machine_terms:
            return True, f"contains machine token '{tok_l}'"

    return False, ""


def check_gate(
    gate: str,
    root_dir: str,
    artifact_override: Optional[str] = None,
    approval_override: Optional[str] = None,
):
    norm_gate = normalize_gate_name(gate)
    default_artifact, default_approval = get_default_gate_paths(norm_gate, root_dir)

    # 默认路径已由 get_default_gate_paths 基于 root_dir 拼接完毕，严禁二次拼接；
    # 仅当调用方显式传入相对路径 override 时才以 root_dir 为基准解析。
    artifact_path = default_artifact
    if artifact_override:
        artifact_path = (
            os.path.normpath(artifact_override)
            if os.path.isabs(artifact_override)
            else os.path.normpath(os.path.join(root_dir, artifact_override))
        )
    approval_path = default_approval
    if approval_override:
        approval_path = (
            os.path.normpath(approval_override)
            if os.path.isabs(approval_override)
            else os.path.normpath(os.path.join(root_dir, approval_override))
        )
    artifact_path = os.path.normpath(artifact_path)
    approval_path = os.path.normpath(approval_path)

    # 1. 检查签署件文件是否存在
    if not os.path.exists(approval_path):
        emit_json_and_exit(
            gate=norm_gate,
            state="PENDING",
            blocked=True,
            artifact_sha256=None,
            reason=f"Approval file not found: {approval_path}",
            exit_code=1,
        )

    # 2. 解析签署件字段
    fields = parse_approval_file(approval_path)

    # 2a. 桩签署件硬拒绝 (STUB_REJECTED)
    # 门禁只接受真实人类签署件。任何声明为 stub: true / stub:true 的演练桩、样板件或
    # 自动生成件一律不得放行，即使其哈希完全吻合。G0/G1/G2/G3/change-<id> 五门共用本校验。
    stub_flag = (fields.get("stub") or "").strip().lower()
    if stub_flag in ("true", "yes", "1"):
        emit_json_and_exit(
            gate=norm_gate,
            state="STUB_REJECTED",
            blocked=True,
            artifact_sha256=(fields.get("artifact_sha256") or "").strip().lower() or None,
            reason="Stub approval rejected: files declaring 'stub: true' are drill mocks, never a human signature",
            exit_code=1,
        )

    # 检查必填字段: gate, decision, signed_by, signed_at, artifact_sha256, signature
    required_keys = ["gate", "decision", "signed_by", "signed_at", "artifact_sha256", "signature"]
    missing_keys = [k for k in required_keys if not fields.get(k)]
    if missing_keys:
        decision_val = fields.get("decision", "PENDING").upper()
        emit_json_and_exit(
            gate=norm_gate,
            state=decision_val if decision_val in ("CHANGES_REQUESTED", "REJECTED") else "PENDING",
            blocked=True,
            artifact_sha256=None,
            reason=f"Approval file missing required field(s): {', '.join(missing_keys)}",
            exit_code=1,
        )

    file_gate = normalize_gate_name(fields["gate"])
    decision = fields["decision"].strip().upper()
    signed_by = fields["signed_by"].strip()
    declared_sha256 = fields["artifact_sha256"].strip().lower()
    signature = fields["signature"].strip()

    # 3. 门禁名称匹配性校验
    if file_gate.lower() != norm_gate.lower():
        emit_json_and_exit(
            gate=norm_gate,
            state="GATE_MISMATCH",
            blocked=True,
            artifact_sha256=declared_sha256 or None,
            reason=f"Approval gate mismatch: expected {norm_gate}, got {file_gate}",
            exit_code=1,
        )

    # 3a. 授权模式判定与校验
    # human_signed：人类直接手工签署（既有路径）。
    # session_transcribed：人类在会话中明确授权，Agent 依授权代录签署件。
    # 代录不改变裁决归属——裁决仍由人类作出，Agent 仅忠实转写并留下可审计溯源。
    auth_mode = (fields.get("authorization_mode") or "human_signed").strip().lower()
    if auth_mode not in AUTHORIZATION_MODES:
        emit_json_and_exit(
            gate=norm_gate,
            state="AUTHORIZATION_MODE_INVALID",
            blocked=True,
            artifact_sha256=declared_sha256 or None,
            reason=f"authorization_mode must be one of {sorted(AUTHORIZATION_MODES)}, got '{auth_mode}'",
            exit_code=1,
        )

    if auth_mode == AUTHORIZATION_MODE_TRANSCRIBED:
        missing_auth = [k for k in TRANSCRIBED_REQUIRED_FIELDS if not (fields.get(k) or "").strip()]
        if missing_auth:
            emit_json_and_exit(
                gate=norm_gate,
                state="AUTHORIZATION_TRACE_INCOMPLETE",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason=(
                    "Session-transcribed approval missing authorization trace field(s): "
                    + ", ".join(missing_auth)
                ),
                exit_code=1,
            )
        quote = (fields.get("authorization_quote") or "").strip()
        if len(quote) < MIN_AUTHORIZATION_QUOTE_LEN:
            emit_json_and_exit(
                gate=norm_gate,
                state="AUTHORIZATION_TRACE_INCOMPLETE",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason=(
                    "authorization_quote must carry the human's own wording "
                    f"(>= {MIN_AUTHORIZATION_QUOTE_LEN} chars), got {len(quote)}"
                ),
                exit_code=1,
            )
        # 授权人必须是人类身份；代录者字段允许是 Agent（由 recorded_by 承载）
        authorized_by = (fields.get("authorized_by") or "").strip()
        is_mach_auth, reason_auth = is_machine_identity(authorized_by)
        if is_mach_auth:
            emit_json_and_exit(
                gate=norm_gate,
                state="AGENT_SIGNATURE_PROHIBITED",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason=(
                    "authorized_by must be a human identifier "
                    f"({reason_auth}), got '{authorized_by}'"
                ),
                exit_code=1,
            )
        # 授权人与签署人必须是同一人，防止代录时张冠李戴
        if authorized_by.lower() != signed_by.lower():
            emit_json_and_exit(
                gate=norm_gate,
                state="AUTHORIZATION_TRACE_INCOMPLETE",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason=(
                    f"authorized_by '{authorized_by}' does not match signed_by '{signed_by}'; "
                    "the transcribed signer must be the human who gave the authorization"
                ),
                exit_code=1,
            )

    # 4. 人类身份与防伪校验 (Human Identity Verification)
    # 4a. 可选字段 approver_role 校验：若存在则必须为 human_decision_maker
    approver_role = fields.get("approver_role")
    if approver_role is not None and approver_role.strip():
        if approver_role.strip().lower() != "human_decision_maker":
            emit_json_and_exit(
                gate=norm_gate,
                state="AGENT_SIGNATURE_PROHIBITED",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason=f"approver_role must be 'human_decision_maker', got '{approver_role.strip()}'",
                exit_code=1,
            )

    # 4b. signed_by 与 signature 两字段任一命中机器标记即拒绝
    is_mach_by, reason_by = is_machine_identity(signed_by)
    if is_mach_by:
        emit_json_and_exit(
            gate=norm_gate,
            state="AGENT_SIGNATURE_PROHIBITED",
            blocked=True,
            artifact_sha256=declared_sha256 or None,
            reason=f"Agent self-signing is strictly prohibited; signed_by must be a human identifier ({reason_by}), got '{signed_by}'",
            exit_code=1,
        )

    # signature 在代录模式下承载人类原话，不得按机器标记误判（人类原话可能含“模型”“自动”等词）
    if auth_mode == AUTHORIZATION_MODE_TRANSCRIBED:
        if not signature:
            emit_json_and_exit(
                gate=norm_gate,
                state="AUTHORIZATION_TRACE_INCOMPLETE",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason="signature must carry the human's own confirming words in session-transcribed mode",
                exit_code=1,
            )
    else:
        is_mach_sig, reason_sig = is_machine_identity(signature)
        if is_mach_sig:
            emit_json_and_exit(
                gate=norm_gate,
                state="AGENT_SIGNATURE_PROHIBITED",
                blocked=True,
                artifact_sha256=declared_sha256 or None,
                reason=f"Agent self-signing is strictly prohibited; signature must not contain machine marker ({reason_sig}), got '{signature}'",
                exit_code=1,
            )

    # 5. 校验 decision 决策状态（优先判定，若未 APPROVED 则直接阻断）
    if decision != "APPROVED":
        # 常见状态: PENDING, REJECTED, CHANGES_REQUESTED
        emit_json_and_exit(
            gate=norm_gate,
            state=decision,
            blocked=True,
            artifact_sha256=declared_sha256 or None,
            reason=f"Approval gate {norm_gate} is in state {decision}",
            exit_code=1,
        )

    # 6. 校验工件是否存在
    if not os.path.exists(artifact_path):
        emit_json_and_exit(
            gate=norm_gate,
            state="ARTIFACT_NOT_FOUND",
            blocked=True,
            artifact_sha256=None,
            reason=f"Artifact file not found: {artifact_path}",
            exit_code=1,
        )

    # 7. 计算工件实际哈希
    actual_sha256 = compute_file_sha256(artifact_path).lower()

    # 8. 校验哈希一致性
    if actual_sha256 != declared_sha256:
        emit_json_and_exit(
            gate=norm_gate,
            state="HASH_MISMATCH",
            blocked=True,
            artifact_sha256=actual_sha256,
            reason=f"Artifact SHA-256 mismatch: artifact={actual_sha256}, approved={declared_sha256}",
            exit_code=1,
        )

    # 9. 校验通过，放行
    emit_json_and_exit(
        gate=norm_gate,
        state="APPROVED",
        blocked=False,
        artifact_sha256=actual_sha256,
        reason=f"Gate {norm_gate} successfully verified and approved by {signed_by}",
        exit_code=0,
    )


def verify_brief_file(brief_path: str) -> None:
    """
    核验 brief.md 是否满足 CRITERION M1-1, M1-2, M1-4, M1-5, M1-6, M2-2, M2-5
    以及 brief_content_sha256 自校验。

    八项澄清（2.1-2.8）为「建议澄清清单」，不是准入条件：
    - 每项必须有合法 clarification_status ∈ {CLARIFIED, NOT_CLARIFIED, NOT_APPLICABLE}；
    - CLARIFIED 项：内容字段非空、无占位符/待定词、枚举取值合法；
    - 非 CLARIFIED 项：必须有 unclarified_reason，正文允许为空或含「未澄清」「不适用」
      标记（占位符/待定词扫描对其豁免），并按协议默认行为给出可执行值（M1-6）。
    结构性不变量不放宽：11 个小节存在、宪法五原则、派生声明、哈希、
    target_local_dir 绝对路径、2.11 每条 human_decision 合法。
    """
    if not os.path.exists(brief_path):
        res = {"valid": False, "reason": f"File not found: {brief_path}"}
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(1)

    with open(brief_path, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []

    # 1. CRITERION M1-1: 检查 11 个独立小节 (2.1 - 2.11)
    expected_sections = [
        "2.1 报告受众",
        "2.2 研究标的与对象",
        "2.3 风格与基调",
        "2.4 背景与历史上下文",
        "2.5 交付目的地",
        "2.6 交付形态与格式约定",
        "2.7 在线载体基准判定",
        "2.8 人机交互与问询模式",
        "2.9 诉求与实体索引",
        "2.10 术语与口径",
        "2.11 继承声明与人工裁决",
    ]
    for sec in expected_sections:
        if sec not in content:
            errors.append(f"Missing section: {sec}")

    # 2. CRITERION M1-2: 派生声明
    sole_declaration = "本文件为本项目唯一事实源，后续大纲、调研与撰写均由此派生；口径冲突时以本文件为准"
    if sole_declaration not in content:
        errors.append(f"Missing authoritative declaration: '{sole_declaration}'")

    # 3. CRITERION M2-2: 项目宪法五原则（全局系统常量逐字比对）
    if "3. 项目宪法" not in content:
        errors.append("Missing section '3. 项目宪法'")
    else:
        for rule in CONSTITUTION_RULES:
            if rule not in content:
                errors.append(f"Missing constitutional rule: {rule}")

    # 4. 八项澄清状态校验 (2.1-2.8)
    # 八项为「建议澄清清单」：不要求全部填满，但每项必须登记合法 clarification_status；
    # 未澄清/不适用项必须登记 unclarified_reason，并按协议默认行为给出可执行值。
    sections = split_brief_clarification_sections(content)
    section_fields: Dict[str, Dict[str, str]] = {}
    scan_text = content  # 占位符/待定词扫描作用域：非 CLARIFIED 项正文整体豁免
    for sec in CLARIFICATION_SECTIONS:
        sec_text = sections.get(sec)
        if sec_text is None:
            continue  # 小节缺失已由 M1-1 报错
        fields = parse_brief_section_fields(sec_text)
        section_fields[sec] = fields

        raw_status = fields.get("clarification_status", "").strip()
        status = raw_status.upper()
        if not raw_status:
            errors.append(
                f"Missing clarification_status in section {sec}. "
                f"Allowed: {list(CLARIFICATION_STATUSES)}"
            )
            continue
        if status not in CLARIFICATION_STATUSES:
            errors.append(
                f"Section {sec} has invalid clarification_status '{raw_status}'. "
                f"Allowed: {list(CLARIFICATION_STATUSES)}"
            )
            continue

        reason = fields.get("unclarified_reason", "").strip()
        if status == "CLARIFIED":
            for key in SECTION_REQUIRED_FIELDS.get(sec, ()):  # 内容字段必须非空
                if is_blank_field_value(fields.get(key, "")):
                    errors.append(
                        f"Section {sec} is CLARIFIED but required field '{key}' is empty"
                    )
            for key, allowed in SOFT_ENUM_FIELDS.get(sec, {}).items():
                val = fields.get(key, "").strip()
                if val and val not in allowed:
                    errors.append(
                        f"Field '{key}' has invalid value '{val}'. Allowed: {sorted(allowed)}"
                    )
        else:
            # 未澄清/不适用：正文允许为空或含「未澄清」「不适用」等标记，从扫描范围中剔除
            scan_text = scan_text.replace(sec_text, "")
            if not reason or "{{" in reason:
                errors.append(
                    f"Section {sec} status {status} requires a non-empty "
                    f"'unclarified_reason' explaining why it was not clarified"
                )
            for key, expected in DEFAULT_NOT_CLARIFIED_FIELD_VALUES.get(sec, {}).items():
                actual = fields.get(key, "").strip()
                if actual != expected:
                    errors.append(
                        f"[CRITERION M1-6] Section {sec} is {status}; field '{key}' must carry the "
                        f"protocol default '{expected}', got '{actual}'"
                    )

    # 4a. 占位符残留检测（作用域：CLARIFIED 八项正文 + 其余小节）
    placeholders = re.findall(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}", scan_text)
    if placeholders:
        errors.append(f"Unresolved template placeholders found: {', '.join(sorted(set(placeholders)))}")

    # 4b. 待定值词表检测 (仅作用于 CLARIFIED 项正文；放行合法状态标记: 待核 与 待索证)
    found_pending = [term for term in FORBIDDEN_PENDING_TERMS if term in scan_text]
    tbd_todo = re.findall(r"(?i)\b(TBD|TODO)\b", scan_text)
    if tbd_todo:
        found_pending.extend(sorted(set(tbd_todo)))
    if found_pending:
        errors.append(f"Forbidden pending/unresolved terms found: {', '.join(sorted(set(found_pending)))}")

    # 4c. source_of_truth [CRITERION M2-5]: 必填；CLARIFIED 时值必须属于声明集合，
    # 非 CLARIFIED 时由 M1-6 默认行为约束（默认 LOCAL_AUTHORITATIVE）。
    if "source_of_truth" not in section_fields.get("2.7", {}):
        errors.append("Missing mandatory enum field: source_of_truth")

    # 4d. 落盘路径 target_local_dir 必须为绝对路径（结构性不变量，与澄清状态无关）
    m_dir = re.search(r"^\s*(?:-\s+)?target_local_dir\s*:\s*[\"']?([^\r\n\"']+)[\"']?", content, re.MULTILINE)
    if not m_dir:
        errors.append("Missing mandatory field: target_local_dir")
    else:
        local_dir_val = m_dir.group(1).strip()
        if not local_dir_val or not os.path.isabs(local_dir_val):
            errors.append(f"target_local_dir must be an absolute path, got '{local_dir_val}'")

    # 5. [CRITERION M1-5]: 2.11 继承声明与人工裁决条目校验
    ic_rows = re.findall(r"\|\s*(IC-[0-9A-Za-z_-]+)\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|", content)
    for row in ic_rows:
        ic_id, claim, src_path, src_sha, decision = row
        d_val = decision.strip().strip("[]").upper()
        if d_val not in {"CONFIRMED", "REVISED"}:
            errors.append(f"Inherited claim '{ic_id}' missing or invalid human_decision: '{decision.strip()}'. Must be CONFIRMED or REVISED")

    # 6. 提取 brief_content_sha256 并验证
    m = re.search(r"brief_content_sha256\s*:\s*[\"']?([a-fA-F0-9]{64})[\"']?", content)
    computed_hash = compute_brief_content_sha256(brief_path)
    if not m:
        errors.append("Missing or invalid brief_content_sha256 (expected 64-char hex)")
    else:
        found_hash = m.group(1).lower()
        if found_hash != computed_hash.lower():
            errors.append(f"brief_content_sha256 mismatch: recorded={found_hash}, computed={computed_hash}")

    if errors:
        res = {"valid": False, "errors": errors}
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(1)
    else:
        res = {"valid": True, "brief_content_sha256": computed_hash, "errors": []}
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.exit(0)


def extract_model_vendor(model_name: str) -> str:
    """提取模型厂商前缀，用于异族模型隔离性比对"""
    m = model_name.strip().lower()
    if "/" in m:
        return m.split("/", 1)[0]
    if ":" in m:
        return m.split(":", 1)[0]
    parts = re.split(r"[-_.]", m)
    return parts[0] if parts else m


def check_provenance_file(file_path: str) -> None:
    """
    [AL-06 & M6-2] 校验对抗复核调用证明 (provenance.json) 的隔离性与防伪契约。
    严格只读，不得修改证明文件。

    判据:
    1. writer.session != reviewer.session；
    2. 当 channel == "异族" 时，校验两者 model 厂商前缀不同；
    3. 当 channel == "同族-零记忆隔离" 时，校验 context_reset == True 且 reviewer.session 为新建会话；
    4. 判定通过时 stdout 输出 {"provenance_valid":true,"isolated":true,"channel":"...","errors":[]}，退出码 0；
    5. 判定失败时 stdout 输出 {"provenance_valid":false,"isolated":false,"status":"BLOCKED_NO_REVIEWER","errors":[...]}，退出码 1。
    """
    if not os.path.exists(file_path):
        payload = {
            "provenance_valid": False,
            "isolated": False,
            "status": "BLOCKED_NO_REVIEWER",
            "errors": [f"Provenance file not found: {file_path}"],
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        payload = {
            "provenance_valid": False,
            "isolated": False,
            "status": "BLOCKED_NO_REVIEWER",
            "errors": [f"Failed to parse provenance JSON: {str(e)}"],
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.exit(1)

    if not isinstance(data, dict):
        payload = {
            "provenance_valid": False,
            "isolated": False,
            "status": "BLOCKED_NO_REVIEWER",
            "errors": ["Provenance content must be a JSON object"],
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.exit(1)

    errors = []

    writer = data.get("writer")
    reviewer = data.get("reviewer")

    if not isinstance(writer, dict):
        errors.append("Missing or invalid 'writer' block in provenance")
    if not isinstance(reviewer, dict):
        errors.append("Missing or invalid 'reviewer' block in provenance")

    if errors:
        payload = {
            "provenance_valid": False,
            "isolated": False,
            "status": "BLOCKED_NO_REVIEWER",
            "errors": errors,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.exit(1)

    writer_session = str(writer.get("session") or "").strip()
    reviewer_session = str(reviewer.get("session") or "").strip()
    writer_model = str(writer.get("model") or "").strip()
    reviewer_model = str(reviewer.get("model") or "").strip()

    # 1. session 必须非空且必须不相同
    if not writer_session:
        errors.append("writer.session must be non-empty")
    if not reviewer_session:
        errors.append("reviewer.session must be non-empty")
    if writer_session and reviewer_session and writer_session == reviewer_session:
        errors.append(f"Writer session and reviewer session must be distinct; found matching '{writer_session}'")

    # 获取 channel 与 context_reset
    channel = (reviewer.get("channel") or data.get("channel") or "").strip()
    context_reset = reviewer.get("context_reset") if "context_reset" in reviewer else data.get("context_reset")

    if not channel:
        errors.append("Missing review 'channel' specification (expected '异族' or '同族-零记忆隔离')")
    elif channel == "异族":
        if not writer_model:
            errors.append("writer.model must be specified for channel '异族'")
        if not reviewer_model:
            errors.append("reviewer.model must be specified for channel '异族'")
        if writer_model and reviewer_model:
            w_vendor = extract_model_vendor(writer_model)
            r_vendor = extract_model_vendor(reviewer_model)
            if w_vendor == r_vendor:
                errors.append(
                    f"Non-homologous channel ('异族') requires differing model vendor prefixes; "
                    f"got writer vendor '{w_vendor}' ({writer_model}) and reviewer vendor '{r_vendor}' ({reviewer_model})"
                )
    elif channel == "同族-零记忆隔离":
        if context_reset is not True:
            errors.append(f"Homologous channel ('同族-零记忆隔离') requires context_reset to be strictly True; got {context_reset}")
    else:
        errors.append(f"Unknown review channel '{channel}'; must be '异族' or '同族-零记忆隔离'")

    if errors:
        payload = {
            "provenance_valid": False,
            "isolated": False,
            "status": "BLOCKED_NO_REVIEWER",
            "errors": errors,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.exit(1)
    else:
        payload = {
            "provenance_valid": True,
            "isolated": True,
            "channel": channel,
            "errors": [],
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.exit(0)


def record_session_approval(
    gate: str,
    root_dir: str,
    authorized_by: str,
    authorization_quote: str,
    authorization_turn: str,
    artifact_override: Optional[str] = None,
    signature: Optional[str] = None,
    decision: str = "APPROVED",
    comments: Optional[str] = None,
    recorded_by: str = "agent:zcode",
) -> None:
    """
    会话授权代录 (Session-Transcribed Approval)

    人类在会话中明确授权后，由 Agent 依授权内容代写门禁签署件。
    代录不改变裁决归属：decision 仍由人类作出，Agent 只负责忠实转写与留痕。

    必填溯源字段：authorization_quote / authorization_turn / authorization_at /
    authorized_by / recorded_by。脚本自动计算工件哈希并回读校验，杜绝手填哈希漂移。
    """
    norm_gate = normalize_gate_name(gate)
    default_artifact, default_approval = get_default_gate_paths(norm_gate, root_dir)

    if artifact_override:
        artifact_path = (
            os.path.normpath(artifact_override)
            if os.path.isabs(artifact_override)
            else os.path.normpath(os.path.join(root_dir, artifact_override))
        )
    else:
        artifact_path = default_artifact
    approval_path = default_approval

    if not os.path.exists(artifact_path):
        emit_json_and_exit(
            gate=norm_gate,
            state="ARTIFACT_NOT_FOUND",
            blocked=True,
            artifact_sha256=None,
            reason=f"Artifact file not found: {artifact_path}",
            exit_code=1,
        )

    quote = (authorization_quote or "").strip()
    if len(quote) < MIN_AUTHORIZATION_QUOTE_LEN:
        emit_json_and_exit(
            gate=norm_gate,
            state="AUTHORIZATION_TRACE_INCOMPLETE",
            blocked=True,
            artifact_sha256=None,
            reason=(
                "authorization_quote must carry the human's own wording "
                f"(>= {MIN_AUTHORIZATION_QUOTE_LEN} chars), got {len(quote)}"
            ),
            exit_code=1,
        )

    is_mach_auth, reason_auth = is_machine_identity(authorized_by)
    if is_mach_auth:
        emit_json_and_exit(
            gate=norm_gate,
            state="AGENT_SIGNATURE_PROHIBITED",
            blocked=True,
            artifact_sha256=None,
            reason=f"authorized_by must be a human identifier ({reason_auth}), got '{authorized_by}'",
            exit_code=1,
        )

    actual_sha256 = compute_file_sha256(artifact_path).lower()
    signed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sig_text = (signature or quote).strip()

    body = f"""# 门禁审批签署件 ({norm_gate} Approval Sign-off)

> 本件由 Agent 依人类在会话中的明确授权代录（authorization_mode: session_transcribed）。
> 授权原话、授权轮次与授权时间见下方字段；裁决归属仍为人类，Agent 仅忠实转写。

- gate: {norm_gate}
- decision: {decision.strip().upper()}
- signed_by: {authorized_by.strip()}
- signed_at: {signed_at}
- artifact_sha256: {actual_sha256}
- signature: {sig_text}
- authorization_mode: {AUTHORIZATION_MODE_TRANSCRIBED}
- authorized_by: {authorized_by.strip()}
- authorization_quote: {quote}
- authorization_turn: {authorization_turn.strip()}
- authorization_at: {signed_at}
- recorded_by: {recorded_by}
- comments: {(comments or "").strip()}
"""

    with open(approval_path, "w", encoding="utf-8") as f:
        f.write(body)

    # 代录后立即回读校验，确保写出的签署件自身能通过门禁
    check_gate(
        gate=norm_gate,
        root_dir=root_dir,
        artifact_override=artifact_path,
        approval_override=approval_path,
    )


def main():
    parser = argparse.ArgumentParser(description="Universal Gate Guard for rigorous research report pipeline")
    parser.add_argument("--gate", type=str, help="Gate name: G0, G1, G2, G3, change-<id>")
    parser.add_argument("--check-only", action="store_true", help="Perform non-interactive check on gate status")
    parser.add_argument("--verify", action="store_true", help="Verify gate with explicit artifact and approval paths")
    parser.add_argument("--artifact", type=str, help="Explicit path to artifact file")
    parser.add_argument("--approval", type=str, help="Explicit path to approval file")
    parser.add_argument("--root", type=str, default=".", help="Workspace root directory (default: current directory)")

    # 辅助工具选项
    parser.add_argument("--compute-hash", type=str, help="Compute file SHA-256")
    parser.add_argument("--compute-brief-content-hash", type=str, help="Compute brief.md content hash (UTF-8 LF, field blanked)")
    parser.add_argument("--verify-brief", type=str, help="Verify brief.md against constitutional & section standards")
    parser.add_argument("--check-provenance", type=str, help="Verify machine-readable adversarial review provenance JSON")

    # 会话授权代录
    parser.add_argument("--record-approval", action="store_true", help="Record a session-transcribed gate approval on behalf of an authorized human")
    parser.add_argument("--authorized-by", type=str, help="Human identity who gave the authorization")
    parser.add_argument("--authorization-quote", type=str, help="Verbatim human authorizing words")
    parser.add_argument("--authorization-turn", type=str, help="Session/turn reference of the authorization")
    parser.add_argument("--signature", type=str, help="Confirming words; defaults to the authorization quote")
    parser.add_argument("--decision", type=str, default="APPROVED", help="Decision to record (APPROVED / REJECTED / CHANGES_REQUESTED)")
    parser.add_argument("--comments", type=str, help="Free-text comments to record")
    parser.add_argument("--recorded-by", type=str, default="agent:zcode", help="Identity of the agent performing the transcription")

    args = parser.parse_args()

    if args.check_provenance:
        check_provenance_file(args.check_provenance)
        return

    if args.compute_hash:
        target = args.compute_hash
        if not os.path.exists(target):
            sys.stderr.write(f"File not found: {target}\n")
            sys.exit(1)
        h = compute_file_sha256(target)
        sys.stdout.write(json.dumps({"file": target, "sha256": h}) + "\n")
        sys.exit(0)

    if args.compute_brief_content_hash:
        target = args.compute_brief_content_hash
        if not os.path.exists(target):
            sys.stderr.write(f"File not found: {target}\n")
            sys.exit(1)
        h = compute_brief_content_sha256(target)
        sys.stdout.write(json.dumps({"file": target, "brief_content_sha256": h}) + "\n")
        sys.exit(0)

    if args.verify_brief:
        verify_brief_file(args.verify_brief)
        return

    if not args.gate:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.record_approval:
        if not (args.authorized_by and args.authorization_quote and args.authorization_turn):
            sys.stderr.write(
                "--record-approval requires --authorized-by, --authorization-quote and --authorization-turn\n"
            )
            sys.exit(1)
        record_session_approval(
            gate=args.gate,
            root_dir=args.root,
            authorized_by=args.authorized_by,
            authorization_quote=args.authorization_quote,
            authorization_turn=args.authorization_turn,
            artifact_override=args.artifact,
            signature=args.signature,
            decision=args.decision,
            comments=args.comments,
            recorded_by=args.recorded_by,
        )
        return

    check_gate(
        gate=args.gate,
        root_dir=args.root,
        artifact_override=args.artifact,
        approval_override=args.approval,
    )


if __name__ == "__main__":
    main()
