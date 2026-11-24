#!/usr/bin/env python3
"""
test_m7_delivery.py - M7 统一合稿与多格式交付模块独立黑箱验收测试套件
Testing M7: Monolithic Drafting, Text Hygiene, OOXML Builder & Delivery Readback

契约绑定:
- specs/draft-synthesis/spec.md
- 建设方案 v2.1: §1.2 M7, §1.3 (CRITERION M7-1/2/3/4), §3.3, §8.1, §9.2
- 审查裁决 2: D-6 (delivery_readback.json), D-7 (broken_citation_draft.md),
              D-8 (共享连续 30 字符子串去重判据), D-15 (注入数 5 处与数字撞号消除)
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_BUILD_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import pdf_probe  # noqa: E402  测试侧独立 PDF 取证（不导入被测脚本）

SRC_SCRIPTS = os.path.join(SKILL_BUILD_DIR, "src", "scripts")
SRC_TEMPLATES = os.path.join(SKILL_BUILD_DIR, "src", "templates")
SRC_REFERENCES = os.path.join(SKILL_BUILD_DIR, "src", "references")
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")

AUDIT_TEXT_HYGIENE_PY = os.path.join(SRC_SCRIPTS, "audit_text_hygiene.py")
CITATION_CHECK_PY = os.path.join(SRC_SCRIPTS, "citation_check.py")
BUILD_DOCX_PY = os.path.join(SRC_SCRIPTS, "build_docx.py")
BUILD_PDF_PY = os.path.join(SRC_SCRIPTS, "build_pdf.py")
TOC_TWO_PASS_PY = os.path.join(SRC_SCRIPTS, "toc_two_pass.py")
DELIVERY_READBACK_PY = os.path.join(SRC_SCRIPTS, "delivery_readback.py")
GATE_GUARD_PY = os.path.join(SRC_SCRIPTS, "gate_guard.py")
FORBIDDEN_TERMS_JSON = os.path.join(SRC_TEMPLATES, "forbidden_terms.json")

DRAFT_CLEAN_MD = os.path.join(FIXTURES_DIR, "draft_full_clean.md")
EVIDENCE_INDEX_MD = os.path.join(FIXTURES_DIR, "evidence-index.md")
DIRTY_META_DRAFT_MD = os.path.join(FIXTURES_DIR, "dirty_meta_draft.md")
BROKEN_CITATION_DRAFT_MD = os.path.join(FIXTURES_DIR, "broken_citation_draft.md")
REDUNDANT_SECTIONS_DRAFT_MD = os.path.join(FIXTURES_DIR, "redundant_sections_draft.md")
INLINE_VIOLATION_DRAFT_MD = os.path.join(FIXTURES_DIR, "inline_violation_with_allowlist.md")
MULTIPAGE_TOC_DRAFT_MD = os.path.join(FIXTURES_DIR, "toc_multipage.md")
DELIVERY_DOCX_FIXTURE = os.path.join(FIXTURES_DIR, "delivery", "output.docx")
G3_APPROVAL_VALID = os.path.join(FIXTURES_DIR, "gates", "G3-approval-valid.md")
G3_APPROVAL_MACHINE = os.path.join(FIXTURES_DIR, "gates", "G3-approval-machine-signed.md")
G3_APPROVAL_INVALID_ROLE = os.path.join(FIXTURES_DIR, "gates", "G3-approval-invalid-role.md")
G3_APPROVAL_HASH_MISMATCH = os.path.join(FIXTURES_DIR, "gates", "G3-approval-hash-mismatch.md")


def test_forbidden_terms_rules_and_9_rigor_declarations_schema():
    """
    [Scenario: Allowlisted rigor declarations pass without false positives]
    核验 src/templates/forbidden_terms.json:
    1. 结构完整：含 patterns 与 allowlist；
    2. 穷尽保护既有的 9 类严谨性声明白名单；
    3. 模式覆盖元叙述、自述型表述与 AI 腔。
    """
    assert os.path.exists(FORBIDDEN_TERMS_JSON), f"Missing config: {FORBIDDEN_TERMS_JSON}"

    with open(FORBIDDEN_TERMS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "patterns" in data and len(data["patterns"]) >= 4
    assert "allowlist" in data and len(data["allowlist"]) >= 9

    # 验证 9 类严谨性声明白名单关键词
    expected_rigor_keywords = [
        "不得跨口径相减",
        "不是发布数据",
        "不构成法律意见",
        "情景假设",
        "不构成对全部品类与全部时点的普遍结论",
        "不得以数量拆分规避",
        "不构成降价或涨价",
        "不能与单一输出挂牌价相减",
        "不重复正文叙述",
    ]

    all_allow_regexes = " ".join(item.get("regex", "") for item in data["allowlist"])
    all_allow_descs = " ".join(item.get("description", "") for item in data["allowlist"])

    for kw in expected_rigor_keywords:
        assert kw in all_allow_regexes or kw in all_allow_descs, f"Missing 9-rigor declaration keyword: {kw}"


def test_audit_text_hygiene_positive_control():
    """
    [CRITERION M7-1 正向用例]
    运行 audit_text_hygiene.py 扫描干净草稿，断言违规匹配计数为 0，
    且 9 类严谨性声明零误报，退出码为 0。
    """
    cmd = [
        sys.executable,
        AUDIT_TEXT_HYGIENE_PY,
        DRAFT_CLEAN_MD,
        "--rules",
        FORBIDDEN_TERMS_JSON,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 0, f"audit_text_hygiene failed with returncode {res.returncode}: {res.stderr}"
    data = json.loads(res.stdout.strip())
    assert "violations" in data
    assert data["violations"] == [], f"Expected 0 violations, got: {data['violations']}"


def test_audit_text_hygiene_section_deduplication():
    """
    [Scenario: Section deduplication verification passes]
    核验去重判据：任意两节间共享连续 30 字符子串数量为 0。
    """
    cmd = [
        sys.executable,
        AUDIT_TEXT_HYGIENE_PY,
        DRAFT_CLEAN_MD,
        "--rules",
        FORBIDDEN_TERMS_JSON,
        "--check-dedup",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert "shared_substrings" in data
    assert data["shared_substrings"] == [], f"Found unexpected shared substrings: {data['shared_substrings']}"


def test_audit_text_hygiene_negative_control_dirty_meta_draft():
    """
    [CRITERION M7-1 阴性对照 (a) - D-15 闭环]
    传入含 5 处元叙述/自述词的旧稿 dirty_meta_draft.md，
    断言精准捕获全部 5 处违规项，9 类严谨性声明零误报，退出码为 1。
    """
    cmd = [
        sys.executable,
        AUDIT_TEXT_HYGIENE_PY,
        DIRTY_META_DRAFT_MD,
        "--rules",
        FORBIDDEN_TERMS_JSON,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Expected returncode 1 for dirty draft, got {res.returncode}"
    data = json.loads(res.stdout.strip())
    violations = data.get("violations", [])

    # 断言精准捕获全部 5 处注入违禁词
    assert len(violations) == 5, f"Expected exactly 5 violations, got {len(violations)}: {violations}"

    matched_texts = [v["matched_text"] for v in violations]
    assert "如前所述" in matched_texts
    assert "前轮内部测算" in matched_texts
    assert "本报告不给出" in matched_texts
    assert "本节不引述" in matched_texts
    assert "第一性原理" in matched_texts


def test_audit_text_hygiene_negative_control_redundant_sections():
    """
    [Scenario: Section deduplication negative control - D-8 闭环]
    传入包含跨章节连续 30 字符重复的草稿，断言检出章节冗余并退出码 1。
    """
    cmd = [
        sys.executable,
        AUDIT_TEXT_HYGIENE_PY,
        REDUNDANT_SECTIONS_DRAFT_MD,
        "--rules",
        FORBIDDEN_TERMS_JSON,
        "--check-dedup",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Expected returncode 1 for redundant sections, got {res.returncode}"
    data = json.loads(res.stdout.strip())
    assert "shared_substrings" in data and len(data["shared_substrings"]) >= 1

    shared = data["shared_substrings"][0]
    assert shared["length"] >= 30
    assert "海外算力中心选址需综合评估" in shared["shared_text"]


def test_citation_check_positive_control():
    """
    [CRITERION M7-2 正向用例]
    运行 citation_check.py 检查合规草稿，所有正文引用均在 evidence-index 存在，
    图表编号连续无断号，stdout 字段齐备，退出码为 0。
    """
    cmd = [
        sys.executable,
        CITATION_CHECK_PY,
        DRAFT_CLEAN_MD,
        "--evidence-index",
        EVIDENCE_INDEX_MD,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 0, f"citation_check failed: {res.stderr}"
    data = json.loads(res.stdout.strip())
    assert data["dangling_refs"] == []
    assert data["unnumbered_figs"] == []
    assert data["dangling_tables"] == []


def test_citation_check_negative_control_broken_citations_and_figs():
    """
    [CRITERION M7-2 阴性对照 (b) - D-7 闭环]
    传入含虚构引用与断号图表的旧料 broken_citation_draft.md，
    断言捕获悬空引用 EVD-999_FICTIONAL、缺少 图 2 及未定义 表 9，退出码为 1。
    """
    cmd = [
        sys.executable,
        CITATION_CHECK_PY,
        BROKEN_CITATION_DRAFT_MD,
        "--evidence-index",
        EVIDENCE_INDEX_MD,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Expected exit code 1 for broken citations, got {res.returncode}"
    data = json.loads(res.stdout.strip())

    assert "EVD-999_FICTIONAL" in data["dangling_refs"]
    assert any("缺少 图 2" in item for item in data["unnumbered_figs"])
    assert any("表 9" in item for item in data["dangling_tables"])


def test_build_docx_idempotency_and_component_hashes():
    """
    [Scenario: Idempotent build produces identical component hashes]
    [CRITERION M7-3 构建幂等性]
    对同一 draft_full_clean.md 连续构建两次 Word 交付物，
    断言 build_manifest.json 中所有部件哈希 100% 逐项一致，且 docx 二进制哈希一致。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx1 = os.path.join(tmpdir, "output_run1.docx")
        manifest1 = os.path.join(tmpdir, "manifest_run1.json")
        docx2 = os.path.join(tmpdir, "output_run2.docx")
        manifest2 = os.path.join(tmpdir, "manifest_run2.json")

        cmd1 = [sys.executable, BUILD_DOCX_PY, DRAFT_CLEAN_MD, "--out", docx1, "--manifest", manifest1]
        res1 = subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert res1.returncode == 0, f"Run 1 failed: {res1.stderr}"

        cmd2 = [sys.executable, BUILD_DOCX_PY, DRAFT_CLEAN_MD, "--out", docx2, "--manifest", manifest2]
        res2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert res2.returncode == 0, f"Run 2 failed: {res2.stderr}"

        with open(manifest1, "r", encoding="utf-8") as f:
            m1 = json.load(f)
        with open(manifest2, "r", encoding="utf-8") as f:
            m2 = json.load(f)

        comp1 = m1["components"]
        comp2 = m2["components"]

        # 断言所有 8 个部件哈希完全一致
        assert len(comp1) == 8, f"Expected 8 components, got {len(comp1)}"
        for part_name, hash1 in comp1.items():
            assert part_name in comp2, f"Missing part in run 2: {part_name}"
            assert hash1 == comp2[part_name], f"Hash mismatch for {part_name}: {hash1} vs {comp2[part_name]}"

        # 断言生成的两个 docx 二进制文件哈希 100% 一致
        with open(docx1, "rb") as f1, open(docx2, "rb") as f2:
            h1 = hashlib.sha256(f1.read()).hexdigest()
            h2 = hashlib.sha256(f2.read()).hexdigest()
        assert h1 == h2, f"Binary docx hash mismatch: {h1} vs {h2}"


