#!/usr/bin/env python3
# 代碼功能說明: 清理 logs 目錄下的僵尸 log 文件
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""
清理 logs 目錄下的僵尸 log 文件

保留（當前正在使用的）：
- fastapi.log 及輪轉日誌（.1, .2, .3, .4）
- mcp_server.log
- rq_worker_rq_worker_ai_box_[1-5].log（當前 worker）
- rq_dashboard.log
- frontend.log
- worker_service.log

刪除（舊的、測試的、不再使用的）：
- 所有 12 月的 API 日誌
- 1 月 22-26 的舊 RQ worker 日誌
- 其他測試和舊日誌
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# 日誌目錄
LOGS_DIR = Path("/Users/daniel/GitHub/AI-Box/logs")

# 要保留的日誌文件（當前正在使用的）
KEEP_FILES = {
    "fastapi.log",
    "fastapi.log.1",
    "fastapi.log.2",
    "fastapi.log.3",
    "fastapi.log.4",
    "mcp_server.log",
    "rq_worker_rq_worker_ai_box_1.log",
    "rq_worker_rq_worker_ai_box_2.log",
    "rq_worker_rq_worker_ai_box_3.log",
    "rq_worker_rq_worker_ai_box_4.log",
    "rq_worker_rq_worker_ai_box_5.log",
    "rq_dashboard.log",
    "frontend.log",
    "worker_service.log",
}

# 要保留的目錄
KEEP_DIRS = {
    "data_agent",
    "kg_quality",
    "kg_templates",
}

# 要刪除的日誌文件模式（舊的 API 日誌）
DELETE_PATTERNS = [
    "api_final*.log",
    "api_kg_*.log",
    "api_restart*.log",
    "api_stats.log",
    "api_test*.log",
    "rq_worker_rq_worker_16618.log",
    "rq_worker_rq_worker_18426.log",
    "rq_worker_rq_worker_3410_*.log",
    "rq_worker_rq_worker_ai_box.log",
    "rq_worker_rq_worker_phase3_*.log",
    "rq_worker_rq_worker_test_*.log",
    "rq_worker_test_worker.log",
    "fastapi_foreground.log",
    "fastapi_startup.log",
    "vectorization_details.json",
]


def calculate_size(path: Path) -> int:
    """計算文件或目錄的大小（字節）"""
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return 0


def format_size(size: int) -> str:
    """格式化大小為人類可讀格式"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def analyze_logs() -> dict:
    """分析 logs 目錄"""
    print("=" * 60)
    print("📊 分析 logs 目錄")
    print("=" * 60)

    all_files = []
    all_dirs = []

    # 收集所有文件和目錄
    for item in LOGS_DIR.iterdir():
        if item.is_file():
            all_files.append(item)
        elif item.is_dir():
            all_dirs.append(item)

    # 計算大小
    total_size = sum(calculate_size(f) for f in all_files) + sum(
        calculate_size(d) for d in all_dirs
    )

    # 分類
    keep_files = [f for f in all_files if f.name in KEEP_FILES]
    keep_dirs = [d for d in all_dirs if d.name in KEEP_DIRS]

    delete_files = []
    for f in all_files:
        if f.name not in KEEP_FILES:
            # 檢查是否匹配刪除模式
            if any(f.match(pattern) for pattern in DELETE_PATTERNS):
                delete_files.append(f)

    # 其他文件（未匹配保留或刪除模式）
    other_files = [f for f in all_files if f.name not in KEEP_FILES and f not in delete_files]

    # 計算大小
    keep_size = sum(calculate_size(f) for f in keep_files) + sum(
        calculate_size(d) for d in keep_dirs
    )
    delete_size = sum(calculate_size(f) for f in delete_files)
    other_size = sum(calculate_size(f) for f in other_files)

    # 顯示統計
    print(f"\n📁 總計:")
    print(f"  總大小: {format_size(total_size)}")
    print(f"  文件數: {len(all_files)}")
    print(f"  目錄數: {len(all_dirs)}")

    print(f"\n✅ 保留（當前正在使用）:")
    print(f"  文件: {len(keep_files)} 個")
    print(f"  目錄: {len(keep_dirs)} 個")
    print(f"  大小: {format_size(keep_size)}")

    print(f"\n🗑️  建議刪除（舊日誌）:")
    print(f"  文件: {len(delete_files)} 個")
    print(f"  大小: {format_size(delete_size)}")

    if delete_files:
        print(f"\n  將刪除的文件:")
        for f in sorted(delete_files, key=lambda x: x.stat().st_mtime):
            size = calculate_size(f)
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"    - {f.name} ({format_size(size)}, {mtime.strftime('%Y-%m-%d %H:%M')})")

    print(f"\n❓ 其他文件（未分類）:")
    print(f"  文件: {len(other_files)} 個")
    print(f"  大小: {format_size(other_size)}")

    if other_files:
        print(f"\n  其他文件:")
        for f in sorted(other_files, key=lambda x: x.stat().st_mtime):
            size = calculate_size(f)
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"    - {f.name} ({format_size(size)}, {mtime.strftime('%Y-%m-%d %H:%M')})")

    return {
        "total_size": total_size,
        "keep_size": keep_size,
        "delete_size": delete_size,
        "other_size": other_size,
        "delete_files": delete_files,
        "other_files": other_files,
    }


def cleanup_logs(analysis: dict) -> dict:
    """清理日誌文件"""
    print("\n" + "=" * 60)
    print("🗑️  清理日誌文件")
    print("=" * 60)

    delete_files = analysis["delete_files"]
    other_files = analysis["other_files"]

    if not delete_files and not other_files:
        print("✅ 沒有需要清理的文件")
        return {"deleted": 0, "skipped": 0, "errors": 0}

    # 刪除匹配模式的文件
    deleted = 0
    errors = 0

    for f in delete_files:
        try:
            size = calculate_size(f)
            f.unlink()
            print(f"  ✅ 刪除: {f.name} ({format_size(size)})")
            deleted += 1
        except Exception as e:
            print(f"  ❌ 刪除失敗: {f.name}, 錯誤: {e}")
            errors += 1

    # 詢問是否刪除其他文件
    if other_files:
        print(f"\n⚠️  發現 {len(other_files)} 個未分類的文件:")
        for f in sorted(other_files):
            size = calculate_size(f)
            print(f"  - {f.name} ({format_size(size)})")

        print(f"\n⚠️  這些文件不會自動刪除，請確認是否需要刪除")

    return {"deleted": deleted, "skipped": len(other_files), "errors": errors}


def main():
    """主函數"""
    print("\n" + "=" * 60)
    print("清理 logs 目錄下的僵尸 log 文件")
    print(f"執行時間: {datetime.now().isoformat()}")
    print("=" * 60)

    if not LOGS_DIR.exists():
        print(f"❌ 目錄不存在: {LOGS_DIR}")
        return

    # 1. 分析
    analysis = analyze_logs()

    # 2. 清理
    result = cleanup_logs(analysis)

    # 3. 總結
    print("\n" + "=" * 60)
    print("📋 清理總結")
    print("=" * 60)
    print(f"刪除的文件: {result['deleted']}")
    print(f"跳過的文件: {result['skipped']}")
    print(f"錯誤: {result['errors']}")
    print(f"釋放空間: {format_size(analysis['delete_size'])}")
    print(f"保留空間: {format_size(analysis['keep_size'])}")
    print("=" * 60)
    print("✅ 清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷操作")
    except Exception as e:
        print(f"\n\n❌ 發生錯誤: {e}")
        import traceback

        traceback.print_exc()
