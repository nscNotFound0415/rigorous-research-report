#!/usr/bin/env python3
"""
adapter_git_sync.py - 本地 Git 载体同步、快照归档与差异校验工具

纯 Python 3 标准库实现，零第三方外部库依赖。
支持调用本地 git 命令，当 git 不可用或非 git 仓库时优雅降级输出 {"git":false,...} 而非崩溃。

CLI 契约:
    python3 scripts/adapter_git_sync.py --hash <file>
    python3 scripts/adapter_git_sync.py --root <dir> --snapshot <label> [--target <file_or_dir>]
    python3 scripts/adapter_git_sync.py --diff-mode --old <dir_or_file> --new <file> --declared <id>
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def compute_content_sha256(file_path: str) -> str:
    """计算物理文件的二进制 SHA-256 哈希"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_nettext_sha256(file_path: str) -> str:
    """
    计算 Markdown / 纯文本的净文本 (nettext) SHA-256 哈希。
    净文本规则：
    1. 统一 LF 换行，解码 UTF-8。
    2. 清除 HTML / Markdown 注释 <!-- ... -->。
    3. 行尾空白字符去除。
    4. 折叠连续空行，去除首尾空白。
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()

    # 1. 统一 LF
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. 清除 HTML/Markdown 注释
    text = re.sub(r"<!--[\s\S]*?-->", "", text)

    # 3. 去除每行行尾空格，折叠空行
    lines = [line.rstrip() for line in text.split("\n")]
    cleaned_lines: List[str] = []
    prev_blank = False
    for l in lines:
        if not l.strip():
            if not prev_blank:
                cleaned_lines.append("")
                prev_blank = True
        else:
            cleaned_lines.append(l)
            prev_blank = False

    net_text = "\n".join(cleaned_lines).strip()
    return hashlib.sha256(net_text.encode("utf-8")).hexdigest()


def get_git_status_and_rev(root_dir: str) -> Tuple[bool, str]:
    """
    优雅检测 Git 可用性与当前 commit / revision。
    git 不可用或非 git 仓库时不报错，降级返回 (False, fallback_hash)
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            commit_id = proc.stdout.strip()
            return True, commit_id
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        pass

    # 降级：基于时间戳与路径生成虚拟 revision 哈希
    seed = f"{root_dir}_{datetime.now(timezone.utc).isoformat()}"
    fallback_rev = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return False, fallback_rev


