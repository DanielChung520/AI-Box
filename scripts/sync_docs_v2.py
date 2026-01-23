#!/usr/bin/env python3
"""
文檔同步腳本 V2
更精確的文檔分類
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs")
DOCS_DOT_DIR = Path("/Users/daniel/GitHub/AI-Box/.docs")

# 精確的目錄映射 - 根據文件名關鍵詞
DIRECTORY_MAP = {
    # 系統架構相關 - 保留
    "系統架構": "01-系統架構",
    "架構規格書": "01-系統架構",
    "架構設計": "01-系統架構",
    "AI-Box-Agent-架構規格書": "01-系統架構",
    "AI-Box 語義與任務工程-設計說明書-v4": "01-系統架構",
    "Agent_Orchestration_White_Paper": "01-系統架構",
    # API 文檔
    "API": "02-API文檔",
    "-api.md": "02-API文檔",
    "document-editing-agent-v2-api": "02-API文檔",
    # 開發指南 - 包含計劃、指南、規範
    "開發規範": "03-開發指南",
    "開發指南": "03-開發指南",
    "計劃": "03-開發指南",
    "重構計劃": "03-開發指南",
    "实施报告": "03-開發指南",
    "實施報告": "03-開發指南",
    "問題診斷": "03-開發指南",
    "故障排查": "03-開發指南",
    "修復說明": "03-開發指南",
    "錯誤分析": "03-開發指南",
    "規範指南": "03-開發指南",
    "集成指南": "03-開發指南",
    "實現總結": "03-開發指南",
    "部署指南": "03-開發指南",
    "設置指南": "03-開發指南",
    "配置指南": "03-開發指南",
    "最佳實踐": "03-開發指南",
    "使用說明": "03-開發指南",
    "使用指南": "03-開發指南",
    "查詢說明": "03-開發指南",
    "處理示例": "03-開發指南",
    "CRUD示例": "03-開發指南",
    "初始化指南": "03-開發指南",
    "開發指南": "03-開發指南",
    "LLM模型列表": "03-開發指南",
    "Git分支策略": "03-開發指南",
    "GitHub設置指南": "03-開發指南",
    "DevSecOps開發指南": "03-開發指南",
    "混合策略": "03-開發指南",
    "HybridRAG": "03-開發指南",
    "GraphRAG": "03-開發指南",
    "genai-pipeline": "03-開發指南",
    "AAM": "03-開發指南",
    # 測試報告
    "測試報告": "05-測試報告",
    "測試計劃": "05-測試報告",
    "測試指南": "05-測試報告",
    "測試說明": "05-測試報告",
    "測試數據": "05-測試報告",
    "測試劇本": "05-測試報告",
    "執行報告": "05-測試報告",
    "測試結果": "05-測試報告",
    # 運維文檔
    "系統管理": "04-運維文檔",
    "監控": "04-運維文檔",
    "配置元數據": "04-運維文檔",
    "ConfigMetadata": "04-運維文檔",
    "模型參數配置": "04-運維文檔",
    # 數據庫相關
    "arangodb": "01-系統架構",
    "ArangoDB": "01-系統架構",
    "存儲架構": "01-系統架構",
    "data-structure": "01-系統架構",
    "schema": "01-系統架構",
    # MCP 相關
    "MCP": "03-開發指南",
    "Cloudflare": "03-開發指南",
    # 預設
    "核心組件": "01-系統架構",
    "系統設計文檔": "01-系統架構",
}

EXCLUDE_PATTERNS = [
    "archive",
    "備份",
    "歷史報告",
    "歷史歸檔",
    "測試報告/歷史報告",
    "測試報告/執行結果",
]


def get_target_directory(doc_path, doc_name):
    """根據文檔路徑和名稱決定目標目錄"""
    # 先檢查排除模式
    for pattern in EXCLUDE_PATTERNS:
        if pattern.lower() in doc_path.lower():
            return "06-歷史歸檔"

    # 檢查文件名映射
    for key, target in DIRECTORY_MAP.items():
        if key.lower() in doc_name.lower() or key in doc_path:
            return target

    # 根據路徑判斷
    if "API文檔" in doc_path:
        return "02-API文檔"
    if "測試報告" in doc_path:
        return "05-測試報告"
    if "系統管理" in doc_path:
        return "04-運維文檔"
    if "开发进度" in doc_path or "開發過程" in doc_path:
        return "03-開發指南"

    return "01-系統架構"  # 預設


def sync_documents_v2():
    """同步文檔 V2"""
    inventory_file = DOCS_DOT_DIR / "document_inventory.json"
    with open(inventory_file, encoding="utf-8") as f:
        inventory = json.load(f)

    processed = set()
    synced = []
    skipped = []
    errors = []
    moved_to_archive = []

    for doc in inventory["all_documents"]:
        # 計算基礎名稱
        name = doc["name"]
        base = (
            name.replace("-v4.0", "").replace("-v3.0", "").replace("-v2.0", "").replace("-v1.0", "")
        )
        base = base.replace("-v4", "").replace("-v3", "").replace("-v2", "").replace("-v1", "")
        base = base.split(".")[0]

        if base in processed:
            continue
        processed.add(base)

        # 檢查是否為最新版本
        latest_info = inventory["latest_versions"].get(base)
        if not latest_info or latest_info["latest_path"] != doc["path"]:
            skipped.append(doc)
            continue

        # 決定目標目錄
        target_dir_name = get_target_directory(doc["path"], doc["name"])
        target_dir = DOCS_DOT_DIR / target_dir_name

        # 清理目標目錄
        target_dir.mkdir(parents=True, exist_ok=True)
        for old_file in target_dir.glob(f"{base}*.md"):
            old_file.unlink()

        # 複製
        try:
            src = DOCS_DIR / doc["path"]
            dst = target_dir / src.name
            shutil.copy2(src, dst)

            synced.append(
                {
                    "source": doc["path"],
                    "target": str(dst.relative_to(DOCS_DOT_DIR)),
                    "category": target_dir_name,
                }
            )

            if target_dir_name == "06-歷史歸檔":
                moved_to_archive.append(doc)

        except Exception as e:
            errors.append({"doc": doc["path"], "error": str(e)})

    report = {
        "synced_at": datetime.now().isoformat(),
        "synced_count": len(synced),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "by_category": {},
        "moved_to_archive": len(moved_to_archive),
    }

    # 統計分類
    for doc in synced:
        cat = doc["category"]
        report["by_category"][cat] = report["by_category"].get(cat, 0) + 1

    report_file = DOCS_DOT_DIR / "sync_report_v2.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    print("=== 文檔同步 V2 - 精確分類 ===")
    report = sync_documents_v2()

    print("\n✅ 同步完成!")
    print(f"   已同步: {report['synced_count']} 個")
    print(f"   已跳過: {report['skipped_count']} 個")
    print(f"   錯誤: {report['error_count']} 個")

    print("\n📊 分類統計:")
    for cat, count in sorted(report["by_category"].items()):
        print(f"   {cat}: {count} 個")

    print(f"\n📄 報告: {report['synced_at']}")


if __name__ == "__main__":
    main()
