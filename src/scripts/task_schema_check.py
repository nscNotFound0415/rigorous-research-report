#!/usr/bin/env python3
"""
task_schema_check.py - 调研任务配置合规性、guidelines 数据三要素、REQ-ID 覆盖率与 DAG 无环性校验工具

符合 OpenSpec 规格与《复杂调研报告写作 AI Skill 建设方案 (v2.1)》§1.2 M3 与 §1.3 契约。
纯 Python 3 标准库实现，零第三方依赖，无外网访问，无跨调用状态残留。

CLI 契约:
  1. python3 scripts/task_schema_check.py task.json --schema schemas/task.schema.json
     -> 校验 JSON Schema 规范、字段有效性与 DAG 无环性（有环时 errors 输出环路径）；
        同时校验 guidelines 数据三要素，合规时输出: {"errors":[],"guidelines_validated":true}，退出码 0/1。
  2. python3 scripts/task_schema_check.py task.json --req-index brief.md --coverage
     -> 比对 brief.md §2.9 诉求索引与 task.json target_req_ids 集合；
        100% 覆盖时输出: {"uncovered_req_ids":[],"coverage_ratio":1.0}，退出码 0；存在未覆盖时退出码 1。
  3. python3 scripts/task_schema_check.py task.json --guidelines-check
     -> 专项目标校验 guidelines 数据三要素（出处、基准日、口径/单位），退出码 0/1。
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# 1. 辅助与 JSON 输出统一函数
# ==============================================================================

def emit_json_and_exit(payload: Dict[str, Any], exit_code: int) -> None:
    """标准单行 JSON 输出并以此退出码结束进程"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


# ==============================================================================
# 2. JSON Schema 纯标准库轻量校验器
# ==============================================================================

VALID_SOURCE_TYPES = {"measured", "derived", "estimated", "quoted"}


def load_json_file(file_path: str) -> Tuple[Optional[Any], Optional[str]]:
    """加载 JSON 文件，返回 (parsed_data, error_message)"""
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data, None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON syntax in {file_path}: {exc}"
    except Exception as exc:
        return None, f"Error reading {file_path}: {exc}"


def validate_task_item_structure(item: Any, item_index: int, errors: List[str]) -> None:
    """校验单个 task 项的基础字段类型与业务规则"""
    prefix = f"Task[{item_index}]"
    if not isinstance(item, dict):
        errors.append(f"{prefix}: Must be an object, got {type(item).__name__}")
        return

    task_id = item.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        errors.append(f"{prefix}: 'task_id' must be a non-empty string")
    else:
        prefix = f"Task '{task_id}'"
        if not re.match(r"^[A-Za-z0-9_-]+$", task_id):
            errors.append(f"{prefix}: 'task_id' contains invalid characters (must match ^[A-Za-z0-9_-]+$)")

    sub_topic = item.get("sub_topic")
    if not isinstance(sub_topic, str) or not sub_topic.strip():
        errors.append(f"{prefix}: 'sub_topic' must be a non-empty string")

    perspective = item.get("perspective")
    if not isinstance(perspective, str) or not perspective.strip():
        errors.append(f"{prefix}: 'perspective' must be a non-empty string")

    target_req_ids = item.get("target_req_ids")
    if not isinstance(target_req_ids, list) or len(target_req_ids) == 0:
        errors.append(f"{prefix}: 'target_req_ids' must be a non-empty array of REQ-IDs")
    else:
        for req_idx, req in enumerate(target_req_ids):
            if not isinstance(req, str) or not re.match(r"^REQ-[A-Za-z0-9_-]+$", req):
                errors.append(f"{prefix}: target_req_ids[{req_idx}] '{req}' is not a valid REQ-ID format")

    guidelines = item.get("guidelines")
    if not isinstance(guidelines, list) or len(guidelines) == 0:
        errors.append(f"{prefix}: 'guidelines' must be a non-empty array of strings")
    else:
        for g_idx, g in enumerate(guidelines):
            if not isinstance(g, str) or not g.strip():
                errors.append(f"{prefix}: guidelines[{g_idx}] must be a non-empty string")

    output_path = item.get("output_path")
    if not isinstance(output_path, str) or not output_path.strip():
        errors.append(f"{prefix}: 'output_path' must be a non-empty string")

    dependencies = item.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append(f"{prefix}: 'dependencies' must be an array of task_id strings")
    else:
        for d_idx, dep in enumerate(dependencies):
            if not isinstance(dep, str):
                errors.append(f"{prefix}: dependencies[{d_idx}] must be a string")

    data_requirements = item.get("data_requirements")
    if not isinstance(data_requirements, list) or len(data_requirements) == 0:
        errors.append(f"{prefix}: 'data_requirements' must be a non-empty array of data requirement objects")
    else:
        for dr_idx, dr in enumerate(data_requirements):
            dr_prefix = f"{prefix}.data_requirements[{dr_idx}]"
            if not isinstance(dr, dict):
                errors.append(f"{dr_prefix}: Must be an object")
                continue
            source_type = dr.get("source_type")
            if source_type not in VALID_SOURCE_TYPES:
                errors.append(
                    f"{dr_prefix}: 'source_type' must be one of {sorted(list(VALID_SOURCE_TYPES))}, got '{source_type}'"
                )
            if source_type == "estimated":
                assumption_tag = dr.get("assumption_tag")
                if not isinstance(assumption_tag, str) or not assumption_tag.strip():
                    errors.append(
                        f"{dr_prefix}: When source_type is 'estimated', 'assumption_tag' must be a non-empty string"
                    )


