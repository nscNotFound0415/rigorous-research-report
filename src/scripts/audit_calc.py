#!/usr/bin/env python3
"""
audit_calc.py - 数据底表纯代码算术复算、口径隔离与证据索引映射核验工具

符合 OpenSpec 规范与建设方案 v2.1 规范要求：
- 纯 Python 3 标准库实现，零第三方依赖，无外网访问，零跨调用状态残留。
- 支持基于 ast.parse 白名单的安全算术表达式求值（数字、+ - * / % ** //、括号、一元正负号、变量代入）。
- 容差 (tolerance) 按单元格声明判定（整数默认 0，浮点默认 1e-9 并支持声明舍入模式），禁止全局写死 0。
- 口径隔离检查：当两行的 caliber 不同却出现在同一公式的运算里时，报告 cross_caliber 错误并以退出码 1 阻断。
- 裸数字检查：source_type=estimated 且 assumption_tag 为空时报告 bare_estimate 错误；source_ref 为空时报告 missing_source 错误。
- 证据映射核验：支持比对 evidence-index.md 中的有效条目 ID。

CLI 契约:
    python3 scripts/audit_calc.py datatable.csv
    python3 scripts/audit_calc.py datatable.csv --strict-tolerance
    python3 scripts/audit_calc.py datatable.csv --evidence-index evidence-index.md
"""

import argparse
import ast
import csv
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


# 白名单 AST 节点与运算符
ALLOWED_NODES = (
    ast.Expression,
    ast.Constant,
    ast.Name,
    ast.UnaryOp,
    ast.BinOp,
    ast.Load,
)

ALLOWED_BINOPS = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.FloorDiv,
)

ALLOWED_UNARYOPS = (
    ast.UAdd,
    ast.USub,
)

VALID_SOURCE_TYPES = {"measured", "derived", "estimated", "quoted"}
IGNORED_CALIBERS = {"", "n/a", "na", "common", "all", "universal", "none"}


