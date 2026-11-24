#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BUILD_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=== [M6 Test Suite] Running Pytest ==="
pytest "${SCRIPT_DIR}/test_m6_review_loop.py" -v

echo "=== [M6 Test Suite] Running Direct CLI Assertions ==="

echo "1. Testing verify_readback.py --plan --target (Positive Control)"
python3 "${SKILL_BUILD_DIR}/src/scripts/verify_readback.py" \
  --plan "${SCRIPT_DIR}/fixtures/correction_diff.md" \
  --target "${SCRIPT_DIR}/fixtures/draft_full_corrected.md"

echo "2. Testing verify_readback.py --check-provenance (Heterogeneous Channel Positive Control)"
python3 "${SKILL_BUILD_DIR}/src/scripts/verify_readback.py" \
  --check-provenance "${SCRIPT_DIR}/fixtures/valid_heterogeneous_provenance.json"

echo "3. Testing verify_readback.py --diff-mode (Declared Drift Positive Control)"
python3 "${SKILL_BUILD_DIR}/src/scripts/verify_readback.py" \
  --diff-mode \
  --old "${SCRIPT_DIR}/fixtures/injected_defects_draft.md" \
  --new "${SCRIPT_DIR}/fixtures/patch_only_c01.md" \
  --declared "C-01"

echo "4. Testing verify_readback.py --verify-backup (Backup Snapshot Positive Control)"
python3 "${SKILL_BUILD_DIR}/src/scripts/verify_readback.py" \
  --verify-backup "${SCRIPT_DIR}/fixtures/valid_backup" \
  --change-table "${SCRIPT_DIR}/fixtures/change_table.md"

echo "=== [M6 Test Suite] All tests successfully passed! ==="