def extract_task_list(data: Any) -> Tuple[Optional[List[Dict[str, Any]]], List[str]]:
    """从解析的 JSON 数据中提取任务项列表（支持顶层 tasks 数组或顶层数组）"""
    errors: List[str] = []
    if isinstance(data, dict):
        if "tasks" not in data:
            errors.append("Root object missing required property 'tasks'")
            return None, errors
        tasks = data.get("tasks")
        if not isinstance(tasks, list):
            errors.append("Property 'tasks' must be an array")
            return None, errors
        return tasks, errors
    elif isinstance(data, list):
        return data, errors
    else:
        errors.append(f"Root JSON must be an object or array, got {type(data).__name__}")
        return None, errors


def validate_schema(data: Any, schema_data: Optional[Dict[str, Any]] = None) -> List[str]:
    """对 task.json 实行全量结构校验与唯一性约束"""
    errors: List[str] = []

    tasks, extract_errors = extract_task_list(data)
    if extract_errors:
        return extract_errors

    if not tasks:
        errors.append("Task list is empty; at least one task is required")
        return errors

    seen_ids: Set[str] = set()
    for idx, item in enumerate(tasks):
        validate_task_item_structure(item, idx, errors)
        if isinstance(item, dict):
            task_id = item.get("task_id")
            if isinstance(task_id, str) and task_id.strip():
                if task_id in seen_ids:
                    errors.append(f"Duplicate task_id detected: '{task_id}'")
                seen_ids.add(task_id)

    # 如果有 _examples 字段，亦对其基础结构执行一致性检查
    if isinstance(data, dict) and "_examples" in data:
        examples = data.get("_examples")
        if isinstance(examples, list):
            for ex_idx, ex_item in enumerate(examples):
                validate_task_item_structure(ex_item, f"_example_{ex_idx}", errors)
        elif examples is not None:
            errors.append("Property '_examples' must be an array if provided")

    return errors


# ==============================================================================
# 3. DAG 有向无环图与依赖闭环校验
# ==============================================================================

def validate_dag(tasks: List[Dict[str, Any]]) -> Tuple[List[str], Optional[List[str]]]:
    """
    校验任务依赖图的完整性与有向无环性（DAG）。
    返回: (errors, detected_cycle_path)
    """
    errors: List[str] = []
    task_map: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        if isinstance(t, dict) and "task_id" in t and isinstance(t["task_id"], str):
            task_map[t["task_id"]] = t

    all_ids = set(task_map.keys())

    # 1. 检查是否存在悬空依赖（引用了不存在的 task_id）
    for t_id, item in task_map.items():
        deps = item.get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, str) and dep not in all_ids:
                    errors.append(f"Task '{t_id}' depends on non-existent task '{dep}'")

    if errors:
        return errors, None

    # 2. DFS 检测环路
    # 状态: 0 = unvisited, 1 = visiting (in call stack), 2 = visited
    state: Dict[str, int] = {t_id: 0 for t_id in all_ids}
    cycle_path: Optional[List[str]] = None

    def dfs(curr: str, path: List[str]) -> bool:
        nonlocal cycle_path
        state[curr] = 1
        path.append(curr)

        deps = task_map.get(curr, {}).get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                if not isinstance(dep, str):
                    continue
                if state.get(dep, 0) == 1:
                    # 发现环，截取环路径
                    try:
                        idx = path.index(dep)
                        cycle_path = path[idx:] + [dep]
                    except ValueError:
                        cycle_path = [curr, dep, curr]
                    return True
                elif state.get(dep, 0) == 0:
                    if dfs(dep, path):
                        return True

        path.pop()
        state[curr] = 2
        return False

    for t_id in sorted(list(all_ids)):
        if state[t_id] == 0:
            if dfs(t_id, []):
                break

    if cycle_path:
        cycle_str = " -> ".join(cycle_path)
        errors.append(f"Circular dependency detected in tasks: {cycle_str}")
        return errors, cycle_path

    return [], None


