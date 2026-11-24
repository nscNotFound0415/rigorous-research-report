#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BUILD_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=== [M2 Test Suite] Running Pytest ==="
pytest "${SCRIPT_DIR}/test_m2_governance.py" -v

echo "=== [M2 Test Suite] All tests successfully passed! ==="
