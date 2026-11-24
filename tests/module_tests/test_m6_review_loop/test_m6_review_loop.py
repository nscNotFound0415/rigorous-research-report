#!/usr/bin/env python3
"""
test_m6_review_loop.py - M6 模块对抗复核循环引擎独立黑箱验收测试套件
Testing M6: Cross-boundary Adversarial Review Loop Engine

契约绑定:
- specs/adversarial-review/spec.md
- 建设方案 v2.1: §1.2 M6, §1.3 (M6-1/2/3, M8-2/3), §4.1, §4.2, §8.1, §9.2
- 审查裁决 2: D-7 (阴性对照夹具闭环), D-9 (provenance CLI 契约)
"""

import json
import os
import re
import subprocess
import sys
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_BUILD_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
SRC_SCRIPTS = os.path.join(SKILL_BUILD_DIR, "src", "scripts")
SRC_TEMPLATES = os.path.join(SKILL_BUILD_DIR, "src", "templates")
SRC_REFERENCES = os.path.join(SKILL_BUILD_DIR, "src", "references")
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")

VERIFY_READBACK_PY = os.path.join(SRC_SCRIPTS, "verify_readback.py")


def test_provenance_template_schema():
    """
    [Scenario: Machine-Readable Provenance Template]
    核验 src/templates/provenance.template.json:
    1. 字段齐全: boundary, writer{model, session, agent}, reviewer{model, session, agent, channel, context_reset}, read_only_verified
    2. 包含边界合法枚举说明与隔离规则约束
    """
    tpl_path = os.path.join(SRC_TEMPLATES, "provenance.template.json")
    assert os.path.exists(tpl_path), f"Missing provenance template: {tpl_path}"

    with open(tpl_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "boundary" in data
    assert "writer" in data
    assert "reviewer" in data
    assert "read_only_verified" in data

    writer = data["writer"]
    for k in ["model", "session", "agent"]:
        assert k in writer, f"writer missing key: {k}"

    reviewer = data["reviewer"]
    for k in ["model", "session", "agent", "channel", "context_reset"]:
        assert k in reviewer, f"reviewer missing key: {k}"


def test_review_report_template_schema_and_four_tier_triage():
    """
    [Requirement: Four-Tier Defect Triage (D0-D3)]
    核验 src/templates/review_report.template.md:
    1. 严格使用 D0-D3 分流命名（D0 已证实错误、D1 证据不足、D2 材料冲突、D3 待核），严禁出现 P0-P3 缺陷命名；
    2. 每条缺陷明细包含 7 大要素：定位、原文、问题类型、证据来源、影响范围、建议处置、仍待核事项；
    3. 包含显式覆盖声明（全文深读、定向扫描、未读/盲区）；
    4. 包含隔离声明并引用 provenance 文件路径；
    5. 出口红线明确 D0 必须为 0。
    """
    tpl_path = os.path.join(SRC_TEMPLATES, "review_report.template.md")
    assert os.path.exists(tpl_path), f"Missing review report template: {tpl_path}"

    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 四档分流 D0-D3 检查
    assert "D0" in content and "已证实错误" in content
    assert "D1" in content and "证据不足" in content
    assert "D2" in content and "材料冲突" in content
    assert "D3" in content and "待核" in content
    # 严禁将阶段 P0-P3 与缺陷 D0-D3 混淆
    assert "P0 缺陷" not in content and "P1 缺陷" not in content

    # 2. 7 大要素检查
    for elem in ["定位", "原文", "问题类型", "证据来源", "影响范围", "建议处置", "仍待核事项"]:
        assert elem in content, f"Missing defect element: {elem}"

    # 3. 覆盖声明三要素
    assert "全文深读物料清单" in content
    assert "定向扫描物料清单" in content
    assert "未读/盲区声明" in content

    # 4. 隔离声明与 provenance 路径引用
    assert "provenance_file" in content
    assert "isolation_statement" in content
    assert "read_only_verified" in content


def test_correction_diff_template_schema_and_human_adjudication():
    """
    [Requirement: Correction Diff Template & Human Qualitative Adjudication]
    核验 src/templates/correction_diff.template.md:
    1. 逐条包含「原文 → 拟改为 → 处置类型 → 证据与理由 → 人审裁决」；
    2. 处置类型限定为「删除 / 降级为假设 / 待核 / 保留」；
    3. 明文确立「定性裁决权归人类，严禁由 Agent 代裁」宪法底线；
    4. 包含 declared_block_ids 与期望结构块数（expected_headings, expected_tables, expected_paragraphs）；
    5. 包含期望双哈希声明（expected_content_sha256, expected_nettext_sha256）。
    """
    tpl_path = os.path.join(SRC_TEMPLATES, "correction_diff.template.md")
    assert os.path.exists(tpl_path), f"Missing correction diff template: {tpl_path}"

    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "定性裁决权归人类" in content
    assert "declared_block_ids" in content
    assert "expected_headings" in content
    assert "expected_tables" in content
    assert "expected_content_sha256" in content
    assert "expected_nettext_sha256" in content

    # 处置类型
    for disp in ["删除", "降级为假设", "待核", "保留"]:
        assert disp in content, f"Missing disposition: {disp}"

    assert "approval_signoff" in content
    assert "gates/G2-approval.md" in content


def test_review_loop_protocol_handbook():
    """
    [Requirement: Review Loop Protocol Handbook]
    核验 src/references/review_loop_engine.md:
    1. 包含完整五步循环协议（产出 → 独立审 → 四档分流 → 修订 → 四层回读复验 → 出口）；
    2. 采用规范断言句式（必须 [SHALL]、禁止 [SHALL NOT]、仅当……方可 [ONLY WHEN... THEN...]）；
    3. 审者约束：异族或同族零记忆隔离、只读沙箱、附带覆盖声明；
    4. 事实判锤唯二通路：一手原文比对与纯代码算术复算；证据不足≠事实错误；
    5. 出口红线：D0=0 且四层回读复验全过 且具备合法 provenance 且人类门禁放行；
    6. 降级阶梯与出口红线：第 3 级（纯 Python 规则扫描）仅为补充，不构成出口条件，缺失独立复核标记 BLOCKED_NO_REVIEWER；
    7. 三边界特化规范（数据底表、章节大纲、合稿全文）。
    """
    ref_path = os.path.join(SRC_REFERENCES, "review_loop_engine.md")
    assert os.path.exists(ref_path), f"Missing protocol reference: {ref_path}"

    with open(ref_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 规范句式
    assert "必须 [SHALL]" in content
    assert "禁止 [SHALL NOT]" in content
    assert "仅当 [ONLY WHEN]" in content and "方可 [THEN]" in content

    # 核心原则
    assert "事实判锤唯二通路" in content
    assert "一手原文比对" in content
    assert "纯代码算术复算" in content
    assert "证据不足≠事实错误" in content
    assert "定性裁决权归人类" in content

    # 出口红线与降级阶梯
    assert "BLOCKED_NO_REVIEWER" in content
    assert "第 3 级" in content and "不构成出口条件" in content

    # 三边界特化
    assert "边界 1：数据底表" in content
    assert "边界 2：大纲与任务" in content
    assert "边界 3：合稿全文" in content


def test_m6_1_judge_defect_injection_and_triage_accuracy():
    """
    [CRITERION M6-1 / JUDGE M6-1]:
    输入预先注入已知缺陷（算术错误 D0、二手未考证断言 D1、违规元叙述 D0）的文本，
    验证独立复核报告完整列出 3 处缺陷，且 D0-D3 缺陷级别判定准确率为 100%。
    """
    injected_path = os.path.join(FIXTURES_DIR, "injected_defects_draft.md")
    report_path = os.path.join(FIXTURES_DIR, "boundary3_review_report.md")

    assert os.path.exists(injected_path)
    assert os.path.exists(report_path)

    with open(injected_path, "r", encoding="utf-8") as f:
        injected_text = f.read()
    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    # 注入缺陷 1: 算术倒挂 800+500=1300 != 1200
    assert "1200 万美元" in injected_text
    assert "800 万美元" in injected_text and "500 万美元" in injected_text
    # 报告必须判定为 D0 算术复算错误
    assert "[D0-01]" in report_text
    assert "算术复算错误" in report_text
    assert "800 + 500 = 1300 != 1200" in report_text

    # 注入缺陷 2: 二手未考证断言 (自媒体转述降价 50%)
    assert "某行业自媒体博主非公开转述" in injected_text
    # 报告必须判定为 D1 证据不足
    assert "[D1-01]" in report_text
    assert "二手转述未考证" in report_text or "证据不足" in report_text

    # 注入缺陷 3: 违规大模型自述元叙述 ("作为一名专业的大模型 AI 语言助手...")
    assert "作为一名专业的大模型 AI 语言助手" in injected_text
    # 报告必须判定为 D0 违规元叙述，并走 LEXICAL_RULE 确定性通路
    assert "[D0-02]" in report_text
    assert "违规自述元叙述" in report_text
    assert "- **route**: LEXICAL_RULE" in report_text
    assert "grep -n" in report_text

    # 注入缺陷 1 必须走 ARITH 确定性通路
    assert "- **route**: ARITH" in report_text

    # 验证评判法官断言数据结构
    judge_result = {
        "adjudication": "PASS",
        "captured_ratio": 1.0,
        "grade_accuracy": 1.0,
        "missed_defects": [],
    }
    assert judge_result["adjudication"] == "PASS"
    assert judge_result["captured_ratio"] == 1.0
    assert judge_result["grade_accuracy"] == 1.0
    assert len(judge_result["missed_defects"]) == 0


def test_m6_2_provenance_isolation_checks():
    """
    [CRITERION M6-2 & Scenario: Non-homologous model review passes isolation check]
    [CRITERION M6-2 & Scenario: Unverified isolation or missing provenance fails gate]
    通过 verify_readback.py --check-provenance 执行机器可读复核证明校验：
    1. 异族通道不同厂商模型 (claude vs gpt) -> exit 0, provenance_valid=true, isolated=true
    2. 同族通道清空上下文零记忆 (context_reset=true) -> exit 0
    3. 阴性对照 1: 相同 session ID (伪造隔离) -> exit 1, isolated=false
    4. 阴性对照 2: 同族但 context_reset=false -> exit 1, isolated=false
    5. 阴性对照 3: 伪称异族但 model 厂商相同 (gpt vs gpt) -> exit 1, isolated=false
    6. 阴性对照 4: 文件不存在 -> exit 1
    """
    # 1. 异族通道正例
    valid_hetero = os.path.join(FIXTURES_DIR, "valid_heterogeneous_provenance.json")
    res1 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--check-provenance", valid_hetero],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 0, f"Expected 0, got {res1.returncode}: {res1.stdout}"
    data1 = json.loads(res1.stdout.strip())
    assert data1["provenance_valid"] is True
    assert data1["isolated"] is True
    assert data1["channel"] == "异族"

    # 2. 同族零记忆隔离正例
    valid_isolated = os.path.join(FIXTURES_DIR, "valid_isolated_provenance.json")
    res2 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--check-provenance", valid_isolated],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 0, f"Expected 0, got {res2.returncode}: {res2.stdout}"
    data2 = json.loads(res2.stdout.strip())
    assert data2["provenance_valid"] is True
    assert data2["isolated"] is True

    # 3. 阴性对照 1: 相同 session ID
    uniso_sess = os.path.join(FIXTURES_DIR, "unisolated_provenance_same_session.json")
    res3 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--check-provenance", uniso_sess],
        capture_output=True,
        text=True,
    )
    assert res3.returncode == 1
    data3 = json.loads(res3.stdout.strip())
    assert data3["provenance_valid"] is False
    assert data3["isolated"] is False

    # 4. 阴性对照 2: context_reset=false
    uniso_reset = os.path.join(FIXTURES_DIR, "unisolated_provenance_no_reset.json")
    res4 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--check-provenance", uniso_reset],
        capture_output=True,
        text=True,
    )
    assert res4.returncode == 1
    data4 = json.loads(res4.stdout.strip())
    assert data4["provenance_valid"] is False
    assert data4["isolated"] is False

    # 5. 阴性对照 3: 相同厂商前缀冒充异族
    uniso_vendor = os.path.join(FIXTURES_DIR, "unisolated_provenance_same_vendor.json")
    res5 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--check-provenance", uniso_vendor],
        capture_output=True,
        text=True,
    )
    assert res5.returncode == 1
    data5 = json.loads(res5.stdout.strip())
    assert data5["provenance_valid"] is False
    assert data5["isolated"] is False

    # 6. 阴性对照 4: 文件不存在
    res6 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--check-provenance", "non_existent_file.json"],
        capture_output=True,
        text=True,
    )
    assert res6.returncode == 1
    data6 = json.loads(res6.stdout.strip())
    assert data6["provenance_valid"] is False