# ==============================================================================
# 4. Guidelines 数据三要素检查器
# ==============================================================================

SOURCE_KEYWORDS = [
    "来源", "出处", "信源", "一手", "官方", "引用",
    "source", "provenance", "url", "citation", "document"
]
DATE_KEYWORDS = [
    "取价日", "基准日", "时间", "日期", "年份", "周期", "季度",
    "date", "time", "pricing", "timestamp", "benchmark_date"
]
METRIC_KEYWORDS = [
    "口径", "标准", "指标", "统计", "单位",
    "metric", "standard", "unit", "usd", "sar", "cny", "kwh", "pue", "tco", "token"
]


def check_task_guidelines_essentials(guidelines: List[str]) -> List[str]:
    """
    检查单个任务的 guidelines 列表是否覆盖数据三要素：
    1. 来源出处 (source provenance / URL)
    2. 取价日/基准时间 (pricing date / timestamp)
    3. 统计口径与单位 (metric standard / unit)
    返回缺失的三要素名称列表（全部满足则返回空列表）。
    """
    combined_text = " ".join(guidelines).lower()

    missing: List[str] = []

    has_source = any(kw in combined_text for kw in SOURCE_KEYWORDS)
    if not has_source:
        missing.append("source_provenance")

    has_date = any(kw in combined_text for kw in DATE_KEYWORDS)
    if not has_date:
        missing.append("pricing_date")

    has_metric = any(kw in combined_text for kw in METRIC_KEYWORDS)
    if not has_metric:
        missing.append("metric_unit")

    return missing


