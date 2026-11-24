#!/usr/bin/env bash
# run_e2e.sh - One-click E2E runner for 建设方案 v2.1 §8.2.
#
# Track E2E-a: automated gate stub / blocker verification (5 gates x 3 states + hash binding)
# Track E2E-c: deterministic offline fixture closed loop (M3 -> M4 -> M5 -> M6 -> M7 -> M8)
# E2E-b      : human runbook skeleton only (see E2E_B_RUNBOOK.md); no agent may sign it.
#
# Usage:
#   bash tests/e2e/run_e2e.sh
#   E2E_KEEP_WORK=1 bash tests/e2e/run_e2e.sh   # keep tests/e2e/_work for inspection
#
# Exit code: 0 only when every automated assertion passes.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BUILD_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "======================================================================"
echo "  Rigorous Research Report Pipeline - E2E Suite (E2E-a + E2E-c)"
echo "  E2E-b is a human-only runbook; no signatures are generated here."
echo "======================================================================"
echo "Workspace : ${SKILL_BUILD_DIR}"
echo "Time      : $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Python    : $(python3 --version 2>&1)"
echo "Soffice   : $(command -v soffice || echo 'NOT AVAILABLE')"
echo "Work dir  : ${SCRIPT_DIR}/_work (cleaned at the end unless E2E_KEEP_WORK=1)"
echo "----------------------------------------------------------------------"

cd "${SKILL_BUILD_DIR}" || exit 1

python3 -I "${SCRIPT_DIR}/harness.py"
E2E_EXIT=$?

echo ""
if [ "${E2E_EXIT}" -eq 0 ]; then
    echo "======================================================================"
    echo "  [SUCCESS] All automated E2E assertions passed."
    echo "  Results : ${SCRIPT_DIR}/e2e_results.json"
    echo "  Report  : ${SCRIPT_DIR}/E2E_REPORT.md"
    echo "  Runbook : ${SCRIPT_DIR}/E2E_B_RUNBOOK.md"
    echo "  NOTE    : E2E-b human sign-offs remain PENDING by design."
    echo "======================================================================"
else
    echo "======================================================================"
    echo "  [FAILURE] E2E suite failed with exit code ${E2E_EXIT}."
    echo "  Inspect the FAIL lines above and ${SCRIPT_DIR}/e2e_results.json"
    echo "======================================================================"
fi

exit "${E2E_EXIT}"
