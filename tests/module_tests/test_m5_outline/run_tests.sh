#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

echo "=== 正在执行 M5 (outline-approval) 模块自动化测试套件 ==="
pytest tests/module_tests/test_m5_outline/test_m5_outline.py -v

echo "=== M5 模块全部测试执行通过 ==="
