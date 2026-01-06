#!/usr/bin/env python3
# 代碼功能說明: 監控批量處理進度
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""監控批量處理進度

使用方法:
    python scripts/monitor_kg_extract.py
    # 或
    watch -n 5 python scripts/monitor_kg_extract.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

project_root = Path(__file__).parent.parent.resolve()
PROGRESS_FILE = project_root / "scripts/kg_extract_progress.json"


def load_progress() -> Dict[str, Any]:
    """加載進度數據"""
    if not PROGRESS_FILE.exists():
        return {}
    
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  讀取進度文件失敗: {e}")
        return {}


def format_duration(seconds: float) -> str:
    """格式化時間長度"""
    if seconds is None:
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def main():
    """主函數"""
    import os
    os.system('clear' if os.name != 'nt' else 'cls')  # 清屏
    
    print("=" * 80)
    print("📊 批量處理進度監控")
    print("=" * 80)
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    data = load_progress()
    
    if not data:
        print("⚠️  進度文件不存在或為空")
        return
    
    summary = data.get("summary", {})
    files = data.get("files", {})
    
    # 統計信息
    total = summary.get("total_files", len(files))
    processed = summary.get("processed_files", 0)
    failed = summary.get("failed_files", 0)
    processing = sum(1 for f in files.values() if f.get("status") == "processing")
    
    # 進度條
    progress_pct = (processed / total * 100) if total > 0 else 0
    bar_length = 50
    filled = int(bar_length * processed / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    
    print(f"進度: [{bar}] {progress_pct:.1f}%")
    print(f"總文件數: {total}")
    print(f"✅ 已完成: {processed}")
    print(f"❌ 失敗: {failed}")
    print(f"🔄 處理中: {processing}")
    print()
    
    # KG 統計
    total_entities = summary.get("total_entities", 0)
    total_relations = summary.get("total_relations", 0)
    total_chunks = summary.get("total_chunk_count", 0)
    
    print(f"📊 知識圖譜統計:")
    print(f"  實體: {total_entities}")
    print(f"  關係: {total_relations}")
    print(f"  分塊: {total_chunks}")
    print()
    
    # 時間統計
    total_time = summary.get("total_processing_time", 0.0)
    avg_time = total_time / processed if processed > 0 else 0
    
    print(f"⏱️  時間統計:")
    print(f"  總處理時間: {format_duration(total_time)}")
    print(f"  平均處理時間: {format_duration(avg_time)}")
    print()
    
    # 最近處理的文件
    print("📝 最近處理的文件:")
    sorted_files = sorted(
        files.items(),
        key=lambda x: x[1].get("updated_at", x[1].get("uploaded_at", "")),
        reverse=True
    )
    
    for filename, info in sorted_files[:10]:
        status = info.get("status", "unknown")
        status_icon = {
            "completed": "✅",
            "failed": "❌",
            "processing": "🔄",
        }.get(status, "⏳")
        
        print(f"  {status_icon} {filename}: {status}")
        
        if status == "failed":
            error = info.get("error", "")
            if error:
                print(f"     錯誤: {error[:80]}")
        elif status == "completed":
            entities = info.get("entities_count", 0)
            relations = info.get("relations_count", 0)
            total_time_file = info.get("total_time", 0)
            print(f"     實體: {entities}, 關係: {relations}, 耗時: {format_duration(total_time_file)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 再見")
        sys.exit(0)
