#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BUILD_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "=== [M9 SKILL Entry Test Suite] ==="
echo "Testing src/SKILL.md contract and entry validator..."

# 1. 运行独立 entry_validator CLI
echo ""
echo "[Step 1] Running entry_validator.py CLI..."
python3 "${SCRIPT_DIR}/entry_validator.py" --skill "${SKILL_BUILD_ROOT}/src/SKILL.md" --src-root "${SKILL_BUILD_ROOT}/src"

# 2. 运行 pytest 自动化测试套件
echo ""
echo "[Step 2] Running pytest test_m9_skill_entry.py..."
pytest "${SCRIPT_DIR}/test_m9_skill_entry.py" -v

echo ""
echo "=== All M9 Skill Entry Tests Passed Successfully! ==="