def validate_all_guidelines(tasks: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    对全部 task 执行 guidelines 校验。
    返回: (errors, offending_tasks_list)
    """
    errors: List[str] = []
    offending_tasks: List[Dict[str, Any]] = []

    for t in tasks:
        if not isinstance(t, dict):
            continue
        t_id = t.get("task_id", "UNKNOWN_TASK")
        guidelines = t.get("guidelines")

        if not isinstance(guidelines, list) or len(guidelines) == 0:
            errors.append(f"Task '{t_id}': 'guidelines' must be a non-empty array")
            offending_tasks.append({
                "task_id": t_id,
                "missing_essentials": ["empty_guidelines"]
            })
            continue

        missing = check_task_guidelines_essentials(guidelines)
        if missing:
            errors.append(
                f"Task '{t_id}' guidelines missing essential assertion(s): {', '.join(missing)}"
            )
            offending_tasks.append({
                "task_id": t_id,
                "missing_essentials": missing
            })

    return errors, offending_tasks


# ==============================================================================
# 5. brief.md REQ-ID 索引解析与覆盖率核验
# ==============================================================================

def extract_req_ids_from_brief(brief_path: str) -> Tuple[Set[str], Optional[str]]:
    """
    解析 brief.md 文件中的「### 2.9 诉求与实体索引」小节，提取全部 REQ-ID 集合。
    """
    if not os.path.exists(brief_path):
        return set(), f"Brief file not found: {brief_path}"

    try:
        with open(brief_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        return set(), f"Error reading brief file: {exc}"

    # 匹配 2.9 诉求与实体索引 到下一个 2.10 或 3. 项目宪法 或其他二级/三级标题
    section_pattern = r"(?:###\s*2\.9[^\n]*\n)(.*?)(?=\n###|\n##|\Z)"
    match = re.search(section_pattern, content, flags=re.DOTALL)
    if not match:
        # 兼容只写 2.9 的情况
        fallback_pattern = r"(?:2\.9\s*诉求与实体索引[^\n]*\n)(.*?)(?=\n###|\n##|\Z)"
        match = re.search(fallback_pattern, content, flags=re.DOTALL)

    if not match:
        return set(), "Section '2.9 诉求与实体索引' not found in brief.md"

    section_text = match.group(1)
    req_ids = set(re.findall(r"\b(REQ-[A-Za-z0-9_-]+)\b", section_text))
    if not req_ids:
        return set(), "No REQ-IDs found in section 2.9 of brief.md"

    return req_ids, None


def validate_req_coverage(tasks: List[Dict[str, Any]], brief_path: str) -> Tuple[Dict[str, Any], int]:
    """
    核验 task.json 对 brief.md REQ-ID 的覆盖率。
    返回: (payload, exit_code)
    """
    brief_reqs, brief_err = extract_req_ids_from_brief(brief_path)
    if brief_err:
        return {"uncovered_req_ids": [], "coverage_ratio": 0.0, "errors": [brief_err]}, 1

    # 提取 task.json 中出现的全部 target_req_ids
    task_reqs: Set[str] = set()
    for t in tasks:
        if isinstance(t, dict):
            for req in t.get("target_req_ids", []):
                if isinstance(req, str):
                    task_reqs.add(req.strip())

    uncovered = sorted(list(brief_reqs - task_reqs))
    total_brief = len(brief_reqs)
    covered_count = len(brief_reqs & task_reqs)
    coverage_ratio = round(covered_count / total_brief, 4) if total_brief > 0 else 1.0

    if not uncovered and coverage_ratio >= 1.0:
        return {"uncovered_req_ids": [], "coverage_ratio": 1.0}, 0
    else:
        return {
            "uncovered_req_ids": uncovered,
            "coverage_ratio": coverage_ratio,
            "errors": [f"Uncovered REQ-IDs: {', '.join(uncovered)}"]
        }, 1


# ==============================================================================
# 6. 主 CLI 调度逻辑
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="M3 Task Schema, DAG, Guidelines and REQ Coverage Verifier"
    )
    parser.add_argument("task_file", help="Path to task.json file")
    parser.add_argument("--schema", help="Path to schemas/task.schema.json schema file")
    parser.add_argument("--req-index", help="Path to brief.md to read requirement indices")
    parser.add_argument("--coverage", action="store_true", help="Perform REQ-ID coverage check against brief.md")
    parser.add_argument("--guidelines-check", action="store_true", help="Check guidelines data three essentials")

    args = parser.parse_args()

    # 1. 加载 task.json
    task_data, task_err = load_json_file(args.task_file)
    if task_err:
        emit_json_and_exit({"errors": [task_err]}, exit_code=1)

    tasks, extract_errors = extract_task_list(task_data)
    if extract_errors:
        emit_json_and_exit({"errors": extract_errors}, exit_code=1)

    # 2. 如果指定了覆盖率检查模式 (--req-index brief.md --coverage)
    if args.coverage or args.req_index:
        if not args.req_index:
            emit_json_and_exit(
                {"uncovered_req_ids": [], "coverage_ratio": 0.0, "errors": ["--req-index <brief.md> is required for coverage check"]},
                exit_code=1
            )
        coverage_payload, cov_exit_code = validate_req_coverage(tasks, args.req_index)
        emit_json_and_exit(coverage_payload, exit_code=cov_exit_code)

    # 3. 如果指定了专有 --guidelines-check (且未指定 --schema)
    if args.guidelines_check and not args.schema:
        g_errors, offending = validate_all_guidelines(tasks)
        if g_errors:
            emit_json_and_exit({
                "errors": g_errors,
                "guidelines_validated": False,
                "offending_tasks": offending
            }, exit_code=1)
        else:
            emit_json_and_exit({
                "errors": [],
                "guidelines_validated": True
            }, exit_code=0)

    # 4. 默认/Schema 校验流程 (--schema schemas/task.schema.json)
    all_errors: List[str] = []
    cycle_info: Optional[List[str]] = None
    offending_guidelines: List[Dict[str, Any]] = []

    # 4.1 Schema 文件加载与验证
    if args.schema:
        schema_data, schema_err = load_json_file(args.schema)
        if schema_err:
            emit_json_and_exit({"errors": [schema_err]}, exit_code=1)
        schema_errors = validate_schema(task_data, schema_data)
        all_errors.extend(schema_errors)
    else:
        # 未显式指定 schema 时亦执行基本任务对象结构检查
        all_errors.extend(validate_schema(task_data, None))

    # 4.2 DAG 有向无环性检查
    dag_errors, detected_cycle = validate_dag(tasks)
    if dag_errors:
        all_errors.extend(dag_errors)
        cycle_info = detected_cycle

    # 4.3 Guidelines 数据三要素检查
    g_errors, offending = validate_all_guidelines(tasks)
    if g_errors:
        all_errors.extend(g_errors)
        offending_guidelines = offending

    # 4.4 组织输出与退出码
    if all_errors:
        out_payload: Dict[str, Any] = {"errors": all_errors}
        if cycle_info:
            out_payload["cycle"] = cycle_info
        if offending_guidelines:
            out_payload["offending_tasks"] = offending_guidelines
            out_payload["guidelines_validated"] = False
        emit_json_and_exit(out_payload, exit_code=1)
    else:
        emit_json_and_exit({
            "errors": [],
            "guidelines_validated": True
        }, exit_code=0)


if __name__ == "__main__":
    main()
