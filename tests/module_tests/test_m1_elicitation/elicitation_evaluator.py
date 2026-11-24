#!/usr/bin/env python3
"""
elicitation_evaluator.py - M1 落地澄清决策树与 Frontier 计算执行器

纯 Python 3 标准库实现。
用于黑箱评估输入材料对八项核心澄清维度的覆盖度，依据 DAG 计算待澄清 Active Frontier 队列，
并为就绪的待澄清维度生成附带推荐选项 (2-4 项 + Other) 的问题结构。
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Set, Tuple


# 澄清八项元数据与依赖定义
DIMENSIONS = {
    "D1_subject": {
        "id": "D1",
        "name": "研究标的与对象 (Subject Entity)",
        "fields": ["subject_name", "scope_boundaries"],
        "depends_on": [],
        "options": [
            "标的：中国大模型与算力企业出海样例法域；边界：聚焦样例市/样例港云节点建设与合规牌照",
            "标的：东南亚中资跨境电商算力出海；边界：聚焦印尼与新加坡数据合规",
            "标的：全球开源大模型商业化可行性；边界：聚焦 2026 年欧美合规政策",
        ],
    },
    "D2_background": {
        "id": "D2",
        "name": "项目背景与历史上下文 (Background Context)",
        "fields": ["context_summary", "inherited_materials"],
        "depends_on": ["D1_subject"],
        "options": [
            "新业务样例区域出海规划，需全新论证；无前序继承资料",
            "接手既有样例法域试点方案，需基于 2026 最新政策与电费重新复核",
            "应对高层决策委员会投资审查，需事实穿透核验",
        ],
    },
    "D3_readers": {
        "id": "D3",
        "name": "报告受众与偏好 (Target Readers)",
        "fields": ["primary_readers", "reader_preferences"],
        "depends_on": ["D1_subject", "D2_background"],
        "options": [
            "受众：CEO/投资委员会；偏好：投资回报测算、合规终局风险与可行性",
            "受众：法务总监/合规专委会；偏好：样例法域 样例数据保护法/SCA 牌照与罚则红线",
            "受众：技术总监/首席架构师；偏好：网络出境延迟、IDC 机房 PUE 与供电",
        ],
    },
    "D4_style": {
        "id": "D4",
        "name": "风格与基调 (Tone & Style)",
        "fields": ["style_mode", "perspective"],
        "depends_on": ["D3_readers"],
        "options": [
            "严谨深度剖析 + 独立第三方中立立场 (rigorous_analytical + third_party_neutral)",
            "高管决策导向 + 战略参谋建议立场 (executive_brief + strategic_advisor)",
            "风险穿透审计 + 红蓝对抗审查立场 (adversarial_audit + third_party_neutral)",
        ],
    },
    "D5_format": {
        "id": "D5",
        "name": "交付形态与格式约定 (Format Contract)",
        "fields": ["primary_format", "pagination_limit"],
        "depends_on": ["D4_style"],
        "options": [
            "格式：标准排版 DOCX (附自动生成 PDF)；篇幅：严谨详尽版（以事实闭环为准）",
            "格式：高管精要 PDF (单源 Markdown 直转)；篇幅：控制在 30 页以内",
            "格式：纯 Markdown 母本；篇幅：不设硬性限制",
        ],
    },
    "D6_delivery_path": {
        "id": "D6",
        "name": "交付目的地 (Delivery Path)",
        "fields": ["target_local_dir", "target_delivery_dir"],
        "depends_on": ["D5_format"],
        "options": [
            "本地根目录：./output；交付件目录：./output/delivery",
            "本地根目录：/home/ubuntu/workspace/sample_report；交付件目录：/home/ubuntu/workspace/sample_report/final",
            "本地根目录：./artifacts；交付件目录：./artifacts/release",
        ],
    },
    "D7_online_baseline": {
        "id": "D7",
        "name": "在线载体基准判定 (Online Baseline Rule)",
        "fields": ["online_enabled", "source_of_truth", "sync_policy"],
        "depends_on": ["D5_format", "D6_delivery_path"],
        "options": [
            "本地 Git 优先 (LOCAL_GIT_FIRST)；在线文档仅作为镜像或附件",
            "纯本地文件系统独占 (online_enabled: false)",
            "在线云优先 (REMOTE_ONLINE_FIRST)；本地物料作为阶段备份镜像",
        ],
    },
    "D8_interaction": {
        "id": "D8",
        "name": "人机交互与问询模式 (Interaction Mode)",
        "fields": ["interaction_mode", "interruption_threshold"],
        "depends_on": ["D3_readers", "D7_online_baseline"],
        "options": [
            "极简免打扰模式 (minimal_interruption)：仅在 G 级人审门禁与定性裁决中断",
            "同步交互模式 (synchronous_frontier)：在每个阶段汇合点主动输出进展简讯",
        ],
    },
}


def evaluate_elicitation(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据输入数据计算各维度状态及待澄清 Active Frontier。
    """
    resolved_dim_keys: Set[str] = set()
    missing_fields_by_dim: Dict[str, List[str]] = {}

    for dim_key, dim_meta in DIMENSIONS.items():
        missing_fields = []
        for field in dim_meta["fields"]:
            val = user_data.get(field)
            if val is None or val == "" or val == "待定":
                missing_fields.append(field)
        if not missing_fields:
            resolved_dim_keys.add(dim_key)
        else:
            missing_fields_by_dim[dim_key] = missing_fields

    # 计算 Active Frontier：前置依赖全为 RESOLVED 且自身未 RESOLVED
    active_frontier = []
    all_unresolved = []

    for dim_key, dim_meta in DIMENSIONS.items():
        if dim_key in resolved_dim_keys:
            continue
        all_unresolved.append({
            "dimension_key": dim_key,
            "id": dim_meta["id"],
            "name": dim_meta["name"],
            "missing_fields": missing_fields_by_dim[dim_key],
            "prerequisites_met": all(dep in resolved_dim_keys for dep in dim_meta["depends_on"]),
        })

    for dim_key, dim_meta in DIMENSIONS.items():
        if dim_key in resolved_dim_keys:
            continue
        deps_met = all(dep in resolved_dim_keys for dep in dim_meta["depends_on"])
        if deps_met:
            frontier_item = {
                "id": dim_meta["id"],
                "dimension_key": dim_key,
                "name": dim_meta["name"],
                "missing_fields": missing_fields_by_dim[dim_key],
                "recommended_options": dim_meta["options"] + ["[Other] 自定义补充输入"],
                "options_count": len(dim_meta["options"]) + 1,
            }
            active_frontier.append(frontier_item)

    is_complete = len(resolved_dim_keys) == len(DIMENSIONS)

    return {
        "total_dimensions": len(DIMENSIONS),
        "resolved_count": len(resolved_dim_keys),
        "unresolved_count": len(DIMENSIONS) - len(resolved_dim_keys),
        "is_complete": is_complete,
        "resolved_dimensions": sorted(list(resolved_dim_keys)),
        "all_unresolved_dimensions": all_unresolved,
        "active_frontier": active_frontier,
        "next_question": active_frontier[0] if active_frontier else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate elicitation input and compute frontier queue")
    parser.add_argument("--input", required=True, help="Path to input JSON file with provided clarifications")
    parser.add_argument("--output", help="Optional path to output frontier JSON")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.stderr.write(f"Error: input file {args.input} not found\n")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = evaluate_elicitation(data)

    output_str = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str + "\n")
    else:
        sys.stdout.write(output_str + "\n")


if __name__ == "__main__":
    main()
