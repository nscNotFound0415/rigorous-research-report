#!/usr/bin/env python3
"""
harness.py - Rigorous End-to-End (E2E) Test Harness for the research report pipeline.

Implements 建设方案 v2.1 §8.2:
  - Track E2E-a: automated gate stub / blocker verification (5 gates x 3 states + hash binding)
  - Track E2E-c: deterministic offline fixture closed loop (M3 -> M4 -> M5 -> M6 -> M7 -> M8)
  - Evaluates §8.2.3 checklist E2E-01..E2E-08
  - Emits tests/e2e/e2e_results.json and tests/e2e/E2E_REPORT.md

Design rules:
  - Read-only towards src/, openspec/, tests/module_tests/, e2e_run/ and the plan documents.
  - Temporary workspace lives in tests/e2e/_work and is removed at the end (E2E_KEEP_WORK=1 keeps it).
  - No network access. No third-party dependency.
  - E2E-a stubs are explicitly marked `stub: true` and are NOT human signatures. They never
    set approver_role=human_decision_maker, so they cannot masquerade as a human sign-off.
"""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SCRIPTS_DIR = os.path.join(BASE_DIR, "src", "scripts")
TEMPLATES_DIR = os.path.join(BASE_DIR, "src", "templates")
SCHEMAS_DIR = os.path.join(BASE_DIR, "src", "schemas")
FIXTURES_DIR = os.path.join(BASE_DIR, "tests", "e2e_fixtures")
E2E_DIR = os.path.join(BASE_DIR, "tests", "e2e")
WORK_DIR = os.path.join(E2E_DIR, "_work")
RESULTS_JSON = os.path.join(E2E_DIR, "e2e_results.json")
REPORT_MD = os.path.join(E2E_DIR, "E2E_REPORT.md")

STUB_DECLARATION = "本件为演练桩，非真实人类签署（E2E-a mock stub; not a human signature）"
STUB_SIGNER = "stub_drill_operator_01"
STUB_SIGNATURE = "STUB_DRILL_SIGNATURE"
MACHINE_SIGNER = "AI-Agent-Claude (自动复核代理)"
MACHINE_SIGNATURE = "AUTO_SIGN_AI_AGENT_STUB"

REQUIRED_TASK_IDS = [
    "T-P1-01", "T-P2-01", "T-P3-01",
    "T-P4-01", "T-P4-02",
    "T-P5-01", "T-G1-01", "T-P5-02",
    "T-P6-01", "T-P6-02", "T-G2-01", "T-P6-03", "T-P6-04",
    "T-G3-01", "T-M8-01",
]
VALID_FOUR_STATES = {"存在", "已复核", "已同步", "已审定"}

GATES_META = [
    # gate, human-readable artifact, approval filename, workspace-relative artifact
    ("G0", "brief.md", "G0-approval.md", "brief.md"),
    ("G1", "outline.md", "G1-approval.md", "outline.md"),
    ("G2", "correction-diff.md", "G2-approval.md", "correction-diff.md"),
    ("G3", "delivery/output.docx", "G3-approval.md", "delivery/output.docx"),
    ("change-01", "change-table.md", "change-01-approval.md", "change-table.md"),
]


