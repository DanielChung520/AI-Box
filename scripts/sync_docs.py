#!/usr/bin/env python3
"""
文檔同步腳本
將 docs/ 中的最新版本文檔同步到 .docs/
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs")
DOCS_DOT_DIR = Path("/Users/daniel/GitHub/AI-Box/.docs")

# 目錄映射
DIRECTORY_MAP = {
    "系統設計文檔/核心組件": "01-系統架構",
    "系統設計文檔/API文檔": "02-API文檔",
    "开发进度": "03-開發指南",
    "系統設計文檔/核心組件/IEE對話式開發文件編輯": "03-開發指南",
    "系統設計文檔/核心組件/Agent平台": "01-系統架構",
    "系統設計文檔/核心組件/文件上傳向量圖譜": "01-系統架構",
    "系統設計文檔/核心組件/存儲架構": "01-系統架構",
    "系統設計文檔/核心組件/系統管理": "04-運維文檔",
    "系統設計文檔/核心組件/語義與任務分析": "01-系統架構",
    "系統設計文檔/核心組件/MCP工具": "03-開發指南",
    "运维文档": "04-運維文檔",
    "测试报告": "05-測試報告",
    "測試報告": "05-測試報告",
    "備份與歸檔": "06-歷史歸檔",
    "開發過程文件": "03-開發指南",
}


def get_target_directory(doc_path):
    """根據文檔路徑決定目標目錄"""
    for key, target in DIRECTORY_MAP.items():
        if key in doc_path:
            return target
    return "01-系統架構"  # 預設


def sync_latest_documents():
    """同步最新版本的文檔"""
    # 讀取清單
    inventory_file = DOCS_DOT_DIR / "document_inventory.json"
    with open(inventory_file, encoding="utf-8") as f:
        inventory = json.load(f)

    # 追蹤已處理的基礎名稱
    processed = set()
    synced = []
    skipped = []
    errors = []

    for doc in inventory["all_documents"]:
        # 跳過歸檔目錄
        if "archive" in doc["path"].lower() or "備份" in doc["path"]:
            skipped.append(doc)
            continue

        # 計算基礎名稱
        name = doc["name"]
        base = (
            name.replace("-v4.0", "").replace("-v3.0", "").replace("-v2.0", "").replace("-v1.0", "")
        )
        base = base.replace("-v4", "").replace("-v3", "").replace("-v2", "").replace("-v1", "")
        base = base.split(".")[0]

        # 如果已處理過這個基礎名稱，跳過
        if base in processed:
            continue

        processed.add(base)

        # 檢查是否為最新版本
        latest_info = inventory["latest_versions"].get(base)
        if latest_info and latest_info["latest_path"] == doc["path"]:
            # 這是最新版本，複製它
            try:
                src = DOCS_DIR / doc["path"]
                target_dir = DOCS_DOT_DIR / get_target_directory(doc["path"])
                target_dir.mkdir(parents=True, exist_ok=True)

                # 清理目標目錄中的舊版本
                for old_file in target_dir.glob(f"{base}*.md"):
                    old_file.unlink()

                # 複製新版本
                dst = target_dir / src.name
                shutil.copy2(src, dst)

                synced.append(
                    {
                        "source": doc["path"],
                        "target": str(dst.relative_to(DOCS_DOT_DIR)),
                        "mtime": doc["mtime"],
                    }
                )
            except Exception as e:
                errors.append({"doc": doc["path"], "error": str(e)})
        else:
            skipped.append(doc)

    # 生成報告
    report = {
        "synced_at": datetime.now().isoformat(),
        "synced_count": len(synced),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "documents": synced[:20],
        "errors": errors[:10],
    }

    # 保存報告
    report_file = DOCS_DOT_DIR / "sync_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    print("=== 同步最新文檔到 .docs/ ===")
    report = sync_latest_documents()

    print("\n✅ 同步完成!")
    print(f"   已同步: {report['synced_count']} 個文檔")
    print(f"   已跳過: {report['skipped_count']} 個（舊版本或歸檔）")
    print(f"   錯誤: {report['error_count']} 個")

    print(f"\n📄 同步報告: {report['synced_at']}")

    if report["documents"]:
        print("\n=== 同步的文檔（部分）===")
        for doc in report["documents"][:10]:
            print(f"   📄 {doc['source']}")
            print(f"      → {doc['target']}")

    if report["errors"]:
        print("\n⚠️  錯誤:")
        for err in report["errors"]:
            print(f"   {err['doc']}: {err['error']}")


if __name__ == "__main__":
    main()
