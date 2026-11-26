#!/usr/bin/env python3
"""
test_g0_session_authorization.py - 会话授权代录门禁签署件独立黑箱验收测试套件

测试对象:
- src/scripts/gate_guard.py（--record-approval 代录命令与放行校验）
- src/scripts/storage_guard.py（台账打勾对代录签署件的授权认定）
- src/templates/approval_gate.template.md（两种签署模式的模板契约）
- src/references/P1_grill_me_protocol.md（P1 第 4.4 节阻断铁律与代录规则）

契约绑定:
- 宪法原则 2「定性裁决权归人类」：裁决归属与记录方式分离，Agent 不得自行裁决。
- P1 §4.4：签署件两种记录方式（human_signed / session_transcribed）与五个溯源字段。
- G0/G1/G2/G3/change-<id> 五门共用同一套防伪校验。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SRC_SCRIPTS = os.path.join(MODULE_ROOT, "src", "scripts")
SRC_TEMPLATES = os.path.join(MODULE_ROOT, "src", "templates")
SRC_REFERENCES = os.path.join(MODULE_ROOT, "src", "references")

GATE_GUARD_PY = os.path.join(SRC_SCRIPTS, "gate_guard.py")
STORAGE_GUARD_PY = os.path.join(SRC_SCRIPTS, "storage_guard.py")
APPROVAL_TEMPLATE = os.path.join(SRC_TEMPLATES, "approval_gate.template.md")
P1_PROTOCOL = os.path.join(SRC_REFERENCES, "P1_grill_me_protocol.md")


def run_gate(*args):
    """运行 gate_guard.py，返回 (exit_code, parsed_json)。"""
    proc = subprocess.run(
        [sys.executable, GATE_GUARD_PY, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = None
    if proc.stdout.strip():
        payload = json.loads(proc.stdout.strip())
    return proc.returncode, payload


def make_workspace(tmp_path):
    """构造最小工作区：brief.md + gates/ 目录。"""
    (tmp_path / "gates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "brief.md").write_text("artifact v1\n", encoding="utf-8")
    return tmp_path


def record_approval(ws, **kwargs):
    """调用 --record-approval 代录签署件。"""
    args = [
        "--record-approval",
        "--gate", "G0",
        "--artifact", "brief.md",
        "--root", str(ws),
    ]
    args += kwargs.get("extra", [])
    return run_gate(*args)


# ---------------------------------------------------------------------------
# 1. 代录命令正向路径
# ---------------------------------------------------------------------------

def test_record_approval_writes_traceable_signoff_and_passes_gate(tmp_path):
    """
    [Scenario: 人类会话授权后 Agent 代录签署件并自动放行]
    人类在会话中明确授权后，Agent 依授权原话代写 G0 签署件：
    1. 命令退出码为 0，state 为 APPROVED、blocked 为 false；
    2. 签署件含五个溯源字段 authorization_quote / authorization_turn /
       authorization_at / authorized_by / recorded_by；
    3. authorization_mode 标记为 session_transcribed；
    4. signed_by 与 authorized_by 同为人类身份；
    5. artifact_sha256 由脚本计算，与工件实际哈希一致。
    """
    ws = make_workspace(tmp_path)
    code, data = record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过，确认放行 G0",
            "--authorization-turn", "session:sess_abc/msg:123",
        ],
    )
    assert code == 0, f"record-approval should exit 0, got {code}: {data}"
    assert data["state"] == "APPROVED"
    assert data["blocked"] is False

    approval = (ws / "gates" / "G0-approval.md").read_text(encoding="utf-8")
    for field in (
        "authorization_quote",
        "authorization_turn",
        "authorization_at",
        "authorized_by",
        "recorded_by",
    ):
        assert f"- {field}:" in approval, f"Missing trace field: {field}"
    assert "- authorization_mode: session_transcribed" in approval
    assert "- signed_by: 聂绍臣" in approval
    assert "- authorized_by: 聂绍臣" in approval
    assert "通过，确认放行 G0" in approval
    assert "session:sess_abc/msg:123" in approval

    # 哈希必须与工件实际一致
    proc = subprocess.run(
        [sys.executable, GATE_GUARD_PY, "--compute-hash", str(ws / "brief.md")],
        stdout=subprocess.PIPE,
        text=True,
    )
    actual = json.loads(proc.stdout.strip())["sha256"]
    assert data["artifact_sha256"] == actual


def test_record_approval_requires_all_authorization_arguments(tmp_path):
    """
    [Scenario: 缺少授权原话或授权轮次时拒绝代录]
    Agent 不得在缺少人类授权留痕要素时生成签署件：
    1. 缺 --authorization-quote 时退出码为 1；
    2. 缺 --authorization-turn 时退出码为 1；
    3. 两种情况下均不产生 gates/G0-approval.md。
    """
    ws = make_workspace(tmp_path)
    code, _ = record_approval(
        ws,
        extra=["--authorized-by", "聂绍臣", "--authorization-turn", "session:s1/msg:1"],
    )
    assert code == 1
    assert not (ws / "gates" / "G0-approval.md").exists()

    code, _ = record_approval(
        ws,
        extra=["--authorized-by", "聂绍臣", "--authorization-quote", "通过"],
    )
    assert code == 1
    assert not (ws / "gates" / "G0-approval.md").exists()


def test_record_approval_rejects_machine_identity_as_authorizer(tmp_path):
    """
    [Scenario: 授权人写成机器身份时拒绝代录]
    授权人必须是人类身份：--authorized-by agent:xxx 必须被拒绝，
    且不得留下半成品签署件。
    """
    ws = make_workspace(tmp_path)
    code, _ = record_approval(
        ws,
        extra=[
            "--authorized-by", "agent:zcode",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    assert code == 1
    assert not (ws / "gates" / "G0-approval.md").exists()


# ---------------------------------------------------------------------------
# 2. 代录签署件的防伪校验
# ---------------------------------------------------------------------------

def _write_approval(ws, body):
    (ws / "gates" / "G0-approval.md").write_text(body, encoding="utf-8")


def test_transcribed_approval_missing_trace_field_is_blocked(tmp_path):
    """
    [Scenario: 代录签署件缺任一溯源字段即阻断]
    缺少 authorization_turn 时门禁必须返回 AUTHORIZATION_TRACE_INCOMPLETE、
    blocked=true、退出码 1。
    """
    ws = make_workspace(tmp_path)
    _write_approval(
        ws,
        "# 审批\n\n"
        "- gate: G0\n"
        "- decision: APPROVED\n"
        "- signed_by: 聂绍臣\n"
        "- signed_at: 2026-11-26T03:00:00Z\n"
        "- artifact_sha256: " + "0" * 64 + "\n"
        "- signature: 通过\n"
        "- authorization_mode: session_transcribed\n"
        "- authorized_by: 聂绍臣\n"
        "- authorization_quote: 通过\n"
        "- authorization_at: 2026-11-26T03:00:00Z\n"
        "- recorded_by: agent:zcode\n",
    )
    code, data = run_gate("--gate", "G0", "--check-only", "--root", str(ws))
    assert code == 1
    assert data["state"] == "AUTHORIZATION_TRACE_INCOMPLETE"
    assert data["blocked"] is True
    assert "authorization_turn" in data["reason"]


def test_transcribed_approval_authorizer_mismatch_is_blocked(tmp_path):
    """
    [Scenario: 授权人与签署人不是同一人即阻断]
    代录不得张冠李戴：authorized_by 与 signed_by 不一致时必须阻断。
    """
    ws = make_workspace(tmp_path)
    record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    approval = ws / "gates" / "G0-approval.md"
    approval.write_text(
        approval.read_text(encoding="utf-8").replace(
            "- authorized_by: 聂绍臣", "- authorized_by: 李四"
        ),
        encoding="utf-8",
    )
    code, data = run_gate("--gate", "G0", "--check-only", "--root", str(ws))
    assert code == 1
    assert data["state"] == "AUTHORIZATION_TRACE_INCOMPLETE"
    assert "authorized_by" in data["reason"]


def test_transcribed_approval_rejects_machine_authorizer(tmp_path):
    """
    [Scenario: 代录签署件的授权人写成机器身份即阻断]
    authorized_by 命中 agent: 前缀时返回 AGENT_SIGNATURE_PROHIBITED。
    """
    ws = make_workspace(tmp_path)
    record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    approval = ws / "gates" / "G0-approval.md"
    approval.write_text(
        approval.read_text(encoding="utf-8").replace(
            "- authorized_by: 聂绍臣", "- authorized_by: agent:zcode"
        ).replace("- signed_by: 聂绍臣", "- signed_by: agent:zcode"),
        encoding="utf-8",
    )
    code, data = run_gate("--gate", "G0", "--check-only", "--root", str(ws))
    assert code == 1
    assert data["state"] == "AGENT_SIGNATURE_PROHIBITED"
    assert data["blocked"] is True


def test_transcribed_approval_allows_human_wording_containing_machine_words(tmp_path):
    """
    [Scenario: 人类原话含“模型”“自动”等词不得被误判为机器签署]
    代录模式下 signature 与 authorization_quote 承载人类原话，
    不得按机器标记误杀；防伪由 authorized_by 与溯源字段承担。
    """
    ws = make_workspace(tmp_path)
    quote = "模型网关的自动选型方案我看过了，确认通过"
    code, data = record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", quote,
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    assert code == 0, f"Human wording must not be misjudged, got {code}: {data}"
    assert data["state"] == "APPROVED"


def test_transcribed_approval_blocked_when_artifact_changed_after_signing(tmp_path):
    """
    [Scenario: 签署后工件被改动即阻断]
    代录签署件同样受哈希约束：工件内容变化后门禁必须返回 HASH_MISMATCH。
    """
    ws = make_workspace(tmp_path)
    record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    (ws / "brief.md").write_text("artifact v2 changed\n", encoding="utf-8")
    code, data = run_gate("--gate", "G0", "--check-only", "--root", str(ws))
    assert code == 1
    assert data["state"] == "HASH_MISMATCH"
    assert data["blocked"] is True


def test_invalid_authorization_mode_is_blocked(tmp_path):
    """
    [Scenario: 非法 authorization_mode 即阻断]
    取值必须属于 {human_signed, session_transcribed}，否则阻断。
    """
    ws = make_workspace(tmp_path)
    record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    approval = ws / "gates" / "G0-approval.md"
    approval.write_text(
        approval.read_text(encoding="utf-8").replace(
            "authorization_mode: session_transcribed", "authorization_mode: whatever"
        ),
        encoding="utf-8",
    )
    code, data = run_gate("--gate", "G0", "--check-only", "--root", str(ws))
    assert code == 1
    assert data["state"] == "AUTHORIZATION_MODE_INVALID"


def test_legacy_human_signed_path_still_passes(tmp_path):
    """
    [Scenario: 人类直接签署的旧路径不受新机制影响]
    不写 authorization_mode 字段时按 human_signed 处理，校验行为与改动前一致。
    """
    ws = make_workspace(tmp_path)
    code, data = record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    assert code == 0
    approval = ws / "gates" / "G0-approval.md"
    approval.write_text(
        approval.read_text(encoding="utf-8").replace(
            "- authorization_mode: session_transcribed\n", ""
        ),
        encoding="utf-8",
    )
    code, data = run_gate("--gate", "G0", "--check-only", "--root", str(ws))
    assert code == 0, f"Legacy path must still pass, got {code}: {data}"
    assert data["state"] == "APPROVED"


# ---------------------------------------------------------------------------
# 3. 台账打勾授权认定
# ---------------------------------------------------------------------------

LEDGER_TEMPLATE = (
    "# 台账\n\n"
    "| 阶段 | 任务 ID | 任务内容与目标 | 任务完成 | 四分状态 | 责任角色 | agent_建议 | 产出物路径与 content_sha256 | 依据签署件与哈希 |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    "| P1 | T-P1-01 | G0 门禁签署 | {mark} | 已审定 | Human | - | gates/G0-approval.md | G0 签署放行件 |\n"
)


def _write_ledger(ws, mark="[x]"):
    (ws / "progress-log.md").write_text(
        LEDGER_TEMPLATE.format(mark=mark), encoding="utf-8"
    )


def test_ledger_accepts_checkbox_backed_by_transcribed_approval(tmp_path):
    """
    [Scenario: 代录签署件可作为台账打勾依据]
    有效代录签署件在场时，T-P1-01 的 [x] 必须被认可，不得回滚。
    """
    ws = make_workspace(tmp_path)
    record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    _write_ledger(ws, "[x]")
    proc = subprocess.run(
        [
            sys.executable,
            STORAGE_GUARD_PY,
            "--root", str(ws),
            "--check-ledger",
            "--ledger", str(ws / "progress-log.md"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["ledger_valid"] is True, payload
    assert "[x]" in (ws / "progress-log.md").read_text(encoding="utf-8")


def test_ledger_reverts_checkbox_when_transcribed_trace_incomplete(tmp_path):
    """
    [Scenario: 溯源字段不完整时台账打勾必须回滚]
    代录签署件缺 authorization_turn 时，T-P1-01 的 [x] 必须被强制回滚为 [ ]。
    """
    ws = make_workspace(tmp_path)
    record_approval(
        ws,
        extra=[
            "--authorized-by", "聂绍臣",
            "--authorization-quote", "通过",
            "--authorization-turn", "session:s1/msg:1",
        ],
    )
    approval = ws / "gates" / "G0-approval.md"
    approval.write_text(
        approval.read_text(encoding="utf-8").replace(
            "- authorization_turn: session:s1/msg:1\n", ""
        ),
        encoding="utf-8",
    )
    _write_ledger(ws, "[x]")
    proc = subprocess.run(
        [
            sys.executable,
            STORAGE_GUARD_PY,
            "--root", str(ws),
            "--check-ledger",
            "--ledger", str(ws / "progress-log.md"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["ledger_valid"] is False, payload
    assert "T-P1-01" in payload["reverted_tasks"]
    assert "[x]" not in (ws / "progress-log.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 4. 模板与协议文本契约
# ---------------------------------------------------------------------------

def test_approval_template_documents_both_signing_modes():
    """
    [Scenario: 签署件模板声明两种记录方式与代录字段]
    approval_gate.template.md 必须：
    1. 出现 human_signed 与 session_transcribed 两种模式；
    2. 列出五个溯源字段；
    3. 给出 --record-approval 命令示例。
    """
    text = open(APPROVAL_TEMPLATE, encoding="utf-8").read()
    assert "human_signed" in text
    assert "session_transcribed" in text
    for field in (
        "authorization_quote",
        "authorization_turn",
        "authorization_at",
        "authorized_by",
        "recorded_by",
    ):
        assert field in text, f"Missing trace field in template: {field}"
    assert "--record-approval" in text


def test_p1_protocol_states_transcription_rule_and_anti_fabrication():
    """
    [Scenario: P1 协议写明代录规则与禁止伪造授权]
    P1_grill_me_protocol.md 必须：
    1. 声明两种记录方式；
    2. 列出五个溯源字段；
    3. 明确 Agent 不得自行裁决、不得伪造授权原话；
    4. 保留 agent:* 自签阻断条款。
    """
    text = open(P1_PROTOCOL, encoding="utf-8").read()
    assert "session_transcribed" in text
    assert "human_signed" in text
    for field in (
        "authorization_quote",
        "authorization_turn",
        "authorization_at",
        "authorized_by",
        "recorded_by",
    ):
        assert field in text, f"Missing trace field in P1 protocol: {field}"
    assert "严禁伪造授权" in text
    assert "严禁代理自签" in text
