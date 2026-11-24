#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BUILD_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=== [M7 Test Suite] Running Pytest ==="
pytest "${SCRIPT_DIR}/test_m7_delivery.py" -v

echo "=== [M7 Test Suite] Running Direct CLI Assertions ==="

echo "1. Testing audit_text_hygiene.py (Positive Control - 9 Rigor Declarations Protected)"
python3 "${SKILL_BUILD_DIR}/src/scripts/audit_text_hygiene.py" \
  "${SCRIPT_DIR}/fixtures/draft_full_clean.md" \
  --rules "${SKILL_BUILD_DIR}/src/templates/forbidden_terms.json"

echo "2. Testing audit_text_hygiene.py (Negative Control - 5 Injected Violations Caught)"
set +e
python3 "${SKILL_BUILD_DIR}/src/scripts/audit_text_hygiene.py" \
  "${SCRIPT_DIR}/fixtures/dirty_meta_draft.md" \
  --rules "${SKILL_BUILD_DIR}/src/templates/forbidden_terms.json"
DIRTY_EXIT=$?
set -e
if [ "$DIRTY_EXIT" -ne 1 ]; then
  echo "Expected exit code 1 for dirty_meta_draft.md, got $DIRTY_EXIT"
  exit 1
fi
echo "-> Successfully blocked dirty draft with exit code 1"

echo "3. Testing citation_check.py (Positive Control - Closed Reference Loop)"
python3 "${SKILL_BUILD_DIR}/src/scripts/citation_check.py" \
  "${SCRIPT_DIR}/fixtures/draft_full_clean.md" \
  --evidence-index "${SCRIPT_DIR}/fixtures/evidence-index.md"

echo "4. Testing citation_check.py (Negative Control - Dangling Ref & Broken Fig)"
set +e
python3 "${SKILL_BUILD_DIR}/src/scripts/citation_check.py" \
  "${SCRIPT_DIR}/fixtures/broken_citation_draft.md" \
  --evidence-index "${SCRIPT_DIR}/fixtures/evidence-index.md"
BROKEN_EXIT=$?
set -e
if [ "$BROKEN_EXIT" -ne 1 ]; then
  echo "Expected exit code 1 for broken_citation_draft.md, got $BROKEN_EXIT"
  exit 1
fi
echo "-> Successfully blocked broken citations with exit code 1"

echo "5. Testing build_docx.py, build_pdf.py, toc_two_pass.py & delivery_readback.py Pipeline"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

python3 "${SKILL_BUILD_DIR}/src/scripts/build_docx.py" \
  "${SCRIPT_DIR}/fixtures/draft_full_clean.md" \
  --out "${TMP_DIR}/output.docx" \
  --manifest "${TMP_DIR}/build_manifest.json"

python3 "${SKILL_BUILD_DIR}/src/scripts/build_pdf.py" \
  "${TMP_DIR}/output.docx" \
  --out "${TMP_DIR}/output.pdf"

python3 "${SKILL_BUILD_DIR}/src/scripts/toc_two_pass.py" \
  "${TMP_DIR}/output.docx" \
  "${TMP_DIR}/output.pdf"

python3 "${SKILL_BUILD_DIR}/src/scripts/delivery_readback.py" \
  --docx "${TMP_DIR}/output.docx" \
  --pdf "${TMP_DIR}/output.pdf" \
  --source "${SCRIPT_DIR}/fixtures/draft_full_clean.md" \
  --out "${TMP_DIR}/delivery_readback.json"

echo "6. Testing gate_guard.py for G3 Gate (Positive Control - Human Signoff)"
python3 "${SKILL_BUILD_DIR}/src/scripts/gate_guard.py" \
  --gate G3 \
  --verify \
  --artifact "${SCRIPT_DIR}/fixtures/delivery/output.docx" \
  --approval "${SCRIPT_DIR}/fixtures/gates/G3-approval-valid.md"

echo "7. Testing gate_guard.py for G3 Gate (Negative Control - Machine Signature Prohibited)"
set +e
python3 "${SKILL_BUILD_DIR}/src/scripts/gate_guard.py" \
  --gate G3 \
  --verify \
  --artifact "${SCRIPT_DIR}/fixtures/delivery/output.docx" \
  --approval "${SCRIPT_DIR}/fixtures/gates/G3-approval-machine-signed.md"
G3_MACHINE_EXIT=$?
set -e
if [ "$G3_MACHINE_EXIT" -ne 1 ]; then
  echo "Expected exit code 1 for G3-approval-machine-signed.md, got $G3_MACHINE_EXIT"
  exit 1
fi
echo "-> Successfully blocked machine signature with exit code 1"

echo "=== [M7 Test Suite] All blackbox tests successfully passed! ==="
