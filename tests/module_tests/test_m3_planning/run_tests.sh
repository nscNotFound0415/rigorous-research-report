#!/usr/bin/env bash
# run_tests.sh - M3 课题拆分与调研规划 自动化测试一键执行脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "================================================================="
echo "  M3 (research-decomposition) 全量黑箱与阴性对照测试套件"
echo "================================================================="
echo "工作区根目录: ${ROOT_DIR}"
echo ""

cd "${ROOT_DIR}"

if command -v pytest >/dev/null 2>&1; then
    echo ">> 使用 pytest 运行测试套件:"
    pytest "${SCRIPT_DIR}/test_m3_planning.py" -v
else
    echo ">> 使用 python3 -m unittest 运行测试套件:"
    python3 -m unittest "${SCRIPT_DIR}/test_m3_planning.py" -v
fi

echo ""
echo ">> 所有 M3 模块测试执行完毕！"