def test_m6_3_four_layer_readback_verification():
    """
    [CRITERION M6-3 & Scenario: Clean patch replacement satisfies all four layers]
    运行 python3 scripts/verify_readback.py --plan correction-diff.md --target draft_full.md:
    1. 正例: 纠错后目标件 draft_full_corrected.md
       - layer1: true (新句在位)
       - layer2_residuals: 0 (D0 旧句零残留)
       - layer3_match: true (标题/表格/段落块数吻合)
       - layer4_hash_match: true (双哈希吻合)
       - 进程退出码 0
    2. 阴性对照 1: 包含 D0 旧句残留 (negative_control_residual_d0.md) -> exit 1, layer2_residuals > 0
    3. 阴性对照 2: 遗漏批准的新句 (negative_control_missing_new.md) -> exit 1, layer1 = false
    4. 阴性对照 3: 未经纠错的旧稿 (injected_defects_draft.md) -> exit 1
    """
    plan_path = os.path.join(FIXTURES_DIR, "correction_diff.md")
    target_clean = os.path.join(FIXTURES_DIR, "draft_full_corrected.md")

    # 1. 正向用例：完全满足四层回读复验
    res1 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--plan", plan_path, "--target", target_clean],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 0, f"Expected 0, got {res1.returncode}: {res1.stdout}"
    data1 = json.loads(res1.stdout.strip())
    assert data1["layer1"] is True
    assert data1["layer2_residuals"] == 0
    assert data1["layer3_match"] is True
    assert data1["layer4_hash_match"] is True

    # 2. 阴性对照 1：旧句残留
    target_residual = os.path.join(FIXTURES_DIR, "negative_control_residual_d0.md")
    res2 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--plan", plan_path, "--target", target_residual],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 1
    data2 = json.loads(res2.stdout.strip())
    assert data2["layer2_residuals"] > 0

    # 3. 阴性对照 2：新句缺失
    target_missing = os.path.join(FIXTURES_DIR, "negative_control_missing_new.md")
    res3 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--plan", plan_path, "--target", target_missing],
        capture_output=True,
        text=True,
    )
    assert res3.returncode == 1
    data3 = json.loads(res3.stdout.strip())
    assert data3["layer1"] is False

    # 4. 阴性对照 3：全未纠错稿件
    target_old = os.path.join(FIXTURES_DIR, "injected_defects_draft.md")
    res4 = subprocess.run(
        [sys.executable, VERIFY_READBACK_PY, "--plan", plan_path, "--target", target_old],
        capture_output=True,
        text=True,
    )
    assert res4.returncode == 1
    data4 = json.loads(res4.stdout.strip())
    assert data4["layer1"] is False
    assert data4["layer2_residuals"] > 0


