#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

export PYTHONPATH="${MODULE_ROOT}:${PYTHONPATH}"

echo "=== Running M4 Datatable Ledger Module Tests ==="
if command -v pytest >/dev/null 2>&1; then
    pytest "${SCRIPT_DIR}/test_m4_datatable.py" -v
else
    python3 "${SCRIPT_DIR}/test_m4_datatable.py"
fi
echo "=== All M4 Tests Passed Successfully ==="