def test_build_pdf_execution_and_graceful_fallback():
    """
    [CRITERION M7-3 PDF 构建与优雅降级]
    若 soffice 可用，执行实际转换；若 soffice 缺失，优雅降级返回退出码 0，严禁造假。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx = os.path.join(tmpdir, "output.docx")
        pdf = os.path.join(tmpdir, "output.pdf")
        manifest = os.path.join(tmpdir, "manifest.json")

        subprocess.run([sys.executable, BUILD_DOCX_PY, DRAFT_CLEAN_MD, "--out", docx, "--manifest", manifest], check=True)

        cmd = [sys.executable, BUILD_PDF_PY, docx, "--out", pdf]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        assert res.returncode == 0, f"build_pdf failed with returncode {res.returncode}: {res.stderr}"
        data = json.loads(res.stdout.strip())

        if shutil.which("soffice") or shutil.which("libreoffice"):
            assert data["pdf"] is True
            assert os.path.exists(pdf) and os.path.getsize(pdf) > 0
        else:
            assert data["pdf"] is False
            assert data.get("reason") == "soffice_unavailable"


def test_toc_two_pass_and_delivery_readback_pipeline():
    """
    [Scenario: Delivery readback confirms zero heading and page mismatches]
    [CRITERION M7-3 双向回读校验与页码零倒挂]
    执行端到端交付流水线：
    1. build_docx.py 生成初版 docx
    2. build_pdf.py 生成 pdf
    3. toc_two_pass.py 执行目录两遍法回填页码
    4. delivery_readback.py 校验目录与标题差集为空且页码吻合，退出码为 0
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        delivery_dir = os.path.join(tmpdir, "delivery")
        docx = os.path.join(delivery_dir, "output.docx")
        pdf = os.path.join(delivery_dir, "output.pdf")
        manifest = os.path.join(delivery_dir, "build_manifest.json")
        readback_json = os.path.join(delivery_dir, "delivery_readback.json")

        # 1. 第一遍构建
        res1 = subprocess.run([sys.executable, BUILD_DOCX_PY, DRAFT_CLEAN_MD, "--out", docx, "--manifest", manifest], check=True)

        # 2. 生成 PDF
        res2 = subprocess.run([sys.executable, BUILD_PDF_PY, docx, "--out", pdf], check=True)

        # 3. 第二遍回填
        res3 = subprocess.run([sys.executable, TOC_TWO_PASS_PY, docx, pdf], stdout=subprocess.PIPE, text=True, check=True)
        toc_info = json.loads(res3.stdout.strip())
        assert toc_info["toc_backfilled"] is True
        assert toc_info["entries_count"] == 3

        # 4. 回读校验
        cmd_rb = [
            sys.executable,
            DELIVERY_READBACK_PY,
            "--docx",
            docx,
            "--pdf",
            pdf,
            "--source",
            DRAFT_CLEAN_MD,
            "--out",
            readback_json,
        ]
        res_rb = subprocess.run(cmd_rb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        assert res_rb.returncode == 0, f"delivery_readback failed: {res_rb.stderr}"
        rb_data = json.loads(res_rb.stdout.strip())

        # 核心契约断言：两个差集与页码不匹配项必须同时为空数组
        assert rb_data["toc_minus_headings"] == []
        assert rb_data["headings_minus_toc"] == []
        assert rb_data["page_mismatch"] == []

        # 检查落盘文件 delivery_readback.json 存在且结构完备
        assert os.path.exists(readback_json)
        with open(readback_json, "r", encoding="utf-8") as f:
            disk_rb = json.load(f)
        assert len(disk_rb["headings"]) == 3
        assert len(disk_rb["toc_entries"]) == 3


def test_delivery_readback_fallback_when_pdf_missing():
    """
    [CRITERION M7-3 显式标记断言]
    若 PDF 不可用（缺失），delivery_readback.py 必须显式输出 page_mismatch: "skipped_no_pdf"，
    绝不可谎报通过。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx = os.path.join(tmpdir, "output.docx")
        manifest = os.path.join(tmpdir, "manifest.json")
        readback_json = os.path.join(tmpdir, "readback.json")

        subprocess.run([sys.executable, BUILD_DOCX_PY, DRAFT_CLEAN_MD, "--out", docx, "--manifest", manifest], check=True)

        cmd = [
            sys.executable,
            DELIVERY_READBACK_PY,
            "--docx",
            docx,
            "--pdf",
            os.path.join(tmpdir, "nonexistent.pdf"),
            "--source",
            DRAFT_CLEAN_MD,
            "--out",
            readback_json,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        assert res.returncode == 0
        data = json.loads(res.stdout.strip())
        assert data["toc_minus_headings"] == []
        assert data["headings_minus_toc"] == []
        assert data["page_mismatch"] == "skipped_no_pdf"


def test_audit_text_hygiene_sentence_granularity_negative_control():
    """
    [R2 阴性对照] 单行内「违禁短语 + 严谨性声明」并存时，
    逐句判定必须精准捕获违禁短语所在句子，同行的严谨性声明不得豁免违禁句，退出码 1。
    """
    cmd = [
        sys.executable,
        AUDIT_TEXT_HYGIENE_PY,
        INLINE_VIOLATION_DRAFT_MD,
        "--rules",
        FORBIDDEN_TERMS_JSON,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Expected returncode 1, got {res.returncode}. stdout: {res.stdout}"
    data = json.loads(res.stdout.strip())
    violations = data.get("violations", [])

    assert len(violations) == 1, f"Expected exactly 1 violation, got {len(violations)}: {violations}"
    v = violations[0]
    assert v["rule_id"] == "F-01"
    assert v["matched_text"] == "如前所述"
    assert v["sentence"] == "如前所述，海外选址需评估电费"


def test_audit_text_hygiene_expanded_forbidden_terms_r3():
    """
    [R3 违禁短语扩展与「如X所述」近邻变体覆盖]
    测试法官抓取的 6 个漏检短语与近邻变体独立注入时均能被精确检出并阻断 (exit 1)。
    """
    terms_to_test = [
        ("综上所述", "F-01"),
        ("众所周知", "F-02"),
        ("值得注意的是", "F-02"),
        ("上文提到", "F-01"),
        ("如上所述", "F-01"),
        ("本报告将", "F-01"),
        ("如前文所述", "F-01"),
        ("正如上文所述", "F-01"),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        for term, expected_cat in terms_to_test:
            sample_file = os.path.join(tmpdir, f"test_{term}.md")
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write(f"# 测试章节\n\n{term}，数据表明成本具备显著优势。\n")

            cmd = [
                sys.executable,
                AUDIT_TEXT_HYGIENE_PY,
                sample_file,
                "--rules",
                FORBIDDEN_TERMS_JSON,
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            assert res.returncode == 1, f"Term '{term}' failed to trigger violation exit code 1"
            data = json.loads(res.stdout.strip())
            violations = data.get("violations", [])
            assert len(violations) >= 1, f"Term '{term}' produced 0 violations"
            matched_terms = [v["matched_text"] for v in violations]
            assert any(term in m or m in term for m in matched_terms), f"Term '{term}' not found in matched: {matched_terms}"


def test_g3_gate_valid_human_approval_passes():
    """
    [CRITERION M7-4 正向用例]
    使用人类排他签署且哈希匹配的 G3 审批件，G3 门禁必须放行，state 为 APPROVED，退出码 0。
    """
    cmd = [
        sys.executable,
        GATE_GUARD_PY,
        "--gate", "G3",
        "--verify",
        "--artifact", DELIVERY_DOCX_FIXTURE,
        "--approval", G3_APPROVAL_VALID,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 0, f"G3 valid gate verification failed: {res.stderr}\nstdout: {res.stdout}"
    data = json.loads(res.stdout.strip())
    assert data["gate"] == "G3"
    assert data["state"] == "APPROVED"
    assert data["blocked"] is False
    assert data["artifact_sha256"] == "8afef4627ded3e2dbc480b4dcb76a02b93b4c4bcc40b973386866fe668714ea5"


def test_g3_gate_machine_signed_negative_blocks():
    """
    [CRITERION M7-4 / R1 机器签名阴性对照 - 法官实测案例]
    当签署件包含 AI/Agent/机器签名时，即使工件哈希 100% 正确，
    亦必须拒绝放行，state 为 AGENT_SIGNATURE_PROHIBITED，blocked 为 true，退出码 1。
    """
    cmd = [
        sys.executable,
        GATE_GUARD_PY,
        "--gate", "G3",
        "--verify",
        "--artifact", DELIVERY_DOCX_FIXTURE,
        "--approval", G3_APPROVAL_MACHINE,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Machine signed G3 approval must exit 1, got {res.returncode}. stdout: {res.stdout}"
    data = json.loads(res.stdout.strip())
    assert data["gate"] == "G3"
    assert data["state"] == "AGENT_SIGNATURE_PROHIBITED"
    assert data["blocked"] is True
    assert "Agent self-signing is strictly prohibited" in data["reason"]


def test_g3_gate_invalid_role_negative_blocks():
    """
    [CRITERION M7-4 / R1 approver_role 校验阴性对照]
    若存在可选字段 approver_role 但值非 human_decision_maker，必须阻断并返回退出码 1。
    """
    cmd = [
        sys.executable,
        GATE_GUARD_PY,
        "--gate", "G3",
        "--verify",
        "--artifact", DELIVERY_DOCX_FIXTURE,
        "--approval", G3_APPROVAL_INVALID_ROLE,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Invalid approver_role must exit 1, got {res.returncode}"
    data = json.loads(res.stdout.strip())
    assert data["gate"] == "G3"
    assert data["state"] == "AGENT_SIGNATURE_PROHIBITED"
    assert data["blocked"] is True
    assert "approver_role must be 'human_decision_maker'" in data["reason"]


def test_g3_gate_hash_mismatch_negative_blocks():
    """
    [CRITERION M7-4 哈希不匹配阴性对照]
    工件实际哈希与签署声明哈希不符时，必须阻断，state 为 HASH_MISMATCH，退出码 1。
    """
    cmd = [
        sys.executable,
        GATE_GUARD_PY,
        "--gate", "G3",
        "--verify",
        "--artifact", DELIVERY_DOCX_FIXTURE,
        "--approval", G3_APPROVAL_HASH_MISMATCH,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Hash mismatch must exit 1, got {res.returncode}"
    data = json.loads(res.stdout.strip())
    assert data["gate"] == "G3"
    assert data["state"] == "HASH_MISMATCH"
    assert data["blocked"] is True


def test_g3_gate_stub_approval_rejected():
    """
    [加固项 G: 桩签署件硬拒绝]
    含 stub: true 的 G3 桩签署件即使哈希完全吻合，也必须 STUB_REJECTED 并无条件阻断。
    """
    stub_approval = os.path.join(FIXTURES_DIR, "gates", "G3-approval-stub.md")
    cmd = [
        sys.executable,
        GATE_GUARD_PY,
        "--gate", "G3",
        "--verify",
        "--artifact", DELIVERY_DOCX_FIXTURE,
        "--approval", stub_approval,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    assert res.returncode == 1, f"Stub approval must exit 1, got {res.returncode}: {res.stdout}"
    data = json.loads(res.stdout.strip())
    assert data["gate"] == "G3"
    assert data["state"] == "STUB_REJECTED"
    assert data["blocked"] is True


# ---------------------------------------------------------------------------
# 目录页码回归用例（交付物目录多页 + 生成/校验分离）
# ---------------------------------------------------------------------------

def _build_delivery(md_path, workdir):
    """构建 docx 与 pdf，返回 (docx_path, pdf_path)。soffice 不可用时 skip。"""
    os.makedirs(workdir, exist_ok=True)
    docx = os.path.join(workdir, "output.docx")
    pdf = os.path.join(workdir, "output.pdf")
    manifest = os.path.join(workdir, "build_manifest.json")

    subprocess.run(
        [sys.executable, BUILD_DOCX_PY, md_path, "--out", docx, "--manifest", manifest],
        check=True,
    )

    env = dict(os.environ)
    env["HOME"] = os.path.join(workdir, "lo_home")
    os.makedirs(env["HOME"], exist_ok=True)
    res = subprocess.run(
        [sys.executable, BUILD_PDF_PY, docx, "--out", pdf],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    assert res.returncode == 0, res.stderr
    info = json.loads(res.stdout.strip())
    if info.get("pdf") is not True:
        pytest.skip(f"soffice unavailable: {info}")
    return docx, pdf


@pytest.fixture(scope="module")
def multipage_delivery(tmp_path_factory):
    """构建 >=40 条目录项（目录占 2 页）的交付物并完成两遍法回填，供多个用例复用。"""
    workdir = str(tmp_path_factory.mktemp("toc_multipage"))
    docx, pdf = _build_delivery(MULTIPAGE_TOC_DRAFT_MD, workdir)

    res = subprocess.run(
        [sys.executable, TOC_TWO_PASS_PY, docx, pdf],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    assert res.returncode == 0, f"toc_two_pass failed: {res.stdout} {res.stderr}"
    toc_info = json.loads(res.stdout.strip())
    return {"workdir": workdir, "docx": docx, "pdf": pdf, "toc": toc_info}


def test_toc_multipage_entries_match_real_body_pages(multipage_delivery):
    """
    [新增用例 1] 目录占 2 页及以上（>=40 条目录项）时，
    逐条核对 docx 目录页码 == 该标题在 PDF 正文中的真实页码。
    """
    docx = multipage_delivery["docx"]
    pdf = multipage_delivery["pdf"]
    toc_info = multipage_delivery["toc"]

    entries = pdf_probe.read_docx_toc(docx)
    assert len(entries) >= 40, f"fixture must produce >=40 TOC entries, got {len(entries)}"

    page_texts = pdf_probe.extract_page_texts(pdf)
    toc_pages = pdf_probe.toc_page_numbers(page_texts)
    assert len(toc_pages) >= 2, f"fixture must produce a multi-page TOC, got {toc_pages}"

    # 被测脚本自己报告的目录页数与测试侧独立实测一致
    assert toc_info["toc_pages"] == len(toc_pages)
    assert toc_info["body_start_page"] == toc_pages[-1] + 1

    titles = [title for title, _ in entries]
    true_pages, missing = pdf_probe.locate_body_pages(titles, page_texts, toc_pages[-1] + 1)
    assert missing == [], f"titles not found in body: {missing}"

    mismatched = [
        {"title": title, "docx_page": recorded, "pdf_page": true_pages.get(title)}
        for title, recorded in entries
        if true_pages.get(title) != recorded
    ]
    assert mismatched == [], f"TOC page vs real body page mismatch: {mismatched[:5]}"

    # 目录页码必须全部落在正文区域，绝不能是目录页
    assert all(true_pages[t] > toc_pages[-1] for t in titles)


def test_toc_heading_present_in_toc_page_does_not_win(multipage_delivery):
    """
    [新增用例 2] 标题文本同时出现在目录页与正文页时，回填结果不得取目录页。
    """
    docx = multipage_delivery["docx"]
    pdf = multipage_delivery["pdf"]

    page_texts = pdf_probe.extract_page_texts(pdf)
    toc_pages = pdf_probe.toc_page_numbers(page_texts)
    toc_region = "".join(page_texts[p] for p in toc_pages)

    entries = pdf_probe.read_docx_toc(docx)
    true_pages, missing = pdf_probe.locate_body_pages(
        [t for t, _ in entries], page_texts, toc_pages[-1] + 1
    )
    assert missing == []

    for title, recorded in entries:
        # 前提：该标题确实同时出现在目录页文本中
        assert title in toc_region
        assert recorded == true_pages[title]
        assert recorded != toc_pages[0]
        assert recorded > toc_pages[-1], f"{title} wrongly resolved to TOC page {recorded}"


def test_toc_unresolved_entry_fails_loudly(tmp_path):
    """
    [新增用例 3] 目录中存在正文不存在的标题时，
    toc_two_pass 必须退出码 1 并报 unresolved_toc_entries，且不得回填任何猜测页码。
    """
    docx, pdf = _build_delivery(DRAFT_CLEAN_MD, str(tmp_path))
    phantom = "幽灵章节：正文中并不存在"

    entries_before = pdf_probe.read_docx_toc(docx)
    pdf_probe.insert_toc_entry(docx, phantom, 2)
    entries_injected = pdf_probe.read_docx_toc(docx)
    assert len(entries_injected) == len(entries_before) + 1

    res = subprocess.run(
        [sys.executable, TOC_TWO_PASS_PY, docx, pdf],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    assert res.returncode == 1, f"expected exit 1, got {res.returncode}: {res.stdout}"
    data = json.loads(res.stdout.strip())
    assert data["toc_backfilled"] is False
    assert phantom in data["unresolved_toc_entries"]

    # 失败时不写猜测页码：目录页码应保持第一遍占位值 2
    entries_after = pdf_probe.read_docx_toc(docx)
    assert [p for _, p in entries_after] == [p for _, p in entries_injected]


def test_delivery_readback_detects_tampered_toc_page(multipage_delivery, tmp_path):
    """
    [新增用例 4] 人为把 docx 目录页码改错后，delivery_readback 必须报出
    page_mismatch 非空并退出码 1（证明校验侧未复用生成侧的错误假设）。
    """
    import xml.sax.saxutils as saxutils

    src_docx = multipage_delivery["docx"]
    pdf = multipage_delivery["pdf"]
    tampered = str(tmp_path / "tampered.docx")
    shutil.copyfile(src_docx, tampered)

    entries = pdf_probe.read_docx_toc(tampered)
    title, recorded = entries[0]
    wrong_page = 1 if recorded != 1 else 2

    old = (
        f"<w:r><w:t>{saxutils.escape(title)}</w:t></w:r>\n"
        "      <w:r><w:tab/></w:r>\n"
        f"      <w:r><w:t>{recorded}</w:t></w:r>"
    )
    new = old.replace(f"<w:t>{recorded}</w:t></w:r>", f"<w:t>{wrong_page}</w:t></w:r>")
    replacements = pdf_probe.rewrite_docx_replace(tampered, old, new)
    assert replacements == 1

    out_json = str(tmp_path / "tampered_readback.json")
    res = subprocess.run(
        [
            sys.executable, DELIVERY_READBACK_PY,
            "--docx", tampered, "--pdf", pdf,
            "--source", MULTIPAGE_TOC_DRAFT_MD, "--out", out_json,
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    assert res.returncode == 1, f"expected exit 1, got {res.returncode}: {res.stdout}"
    data = json.loads(res.stdout.strip())
    assert data["page_mismatch"] != []
    bad = [m for m in data["page_mismatch"] if m["title"] == title]
    assert bad and bad[0]["docx_page"] == wrong_page and bad[0]["pdf_page"] == recorded

    with open(out_json, "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert on_disk["page_mismatch"] != []