def create_snapshot(
    root_dir: str,
    label: str,
    target_path: Optional[str] = None,
) -> None:
    """
    创建变更前快照归档:
    输出目录: <root>/backup/<timestamp>_rev_<hash>/
    """
    is_git, rev = get_git_status_and_rev(root_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir_name = f"{timestamp}_rev_{rev}"
    backup_base = os.path.join(root_dir, "backup")
    snapshot_dir = os.path.join(backup_base, snapshot_dir_name)

    os.makedirs(snapshot_dir, exist_ok=True)

    archived_files: List[Dict[str, str]] = []

    # 确定要归档的目标
    if target_path:
        # 指定了特定文件或目录
        norm_target = os.path.normpath(target_path)
        full_target = norm_target if os.path.isabs(norm_target) else os.path.join(root_dir, norm_target)
        if not os.path.exists(full_target):
            out = {
                "success": False,
                "error": f"Target path for snapshot does not exist: {full_target}",
            }
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.exit(1)

        if os.path.isfile(full_target):
            dest_file = os.path.join(snapshot_dir, os.path.basename(full_target))
            shutil.copy2(full_target, dest_file)
            c_hash = compute_content_sha256(dest_file)
            archived_files.append({"path": os.path.basename(full_target), "content_sha256": c_hash})
        else:
            for item in os.listdir(full_target):
                src_item = os.path.join(full_target, item)
                if os.path.isfile(src_item):
                    dest_file = os.path.join(snapshot_dir, item)
                    shutil.copy2(src_item, dest_file)
                    c_hash = compute_content_sha256(dest_file)
                    archived_files.append({"path": item, "content_sha256": c_hash})
    else:
        # 默认归档工作区中的核心母本与治理文件 (排除 backup/ 与 .git/)
        for item in os.listdir(root_dir):
            if item in ("backup", ".git", "__pycache__", ".pytest_cache"):
                continue
            item_full = os.path.join(root_dir, item)
            if os.path.isfile(item_full):
                dest_file = os.path.join(snapshot_dir, item)
                shutil.copy2(item_full, dest_file)
                c_hash = compute_content_sha256(dest_file)
                archived_files.append({"path": item, "content_sha256": c_hash})
            elif os.path.isdir(item_full) and item in ("gates", "delivery", "fact-store"):
                dest_subdir = os.path.join(snapshot_dir, item)
                shutil.copytree(item_full, dest_subdir, dirs_exist_ok=True)
                for root_w, _, files_w in os.walk(dest_subdir):
                    for fw in files_w:
                        fw_full = os.path.join(root_w, fw)
                        rel_p = os.path.relpath(fw_full, snapshot_dir)
                        c_hash = compute_content_sha256(fw_full)
                        archived_files.append({"path": rel_p, "content_sha256": c_hash})

    # 写入快照元数据清单
    meta = {
        "label": label,
        "timestamp": timestamp,
        "git": is_git,
        "rev": rev,
        "snapshot_dir": snapshot_dir,
        "files": archived_files,
    }
    with open(os.path.join(snapshot_dir, "snapshot_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    out = {
        "success": True,
        "snapshot_dir": snapshot_dir,
        "label": label,
        "git": is_git,
        "rev": rev,
        "files_count": len(archived_files),
        "timestamp": timestamp,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.exit(0)


def split_into_sections(text: str) -> List[Tuple[str, str]]:
    """
    将 Markdown 文本按标题切割为多个命名块:
    返回 [(canonical_section_heading, section_body), ...]
    """
    lines = text.splitlines(keepends=True)
    sections: List[Tuple[str, str]] = []
    current_title = "HEADER_PROLOGUE"
    current_lines: List[str] = []

    heading_pattern = re.compile(r"^(#{1,6}\s+.*)$")

    for line in lines:
        m = heading_pattern.match(line)
        if m:
            if current_lines:
                sections.append((current_title, "".join(current_lines)))
                current_lines = []
            raw_title = m.group(1).strip()
            # 规范化标题用于字典匹配：去除 HTML/Markdown 注释并标准化空白
            canonical_title = re.sub(r"<!--[\s\S]*?-->", "", raw_title).strip()
            current_title = canonical_title
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, "".join(current_lines)))

    return sections


def verify_diff_mode(
    old_target: str,
    new_file: str,
    declared_id: str,
) -> None:
    """
    零漂移比对模式:
    比对 old 历史基线与 new 当前文件。
    除显式声明包含 declared_id 的区域外，未声明漂移数 (undeclared_drift) 必须为 0。
    N > 0 时退出码 1，N == 0 时退出码 0。
    """
    # 确定 old 文件路径
    if os.path.isdir(old_target):
        # 如果 old 是目录，寻找与 new 相同文件名的文件
        candidate = os.path.join(old_target, os.path.basename(new_file))
        if os.path.exists(candidate):
            old_file = candidate
        else:
            # 寻找该目录下任意唯一 markdown 或匹配文件
            mds = [f for f in os.listdir(old_target) if f.endswith(".md") and not f.startswith("snapshot_meta")]
            if mds:
                old_file = os.path.join(old_target, mds[0])
            else:
                out = {"undeclared_drift": 1, "error": f"Cannot find matching old file in {old_target}"}
                sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
                sys.exit(1)
    else:
        old_file = old_target

    if not os.path.exists(old_file):
        out = {"undeclared_drift": 1, "error": f"Old file not found: {old_file}"}
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(1)

    if not os.path.exists(new_file):
        out = {"undeclared_drift": 1, "error": f"New file not found: {new_file}"}
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(1)

    with open(old_file, "r", encoding="utf-8", errors="replace") as f:
        old_text = f.read()
    with open(new_file, "r", encoding="utf-8", errors="replace") as f:
        new_text = f.read()

    # 1. 快速检查：若全文内容逐字节相同，零漂移通过
    if old_text == new_text:
        out = {"undeclared_drift": 0, "declared": declared_id, "drift_details": []}
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(0)

    # 2. 分块比对
    old_sections = split_into_sections(old_text)
    new_sections = split_into_sections(new_text)

    old_sec_dict = {title: body for title, body in old_sections}
    new_sec_dict = {title: body for title, body in new_sections}

    all_titles = list(dict.fromkeys([t for t, _ in old_sections] + [t for t, _ in new_sections]))

    undeclared_drifts: List[Dict[str, Any]] = []

    clean_decl_id = declared_id.strip()

    for title in all_titles:
        old_body = old_sec_dict.get(title)
        new_body = new_sec_dict.get(title)

        if old_body != new_body:
            # 检查变化区域是否包含声明的变更 ID
            # 变更 ID 可以在标题、正文批注、或特定标识中声明
            # 例如: <!-- change: C-01 -->, [C-01], 或文字提到 declared_id
            combined = f"{title}\n{old_body or ''}\n{new_body or ''}"
            is_declared = (
                clean_decl_id.lower() in combined.lower()
                or f"change-{clean_decl_id}".lower() in combined.lower()
            )

            if not is_declared:
                # 产生未声明漂移！
                diff_summary = list(
                    difflib.unified_diff(
                        (old_body or "").splitlines(),
                        (new_body or "").splitlines(),
                        fromfile=f"old:{title}",
                        tofile=f"new:{title}",
                        n=1,
                    )
                )
                undeclared_drifts.append({
                    "section": title,
                    "diff_lines": diff_summary[:10],
                    "reason": f"Section '{title}' modified without declaring '{declared_id}'",
                })

    drift_count = len(undeclared_drifts)
    out = {
        "undeclared_drift": drift_count,
        "declared": declared_id,
        "drift_details": undeclared_drifts,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    if drift_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Git adapter sync and zero-drift verification tool")
    parser.add_argument("--hash", type=str, help="Compute content_sha256 and nettext_sha256 for a file")
    parser.add_argument("--root", type=str, default=".", help="Root directory (default: .)")
    parser.add_argument("--snapshot", type=str, help="Create pre-change backup snapshot with label")
    parser.add_argument("--target", type=str, help="Optional target file or folder for snapshot")
    parser.add_argument("--diff-mode", action="store_true", help="Run diff-mode to verify zero undeclared drift")
    parser.add_argument("--old", type=str, help="Old file or backup directory")
    parser.add_argument("--new", type=str, help="New updated file")
    parser.add_argument("--declared", type=str, help="Declared change identifier (e.g. C-01)")

    args = parser.parse_args()

    if args.hash:
        target_file = args.hash
        if not os.path.exists(target_file):
            sys.stderr.write(f"File not found: {target_file}\n")
            sys.exit(1)
        c_hash = compute_content_sha256(target_file)
        n_hash = compute_nettext_sha256(target_file)
        out = {
            "file": target_file,
            "content_sha256": c_hash,
            "nettext_sha256": n_hash,
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.exit(0)

    if args.snapshot:
        create_snapshot(
            root_dir=os.path.abspath(args.root),
            label=args.snapshot,
            target_path=args.target,
        )
        return

    if args.diff_mode:
        if not args.old or not args.new or not args.declared:
            sys.stderr.write("Error: --diff-mode requires --old, --new, and --declared\n")
            sys.exit(1)
        verify_diff_mode(
            old_target=args.old,
            new_file=args.new,
            declared_id=args.declared,
        )
        return

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