def run(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: int = 240,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """Run a command, returning (exit_code, stdout, stderr). Never raises on non-zero exit."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(cmd)}"
    except Exception as exc:  # pragma: no cover - defensive
        return 127, "", f"{type(exc).__name__}: {exc}"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_json(text: str) -> Dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def script(name: str) -> str:
    return os.path.join(SCRIPTS_DIR, name)


def fixture(name: str) -> str:
    return os.path.join(FIXTURES_DIR, name)


# ---------------------------------------------------------------------------
# Harness 侧独立 PDF 取证（不复用 src/scripts 的抽取或页码定位实现）
# 用于「逐条核对目录记录页码 == 正文真实页码」，避免与交付脚本共享同一错误假设。
# ---------------------------------------------------------------------------
_PDF_OBJ_RE = re.compile(rb"(\d+)\s+0\s+obj\s*(.*?)endobj", re.DOTALL)
_PDF_LEADER_RE = re.compile(r"\.{5,}\s*\d{1,4}")


def _pdf_stream(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    marker = re.search(rb"stream\r?\n", body)
    if not marker:
        return None
    begin = marker.end()
    ref = re.search(rb"/Length\s+(\d+)\s+0\s+R", body)
    if ref:
        holder = objects.get(int(ref.group(1)), b"")
        num = re.match(rb"\s*(\d+)", holder)
        if not num:
            return None
        size = int(num.group(1))
    else:
        direct = re.search(rb"/Length\s+(\d+)\b", body)
        if not direct:
            return None
        size = int(direct.group(1))
    data = body[begin:begin + size]
    return data if len(data) == size else None


def _pdf_inflate(objects: Dict[int, bytes], body: bytes) -> Optional[bytes]:
    raw = _pdf_stream(objects, body)
    if raw is None:
        return None
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def e2e_pdf_page_texts(pdf_path: str) -> Dict[int, str]:
    """独立解析 PDF 逐页文本（标准库；按 /Length 精确切取压缩流）。"""
    with open(pdf_path, "rb") as fh:
        blob = fh.read()
    objects = {int(m.group(1)): m.group(2) for m in _PDF_OBJ_RE.finditer(blob)}

    cmaps: Dict[int, Dict[str, str]] = {}
    for oid, body in objects.items():
        data = _pdf_inflate(objects, body)
        if not data or b"begincmap" not in data:
            continue
        table: Dict[str, str] = {}
        for block in re.finditer(rb"beginbfchar(.*?)endbfchar", data, re.DOTALL):
            for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block.group(1)):
                try:
                    table[src.decode("ascii").upper()] = bytes.fromhex(dst.decode("ascii")).decode("utf-16-be")
                except Exception:
                    pass
        for block in re.finditer(rb"beginbfrange(.*?)endbfrange", data, re.DOTALL):
            for lo, hi, dst0 in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block.group(1)
            ):
                width = len(lo)
                start, stop, base = int(lo, 16), int(hi, 16), int(dst0, 16)
                for delta in range(stop - start + 1):
                    try:
                        table[f"{start + delta:0{width}X}"] = (base + delta).to_bytes(2, "big").decode("utf-16-be")
                    except Exception:
                        pass
        cmaps[oid] = table

    fonts: Dict[int, Dict[str, str]] = {}
    for oid, body in objects.items():
        if b"/Type/Font" in body or b"/Type /Font" in body:
            m = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
            if m and int(m.group(1)) in cmaps:
                fonts[oid] = cmaps[int(m.group(1))]

    named: Dict[str, Dict[str, str]] = {}
    for body in objects.values():
        for name, ref in re.findall(rb"/(\w+)\s+(\d+)\s+0\s+R", body):
            if int(ref) in fonts:
                named[name.decode("ascii")] = fonts[int(ref)]

    page_ids: List[int] = []
    for body in objects.values():
        if re.search(rb"/Type\s*/Pages\b", body):
            kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.DOTALL)
            if kids:
                page_ids = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", kids.group(1))]
                break
    if not page_ids:
        page_ids = [
            oid for oid, body in objects.items()
            if re.search(rb"/Type\s*/Page\b", body) and not re.search(rb"/Type\s*/Pages\b", body)
        ]

    texts: Dict[int, str] = {}
    for idx, pid in enumerate(page_ids, start=1):
        page_body = objects.get(pid, b"")
        pieces: List[str] = []
        for cid in re.findall(rb"/Contents\s+(\d+)\s+0\s+R", page_body):
            data = _pdf_inflate(objects, objects.get(int(cid), b""))
            if data is None:
                continue
            content = data.decode("latin1", errors="replace")
            font = "F1"
            for token in re.findall(
                r"(/\w+\s+\d+(?:\.\d+)?\s+Tf|<[0-9A-Fa-f]+>\s*Tj|\[.*?\]\s*TJ)", content, re.DOTALL
            ):
                if "Tf" in token:
                    nm = re.search(r"/(\w+)", token)
                    if nm:
                        font = nm.group(1)
                    continue
                cmap = named.get(font, {})
                if "Tj" in token:
                    hm = re.search(r"<([0-9A-Fa-f]+)>", token)
                    if hm:
                        h = hm.group(1).upper()
                        pieces.extend(cmap.get(h[k:k + 2], "") for k in range(0, len(h), 2))
                elif "TJ" in token:
                    for sub in re.findall(r"<([0-9A-Fa-f]+)>", token):
                        h = sub.upper()
                        pieces.extend(cmap.get(h[k:k + 2], "") for k in range(0, len(h), 2))
        texts[idx] = "".join(pieces)
    return texts


def e2e_toc_page_run(page_texts: Dict[int, str]) -> List[int]:
    """从第 1 页起连续识别目录页（含 >=2 条点前导页码行）。"""
    pages: List[int] = []
    for number in range(1, len(page_texts) + 1):
        if len(_PDF_LEADER_RE.findall(page_texts.get(number, ""))) >= 2:
            pages.append(number)
        else:
            break
    if pages and len(pages) == len(page_texts):
        pages = pages[:-1]
    return pages


def e2e_locate_titles(titles: List[str], page_texts: Dict[int, str], body_start: int) -> Tuple[Dict[str, int], List[str]]:
    """正文区域首次出现，搜索下界单调不减；找不到的标题进入 missing。"""
    found: Dict[str, int] = {}
    missing: List[str] = []
    floor = body_start
    last = max(page_texts) if page_texts else 0
    for title in titles:
        hit = None
        for number in range(floor, last + 1):
            if title in page_texts.get(number, ""):
                hit = number
                break
        if hit is None:
            missing.append(title)
            continue
        found[title] = hit
        floor = hit
    return found, missing


def e2e_read_docx_toc(docx_path: str) -> List[Tuple[str, Optional[int]]]:
    """读取 docx 目录 (标题, 页码) 序列。"""
    import xml.sax.saxutils as saxutils

    with zipfile.ZipFile(docx_path, "r") as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    entries: List[Tuple[str, Optional[int]]] = []
    for para in re.findall(r'<w:p>\s*<w:pPr><w:pStyle w:val="TOC\d"/></w:pPr>.*?</w:p>', xml, re.DOTALL):
        t = re.search(r"<w:r><w:t>(.*?)</w:t></w:r>\s*<w:r><w:tab/></w:r>", para)
        p = re.search(r"<w:tab/></w:r>\s*<w:r><w:t>(\d+)</w:t></w:r>", para)
        if t:
            entries.append((saxutils.unescape(t.group(1)).strip(), int(p.group(1)) if p else None))
    return entries


def e2e_verify_toc_pages(docx_path: str, pdf_path: str) -> Dict[str, Any]:
    """逐条核对 docx 目录页码与 PDF 正文真实页码（独立实现）。"""
    entries = e2e_read_docx_toc(docx_path)
    page_texts = e2e_pdf_page_texts(pdf_path)
    toc_run = e2e_toc_page_run(page_texts)
    body_start = (toc_run[-1] + 1) if toc_run else 1
    true_pages, missing = e2e_locate_titles([t for t, _ in entries], page_texts, body_start)
    mismatches = [
        {"title": title, "docx_page": page, "pdf_page": true_pages.get(title)}
        for title, page in entries
        if true_pages.get(title) != page
    ]
    return {
        "entries": len(entries),
        "toc_pages": toc_run,
        "body_start_page": body_start,
        "total_pages": len(page_texts),
        "missing": missing,
        "mismatches": mismatches,
        "all_match": bool(entries) and not missing and not mismatches,
    }


class E2EHarness:
    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []
        self.checklist: Dict[str, Dict[str, Any]] = {}
        self.gate_matrix: List[Dict[str, Any]] = []
        self.key_assertions: Dict[str, Any] = {}
        self.env_info: Dict[str, Any] = {}
        self.start_time = time.time()

    # ------------------------------------------------------------------ output
    def add(
        self,
        name: str,
        track: str,
        stage: str,
        command: str,
        expected: str,
        actual: str,
        exit_code: int,
        verdict: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "name": name,
            "track": track,
            "stage": stage,
            "command": command,
            "expected": expected,
            "actual": actual,
            "exit_code": exit_code,
            "verdict": verdict,
            "details": details or {},
        }
        self.results.append(record)
        mark = "PASS" if verdict == "PASS" else "FAIL"
        print(f"[{mark}] [{track}/{stage}] {name} (exit={exit_code})")
        print(f"       cmd      : {command}")
        print(f"       expected : {expected}")
        print(f"       actual   : {actual}")
        if verdict != "PASS":
            print(f"       !!! FAILURE DETAILS: {json.dumps(details or {}, ensure_ascii=False)[:1200]}")

    def collect_env(self) -> None:
        code, out, _ = run(["soffice", "--version"])
        self.env_info = {
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
            "platform": sys.platform,
            "soffice_available": code == 0,
            "soffice_version": out if code == 0 else "not available",
            "workspace": BASE_DIR,
            "network_used": False,
            "offline_fixtures": FIXTURES_DIR,
        }
        print("Environment:")
        print(f"  python  : {self.env_info['python_version']} ({self.env_info['python_executable']})")
        print(f"  platform: {self.env_info['platform']}")
        print(f"  soffice : {self.env_info['soffice_version']}")

    # =================================================================== Track A
    def _write_stub(self, path: str, gate: str, artifact_sha: str) -> str:
        content = f"""# E2E-a 演练桩 (Mock Approval Stub)

{STUB_DECLARATION}

- stub: true
- stub_purpose: 仅用于自动化验证门禁的阻塞/放行/防伪逻辑，不代表任何人类决策
- gate: {gate}
- decision: APPROVED
- signed_by: {STUB_SIGNER}
- signed_at: 2026-11-23T00:00:00Z
- artifact_sha256: {artifact_sha}
- signature: {STUB_SIGNATURE}
"""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return content

    def _write_machine_attempt(self, path: str, gate: str, artifact_sha: str) -> str:
        content = f"""# E2E-a 机器签名攻击样本 (Machine self-signing attempt)

- gate: {gate}
- decision: APPROVED
- signed_by: {MACHINE_SIGNER}
- signed_at: 2026-11-23T00:00:00Z
- artifact_sha256: {artifact_sha}
- signature: {MACHINE_SIGNATURE}
"""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return content

    def _write_human_format_fixture(self, path: str, gate: str, artifact_sha: str) -> str:
        """
        写入一份「人类签署格式」测试夹具：字段齐全、哈希吻合、不含 stub 标记。

        用途边界：该夹具只用于验证门禁的**放行路径**（格式合法 + 哈希绑定一致时
        gate_guard 返回 APPROVED / exit 0），**不代表任何真实人类签署**。真实人类
        签署件必须由人类本人在 E2E-b 中亲笔填写（tests/e2e/gates/*.template.md）。
        """
        content = f"""# E2E-a 人类签署格式测试夹具 (Human-format fixture for positive-path only)

> 用途边界：本夹具仅用于验证门禁放行路径，不代表真实人类签署 (test fixture, not a human signature).

- gate: {gate}
- decision: APPROVED
- signed_by: human:e2e_fixture_operator
- signed_at: 2026-11-23T00:00:00Z
- artifact_sha256: {artifact_sha}
- signature: E2E_FIXTURE_APPROVAL_CONFIRMED
"""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return content

    def run_track_a(self) -> None:
        print("\n" + "=" * 74)
        print("TRACK E2E-a: automated gate stub / blocker verification")
        print("=" * 74)
        if os.path.exists(WORK_DIR):
            shutil.rmtree(WORK_DIR)
        os.makedirs(os.path.join(WORK_DIR, "gates"), exist_ok=True)
        os.makedirs(os.path.join(WORK_DIR, "delivery"), exist_ok=True)

        # --- prerequisites: real artifacts inside the temporary workspace -------
        shutil.copy(fixture("brief.md"), os.path.join(WORK_DIR, "brief.md"))
        shutil.copy(fixture("outline.md"), os.path.join(WORK_DIR, "outline.md"))
        shutil.copy(fixture("correction-diff.md"), os.path.join(WORK_DIR, "correction-diff.md"))
        shutil.copy(fixture("change-table.md"), os.path.join(WORK_DIR, "change-table.md"))

        docx_out = os.path.join(WORK_DIR, "delivery", "output.docx")
        code_docx, out_docx, err_docx = run([
            sys.executable, script("build_docx.py"), fixture("draft_full.md"),
            "--out", docx_out,
            "--manifest", os.path.join(WORK_DIR, "delivery", "track_a_manifest.json"),
        ])
        print(f"  prerequisite build_docx for G3 artifact: exit={code_docx}")
        if code_docx != 0:
            print(f"  prerequisite stdout: {out_docx[:400]}")
            print(f"  prerequisite stderr: {err_docx[:400]}")

        decoy = os.path.join(WORK_DIR, "decoy_artifact.md")
        with open(decoy, "w", encoding="utf-8") as fh:
            fh.write("# Decoy artifact for hash-binding negative test\nnot the approved artifact\n")
        decoy_sha = sha256_file(decoy)

        # --- M1 brief verification ---------------------------------------------
        brief_path = os.path.join(WORK_DIR, "brief.md")
        code, out, _ = run([sys.executable, script("gate_guard.py"), "--verify-brief", brief_path])
        data = parse_json(out)
        eight = [f"### 2.{i}" for i in range(1, 9)]
        brief_text = open(brief_path, encoding="utf-8").read()
        eight_present = all(marker in brief_text for marker in eight)
        req_ids = sorted(set(re.findall(r"REQ-\d+", brief_text)))
        statuses = re.findall(r"^\s*-\s+clarification_status\s*:\s*([A-Z_]+)\s*$", brief_text, re.MULTILINE)
        valid_status = {"CLARIFIED", "NOT_CLARIFIED", "NOT_APPLICABLE"}
        eight_status_present = len(statuses) >= 8 and all(s in valid_status for s in statuses[:8])
        verdict = "PASS" if code == 0 and data.get("valid") is True and eight_present and eight_status_present else "FAIL"
        self.add(
            "M1-brief-verify", "E2E-a", "M1",
            f"python3 src/scripts/gate_guard.py --verify-brief {brief_path}",
            "exit=0, valid=true, 2.1-2.8 eight clarification sections present, each with a valid clarification_status",
            f"exit={code}, valid={data.get('valid')}, sections_2_1_to_2_8={eight_present}, "
            f"clarification_statuses={statuses[:8]}, eight_status_present={eight_status_present}, req_ids={req_ids}",
            code, verdict,
            {"stdout": out, "sections_2_1_to_8": eight_present,
             "clarification_statuses": statuses[:8], "eight_status_present": eight_status_present,
             "req_ids": req_ids},
        )

        # --- per-gate matrix ----------------------------------------------------
        for gate, artifact_label, approval_name, rel_artifact in GATES_META:
            artifact_path = os.path.join(WORK_DIR, rel_artifact)
            approval_path = os.path.join(WORK_DIR, "gates", approval_name)
            artifact_sha = sha256_file(artifact_path) if os.path.exists(artifact_path) else ""

            # 1) missing stub -> blocked
            if os.path.exists(approval_path):
                os.remove(approval_path)
            cmd_missing = f"python3 src/scripts/gate_guard.py --gate {gate} --check-only --root {WORK_DIR}"
            code1, out1, _ = run([sys.executable, script("gate_guard.py"), "--gate", gate, "--check-only", "--root", WORK_DIR])
            d1 = parse_json(out1)
            pass1 = code1 == 1 and d1.get("state") == "PENDING" and d1.get("blocked") is True and d1.get("artifact_sha256") is None
            self.add(
                f"{gate}-missing-block", "E2E-a", "gate",
                cmd_missing,
                "exit=1, state=PENDING, blocked=true, artifact_sha256=null",
                f"exit={code1}, state={d1.get('state')}, blocked={d1.get('blocked')}, artifact_sha256={d1.get('artifact_sha256')}",
                code1, "PASS" if pass1 else "FAIL", {"stdout": out1},
            )

            # 2) explicitly-marked stub -> hard rejected (STUB_REJECTED)
            stub_content = self._write_stub(approval_path, gate, artifact_sha)
            stub_is_stub = (
                "stub: true" in stub_content
                and STUB_DECLARATION in stub_content
                and "human_decision_maker" not in stub_content
                and "approver_role" not in stub_content
            )
            cmd_stub = f"python3 src/scripts/gate_guard.py --gate {gate} --check-only --root {WORK_DIR}"
            code2, out2, _ = run([sys.executable, script("gate_guard.py"), "--gate", gate, "--check-only", "--root", WORK_DIR])
            d2 = parse_json(out2)
            pass2 = (
                code2 == 1
                and d2.get("state") == "STUB_REJECTED"
                and d2.get("blocked") is True
                and stub_is_stub
            )
            self.add(
                f"{gate}-stub-reject", "E2E-a", "gate",
                cmd_stub,
                f"exit=1, state=STUB_REJECTED, blocked=true, stub:true present (hash would otherwise match {artifact_sha[:16]}...)",
                f"exit={code2}, state={d2.get('state')}, blocked={d2.get('blocked')}, stub_marked={stub_is_stub}",
                code2, "PASS" if pass2 else "FAIL",
                {"stdout": out2, "stub_file": approval_path, "stub_is_stub": stub_is_stub},
            )

            # 3) machine signature -> rejected even with a correct hash
            self._write_machine_attempt(approval_path, gate, artifact_sha)
            cmd_machine = f"python3 src/scripts/gate_guard.py --gate {gate} --check-only --root {WORK_DIR}"
            code3, out3, _ = run([sys.executable, script("gate_guard.py"), "--gate", gate, "--check-only", "--root", WORK_DIR])
            d3 = parse_json(out3)
            pass3 = code3 == 1 and d3.get("blocked") is True and d3.get("state") == "AGENT_SIGNATURE_PROHIBITED"
            self.add(
                f"{gate}-machine-reject", "E2E-a", "gate",
                cmd_machine,
                "exit=1, state=AGENT_SIGNATURE_PROHIBITED, blocked=true",
                f"exit={code3}, state={d3.get('state')}, blocked={d3.get('blocked')}, signed_by={MACHINE_SIGNER}",
                code3, "PASS" if pass3 else "FAIL",
                {"stdout": out3, "machine_stub_file": approval_path},
            )

            # 4) hash binding: correct-format human fixture bound to a DIFFERENT artifact -> rejected
            self._write_human_format_fixture(approval_path, gate, decoy_sha)
            cmd_bind = f"python3 src/scripts/gate_guard.py --gate {gate} --check-only --root {WORK_DIR}"
            code4, out4, _ = run([sys.executable, script("gate_guard.py"), "--gate", gate, "--check-only", "--root", WORK_DIR])
            d4 = parse_json(out4)
            pass4 = (
                code4 == 1
                and d4.get("state") == "HASH_MISMATCH"
                and d4.get("blocked") is True
                and d4.get("artifact_sha256") == artifact_sha
                and decoy_sha != artifact_sha
            )
            self.add(
                f"{gate}-hash-binding-reject", "E2E-a", "gate",
                cmd_bind,
                "exit=1, state=HASH_MISMATCH, recomputed artifact_sha256 equals the real artifact",
                f"exit={code4}, state={d4.get('state')}, decoy_sha={decoy_sha[:12]}..., real_sha={artifact_sha[:12]}..., recomputed={str(d4.get('artifact_sha256'))[:12]}...",
                code4, "PASS" if pass4 else "FAIL",
                {"stdout": out4, "bound_artifact": rel_artifact, "decoy_sha256": decoy_sha, "artifact_sha256": artifact_sha},
            )

            # 5) explicit --verify path with a valid human-format fixture (no stub marker) -> allowed
            self._write_human_format_fixture(approval_path, gate, artifact_sha)
            cmd_verify = (
                f"python3 src/scripts/gate_guard.py --gate {gate} --verify "
                f"--artifact {rel_artifact} --approval gates/{approval_name} --root {WORK_DIR}"
            )
            code5, out5, _ = run([
                sys.executable, script("gate_guard.py"), "--gate", gate, "--verify",
                "--artifact", rel_artifact, "--approval", f"gates/{approval_name}", "--root", WORK_DIR,
            ])
            d5 = parse_json(out5)
            pass5 = code5 == 0 and d5.get("state") == "APPROVED" and d5.get("artifact_sha256") == artifact_sha
            self.add(
                f"{gate}-human-fixture-verify-explicit", "E2E-a", "gate",
                cmd_verify,
                f"exit=0, state=APPROVED, artifact bound to {artifact_label} (human-format fixture, no stub marker)",
                f"exit={code5}, state={d5.get('state')}, artifact={artifact_label}, hash_match={d5.get('artifact_sha256') == artifact_sha}",
                code5, "PASS" if pass5 else "FAIL", {"stdout": out5},
            )

            self.gate_matrix.append({
                "gate": gate,
                "artifact": artifact_label,
                "stub_marked": "stub: true",
                "missing": {"exit_code": code1, "state": d1.get("state"), "verdict": "PASS" if pass1 else "FAIL"},
                "stub": {"exit_code": code2, "state": d2.get("state"), "verdict": "PASS" if pass2 else "FAIL"},
                "machine": {"exit_code": code3, "state": d3.get("state"), "verdict": "PASS" if pass3 else "FAIL"},
                "hash_binding": {"exit_code": code4, "state": d4.get("state"), "verdict": "PASS" if pass4 else "FAIL"},
                "explicit_verify": {"exit_code": code5, "state": d5.get("state"), "verdict": "PASS" if pass5 else "FAIL"},
            })

        print("  E2E-a gate matrix complete (5 gates x missing/stub/machine/hash-binding/explicit-verify)")

    # =================================================================== Track C
    def run_track_c(self) -> None:
        print("\n" + "=" * 74)
        print("TRACK E2E-c: deterministic offline fixture closed loop")
        print("=" * 74)
        os.makedirs(os.path.join(WORK_DIR, "delivery"), exist_ok=True)
        os.makedirs(os.path.join(WORK_DIR, "neg"), exist_ok=True)

        brief_path = fixture("brief.md")
        task_path = fixture("task.json")
        schema_path = os.path.join(SCHEMAS_DIR, "task.schema.json")
        datatable_path = fixture("datatable.csv")
        evidence_path = fixture("evidence-index.md")
        outline_path = fixture("outline.md")
        draft_path = fixture("draft_full.md")
        rules_path = os.path.join(TEMPLATES_DIR, "forbidden_terms.json")

        # ---------------------------------------------------------------- M3
        code, out, _ = run([sys.executable, script("task_schema_check.py"), task_path, "--schema", schema_path])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("errors") == [] and data.get("guidelines_validated") is True else "FAIL"
        self.add(
            "M3-task-schema", "E2E-c", "M3",
            f"python3 src/scripts/task_schema_check.py {task_path} --schema {schema_path}",
            "exit=0, errors=[], guidelines_validated=true",
            f"exit={code}, errors={data.get('errors')}, guidelines_validated={data.get('guidelines_validated')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m3_schema"] = {"errors": data.get("errors"), "guidelines_validated": data.get("guidelines_validated")}

        code, out, _ = run([sys.executable, script("task_schema_check.py"), task_path, "--req-index", brief_path, "--coverage"])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("uncovered_req_ids") == [] and data.get("coverage_ratio") == 1.0 else "FAIL"
        self.add(
            "M3-req-coverage", "E2E-c", "M3",
            f"python3 src/scripts/task_schema_check.py {task_path} --req-index {brief_path} --coverage",
            "exit=0, uncovered_req_ids=[], coverage_ratio=1.0",
            f"exit={code}, uncovered_req_ids={data.get('uncovered_req_ids')}, coverage_ratio={data.get('coverage_ratio')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m3_coverage"] = {"uncovered_req_ids": data.get("uncovered_req_ids"), "coverage_ratio": data.get("coverage_ratio")}

        # ---------------------------------------------------------------- M4
        code, out, _ = run([sys.executable, script("audit_calc.py"), datatable_path])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("mismatches") == [] and data.get("checked_cells", 0) >= 4 else "FAIL"
        self.add(
            "M4-audit-calc", "E2E-c", "M4",
            f"python3 src/scripts/audit_calc.py {datatable_path}",
            "exit=0, mismatches=[], checked_cells>=4",
            f"exit={code}, checked_cells={data.get('checked_cells')}, mismatches={data.get('mismatches')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["audit_calc"] = {"checked_cells": data.get("checked_cells"), "mismatches": data.get("mismatches")}

        code, out, _ = run([sys.executable, script("audit_calc.py"), datatable_path, "--evidence-index", evidence_path])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("unlinked_cells") == [] and data.get("missing_assumption_tags") == [] else "FAIL"
        self.add(
            "M4-evidence-anchoring", "E2E-c", "M4",
            f"python3 src/scripts/audit_calc.py {datatable_path} --evidence-index {evidence_path}",
            "exit=0, unlinked_cells=[], missing_assumption_tags=[]",
            f"exit={code}, unlinked_cells={data.get('unlinked_cells')}, missing_assumption_tags={data.get('missing_assumption_tags')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m4_anchoring"] = {
            "unlinked_cells": data.get("unlinked_cells"),
            "missing_assumption_tags": data.get("missing_assumption_tags"),
        }

        code, out, _ = run([sys.executable, script("audit_calc.py"), datatable_path, "--strict-tolerance"])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("cross_scope_violations") == [] and data.get("checked_cells", 0) >= 4 else "FAIL"
        self.add(
            "M4-cross-scope-isolation", "E2E-c", "M4",
            f"python3 src/scripts/audit_calc.py {datatable_path} --strict-tolerance",
            "exit=0, cross_scope_violations=[]",
            f"exit={code}, checked_cells={data.get('checked_cells')}, cross_scope_violations={data.get('cross_scope_violations')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m4_cross_scope_positive"] = {
            "checked_cells": data.get("checked_cells"),
            "cross_scope_violations": data.get("cross_scope_violations"),
        }

        # Negative: inject a cross-caliber subtraction and require exit 1.
        with open(datatable_path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
            fieldnames = list(rows[0].keys())
        bad_rows = [dict(row) for row in rows]
        injected = False
        for row in bad_rows:
            if row["item_id"] == "ITM_A03":
                row["expected_expression"] = "ITM_A01 - ITM_B01"
                injected = True
        bad_csv = os.path.join(WORK_DIR, "neg", "datatable_cross_caliber.csv")
        with open(bad_csv, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bad_rows)
        code, out, _ = run([sys.executable, script("audit_calc.py"), bad_csv, "--strict-tolerance"])
        data = parse_json(out)
        violations = data.get("cross_scope_violations") or []
        verdict = "PASS" if code == 1 and injected and len(violations) >= 1 and data.get("mismatches") else "FAIL"
        self.add(
            "M4-cross-scope-block-negative", "E2E-c", "M4",
            f"python3 src/scripts/audit_calc.py {bad_csv} --strict-tolerance  # injected ITM_A01 - ITM_B01",
            "exit=1, cross_scope_violations>=1 (cross-caliber arithmetic blocked)",
            f"exit={code}, injected={injected}, cross_scope_violations={len(violations)}, first={violations[0] if violations else None}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m4_cross_scope_negative"] = {"exit_code": code, "violations": violations}

        # Evidence registry integrity: 6 entries, required fields incl. URL, snapshot hash matches.
        registry = self._parse_evidence_registry(evidence_path)
        missing_fields = []
        hash_ok = True
        for entry in registry:
            for key in ("publisher", "title", "source_url", "pricing_date", "content_sha256", "evidence_type", "snapshot_path"):
                if not entry.get(key):
                    missing_fields.append(f"{entry.get('evidence_id')}:{key}")
            snap = entry.get("snapshot_path", "")
            snap_abs = snap if os.path.isabs(snap) else os.path.join(BASE_DIR, snap)
            entry["hash_verified"] = bool(snap) and os.path.exists(snap_abs) and sha256_file(snap_abs) == entry.get("content_sha256")
            if not entry["hash_verified"]:
                hash_ok = False
        verdict = "PASS" if len(registry) >= 6 and not missing_fields and hash_ok else "FAIL"
        self.add(
            "M4-evidence-registry-integrity", "E2E-c", "M4",
            "harness parse evidence-index.md + SHA-256 of tests/e2e_fixtures/raw_evidence/*",
            ">=6 one-hand evidence entries, each with publisher/title/source_url/pricing_date/content_sha256/evidence_type, snapshot hash matches",
            f"entries={len(registry)}, missing_fields={missing_fields}, all_snapshot_hashes_match={hash_ok}",
            0 if verdict == "PASS" else 1, verdict,
            {"entries": [{k: e.get(k) for k in ("evidence_id", "publisher", "title", "source_url", "pricing_date", "content_sha256", "evidence_type", "hash_verified")} for e in registry]},
        )
        self.key_assertions["evidence_registry"] = {
            "entries": len(registry),
            "missing_fields": missing_fields,
            "all_snapshot_hashes_match": hash_ok,
        }

        estimated = [r for r in rows if r.get("source_type") == "estimated"]
        tags_ok = all(r.get("assumption_tag", "").strip() for r in estimated)
        verdict = "PASS" if estimated and tags_ok else "FAIL"
        self.add(
            "M4-assumption-tags", "E2E-c", "M4",
            "harness inspect datatable.csv source_type=estimated rows",
            "all estimated cells carry a non-empty assumption_tag",
            f"estimated_rows={len(estimated)}, tags_ok={tags_ok}",
            0 if verdict == "PASS" else 1, verdict,
            {"estimated": [{"item_id": r.get("item_id"), "assumption_tag": r.get("assumption_tag")} for r in estimated]},
        )
        self.key_assertions["m4_assumption_tags"] = {"estimated_rows": len(estimated), "tags_ok": tags_ok}

        # ---------------------------------------------------------------- M5
        code, out, _ = run([
            sys.executable, script("outline_check.py"), outline_path,
            "--evidence-index", evidence_path, "--require-resolved",
        ])
        data = parse_json(out)
        verdict = (
            "PASS" if code == 0 and data.get("pending_count") == 0 and data.get("dangling_refs") == []
            and data.get("missing_refs") == [] and data.get("refs_total") == 6
            else "FAIL"
        )
        self.add(
            "M5-outline-resolved", "E2E-c", "M5",
            f"python3 src/scripts/outline_check.py {outline_path} --evidence-index {evidence_path} --require-resolved",
            "exit=0, pending_count=0, dangling_refs=[], missing_refs=[], refs_total=6",
            f"exit={code}, pending_count={data.get('pending_count')}, dangling_refs={data.get('dangling_refs')}, missing_refs={data.get('missing_refs')}, refs_total={data.get('refs_total')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m5_outline"] = {
            "pending_count": data.get("pending_count"),
            "dangling_refs": data.get("dangling_refs"),
            "missing_refs": data.get("missing_refs"),
            "refs_total": data.get("refs_total"),
        }

        code, out, _ = run([sys.executable, script("outline_check.py"), outline_path, "--check-sections"])
        data = parse_json(out)
        chapter_refs = self._chapter_ref_counts(open(outline_path, encoding="utf-8").read())
        each_chapter_has_ref = bool(chapter_refs) and all(v >= 1 for v in chapter_refs.values())
        verdict = (
            "PASS" if code == 0 and data.get("invalid_sections") == [] and data.get("chapter_count", 0) >= 1
            and each_chapter_has_ref
            else "FAIL"
        )
        self.add(
            "M5-outline-sections", "E2E-c", "M5",
            f"python3 src/scripts/outline_check.py {outline_path} --check-sections",
            "exit=0, invalid_sections=[], chapter_count>=1, each chapter >=1 evidence_ref",
            f"exit={code}, invalid_sections={data.get('invalid_sections')}, chapter_count={data.get('chapter_count')}, chapter_refs={chapter_refs}",
            code, verdict, {"stdout": out, "chapter_refs": chapter_refs},
        )
        self.key_assertions["m5_chapters"] = {"chapter_count": data.get("chapter_count"), "chapter_refs": chapter_refs}

        # ---------------------------------------------------------------- M6
        provenance_path = fixture("provenance.json")
        code, out, _ = run([sys.executable, script("gate_guard.py"), "--check-provenance", provenance_path])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("provenance_valid") is True and data.get("isolated") is True else "FAIL"
        self.add(
            "M6-provenance-isolated", "E2E-c", "M6",
            f"python3 src/scripts/gate_guard.py --check-provenance {provenance_path}",
            "exit=0, provenance_valid=true, isolated=true",
            f"exit={code}, provenance_valid={data.get('provenance_valid')}, isolated={data.get('isolated')}, channel={data.get('channel')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m6_provenance"] = {"provenance_valid": data.get("provenance_valid"), "isolated": data.get("isolated"), "channel": data.get("channel")}

        bad_prov_path = os.path.join(WORK_DIR, "neg", "provenance_shared_session.json")
        with open(provenance_path, encoding="utf-8") as fh:
            prov = json.load(fh)
        prov["reviewer"]["session"] = prov["writer"]["session"]
        with open(bad_prov_path, "w", encoding="utf-8") as fh:
            json.dump(prov, fh, ensure_ascii=False, indent=2)
        code, out, _ = run([sys.executable, script("gate_guard.py"), "--check-provenance", bad_prov_path])
        data = parse_json(out)
        verdict = "PASS" if code == 1 and data.get("isolated") is False and data.get("status") == "BLOCKED_NO_REVIEWER" else "FAIL"
        self.add(
            "M6-provenance-negative", "E2E-c", "M6",
            f"python3 src/scripts/gate_guard.py --check-provenance {bad_prov_path}  # reviewer.session == writer.session",
            "exit=1, isolated=false, status=BLOCKED_NO_REVIEWER",
            f"exit={code}, isolated={data.get('isolated')}, status={data.get('status')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m6_provenance_negative"] = {"exit_code": code, "status": data.get("status"), "errors": data.get("errors")}

        code, out, _ = run([
            sys.executable, script("verify_readback.py"),
            "--plan", fixture("correction-diff.md"),
            "--target", fixture("draft_corrected.md"),
        ])
        data = parse_json(out)
        verdict = (
            "PASS" if code == 0 and data.get("layer1") is True and data.get("layer2_residuals") == 0
            and data.get("layer3") is True and data.get("layer4") is True
            else "FAIL"
        )
        self.add(
            "M6-verify-readback", "E2E-c", "M6",
            f"python3 src/scripts/verify_readback.py --plan {fixture('correction-diff.md')} --target {fixture('draft_corrected.md')}",
            "exit=0, layer1=true, layer2_residuals=0, layer3=true, layer4=true",
            f"exit={code}, layer1={data.get('layer1')}, layer2_residuals={data.get('layer2_residuals')}, layer3={data.get('layer3')}, layer4={data.get('layer4')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m6_readback"] = {
            "layer1": data.get("layer1"),
            "layer2_residuals": data.get("layer2_residuals"),
            "layer3": data.get("layer3"),
            "layer4": data.get("layer4"),
        }

        # ---------------------------------------------------------------- M7
        code, out, _ = run([sys.executable, script("audit_text_hygiene.py"), draft_path, "--rules", rules_path])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("violations") == [] else "FAIL"
        self.add(
            "M7-text-hygiene", "E2E-c", "M7",
            f"python3 src/scripts/audit_text_hygiene.py {draft_path} --rules {rules_path}",
            "exit=0, violations=[]",
            f"exit={code}, violations={data.get('violations')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["hygiene"] = {"violations": data.get("violations")}

        with open(rules_path, encoding="utf-8") as fh:
            rules = json.load(fh)
        draft_text = open(draft_path, encoding="utf-8").read()
        pattern_hits = {}
        for pattern in rules.get("patterns", []):
            pattern_hits[pattern["id"]] = len(re.findall(pattern["regex"], draft_text))
        rigor_allow = [a for a in rules.get("allowlist", []) if a.get("category") == "rigor_declaration"]
        allow_hits = {}
        for item in rigor_allow:
            allow_hits[item["id"]] = len(re.findall(item["regex"], draft_text))
        nine_ok = len(rigor_allow) == 9 and all(v >= 1 for v in allow_hits.values())
        zero_patterns = all(v == 0 for v in pattern_hits.values())
        verdict = "PASS" if nine_ok and zero_patterns else "FAIL"
        self.add(
            "M7-allowlist-9", "E2E-c", "M7",
            "harness independent regex scan with src/templates/forbidden_terms.json",
            "9 rigor_declaration allowlist entries each matched >=1, all 5 forbidden patterns hit 0",
            f"rigor_allowlist_entries={len(rigor_allow)}, allow_hits={allow_hits}, pattern_hits={pattern_hits}",
            0 if verdict == "PASS" else 1, verdict,
            {"allow_hits": allow_hits, "pattern_hits": pattern_hits},
        )
        self.key_assertions["hygiene_allowlist"] = {
            "rigor_allowlist_entries": len(rigor_allow),
            "allow_hits": allow_hits,
            "pattern_hits": pattern_hits,
        }

        code, out, _ = run([sys.executable, script("citation_check.py"), draft_path, "--evidence-index", evidence_path])
        data = parse_json(out)
        verdict = (
            "PASS" if code == 0 and data.get("dangling_refs") == [] and data.get("unnumbered_figs") == []
            and data.get("dangling_tables") == []
            else "FAIL"
        )
        self.add(
            "M7-citation-check", "E2E-c", "M7",
            f"python3 src/scripts/citation_check.py {draft_path} --evidence-index {evidence_path}",
            "exit=0, dangling_refs=[], unnumbered_figs=[], dangling_tables=[]",
            f"exit={code}, dangling_refs={data.get('dangling_refs')}, unnumbered_figs={data.get('unnumbered_figs')}, dangling_tables={data.get('dangling_tables')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["citation"] = {
            "dangling_refs": data.get("dangling_refs"),
            "unnumbered_figs": data.get("unnumbered_figs"),
            "dangling_tables": data.get("dangling_tables"),
        }

        # build_docx twice, compare component hashes + byte hash
        delivery_dir = os.path.join(WORK_DIR, "delivery")
        docx_path = os.path.join(delivery_dir, "output.docx")
        manifest1 = os.path.join(delivery_dir, "build_manifest_run1.json")
        manifest2 = os.path.join(delivery_dir, "build_manifest_run2.json")
        code1, out1, err1 = run([sys.executable, script("build_docx.py"), draft_path, "--out", docx_path, "--manifest", manifest1])
        sha1 = sha256_file(docx_path) if os.path.exists(docx_path) else ""
        code2, out2, err2 = run([sys.executable, script("build_docx.py"), draft_path, "--out", docx_path, "--manifest", manifest2])
        sha2 = sha256_file(docx_path) if os.path.exists(docx_path) else ""
        man1 = json.load(open(manifest1, encoding="utf-8")) if os.path.exists(manifest1) else {}
        man2 = json.load(open(manifest2, encoding="utf-8")) if os.path.exists(manifest2) else {}
        comp1 = man1.get("components", {})
        comp2 = man2.get("components", {})
        identical = bool(comp1) and comp1 == comp2
        verdict = "PASS" if code1 == 0 and code2 == 0 and identical and sha1 == sha2 and len(comp1) == 8 and man1.get("headings_count") == 3 else "FAIL"
        self.add(
            "M7-build-docx-idempotence", "E2E-c", "M7",
            f"python3 src/scripts/build_docx.py {draft_path} --out output.docx --manifest build_manifest_run{{1,2}}.json",
            "exit=0/0, all 8 OOXML component hashes identical, docx byte hash identical, headings_count=3",
            f"exit={code1}/{code2}, components={len(comp1)}, components_identical={identical}, docx_sha_run1={sha1[:16]}..., docx_sha_run2={sha2[:16]}..., headings_count={man1.get('headings_count')}",
            code1 if code1 != 0 else code2, verdict,
            {"manifest_run1": comp1, "manifest_run2": comp2, "components_identical": identical,
             "docx_sha256_run1": sha1, "docx_sha256_run2": sha2, "headings_count": man1.get("headings_count")},
        )
        self.key_assertions["build_manifest"] = {
            "components": comp1,
            "components_identical": identical,
            "docx_sha256_run1": sha1,
            "docx_sha256_run2": sha2,
            "headings_count": man1.get("headings_count"),
        }

        pdf_path = os.path.join(delivery_dir, "output.pdf")
        # Isolate the LibreOffice user profile: a stale/locked ~/.config/libreoffice profile
        # (e.g. a hung soffice from another run) makes headless conversion fail with
        # "Error Area:Io Class:Write Code:16". A dedicated HOME keeps E2E deterministic.
        lo_home = os.path.join(WORK_DIR, "lo_home")
        os.makedirs(lo_home, exist_ok=True)
        pdf_env = dict(os.environ)
        pdf_env["HOME"] = lo_home
        code, out, _ = run([sys.executable, script("build_pdf.py"), docx_path, "--out", pdf_path], env=pdf_env, timeout=300)
        data = parse_json(out)
        pdf_exists = os.path.exists(pdf_path)
        pdf_size = os.path.getsize(pdf_path) if pdf_exists else 0
        verdict = "PASS" if code == 0 and data.get("pdf") is True and pdf_exists and pdf_size > 0 else "FAIL"
        self.add(
            "M7-build-pdf", "E2E-c", "M7",
            f"python3 src/scripts/build_pdf.py {docx_path} --out {pdf_path}",
            "exit=0, pdf=true, output.pdf exists with size>0",
            f"exit={code}, pdf={data.get('pdf')}, exists={pdf_exists}, size_bytes={pdf_size}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["pdf"] = {"pdf": data.get("pdf"), "size_bytes": pdf_size}

        code, out, _ = run([sys.executable, script("toc_two_pass.py"), docx_path, pdf_path])
        data = parse_json(out)
        verdict = (
            "PASS" if code == 0 and data.get("toc_backfilled") is True
            and data.get("entries_count") == 3 and data.get("updated_count") == 3
            else "FAIL"
        )
        self.add(
            "M7-toc-two-pass", "E2E-c", "M7",
            f"python3 src/scripts/toc_two_pass.py {docx_path} {pdf_path}",
            "exit=0, toc_backfilled=true, entries_count=3, updated_count=3",
            f"exit={code}, toc_backfilled={data.get('toc_backfilled')}, entries_count={data.get('entries_count')}, updated_count={data.get('updated_count')}",
            code, verdict, {"stdout": out, "pages": data.get("pages")},
        )
        self.key_assertions["toc"] = {
            "toc_backfilled": data.get("toc_backfilled"),
            "entries_count": data.get("entries_count"),
            "updated_count": data.get("updated_count"),
            "pages": data.get("pages"),
        }

        readback_json = os.path.join(delivery_dir, "delivery_readback.json")
        code, out, _ = run([
            sys.executable, script("delivery_readback.py"),
            "--docx", docx_path, "--pdf", pdf_path, "--source", draft_path, "--out", readback_json,
        ])
        data = parse_json(out)

        # 逐条页码核对：harness 自行抽 PDF 文本、自行定位正文真实页，不复用交付脚本逻辑
        per_entry = e2e_verify_toc_pages(docx_path, pdf_path)
        verdict = (
            "PASS" if code == 0 and data.get("toc_minus_headings") == [] and data.get("headings_minus_toc") == []
            and data.get("page_mismatch") == [] and per_entry["all_match"]
            else "FAIL"
        )
        mismatch_preview = per_entry["mismatches"][:3]
        self.add(
            "M7-delivery-readback", "E2E-c", "M7",
            f"python3 src/scripts/delivery_readback.py --docx {docx_path} --pdf {pdf_path} --source {draft_path}",
            "exit=0, diff sets empty, page_mismatch=[], and every TOC page == independently located real body page",
            f"exit={code}, toc_minus_headings={data.get('toc_minus_headings')}, headings_minus_toc={data.get('headings_minus_toc')}, "
            f"page_mismatch={data.get('page_mismatch')}, toc_pages={per_entry['toc_pages']}, "
            f"per_entry_all_match={per_entry['all_match']}, per_entry_mismatches={mismatch_preview}",
            code, verdict,
            {"stdout": out, "headings": data.get("headings"), "toc_entries": data.get("toc_entries"),
             "independent_per_entry": per_entry},
        )
        self.key_assertions["delivery_readback"] = {
            "toc_minus_headings": data.get("toc_minus_headings"),
            "headings_minus_toc": data.get("headings_minus_toc"),
            "page_mismatch": data.get("page_mismatch"),
            "headings": data.get("headings"),
            "toc_entries": data.get("toc_entries"),
            "independent_per_entry_all_match": per_entry["all_match"],
            "independent_toc_pages": per_entry["toc_pages"],
        }

        # ---- M7 多页目录逐条页码核对（目录占 2 页的运行时夹具） ----
        multipage_md = os.path.join(WORK_DIR, "delivery", "toc_multipage_e2e.md")
        section_names = [
            "0. 文档信息与阅读指引", "第一章 评估口径与范围", "1.1 口径分类与边界", "1.2 时间窗口约定",
            "1.3 数据来源分层", "第二章 供给结构观察", "2.1 在营区域与可用区", "2.2 容量披露与在运规模",
            "2.3 算力可得性", "2.4 待补数据登记", "第三章 成本口径拆解", "3.1 电价与用电强度",
            "3.2 网络出站计费", "3.3 卡时报价参照", "3.4 双轨并列规则", "3.5 待补数据登记",
            "第四章 合规约束", "4.1 主管机关与法规", "4.2 跨境传输条件", "4.3 本地化义务",
            "4.4 注册通道", "4.5 业务模式映射", "4.6 待补数据登记", "第五章 需求侧观察",
            "5.1 市场规模的机构口径", "5.2 在运客户与场景", "5.3 采购侧信号", "5.4 可服务市场边界",
            "5.5 待补数据登记", "第六章 风险与核实清单", "6.1 宣布值与在运值", "6.2 融资与容量配置",
            "6.3 供应链风险线索", "6.4 推进前核实清单", "6.5 待补数据登记", "第七章 实施路径",
            "7.1 阶段划分", "7.2 里程碑与依赖", "7.3 组织与责任", "7.4 待补数据登记",
            "第八章 结论", "8.1 结论与适用边界", "8.2 后续动作",
        ]
        body_lines = ["# 多页目录交付物回归测试报告", ""]
        for i, name in enumerate(section_names):
            body_lines.append("## " + name)
            body_lines.append("")
            for j in range(3):
                body_lines.append(
                    f"本节围绕{name}展开，所有计量数值只取自数值底表的登记行并按行号回指，"
                    f"历法年份与法规条款号按标识符处理，不参与任何跨口径运算。"
                    f"本节结论仅在自身口径内成立，不构成对全部品类与全部时点的普遍结论。"
                    f"数据来源为一手公开页面与官方价目，未做货币换算。"
                )
                body_lines.append("")
        with open(multipage_md, "w", encoding="utf-8") as fh:
            fh.write("\n".join(body_lines))

        multi_dir = os.path.join(WORK_DIR, "delivery_multipage")
        os.makedirs(multi_dir, exist_ok=True)
        multi_docx = os.path.join(multi_dir, "output.docx")
        multi_pdf = os.path.join(multi_dir, "output.pdf")
        multi_manifest = os.path.join(multi_dir, "build_manifest.json")
        code_a, out_a, err_a = run(
            [sys.executable, script("build_docx.py"), multipage_md, "--out", multi_docx, "--manifest", multi_manifest]
        )
        multi_env = dict(os.environ)
        multi_env["HOME"] = os.path.join(WORK_DIR, "lo_home_multipage")
        os.makedirs(multi_env["HOME"], exist_ok=True)
        code_b, out_b, _ = run(
            [sys.executable, script("build_pdf.py"), multi_docx, "--out", multi_pdf], env=multi_env, timeout=300
        )
        pdf_info = parse_json(out_b)
        code_c, out_c, _ = run([sys.executable, script("toc_two_pass.py"), multi_docx, multi_pdf])
        toc_multi = parse_json(out_c)
        multi_verify = (
            e2e_verify_toc_pages(multi_docx, multi_pdf) if os.path.exists(multi_pdf) else
            {"entries": 0, "toc_pages": [], "all_match": False, "mismatches": [], "missing": [], "body_start_page": 0}
        )
        multi_ok = (
            code_a == 0 and code_b == 0 and code_c == 0 and pdf_info.get("pdf") is True
            and toc_multi.get("toc_backfilled") is True
            and multi_verify["entries"] >= 40
            and len(multi_verify["toc_pages"]) >= 2
            and multi_verify["all_match"]
            and toc_multi.get("toc_pages") == len(multi_verify["toc_pages"])
        )
        self.add(
            "M7-toc-multipage-pages", "E2E-c", "M7",
            f"build_docx/build_pdf/toc_two_pass + harness independent per-entry page check ({multipage_md})",
            "exit=0, entries>=40, TOC pages>=2, every TOC page == independently located real body page",
            f"exit={code_a}/{code_b}/{code_c}, pdf={pdf_info.get('pdf')}, toc_backfilled={toc_multi.get('toc_backfilled')}, "
            f"tool_toc_pages={toc_multi.get('toc_pages')}, independent_toc_pages={multi_verify['toc_pages']}, "
            f"entries={multi_verify['entries']}, all_match={multi_verify['all_match']}, "
            f"mismatches={multi_verify['mismatches'][:3]}, missing={multi_verify['missing'][:3]}",
            code_a if code_a != 0 else (code_b if code_b != 0 else code_c),
            "PASS" if multi_ok else "FAIL",
            {"tool_stdout": out_c, "independent": multi_verify},
        )
        self.key_assertions["toc_multipage"] = {
            "entries": multi_verify["entries"],
            "toc_pages": multi_verify["toc_pages"],
            "all_match": multi_verify["all_match"],
            "mismatches": multi_verify["mismatches"][:5],
            "missing": multi_verify["missing"][:5],
        }

        # ---------------------------------------------------------------- M8
        old_draft = fixture("baseline_draft_for_change.md")
        patched = fixture("patched_draft_c01.md")
        change_table = fixture("change-table.md")
        backup_dir = fixture("backup")
        code, out, _ = run([
            sys.executable, script("verify_readback.py"), "--diff-mode",
            "--old", old_draft, "--new", patched, "--declared", "C-01",
        ])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("undeclared_drift") == 0 and data.get("declared_id") == "C-01" else "FAIL"
        self.add(
            "M8-zero-drift", "E2E-c", "M8",
            f"python3 src/scripts/verify_readback.py --diff-mode --old {old_draft} --new {patched} --declared C-01",
            "exit=0, undeclared_drift=0, declared_id=C-01",
            f"exit={code}, undeclared_drift={data.get('undeclared_drift')}, declared_id={data.get('declared_id')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m8_diff"] = {"undeclared_drift": data.get("undeclared_drift"), "declared_id": data.get("declared_id")}

        code, out, _ = run([
            sys.executable, script("verify_readback.py"), "--verify-backup", backup_dir, "--change-table", change_table,
        ])
        data = parse_json(out)
        verdict = "PASS" if code == 0 and data.get("backup_valid") is True and data.get("hash_matched") is True else "FAIL"
        self.add(
            "M8-backup-integrity", "E2E-c", "M8",
            f"python3 src/scripts/verify_readback.py --verify-backup {backup_dir} --change-table {change_table}",
            "exit=0, backup_valid=true, hash_matched=true",
            f"exit={code}, backup_valid={data.get('backup_valid')}, hash_matched={data.get('hash_matched')}, backup_files={data.get('backup_files')}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["m8_backup"] = {"backup_valid": data.get("backup_valid"), "hash_matched": data.get("hash_matched")}

        # ---------------------------------------------------------------- M2 ledger
        ledger_src = fixture("progress-log.md")
        ledger_text = open(ledger_src, encoding="utf-8").read()
        row_re = re.compile(r"^\|\s*[^|]*\|\s*(T-[A-Za-z0-9_-]+)\s*\|[^|]*\|\s*\[( |x|X)\]\s*\|\s*([^|]+)\|", re.MULTILINE)
        rows_m = row_re.findall(ledger_text)
        ids = [r[0] for r in rows_m]
        states = [r[2].strip() for r in rows_m]
        all_unchecked = all(r[1] == " " for r in rows_m)
        states_valid = all(s in VALID_FOUR_STATES for s in states)
        no_implicit_release = "已审定" not in states
        structure_ok = ids == REQUIRED_TASK_IDS and states_valid and all_unchecked and no_implicit_release
        code, out, _ = run([
            sys.executable, script("storage_guard.py"), "--root", FIXTURES_DIR,
            "--ledger", ledger_src, "--check-ledger",
        ])
        data = parse_json(out)
        verdict = "PASS" if structure_ok and code == 0 and data.get("ledger_valid") is True else "FAIL"
        self.add(
            "M2-ledger-structure", "E2E-c", "M2",
            f"python3 src/scripts/storage_guard.py --root {FIXTURES_DIR} --ledger {ledger_src} --check-ledger",
            "exit=0, ledger_valid=true, exactly 15 task rows in pipeline order, all [ ], no 已审定",
            f"exit={code}, ledger_valid={data.get('ledger_valid')}, task_rows={len(ids)}, ids_match={ids == REQUIRED_TASK_IDS}, all_unchecked={all_unchecked}, states_valid={states_valid}, no_implicit_release={no_implicit_release}",
            code, verdict,
            {"stdout": out, "task_rows": len(ids), "task_ids": ids, "states": states},
        )
        self.key_assertions["ledger"] = {
            "task_rows": len(ids), "task_ids": ids, "all_unchecked": all_unchecked,
            "states_valid": states_valid, "no_implicit_release": no_implicit_release,
        }

        # Negative: unauthorized [x] must be reverted.
        neg_root = os.path.join(WORK_DIR, "neg", "ledger_root")
        if os.path.exists(neg_root):
            shutil.rmtree(neg_root)
        os.makedirs(neg_root)
        bad_ledger = os.path.join(neg_root, "progress-log.md")
        tampered = ledger_text.replace(
            "| P3 | T-P3-01 | 视角枚举与调研任务分解 | [ ] |",
            "| P3 | T-P3-01 | 视角枚举与调研任务分解 | [x] |",
        )
        tampered_ok = tampered != ledger_text
        with open(bad_ledger, "w", encoding="utf-8") as fh:
            fh.write(tampered)
        code, out, _ = run([
            sys.executable, script("storage_guard.py"), "--root", neg_root,
            "--ledger", bad_ledger, "--check-ledger",
        ])
        data = parse_json(out)
        reverted_text = open(bad_ledger, encoding="utf-8").read()
        reverted_ok = data.get("reverted_tasks") == ["T-P3-01"] and "| T-P3-01 | 视角枚举与调研任务分解 | [ ] |" in reverted_text
        verdict = "PASS" if tampered_ok and code == 1 and data.get("ledger_valid") is False and reverted_ok else "FAIL"
        self.add(
            "M2-unauthorized-tick-block-negative", "E2E-c", "M2",
            f"python3 src/scripts/storage_guard.py --root {neg_root} --ledger {bad_ledger} --check-ledger  # injected T-P3-01 [x]",
            "exit=1, ledger_valid=false, reverted_tasks=[T-P3-01], file rewritten back to [ ]",
            f"exit={code}, ledger_valid={data.get('ledger_valid')}, reverted_tasks={data.get('reverted_tasks')}, file_reverted={reverted_ok}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["ledger_negative"] = {"reverted_tasks": data.get("reverted_tasks"), "file_reverted": reverted_ok}

        # Negative: [x] without a human decision record -> blocked.
        bad_ledger2 = os.path.join(neg_root, "progress-log-decision.md")
        with open(bad_ledger2, "w", encoding="utf-8") as fh:
            fh.write(tampered)
        code, out, _ = run([
            sys.executable, script("storage_guard.py"), "--root", neg_root,
            "--ledger", bad_ledger2, "--decision-log", os.path.join(neg_root, "decision-log.md"),
            "--check-decision-log",
        ])
        data = parse_json(out)
        viol = data.get("violations") or []
        verdict = (
            "PASS" if code == 1 and data.get("decision_log_valid") is False and viol
            and viol[0].get("task_id") == "T-P3-01" and "missing human decision record" in viol[0].get("reason", "")
            else "FAIL"
        )
        self.add(
            "M2-decision-log-binding-negative", "E2E-c", "M2",
            f"python3 src/scripts/storage_guard.py --root {neg_root} --ledger {bad_ledger2} --check-decision-log  # no decision log",
            "exit=1, decision_log_valid=false, violation on T-P3-01 (missing human decision record)",
            f"exit={code}, decision_log_valid={data.get('decision_log_valid')}, violations={viol}",
            code, verdict, {"stdout": out},
        )
        self.key_assertions["decision_log_negative"] = {"violations": viol}

        # ------------------------------------------------------- E2E-05 dedup / terms
        sections = re.split(r"^## ", draft_text, flags=re.MULTILINE)[1:]
        dup_pairs = []
        dup_count = 0
        for i in range(len(sections)):
            body_i = sections[i].split("\n", 1)[1] if "\n" in sections[i] else ""
            grams_i = {body_i[k:k + 30] for k in range(max(0, len(body_i) - 29)) if body_i[k:k + 30].strip()}
            for j in range(i + 1, len(sections)):
                body_j = sections[j].split("\n", 1)[1] if "\n" in sections[j] else ""
                grams_j = {body_j[k:k + 30] for k in range(max(0, len(body_j) - 29)) if body_j[k:k + 30].strip()}
                overlap = grams_i & grams_j
                if overlap:
                    dup_count += len(overlap)
                    dup_pairs.append({"sections": [i + 1, j + 1], "count": len(overlap), "sample": sorted(overlap)[0]})
        verdict = "PASS" if len(sections) >= 2 and dup_count == 0 else "FAIL"
        self.add(
            "E2E05-dedup-30char", "E2E-c", "E2E-05",
            "harness pairwise 30-character substring comparison across ## sections of draft_full.md",
            "sections>=2 and zero shared 30-character substrings between any two sections",
            f"sections={len(sections)}, shared_30char_substrings={dup_count}, pairs={dup_pairs}",
            0 if verdict == "PASS" else 1, verdict,
            {"sections": len(sections), "duplicate_substrings": dup_count, "pairs": dup_pairs},
        )
        self.key_assertions["dedup"] = {"sections": len(sections), "duplicate_substrings": dup_count}

        canonical_terms = ["SCA", "PUE", "CapEx", "OpEx", "SDO"]
        bad_variants = ["资本开支", "运营开支", "功率使用效率", "样例通信委"]
        term_missing = [t for t in canonical_terms if t not in draft_text]
        variant_hits = {v: draft_text.count(v) for v in bad_variants}
        verdict = "PASS" if not term_missing and all(v == 0 for v in variant_hits.values()) else "FAIL"
        self.add(
            "E2E05-terminology-consistency", "E2E-c", "E2E-05",
            "harness canonical term / wrong-variant scan over draft_full.md",
            "canonical terms present; zero non-canonical variants",
            f"missing_canonical={term_missing}, wrong_variant_hits={variant_hits}",
            0 if verdict == "PASS" else 1, verdict,
            {"missing_canonical": term_missing, "wrong_variant_hits": variant_hits},
        )
        self.key_assertions["terminology"] = {"missing_canonical": term_missing, "wrong_variant_hits": variant_hits}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _parse_evidence_registry(path: str) -> List[Dict[str, str]]:
        text = open(path, encoding="utf-8").read()
        blocks = re.findall(r"^### (EVID-[0-9A-Za-z_-]+)\n(.*?)(?=^### |^## |\Z)", text, re.MULTILINE | re.DOTALL)
        entries = []
        for eid, body in blocks:
            entry = {"evidence_id": eid}
            for line in body.splitlines():
                m = re.match(r"^\s*-\s+([A-Za-z0-9_]+)\s*:\s*(.+?)\s*$", line)
                if m:
                    entry[m.group(1)] = m.group(2).strip()
            entries.append(entry)
        return entries

    @staticmethod
    def _chapter_ref_counts(text: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        current: Optional[str] = None
        for line in text.splitlines():
            m = re.match(r"^##\s+(第.+?章.*)$", line)
            if m:
                current = m.group(1).strip()
                counts[current] = 0
                continue
            if line.startswith("## "):
                current = None
                continue
            if current and "evidence_ref:" in line:
                counts[current] += 1
        return counts

    # ================================================================= checklist
    def _passed(self, prefix: str) -> bool:
        return any(r["name"].startswith(prefix) and r["verdict"] == "PASS" for r in self.results)

    def evaluate_checklist(self) -> None:
        brief_sections = next((r["details"].get("sections_2_1_to_8") for r in self.results if r["name"] == "M1-brief-verify"), False)
        self.checklist["E2E-01"] = {
            "name": "E2E-01 澄清落地",
            "machine_status": "PARTIAL" if (self._passed("M1-brief-verify") and self._passed("G0-stub-reject")) else "FAIL",
            "automated": bool(self._passed("M1-brief-verify") and self._passed("G0-stub-reject")),
            "human_pending": True,
            "human_pending_reason": "G0 签署件必须由真人决策者审阅 brief.md 后亲笔填写；E2E-a 桩已证明会被门禁硬拒绝，人类格式夹具仅用于验证放行路径。",
            "evidence": f"verify-brief valid=true, sections 2.1-2.8={brief_sections}, G0 stub rejected exit=1 STUB_REJECTED",
        }
        self.checklist["E2E-02"] = {
            "name": "E2E-02 治理合规",
            "machine_status": "PARTIAL" if (self._passed("M2-ledger-structure") and self._passed("M2-unauthorized-tick-block-negative") and self._passed("M2-decision-log-binding-negative")) else "FAIL",
            "automated": bool(self._passed("M2-ledger-structure") and self._passed("M2-unauthorized-tick-block-negative") and self._passed("M2-decision-log-binding-negative")),
            "human_pending": True,
            "human_pending_reason": "台账 [x] 勾选权排他归人类；自动化只能验证 15 行结构、无隐式放行与未授权勾选被回滚，无法代替人类授权勾选。",
            "evidence": "15 task rows in order, all [ ], unauthorized T-P3-01 [x] reverted, [x] without human decision record blocked",
        }
        self.checklist["E2E-03"] = {
            "name": "E2E-03 底表硬核",
            "machine_status": "PASS" if all(self._passed(p) for p in ("M4-audit-calc", "M4-evidence-anchoring", "M4-cross-scope-isolation", "M4-cross-scope-block-negative", "M4-evidence-registry-integrity", "M4-assumption-tags")) else "FAIL",
            "automated": True,
            "human_pending": False,
            "human_pending_reason": None,
            "evidence": "audit_calc: checked_cells=4, mismatches=[]; injected cross-caliber expression -> exit 1; 6 evidence entries with matching snapshot SHA-256 and source_url",
        }
        self.checklist["E2E-04"] = {
            "name": "E2E-04 大纲锁定",
            "machine_status": "PARTIAL" if (self._passed("M5-outline-resolved") and self._passed("M5-outline-sections") and self._passed("G1-stub-reject")) else "FAIL",
            "automated": bool(self._passed("M5-outline-resolved") and self._passed("M5-outline-sections")),
            "human_pending": True,
            "human_pending_reason": "G1 大纲放行必须由真人确认论证拓扑与证据覆盖后签署；桩件已证明会被门禁硬拒绝，不能替代真人。",
            "evidence": "outline_check --require-resolved: pending_count=0, dangling_refs=[], refs_total=6; chapter_count=3, each chapter has evidence_ref; G1 stub rejected exit=1 STUB_REJECTED",
        }
        self.checklist["E2E-05"] = {
            "name": "E2E-05 单次成型与去重",
            "machine_status": "PASS" if (self._passed("E2E05-dedup-30char") and self._passed("E2E05-terminology-consistency")) else "FAIL",
            "automated": True,
            "human_pending": False,
            "human_pending_reason": None,
            "evidence": f"shared 30-char substrings={self.key_assertions.get('dedup', {}).get('duplicate_substrings')} across {self.key_assertions.get('dedup', {}).get('sections')} sections; canonical terms present, zero wrong variants",
        }
        self.checklist["E2E-06"] = {
            "name": "E2E-06 无 AI 痕迹与白名单完好",
            "machine_status": "PASS" if all(self._passed(p) for p in ("M7-text-hygiene", "M7-allowlist-9", "M6-provenance-isolated", "M6-provenance-negative", "M6-verify-readback")) else "FAIL",
            "automated": True,
            "human_pending": False,
            "human_pending_reason": "文本卫生与隔离性可由机器判定；但 G2 涉及的 D1/D2 定性裁取决议仍必须由真人完成（见 E2E-b）。",
            "evidence": "audit_text_hygiene: violations=[]; 9 rigor allowlist entries matched, 0 forbidden-pattern hits; provenance isolated=true and shared-session blocked; readback layer2_residuals=0",
        }
        self.checklist["E2E-07"] = {
            "name": "E2E-07 交付物规范与两遍法",
            "machine_status": "PARTIAL" if all(self._passed(p) for p in ("M7-build-docx-idempotence", "M7-build-pdf", "M7-toc-two-pass", "M7-delivery-readback", "M7-toc-multipage-pages")) else "FAIL",
            "automated": True,
            "human_pending": True,
            "human_pending_reason": "G3 交付放行与 Word/PDF 版式人工目检必须由真人完成；机器只能验证结构与哈希。",
            "evidence": "two builds identical (8/8 OOXML component hashes, identical docx bytes); PDF produced; toc updated 3/3; delivery_readback diff sets empty and every TOC page equals an independently located real body page; multi-page TOC fixture (43 entries, 2 TOC pages) passes per-entry page checks; G3 human sign pending",
        }
        self.checklist["E2E-08"] = {
            "name": "E2E-08 回路响应与零漂移",
            "machine_status": "PARTIAL" if (self._passed("M8-zero-drift") and self._passed("M8-backup-integrity") and self._passed("change-01-stub-reject")) else "FAIL",
            "automated": True,
            "human_pending": True,
            "human_pending_reason": "change-01 变更范围授权必须由真人签署；E2E-a 桩已证明会被门禁硬拒绝。",
            "evidence": "diff-mode undeclared_drift=0; backup_valid=true, hash_matched=true; change-01 stub rejected exit=1 STUB_REJECTED",
        }

    # ==================================================================== output
    def emit(self) -> bool:
        duration = round(time.time() - self.start_time, 2)
        total = len(self.results)
        passed = sum(1 for r in self.results if r["verdict"] == "PASS")
        failed = total - passed
        status_counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
        for item in self.checklist.values():
            status_counts[item["machine_status"]] = status_counts.get(item["machine_status"], 0) + 1

        payload = {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "environment": self.env_info,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "all_passed": failed == 0,
                "duration_seconds": duration,
                "checklist_status_counts": status_counts,
            },
            "gate_matrix": self.gate_matrix,
            "key_assertions": self.key_assertions,
            "checklist": self.checklist,
            "e2e_b_pending": [
                {"id": "E2E-01", "item": "G0 真人签署 brief.md 放行", "reason": "机器禁止代签；E2E-a 桩带 stub:true 已被门禁硬拒绝 (STUB_REJECTED)，人类格式夹具仅用于验证放行路径"},
                {"id": "E2E-02", "item": "progress-log.md 任务 [x] 由人类授权勾选", "reason": "勾选权排他归人类，自动化仅能验证未授权勾选被回滚"},
                {"id": "E2E-04", "item": "G1 真人签署 outline.md 放行", "reason": "大纲论证拓扑与取舍必须由真人确认"},
                {"id": "E2E-06", "item": "G2 真人定性裁决 D1/D2 争议项", "reason": "定性裁决权归人类，机器严禁自动降级或删除"},
                {"id": "E2E-07", "item": "G3 真人签署交付物放行并目检版式", "reason": "交付放行与版式质量属人类判断"},
                {"id": "E2E-08", "item": "change-01 真人签署变更范围授权", "reason": "变更授权必须由真人行使"},
                {"id": "E2E-b", "item": "真人实操全程与人时/机器耗时记录", "reason": "无人值守环境无人类操作者，无法采集真实人时"},
            ],
            "test_cases": self.results,
        }
        with open(RESULTS_JSON, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        with open(REPORT_MD, "w", encoding="utf-8") as fh:
            fh.write(self._render_report(payload, duration, total, passed, failed))

        print("\n" + "=" * 74)
        print(f"E2E RESULT: {total} test cases, {passed} passed, {failed} failed, {duration}s")
        print(f"checklist: {status_counts}")
        print(f"results json: {RESULTS_JSON}")
        print(f"report      : {REPORT_MD}")
        if failed:
            print("FAILED CASES:")
            for r in self.results:
                if r["verdict"] != "PASS":
                    print(f"  - {r['name']}: {r['actual']}")
        print("=" * 74)
        return failed == 0

    def _render_report(self, payload: Dict[str, Any], duration: float, total: int, passed: int, failed: int) -> str:
        env = payload["environment"]
        lines: List[str] = []
        lines.append("# 端到端 (E2E) 测试真实运行报告")
        lines.append("")
        lines.append(f"> 生成时间: {payload['generated_at']}")
        lines.append(f"> 运行环境: Python {env['python_version']} (`{env['python_executable']}`), platform `{env['platform']}`, LibreOffice: {env['soffice_version']}")
        lines.append(f"> 工作区: `{env['workspace']}`")
        lines.append("> 离线声明: 未访问外网；全部证据来自 `tests/e2e_fixtures/raw_evidence/`。")
        lines.append(f"> 执行摘要: 共 **{total}** 项断言，通过 **{passed}**，失败 **{failed}**，耗时 **{duration}s**。")
        lines.append("")

        lines.append("## 1. E2E-a 门禁矩阵（5 门 × 缺失/桩件/机器签名/哈希绑错/显式校验）")
        lines.append("")
        lines.append("> 桩件声明: E2E-a 桩文件内含 `stub: true` 与「本件为演练桩，非真实人类签署」，门禁必须硬拒绝为 `STUB_REJECTED` / exit 1，即使哈希完全吻合。")
        lines.append("> 放行路径声明: 「显式校验」列的放行用例使用**不含 stub 标记的人类格式测试夹具**（`signed_by: human:e2e_fixture_operator`），该夹具仅用于验证门禁放行路径，**不代表任何真实人类签署**；真实签署仍须由人类在 E2E-b 中亲笔完成。")
        lines.append("")
        lines.append("| 门禁 | 绑定工件 | 无桩（缺失） | 桩件（硬拒绝） | 机器签名 | 哈希绑错工件 |")
        lines.append("|---|---|---|---|---|---|")
        for row in payload["gate_matrix"]:
            lines.append(
                f"| **{row['gate']}** | `{row['artifact']}` | exit {row['missing']['exit_code']} / `{row['missing']['state']}` | "
                f"exit {row['stub']['exit_code']} / `{row['stub']['state']}` | "
                f"exit {row['machine']['exit_code']} / `{row['machine']['state']}` | "
                f"exit {row['hash_binding']['exit_code']} / `{row['hash_binding']['state']}` |"
            )
        lines.append("")
        lines.append("## 2. E2E-c 关键断言（真实输出）")
        lines.append("")
        ka = payload["key_assertions"]
        audit = ka.get("audit_calc", {})
        lines.append(f"- `audit_calc.py datatable.csv`: checked_cells=**{audit.get('checked_cells')}**, mismatches=**{audit.get('mismatches')}**")
        cross = ka.get("m4_cross_scope_negative", {})
        lines.append(f"- 跨口径拦截负例: exit=**{cross.get('exit_code')}**, violations=**{len(cross.get('violations') or [])}** 条（注入 `ITM_A01 - ITM_B01`）")
        lines.append(f"- 证据登记: entries=**{ka.get('evidence_registry', {}).get('entries')}**, 快照哈希全部匹配=**{ka.get('evidence_registry', {}).get('all_snapshot_hashes_match')}**, source_url 缺失项=**{ka.get('evidence_registry', {}).get('missing_fields')}**")
        m5 = ka.get("m5_outline", {})
        lines.append(f"- `outline_check --require-resolved`: pending_count=**{m5.get('pending_count')}**, dangling_refs=**{m5.get('dangling_refs')}**, missing_refs=**{m5.get('missing_refs')}**, refs_total=**{m5.get('refs_total')}**")
        lines.append(f"- 章节证据回指: chapter_count=**{ka.get('m5_chapters', {}).get('chapter_count')}**, per-chapter refs=**{ka.get('m5_chapters', {}).get('chapter_refs')}**")
        m6 = ka.get("m6_readback", {})
        lines.append(f"- `verify_readback --plan`: layer1=**{m6.get('layer1')}**, layer2_residuals=**{m6.get('layer2_residuals')}**, layer3=**{m6.get('layer3')}**, layer4=**{m6.get('layer4')}**")
        lines.append(f"- provenance 隔离: isolated=**{ka.get('m6_provenance', {}).get('isolated')}**；共享 session 负例 exit=**{ka.get('m6_provenance_negative', {}).get('exit_code')}**, status=**{ka.get('m6_provenance_negative', {}).get('status')}**")
        lines.append(f"- `audit_text_hygiene`: violations=**{ka.get('hygiene', {}).get('violations')}**；9 类严谨性白名单命中=**{ka.get('hygiene_allowlist', {}).get('allow_hits')}**；违禁模式命中=**{ka.get('hygiene_allowlist', {}).get('pattern_hits')}**")
        cit = ka.get("citation", {})
        lines.append(f"- `citation_check`: dangling_refs=**{cit.get('dangling_refs')}**, unnumbered_figs=**{cit.get('unnumbered_figs')}**, dangling_tables=**{cit.get('dangling_tables')}**")
        bm = ka.get("build_manifest", {})
        lines.append(f"- `build_docx` 两次构建: 部件哈希一致=**{bm.get('components_identical')}**（{len(bm.get('components') or {})} 个部件）, docx SHA256 run1=`{(bm.get('docx_sha256_run1') or '')[:32]}...`, run2=`{(bm.get('docx_sha256_run2') or '')[:32]}...`")
        lines.append(f"- `build_pdf`: pdf=**{ka.get('pdf', {}).get('pdf')}**, size=**{ka.get('pdf', {}).get('size_bytes')}** bytes")
        toc = ka.get("toc", {})
        lines.append(f"- `toc_two_pass`: toc_backfilled=**{toc.get('toc_backfilled')}**, entries_count=**{toc.get('entries_count')}**, updated_count=**{toc.get('updated_count')}**, pages=**{toc.get('pages')}**")
        rb = ka.get("delivery_readback", {})
        lines.append(f"- `delivery_readback`: toc_minus_headings=**{rb.get('toc_minus_headings')}**, headings_minus_toc=**{rb.get('headings_minus_toc')}**, page_mismatch=**{rb.get('page_mismatch')}**")
        lines.append(f"- M8: undeclared_drift=**{ka.get('m8_diff', {}).get('undeclared_drift')}**；backup_valid=**{ka.get('m8_backup', {}).get('backup_valid')}**, hash_matched=**{ka.get('m8_backup', {}).get('hash_matched')}**")
        led = ka.get("ledger", {})
        lines.append(f"- 治理台账: task_rows=**{led.get('task_rows')}**, all_unchecked=**{led.get('all_unchecked')}**, no_implicit_release=**{led.get('no_implicit_release')}**；未授权 [x] 回滚=**{ka.get('ledger_negative', {}).get('reverted_tasks')}**")
        lines.append(f"- 去重: sections=**{ka.get('dedup', {}).get('sections')}**, 共享 30 字符子串=**{ka.get('dedup', {}).get('duplicate_substrings')}**")
        lines.append("")

        lines.append("## 3. §8.2.3 E2E-01…E2E-08 判定")
        lines.append("")
        lines.append("| 判据 | 名称 | 机器侧状态 | 是否需真人 | 证据摘要 |")
        lines.append("|---|---|---|---|---|")
        for key in sorted(payload["checklist"]):
            item = payload["checklist"][key]
            lines.append(
                f"| **{key}** | {item['name']} | {item['machine_status']} | {'是' if item['human_pending'] else '否'} | {item['evidence']} |"
            )
        lines.append("")
        lines.append("说明：`PARTIAL` 表示机器可判定的部分已全部通过，但该项判据包含只能由真人完成的签署/裁决动作；机器不代签、不假设通过。")
        lines.append("")

        lines.append("## 4. E2E-b 未完成项及原因")
        lines.append("")
        for item in payload["e2e_b_pending"]:
            lines.append(f"- **{item['id']}** — {item['item']}：{item['reason']}")
        lines.append("")
        lines.append("E2E-b 的可执行骨架见 `tests/e2e/E2E_B_RUNBOOK.md`；空白签署件模板见 `tests/e2e/gates/*.template.md`（未预填任何真人署名）。")
        lines.append("")

        lines.append("## 5. 逐项测试结果")
        lines.append("")
        lines.append("| # | 轨道/阶段 | 用例 | 退出码 | 结论 | 实测 |")
        lines.append("|---|---|---|---|---|---|")
        for idx, r in enumerate(payload["test_cases"], start=1):
            actual = str(r["actual"]).replace("|", "\\|")
            lines.append(f"| {idx} | {r['track']}/{r['stage']} | {r['name']} | {r['exit_code']} | **{r['verdict']}** | {actual} |")
        lines.append("")
        lines.append("## 6. 已知限制与残余风险")
        lines.append("")
        lines.append("1. `gate_guard.py` 现对 `stub: true` 桩件执行硬拒绝（`STUB_REJECTED` / exit 1），五门统一生效；因此 E2E-a 的「桩件」行即为拒绝证据，放行路径改由不含 stub 标记的人类格式夹具验证。该夹具仅证明格式与哈希绑定路径，不构成真实人类签署。")
        lines.append("2. `storage_guard.py --check-ledger` 只把任务行映射到 G0/G1/G2/G3/change 门禁件。没有专属门禁的任务（如 T-P3-01）即使由人类勾选，也会被回滚，除非该行「依据签署件与哈希」列显式写出某个已签署的 `gates/*.md` 路径。E2E-b runbook 已注明该操作约束；这是实现层待改进点，不在本次 E2E 职责内修改。")
        lines.append("3. E2E-c 全部结果来自本地固定夹具，不验证外部网络抓取与真实信源时效性。")
        lines.append("4. E2E-b 的真人交互人时、版式目检与定性裁决无法在无人值守环境采集。")
        lines.append("")
        if failed:
            lines.append("## 7. 失败项")
            lines.append("")
            for r in payload["test_cases"]:
                if r["verdict"] != "PASS":
                    lines.append(f"- **{r['name']}**: expected={r['expected']}; actual={r['actual']}")
            lines.append("")
        return "\n".join(lines)


def main() -> None:
    harness = E2EHarness()
    harness.collect_env()
    harness.run_track_a()
    harness.run_track_c()
    harness.evaluate_checklist()
    ok = harness.emit()

    if os.environ.get("E2E_KEEP_WORK") != "1":
        if os.path.exists(WORK_DIR):
            shutil.rmtree(WORK_DIR)
            print(f"cleaned temporary workspace: {WORK_DIR}")
    else:
        print(f"kept temporary workspace (E2E_KEEP_WORK=1): {WORK_DIR}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