def safe_eval_ast(node: ast.AST, env: Dict[str, float]) -> float:
    """
    通过 AST 白名单遍历递归求值纯算术表达式，杜绝 exec / eval 任意代码执行风险。
    """
    if isinstance(node, ast.Expression):
        return safe_eval_ast(node.body, env)
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Constant must be numeric, got {type(node.value).__name__}: {node.value}")
        return float(node.value)
    elif isinstance(node, ast.Name):
        var_id = node.id
        if var_id in env:
            return float(env[var_id])
        raise ValueError(f"Variable '{var_id}' not found in datatable items")
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ALLOWED_UNARYOPS):
            raise ValueError(f"Disallowed unary operator: {type(node.op).__name__}")
        val = safe_eval_ast(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return +val
        elif isinstance(node.op, ast.USub):
            return -val
    elif isinstance(node, ast.BinOp):
        if not isinstance(node.op, ALLOWED_BINOPS):
            raise ValueError(f"Disallowed binary operator: {type(node.op).__name__}")
        left_val = safe_eval_ast(node.left, env)
        right_val = safe_eval_ast(node.right, env)
        if isinstance(node.op, ast.Add):
            return left_val + right_val
        elif isinstance(node.op, ast.Sub):
            return left_val - right_val
        elif isinstance(node.op, ast.Mult):
            return left_val * right_val
        elif isinstance(node.op, ast.Div):
            if right_val == 0:
                raise ZeroDivisionError("Division by zero in formula calculation")
            return left_val / right_val
        elif isinstance(node.op, ast.Mod):
            if right_val == 0:
                raise ZeroDivisionError("Modulo by zero in formula calculation")
            return left_val % right_val
        elif isinstance(node.op, ast.Pow):
            if abs(right_val) > 100:
                raise ValueError("Exponent too large in power operation")
            return left_val ** right_val
        elif isinstance(node.op, ast.FloorDiv):
            if right_val == 0:
                raise ZeroDivisionError("Floor division by zero")
            return float(left_val // right_val)
    raise ValueError(f"Disallowed AST node: {type(node).__name__}")


def sanitize_item_id_for_var(item_id: str) -> str:
    """将包含中划线等字符的 item_id 转换为合法 Python 变量名"""
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", item_id.strip())
    if not sanitized or sanitized[0].isdigit():
        sanitized = "VAR_" + sanitized
    return sanitized


def extract_var_names(node: ast.AST) -> List[str]:
    """提取表达式中的所有变量名称"""
    names = []
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Name):
            names.append(subnode.id)
    return names


def parse_tolerance_spec(tol_str: str, actual_val: float) -> Tuple[float, Optional[str]]:
    """
    解析容差字符串与舍入模式。
    支持格式: '0', '1e-9', '0.01', '0.01;round=half_up', '1e-4;mode=even'
    整数默认 0，浮点默认 1e-9。
    """
    raw = tol_str.strip() if tol_str else ""
    if not raw:
        if actual_val.is_integer() and "." not in str(raw):
            return 0.0, "exact_int"
        return 1e-9, "default_float"

    parts = raw.split(";")
    tol_num_str = parts[0].strip()
    rounding_mode = parts[1].strip() if len(parts) > 1 else None

    try:
        tol_val = float(tol_num_str)
    except ValueError:
        tol_val = 1e-9

    return tol_val, rounding_mode


def load_evidence_index_ids(evidence_index_path: str) -> Set[str]:
    """从 evidence-index.md 中解析所有有效的 evidence_id"""
    if not os.path.exists(evidence_index_path):
        return set()

    with open(evidence_index_path, "r", encoding="utf-8") as f:
        content = f.read()

    ids = set()
    # 匹配 YAML / 字段式: evidence_id: EVID-001 或 - evidence_id: EVID-001
    for match in re.finditer(r"(?:^|\s|- )evidence_id\s*:\s*([A-Za-z0-9_-]+)", content):
        ids.add(match.group(1).strip())

    # 匹配 Markdown 表格式: | EVID-001 | 或 | evidence_id | ...
    for line in content.splitlines():
        line_s = line.strip()
        if line_s.startswith("|") and not line_s.startswith("|---"):
            cells = [c.strip() for c in line_s.split("|")[1:-1]]
            for c in cells:
                if re.match(r"^EVID-[A-Za-z0-9_-]+$", c):
                    ids.add(c)
                elif re.match(r"^[A-Za-z0-9_]+-[0-9]+$", c):
                    ids.add(c)

    return ids


def load_datatable_rows(datatable_path: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    加载数据底表文件，兼容 CSV 与 Markdown 表格。
    返回: (rows_list, headers_list)
    """
    if not os.path.exists(datatable_path):
        raise FileNotFoundError(f"Datatable file not found: {datatable_path}")

    is_md = datatable_path.lower().endswith((".md", ".markdown"))

    with open(datatable_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    rows: List[Dict[str, str]] = []
    headers: List[str] = []

    if is_md:
        # Markdown 表格解析
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        table_lines = [l for l in lines if l.startswith("|")]
        if table_lines:
            header_line = table_lines[0]
            headers = [c.strip() for c in header_line.split("|")[1:-1]]
            for line_idx, line in enumerate(table_lines[1:], start=2):
                if line.startswith("|---") or line.startswith("|:--"):
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= len(headers):
                    row_dict = {headers[i]: cells[i] for i in range(len(headers))}
                    row_dict["__line_number__"] = str(line_idx)
                    rows.append(row_dict)
    else:
        # CSV 解析
        reader = csv.reader(content.splitlines())
        raw_rows = []
        for line_idx, row in enumerate(reader, start=1):
            if not row or (len(row) == 1 and not row[0].strip()) or row[0].strip().startswith("#"):
                continue
            raw_rows.append((line_idx, [c.strip() for c in row]))

        if raw_rows:
            headers = raw_rows[0][1]
            for line_idx, r in raw_rows[1:]:
                row_dict = {}
                for idx, h in enumerate(headers):
                    val = r[idx] if idx < len(r) else ""
                    row_dict[h] = val
                row_dict["__line_number__"] = str(line_idx)
                rows.append(row_dict)

    return rows, headers


def run_audit(
    datatable_path: str,
    strict_tolerance: bool = False,
    evidence_index_path: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    核心核验主入口：
    返回 (exit_code, result_dict)
    """
    try:
        rows, headers = load_datatable_rows(datatable_path)
    except Exception as e:
        return 1, {
            "checked_cells": 0,
            "errors": [f"Failed to read datatable: {str(e)}"],
            "mismatches": [],
            "cross_scope_violations": [],
            "unlinked_cells": [],
            "missing_assumption_tags": [],
        }

    valid_evidence_ids = set()
    if evidence_index_path:
        valid_evidence_ids = load_evidence_index_ids(evidence_index_path)

    # 1. 建立 item 映射表
    item_by_id: Dict[str, Dict[str, Any]] = {}
    var_to_item_id: Dict[str, str] = {}
    env_values: Dict[str, float] = {}
    value_to_calibers: Dict[float, Set[str]] = {}

    for idx, row in enumerate(rows, start=1):
        item_id = row.get("item_id", "").strip()
        if not item_id:
            continue

        raw_val = row.get("value", "").strip().rstrip("%")
        try:
            num_val = float(raw_val)
        except ValueError:
            num_val = 0.0

        caliber = row.get("caliber", "").strip().upper()
        item_by_id[item_id] = {
            "row_idx": int(row.get("__line_number__", idx + 1)),
            "item_id": item_id,
            "label": row.get("label", "").strip(),
            "value": num_val,
            "raw_value": row.get("value", "").strip(),
            "unit": row.get("unit", "").strip(),
            "source_type": row.get("source_type", "").strip().lower(),
            "source_ref": row.get("source_ref", "").strip(),
            "expected_expression": row.get("expected_expression", "").strip(),
            "tolerance": row.get("tolerance", "").strip(),
            "caliber": caliber,
            "assumption_tag": row.get("assumption_tag", "").strip(),
        }

        var_name = sanitize_item_id_for_var(item_id)
        var_to_item_id[var_name] = item_id
        env_values[var_name] = num_val

        # 也允许直接使用原名（如果已是合法标识符）
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", item_id):
            env_values[item_id] = num_val
            var_to_item_id[item_id] = item_id

        # 记录数值到口径的映射（排除通用/空口径）
        if caliber and caliber.lower() not in IGNORED_CALIBERS:
            if num_val not in value_to_calibers:
                value_to_calibers[num_val] = set()
            value_to_calibers[num_val].add(caliber)

    checked_cells_count = 0
    mismatches: List[Dict[str, Any]] = []
    cross_scope_violations: List[Dict[str, Any]] = []
    missing_assumption_tags: List[Dict[str, Any]] = []
    unlinked_cells: List[Dict[str, Any]] = []
    errors: List[str] = []

    # 2. 逐行核验
    for row in rows:
        item_id = row.get("item_id", "").strip()
        if not item_id or item_id not in item_by_id:
            continue

        item_data = item_by_id[item_id]
        row_idx = item_data["row_idx"]
        source_type = item_data["source_type"]
        source_ref = item_data["source_ref"]
        assumption_tag = item_data["assumption_tag"]
        caliber = item_data["caliber"]
        expr_raw = item_data["expected_expression"]
        tol_raw = item_data["tolerance"]
        actual_val = item_data["value"]

        # A. 裸数字与假设 tag 检查
        if source_type == "estimated":
            if not assumption_tag:
                missing_assumption_tags.append({
                    "row": row_idx,
                    "col": "assumption_tag",
                    "item_id": item_id,
                    "error": "bare_estimate",
                    "message": f"Item '{item_id}' has source_type=estimated but assumption_tag is empty",
                })
                errors.append(f"Row {row_idx} ({item_id}): bare estimate without assumption_tag")

        # B. 证据引用与有效性检查
        if not source_ref:
            unlinked_cells.append({
                "row": row_idx,
                "col": "source_ref",
                "item_id": item_id,
                "error": "missing_source",
                "message": f"Item '{item_id}' has empty source_ref",
            })
            errors.append(f"Row {row_idx} ({item_id}): missing source_ref")
        elif evidence_index_path:
            refs = [r.strip() for r in re.split(r"[,;]\s*", source_ref) if r.strip()]
            for ref in refs:
                if ref not in valid_evidence_ids:
                    unlinked_cells.append({
                        "row": row_idx,
                        "col": "source_ref",
                        "item_id": item_id,
                        "source_ref": ref,
                        "error": "unlinked_evidence",
                        "message": f"Item '{item_id}' references unknown evidence_id '{ref}' in {evidence_index_path}",
                    })
                    errors.append(f"Row {row_idx} ({item_id}): unlinked evidence '{ref}'")

        # C. 公式复算与口径隔离检查
        if expr_raw:
            checked_cells_count += 1

            # 预处理表达式中的变量名（替换为合法标识符）
            processed_expr = expr_raw
            # 按 item_id 长度降序排序替换，防止前缀冲突
            sorted_items = sorted(item_by_id.keys(), key=lambda x: len(x), reverse=True)
            for itm in sorted_items:
                vname = sanitize_item_id_for_var(itm)
                if itm != vname:
                    # 使用正则边界替换中划线等特殊格式的 item_id
                    pattern = r"(?<![A-Za-z0-9_-])" + re.escape(itm) + r"(?![A-Za-z0-9_-])"
                    processed_expr = re.sub(pattern, vname, processed_expr)

            # 解析 AST
            try:
                parsed_ast = ast.parse(processed_expr, mode="eval")
            except SyntaxError as se:
                errors.append(f"Row {row_idx} ({item_id}): formula syntax error '{expr_raw}': {str(se)}")
                mismatches.append({
                    "row": row_idx,
                    "col": "expected_expression",
                    "item_id": item_id,
                    "expected": "valid_syntax",
                    "actual": expr_raw,
                    "diff": None,
                    "error": "syntax_error",
                })
                continue

            # 提取表达式中涉及的变量
            referenced_vars = extract_var_names(parsed_ast)
            referenced_calibers: Set[str] = set()
            referenced_items: List[str] = []

            for var_name in referenced_vars:
                ref_id = var_to_item_id.get(var_name)
                if ref_id and ref_id in item_by_id:
                    referenced_items.append(ref_id)
                    cal = item_by_id[ref_id]["caliber"]
                    if cal and cal.lower() not in IGNORED_CALIBERS:
                        referenced_calibers.add(cal)

            # 口径隔离判定 1：公式引用的不同变量口径不同（如 A vs B）
            cross_scope_detected = False
            calibers_list = sorted(referenced_calibers)
            if len(calibers_list) > 1:
                cross_scope_detected = True

            # 口径隔离判定 2：当前行口径与所引用变量口径冲突
            if caliber and caliber.lower() not in IGNORED_CALIBERS:
                for c in referenced_calibers:
                    if c != caliber:
                        cross_scope_detected = True
                        if c not in calibers_list:
                            calibers_list.append(c)

            # 口径隔离判定 3：常量比对（公式中使用了属于不同口径的数值常数进行运算）
            if not cross_scope_detected and (strict_tolerance or len(referenced_calibers) == 0):
                # 遍历 AST 中的常量数字
                constant_calibers: Set[str] = set()
                for subnode in ast.walk(parsed_ast):
                    if isinstance(subnode, ast.Constant) and isinstance(subnode.value, (int, float)):
                        c_val = float(subnode.value)
                        if c_val in value_to_calibers:
                            constant_calibers.update(value_to_calibers[c_val])
                if len(constant_calibers) > 1:
                    cross_scope_detected = True
                    calibers_list = sorted(constant_calibers)

            # 口径隔离判定 4：显式 cross_scope 标记或不同口径标签加减
            if "cross_caliber" in expr_raw.lower() or "cross_scope" in expr_raw.lower():
                cross_scope_detected = True

            if cross_scope_detected:
                cross_scope_violations.append({
                    "row": row_idx,
                    "col": "expected_expression",
                    "item_id": item_id,
                    "error": "cross_caliber",
                    "calibers": calibers_list,
                    "expression": expr_raw,
                    "message": f"Scope isolation violation: cross-caliber arithmetic detected across calibers {calibers_list} in item {item_id}",
                })
                errors.append(f"Row {row_idx} ({item_id}): cross-caliber arithmetic between {calibers_list}")

            # 执行安全表达式求值
            try:
                computed_val = safe_eval_ast(parsed_ast, env_values)
            except Exception as eval_err:
                errors.append(f"Row {row_idx} ({item_id}): evaluation error in '{expr_raw}': {str(eval_err)}")
                mismatches.append({
                    "row": row_idx,
                    "col": "expected_expression",
                    "item_id": item_id,
                    "expected": "eval_success",
                    "actual": str(eval_err),
                    "diff": None,
                    "error": "eval_error",
                })
                continue

            # 容差判定
            tol_val, rounding_mode = parse_tolerance_spec(tol_raw, actual_val)
            if strict_tolerance:
                # 严格模式下，若未显式指定容差且为浮点数，强制要求 1e-9 容差
                if not tol_raw and not actual_val.is_integer():
                    tol_val = 1e-9

            diff = abs(computed_val - actual_val)
            # 允许标准浮点 epsilon 兜底
            if diff > (tol_val + 1e-12):
                mismatches.append({
                    "row": row_idx,
                    "col": "value",
                    "item_id": item_id,
                    "expected": round(computed_val, 8) if isinstance(computed_val, float) else computed_val,
                    "actual": actual_val,
                    "diff": round(diff, 8),
                    "tolerance": tol_val,
                    "expression": expr_raw,
                })
                errors.append(
                    f"Row {row_idx} ({item_id}): calculation mismatch! Expected {computed_val}, actual {actual_val}, diff {diff} > tol {tol_val}"
                )

    # 3. 汇总判定出口
    has_mismatch = len(mismatches) > 0
    has_cross_scope = len(cross_scope_violations) > 0
    has_missing_assumption = len(missing_assumption_tags) > 0
    has_unlinked = len(unlinked_cells) > 0
    has_errors = len(errors) > 0

    exit_code = 0
    if has_mismatch or has_cross_scope or has_missing_assumption or has_unlinked or has_errors:
        exit_code = 1

    # 4. 根据调用形态组装返回 JSON
    if evidence_index_path:
        # CRITERION M4-2 形态: {"unlinked_cells":[],"missing_assumption_tags":[]}
        output_payload: Dict[str, Any] = {
            "unlinked_cells": unlinked_cells,
            "missing_assumption_tags": missing_assumption_tags,
        }
        if exit_code != 0:
            output_payload["checked_cells"] = checked_cells_count
            output_payload["mismatches"] = mismatches
            output_payload["cross_scope_violations"] = cross_scope_violations
            output_payload["errors"] = errors
    elif strict_tolerance:
        # CRITERION M4-3 形态: {"checked_cells":N,"cross_scope_violations":[]}
        output_payload = {
            "checked_cells": checked_cells_count,
            "cross_scope_violations": cross_scope_violations,
        }
        if exit_code != 0:
            output_payload["mismatches"] = mismatches
            output_payload["missing_assumption_tags"] = missing_assumption_tags
            output_payload["unlinked_cells"] = unlinked_cells
            output_payload["errors"] = errors
    else:
        # CRITERION M4-1 形态: {"checked_cells":N,"mismatches":[]}
        output_payload = {
            "checked_cells": checked_cells_count,
            "mismatches": mismatches,
        }
        if exit_code != 0:
            output_payload["cross_scope_violations"] = cross_scope_violations
            output_payload["missing_assumption_tags"] = missing_assumption_tags
            output_payload["unlinked_cells"] = unlinked_cells
            output_payload["errors"] = errors

    return exit_code, output_payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="audit_calc.py - 数据底表纯代码算术复算与口径隔离核验工具"
    )
    parser.add_argument("datatable", help="Path to datatable CSV or Markdown file")
    parser.add_argument(
        "--strict-tolerance",
        action="store_true",
        help="Enforce strict tolerance and cross-scope isolation checks",
    )
    parser.add_argument(
        "--evidence-index",
        dest="evidence_index",
        default=None,
        help="Path to evidence-index.md for citation verification",
    )

    args = parser.parse_args()

    exit_code, result = run_audit(
        datatable_path=args.datatable,
        strict_tolerance=args.strict_tolerance,
        evidence_index_path=args.evidence_index,
    )

    # 规范：输出单行纯 JSON
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
