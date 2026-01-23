#!/usr/bin/env python3
"""
文檔清單生成器
分析 docs/ 目錄，生成文檔清單和版本追蹤
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs")
OUTPUT_FILE = Path("/Users/daniel/GitHub/AI-Box/.docs/document_inventory.json")


def get_file_info(filepath):
    """獲取文件信息"""
    stat = os.stat(filepath)
    return {
        "path": str(filepath.relative_to(DOCS_DIR)),
        "name": filepath.name,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "ctime": datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }


def extract_version(filename):
    """從文件名提取版本號"""
    import re

    match = re.search(r"-v?(\d+\.\d+)", filename)
    return match.group(1) if match else None


def categorize_document(filepath):
    """分類文檔"""
    path = str(filepath)
    if "archive" in path.lower() or "/old/" in path.lower() or "/歷史報告" in path.lower():
        return "archive"
    if "測試" in path or "test" in path.lower() or "report" in path.lower():
        return "test"
    if "api" in path.lower() or "/API" in path:
        return "api"
    if "開發" in path or "dev" in path.lower() or "develop" in path.lower():
        return "development"
    if "运维" in path or "運維" in path or "operation" in path.lower():
        return "operation"
    return "documentation"


def find_latest_version(documents):
    """找出每組文檔的最新版本"""
    groups = defaultdict(list)

    for doc in documents:
        # 按基礎名稱分組（去除版本號和路徑差異）
        name = doc["name"]
        base = (
            name.replace("-v4.0", "").replace("-v3.0", "").replace("-v2.0", "").replace("-v1.0", "")
        )
        base = base.replace("-v4", "").replace("-v3", "").replace("-v2", "").replace("-v1", "")
        base = base.split(".")[0]  # 去除擴展名
        groups[base].append(doc)

    latest = {}
    for base, docs in groups.items():
        if len(docs) > 1:
            # 多個版本，取最新的
            latest_doc = max(docs, key=lambda x: x["mtime"])
            latest[base] = {
                "latest": latest_doc,
                "versions": sorted(docs, key=lambda x: x["mtime"], reverse=True),
            }
        else:
            latest[base] = {"latest": docs[0], "versions": docs}

    return latest


def main():
    print("=== 生成文檔清單 ===")

    # 收集所有 md 文件
    all_docs = []
    for filepath in DOCS_DIR.rglob("*.md"):
        if "node_modules" in str(filepath):
            continue
        info = get_file_info(filepath)
        info["version"] = extract_version(info["name"])
        info["category"] = categorize_document(filepath)
        all_docs.append(info)

    print(f"找到 {len(all_docs)} 個文檔")

    # 按目錄分組
    by_directory = defaultdict(list)
    for doc in all_docs:
        dir_path = str(Path(doc["path"]).parent)
        by_directory[dir_path].append(doc)

    # 找出最新版本
    latest_versions = find_latest_version(all_docs)

    # 生成清單
    inventory = {
        "generated_at": datetime.now().isoformat(),
        "total_documents": len(all_docs),
        "by_category": {
            "documentation": len([d for d in all_docs if d["category"] == "documentation"]),
            "test": len([d for d in all_docs if d["category"] == "test"]),
            "api": len([d for d in all_docs if d["category"] == "api"]),
            "archive": len([d for d in all_docs if d["category"] == "archive"]),
            "development": len([d for d in all_docs if d["category"] == "development"]),
            "operation": len([d for d in all_docs if d["category"] == "operation"]),
        },
        "by_directory": dict(by_directory),
        "latest_versions": {
            k: {
                "latest_path": v["latest"]["path"],
                "latest_mtime": v["latest"]["mtime"],
                "version_count": len(v["versions"]),
            }
            for k, v in latest_versions.items()
        },
        "all_documents": all_docs,
    }

    # 保存清單
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

    print(f"清單已保存到: {OUTPUT_FILE}")

    # 打印摘要
    print("\n=== 文檔分類摘要 ===")
    for cat, count in inventory["by_category"].items():
        print(f"  {cat}: {count} 個")

    print("\n=== 發現的重複文檔（多版本）===")
    dup_count = sum(1 for v in latest_versions.values() if len(v["versions"]) > 1)
    print(f"  {dup_count} 組文檔有多個版本")

    return inventory


if __name__ == "__main__":
    main()
