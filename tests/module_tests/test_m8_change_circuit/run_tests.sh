#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BUILD_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=== [M8 Test Suite] Running Pytest ==="
pytest "${SCRIPT_DIR}/test_m8_change_circuit.py" -v

echo "=== [M8 Test Suite] Running Direct CLI Assertions ==="

echo "1. Testing change_dispatch.py --classify (Lightweight Rating Tweak)"
python3 "${SKILL_BUILD_DIR}/src/scripts/change_dispatch.py" \
  --root "${SKILL_BUILD_DIR}" \
  --instruction-file "${SCRIPT_DIR}/fixtures/instruction_lightweight.md" \
  --classify

echo "2. Testing change_dispatch.py --classify (Major Architecture Shift)"
python3 "${SKILL_BUILD_DIR}/src/scripts/change_dispatch.py" \
  --root "${SKILL_BUILD_DIR}" \
  --instruction-file "${SCRIPT_DIR}/fixtures/instruction_major.md" \
  --classify

echo "3. Testing verify_readback.py --diff-mode (Zero-Drift Positive Control)"
python3 "${SKILL_BUILD_DIR}/src/scripts/verify_readback.py" \
  --diff-mode \
  --old "${SCRIPT_DIR}/fixtures/baseline_draft_full.md" \
  --new "${SCRIPT_DIR}/fixtures/clean_corrected_draft.md" \
  --declared "C-01"

echo "4. Testing verify_readback.py --diff-mode (Negative Control: Undeclared Drift Interception)"
set +e
python3 "${SKILL_BUILD_DIR}/src/scripts/verify_readback.py" \
  --diff-mode \
  --old "${SCRIPT_DIR}/fixtures/baseline_draft_full.md" \
  --new "${SCRIPT_DIR}/fixtures/undeclared_drift_patch.md" \
  --declared "C-01"
NEG_CODE=$?
set -e

if [ "${NEG_CODE}" -ne 1 ]; then
  echo "FAIL: Expected negative control to exit with code 1, got ${NEG_CODE}"
  exit 1
fi
echo "SUCCESS: Negative control properly intercepted with exit code 1."

echo "=== [M8 Test Suite] All M8 tests successfully passed! ==="
