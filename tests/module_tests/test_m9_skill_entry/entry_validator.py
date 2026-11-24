#!/usr/bin/env python3
"""
entry_validator.py - SKILL.md 主入口契约与语法黑箱校验工具

职责：
  执行针对 src/SKILL.md 的独立确定性黑箱检验，包括：
  1. Frontmatter 字段集严格等于 5 个宿主安全键 (SAFE_FRONTMATTER_KEYS)
  2. 行数严格 < 200 行 (目标 120-170 行)
  3. 正文第一条为逐字触发控制硬规则
  4. 核心宪法五项底线常量逐字校验
  5. 四道人审门禁 (G0-G3) 与变更门禁及签署件路径契约
  6. 9 个 references 相对路径索引与存在性 / 待建状态核验
  7. 引用的 scripts/*.py 脚本存在性与待建清单核验
  8. 三边界复核出口条件 (D0=0, 四层回读, 人放行, BLOCKED_NO_REVIEWER)
  9. 可选增强层标注 (默认不启用)
  10. 禁用词与具体项目实例扫描

CLI 契约:
  python3 entry_validator.py --skill <path_to_SKILL.md>
  stdout: JSON 格式诊断信息
  退出码: 0 (校验通过) / 1 (校验失败)
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Any, Tuple

SAFE_FRONTMATTER_KEYS = {"name", "description", "when_to_use", "license", "metadata"}

MANDATORY_REFERENCES = [
    "references/P1_grill_me_protocol.md",
    "references/P2_governance_protocol.md",
    "references/P3_decomposition_guidelines.md",
    "references/P4_fact_finding_datatable.md",
    "references/P5_outline_gate.md",
    "references/P6_synthesis_delivery.md",
    "references/review_loop_engine.md",
    "references/change_circuit.md",
    "references/storage_adapters.md",
]

CONSTITUTION_CONSTANTS = [
    "事实判锤唯二通路",
    "定性裁决权归人类",
    "无隐藏状态",
    "非同族对抗复核且审者只读",
    "严禁跨口径相减",
]

MANDATORY_GATES = ["G0", "G1", "G2", "G3"]
GATE_APPROVAL_FILES = [
    "gates/G0-approval.md",
    "gates/G1-approval.md",
    "gates/G2-approval.md",
    "gates/G3-approval.md",
]

FORBIDDEN_WORDS = ["应当", "尽量", "注意"]
SPECIFIC_INSTANCES = ["样例法域", "词元"]
PLATFORM_NAMES = ["飞书", "钉钉", "Lark", "Notion", "企业微信", "WeCom", "Slack"]

TRIGGER_RULE_EXACT = (
    "本技能的启动前提是用户显式调用 /rigorous-research-report 或当轮明确要求按本流水线执行；"
    "若无该显式调用，立即输出「本技能需显式调用 /rigorous-research-report 启动」并停止，"
    "不得发起任何澄清提问、不得创建任何文件。"
)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str, List[str]]:
    """解析 Markdown frontmatter 与正文"""
    errors = []
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append("Missing starting frontmatter delimiter '---' at line 1")
        return {}, content, errors

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        errors.append("Missing ending frontmatter delimiter '---'")
        return {}, content, errors

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])

    # 简单逐行解析 YAML 顶层键
    fm_dict = {}
    current_key = None
    for line in fm_lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            current_key = key
            fm_dict[key] = val
        elif current_key and line.startswith("  "):
            # 子键/多行文本处理
            if isinstance(fm_dict[current_key], str):
                if fm_dict[current_key] == "":
                    fm_dict[current_key] = {}
            if isinstance(fm_dict[current_key], dict) and ":" in line:
                sub_parts = line.strip().split(":", 1)
                sub_key = sub_parts[0].strip()
                sub_val = sub_parts[1].strip()
                fm_dict[current_key][sub_key] = sub_val

    return fm_dict, body, errors


def validate_skill(skill_path: str, src_root: str = None) -> Dict[str, Any]:
    """对 SKILL.md 进行完整黑箱校验"""
    results: Dict[str, Any] = {
        "valid": False,
        "line_count": 0,
        "frontmatter_keys": [],
        "safe_keys_valid": False,
        "trigger_rule_valid": False,
        "negative_phrasing_valid": False,
        "constitution_constants_valid": False,
        "references_count": 0,
        "references_indexed": [],
        "unbuilt_references": [],
        "scripts_indexed": [],
        "unbuilt_scripts": [],
        "forbidden_words_found": [],
        "specific_instances_found": [],
        "platform_names_found": [],
        "gates_valid": False,
        "review_loop_exit_valid": False,
        "enhancement_layers_valid": False,
        "errors": [],
    }

    if not os.path.isfile(skill_path):
        results["errors"].append(f"SKILL file does not exist: {skill_path}")
        return results

    if src_root is None:
        src_root = os.path.dirname(os.path.abspath(skill_path))

    with open(skill_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    lines = raw_content.splitlines()
    line_count = len(lines)
    results["line_count"] = line_count

    # 1. 行数检查 (< 200)
    if line_count >= 200:
        results["errors"].append(f"Line count must be < 200 lines, got {line_count}")

    # 2. Frontmatter 检查
    fm_dict, body, fm_errors = parse_frontmatter(raw_content)
    if fm_errors:
        results["errors"].extend(fm_errors)
        return results

    fm_keys = set(fm_dict.keys())
    results["frontmatter_keys"] = sorted(list(fm_keys))

    if fm_keys == SAFE_FRONTMATTER_KEYS:
        results["safe_keys_valid"] = True
    else:
        diff_extra = fm_keys - SAFE_FRONTMATTER_KEYS
        diff_missing = SAFE_FRONTMATTER_KEYS - fm_keys
        if diff_extra:
            results["errors"].append(f"Frontmatter contains disallowed keys: {sorted(list(diff_extra))}")
        if diff_missing:
            results["errors"].append(f"Frontmatter is missing required keys: {sorted(list(diff_missing))}")

    # name 检查
    if fm_dict.get("name") != "rigorous-research-report":
        results["errors"].append(f"Frontmatter name must be 'rigorous-research-report', got '{fm_dict.get('name')}'")

    # description 检查 (显式否定句与典型触发场景)
    desc = str(fm_dict.get("description", ""))
    desc_has_negative = ("默认不触发" in desc) and ("必须由用户显式调用" in desc)
    desc_has_scenarios = any(s in desc for s in ["调研报告", "可行性报告", "行业研判", "尽调报告"])
    if not desc_has_negative:
        results["errors"].append("Frontmatter 'description' must contain '默认不触发，必须由用户显式调用'")
    if not desc_has_scenarios:
        results["errors"].append("Frontmatter 'description' must list typical trigger scenarios")

    # when_to_use 检查
    wtu = str(fm_dict.get("when_to_use", ""))
    wtu_has_negative = ("默认不触发" in wtu) or ("一律不使用" in wtu)
    wtu_has_explicit = "/rigorous-research-report" in wtu
    if not (wtu_has_negative and wtu_has_explicit):
        results["errors"].append("Frontmatter 'when_to_use' must contain negative phrasing and require explicit invocation")

    if desc_has_negative and wtu_has_negative:
        results["negative_phrasing_valid"] = True

    # 3. 正文第一条必须是触发控制硬规则
    body_stripped = body.strip()
    body_lines = [l.strip() for l in body_stripped.splitlines() if l.strip()]

    # 查找第一条实质规则
    first_rule_found = False
    for i, line in enumerate(body_lines):
        if "触发控制硬规则" in line:
            # 紧随其后的段落必须包含触发硬规则内容
            following_text = " ".join(body_lines[i + 1 : i + 4])
            if (
                "用户显式调用 /rigorous-research-report" in following_text
                and "立即输出" in following_text
                and "停止" in following_text
                and "不得发起任何澄清提问" in following_text
                and "不得创建任何文件" in following_text
            ):
                first_rule_found = True
                break

    if first_rule_found:
        results["trigger_rule_valid"] = True
    else:
        results["errors"].append("Body must begin with the trigger control hard rule containing all required fragments")

    # 4. 核心宪法五常量
    missing_constants = [c for c in CONSTITUTION_CONSTANTS if c not in raw_content]
    if missing_constants:
        results["errors"].append(f"Missing mandatory constitution constants: {missing_constants}")
    else:
        results["constitution_constants_valid"] = True

    # 5. 9 个 references 路径核验
    indexed_refs = []
    unbuilt_refs = []
    for ref in MANDATORY_REFERENCES:
        if ref in raw_content:
            indexed_refs.append(ref)
            # 检查在 src_root 下是否存在
            ref_path = os.path.join(src_root, ref.replace("references/", "references/"))
            if not os.path.isfile(ref_path):
                unbuilt_refs.append(ref)
        else:
            results["errors"].append(f"Missing mandatory reference in SKILL.md: {ref}")

    results["references_count"] = len(indexed_refs)
    results["references_indexed"] = indexed_refs
    results["unbuilt_references"] = unbuilt_refs

    # 6. scripts/*.py 脚本核验
    script_matches = re.findall(r"scripts/([a-zA-Z0-9_\-]+\.py)", raw_content)
    unique_scripts = sorted(list(set(script_matches)))
    indexed_scripts = []
    unbuilt_scripts = []
    for s in unique_scripts:
        script_rel = f"scripts/{s}"
        indexed_scripts.append(script_rel)
        full_script_path = os.path.join(src_root, script_rel)
        if not os.path.isfile(full_script_path):
            unbuilt_scripts.append(script_rel)

    results["scripts_indexed"] = indexed_scripts
    results["unbuilt_scripts"] = unbuilt_scripts

    # 7. 人审门禁与签署件路径
    gates_found = all(g in raw_content for g in MANDATORY_GATES)
    approval_files_found = all(af in raw_content for af in GATE_APPROVAL_FILES)
    change_approval_found = "gates/change-" in raw_content
    if gates_found and approval_files_found and change_approval_found:
        results["gates_valid"] = True
    else:
        if not gates_found:
            results["errors"].append("Missing one or more of G0-G3 gates in SKILL.md")
        if not (approval_files_found and change_approval_found):
            results["errors"].append("Missing required gates/*-approval.md paths in SKILL.md")

    # 8. 三边界复核出口条件
    has_d0 = ("D0" in raw_content and ("清零" in raw_content or "== 0" in raw_content or "= 0" in raw_content))
    has_readback = "四层回读" in raw_content
    has_human = "人类签署" in raw_content or "人放行" in raw_content
    has_blocked = "BLOCKED_NO_REVIEWER" in raw_content

    if has_d0 and has_readback and has_human and has_blocked:
        results["review_loop_exit_valid"] = True
    else:
        results["errors"].append("Review loop exit criteria must mention D0=0, four-layer readback, human approval, and BLOCKED_NO_REVIEWER")

    # 9. 可选增强层标注
    has_openspec_opt = "OpenSpec" in raw_content
    has_default_disabled = "默认不启用" in raw_content
    if has_openspec_opt and has_default_disabled:
        results["enhancement_layers_valid"] = True
    else:
        results["errors"].append("Optional enhancement layers must include OpenSpec and be marked '默认不启用'")

    # 10. 禁用词与实例词扫描
    # 扫描正文部分
    for word in FORBIDDEN_WORDS:
        if word in raw_content:
            results["forbidden_words_found"].append(word)
            results["errors"].append(f"Forbidden non-deterministic word '{word}' found in SKILL.md")

    for inst in SPECIFIC_INSTANCES:
        if inst in raw_content:
            results["specific_instances_found"].append(inst)
            results["errors"].append(f"Specific project instance word '{inst}' found in SKILL.md")

    for plat in PLATFORM_NAMES:
        if plat in raw_content:
            results["platform_names_found"].append(plat)
            results["errors"].append(f"Hardcoded platform name '{plat}' found in SKILL.md")

    if not results["errors"]:
        results["valid"] = True

    return results


def main():
    parser = argparse.ArgumentParser(description="SKILL.md Validator")
    parser.add_argument("--skill", default="src/SKILL.md", help="Path to SKILL.md")
    parser.add_argument("--src-root", default=None, help="Path to src root directory")
    args = parser.parse_args()

    skill_path = os.path.abspath(args.skill)
    src_root = os.path.abspath(args.src_root) if args.src_root else os.path.dirname(skill_path)

    res = validate_skill(skill_path, src_root)
    print(json.dumps(res, ensure_ascii=False, indent=2))

    if res["valid"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