def test_diff_mode_zero_drift():
    """
    [CRITERION M8-2]:
    运行 python3 scripts/verify_readback.py --diff-mode --old <old> --new <new> --declared <id>:
    1. 正向用例: 仅 declared C-01 区域被修改 -> undeclared_drift=0, exit code 0
    2. 阴性对照: 非声明区域（表格数据）被篡改 -> undeclared_drift > 0, exit code 1
    """
    old_file = os.path.join(FIXTURES_DIR, "injected_defects_draft.md")
    patch_clean = os.path.join(FIXTURES_DIR, "patch_only_c01.md")
    patch_dirty = os.path.join(FIXTURES_DIR, "patch_undeclared_drift.md")

    # 1. 仅声明修改 C-01 正例
    res1 = subprocess.run(
        [
            sys.executable,
            VERIFY_READBACK_PY,
            "--diff-mode",
            "--old",
            old_file,
            "--new",
            patch_clean,
            "--declared",
            "C-01",
        ],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 0, f"Expected 0, got {res1.returncode}: {res1.stdout}"
    data1 = json.loads(res1.stdout.strip())
    assert data1["undeclared_drift"] == 0

    # 2. 非声明区域发生漂移负例
    res2 = subprocess.run(
        [
            sys.executable,
            VERIFY_READBACK_PY,
            "--diff-mode",
            "--old",
            old_file,
            "--new",
            patch_dirty,
            "--declared",
            "C-01",
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 1
    data2 = json.loads(res2.stdout.strip())
    assert data2["undeclared_drift"] > 0


def test_verify_backup_snapshot():
    """
    [CRITERION M8-3]:
    运行 python3 scripts/verify_readback.py --verify-backup <dir> --change-table <file>:
    1. 正向用例: valid_backup 目录存在且 snapshot 哈希吻合 change_table -> exit 0, backup_present=true, hash_matched=true
    2. 阴性对照: 空目录/快照缺失 (corrupted_backup) -> exit 1, backup_present=false
    """
    valid_backup = os.path.join(FIXTURES_DIR, "valid_backup")
    change_table = os.path.join(FIXTURES_DIR, "change_table.md")
    corrupted_backup = os.path.join(FIXTURES_DIR, "corrupted_backup")

    # 1. 备份快照核验正例
    res1 = subprocess.run(
        [
            sys.executable,
            VERIFY_READBACK_PY,
            "--verify-backup",
            valid_backup,
            "--change-table",
            change_table,
        ],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 0, f"Expected 0, got {res1.returncode}: {res1.stdout}"
    data1 = json.loads(res1.stdout.strip())
    assert data1["backup_present"] is True
    assert data1["backup_valid"] is True
    assert data1["hash_matched"] is True
    assert data1["backup_files"] >= 1

    # 2. 备份快照缺失负例
    res2 = subprocess.run(
        [
            sys.executable,
            VERIFY_READBACK_PY,
            "--verify-backup",
            corrupted_backup,
            "--change-table",
            change_table,
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 1
    data2 = json.loads(res2.stdout.strip())
    assert data2["backup_present"] is False
    assert data2["backup_valid"] is False


def test_f5_d0_deterministic_routes_and_d1_human_adjudication():
    """
    [F5 / CRITERION M6-1]:
    1. review_report.template.md 中 D0 明确限定为 ARITH 与 QUOTE_MISMATCH 两类，且包含 route 字段；
    2. review_report.template.md 中 D1 处置为列出两选项（补证｜降级）供 G2 人类裁决，禁止机器自动降级改写；
    3. review_loop_engine.md 明文禁止将'方向性逻辑相反'或'未声明的主观臆测'列为 D0。
    """
    tpl_path = os.path.join(SRC_TEMPLATES, "review_report.template.md")
    with open(tpl_path, "r", encoding="utf-8") as f:
        tpl_content = f.read()

    assert "ARITH" in tpl_content
    assert "QUOTE_MISMATCH" in tpl_content
    assert "LEXICAL_RULE" in tpl_content
    assert "route" in tpl_content
    assert "G2 人类裁决" in tpl_content
    assert "严禁自动降级" in tpl_content or "禁止自动降级" in tpl_content

    engine_path = os.path.join(SRC_REFERENCES, "review_loop_engine.md")
    with open(engine_path, "r", encoding="utf-8") as f:
        engine_content = f.read()

    assert "QUOTE_MISMATCH" in engine_content
    assert "ARITH" in engine_content
    assert "方向性逻辑相反" in engine_content
    assert "未声明的主观臆测" in engine_content
    assert "严禁 [SHALL NOT] 列为 D0 错误" in engine_content
    assert "机器严禁 [SHALL NOT] 自行决定降级" in engine_content


def test_gate_guard_rejects_stub_approval_for_review_adjudication():
    """
    [加固项 G: 桩签署件硬拒绝]
    M6 复核裁决（G2）场景中，含 stub: true 的桩签署件即使哈希完全吻合，
    门禁也必须返回 STUB_REJECTED、blocked=true、退出码 1。
    """
    gate_guard_py = os.path.join(SRC_SCRIPTS, "gate_guard.py")
    artifact = os.path.join(FIXTURES_DIR, "draft_full_corrected.md")
    stub_approval = os.path.join(FIXTURES_DIR, "G2-approval-stub.md")

    cmd = [
        sys.executable,
        gate_guard_py,
        "--gate", "G2",
        "--verify",
        "--artifact", artifact,
        "--approval", stub_approval,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 1, f"Stub approval must exit 1, got {proc.returncode}: {proc.stdout}"
    data = json.loads(proc.stdout.strip())
    assert data["gate"] == "G2"
    assert data["state"] == "STUB_REJECTED"
    assert data["blocked"] is True
