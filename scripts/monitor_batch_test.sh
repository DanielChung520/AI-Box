#!/bin/bash
# 代碼功能說明: 實時監控批量測試進度
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

PROGRESS_FILE="${1:-batch_test_100_progress.json}"
REFRESH_INTERVAL="${2:-5}"

if [ ! -f "$PROGRESS_FILE" ]; then
    echo "進度文件不存在: $PROGRESS_FILE"
    echo "等待文件創建..."
    while [ ! -f "$PROGRESS_FILE" ]; do
        sleep 1
    done
fi

echo "開始監控測試進度: $PROGRESS_FILE"
echo "刷新間隔: ${REFRESH_INTERVAL}秒"
echo "按 Ctrl+C 停止監控"
echo ""

while true; do
    clear
    echo "=========================================="
    echo "批量測試進度監控 - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""

    if [ -f "$PROGRESS_FILE" ]; then
        if command -v python3 &> /dev/null; then
            python3 << EOF
import json
import sys
from datetime import datetime

try:
    with open('$PROGRESS_FILE', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    files = data.get('files', [])
    
    total = summary.get('total_files', 0)
    success = summary.get('success_count', 0)
    failed = summary.get('failed_count', 0)
    timeout = summary.get('timeout_count', 0)
    processing = total - success - failed - timeout
    
    print(f"總文件數: {total}")
    if total > 0:
        print(f"✅ 成功: {success} ({success/total*100:.1f}%)")
        print(f"❌ 失敗: {failed}")
        print(f"⏱️  超時: {timeout}")
        print(f"🔄 處理中: {processing}")
    print("")
    
    if summary.get('avg_processing_time'):
        print(f"平均處理時間: {summary['avg_processing_time']:.2f}秒/文件")
    if summary.get('total_entities'):
        print(f"總實體數: {summary['total_entities']}")
    if summary.get('total_relations'):
        print(f"總關係數: {summary['total_relations']}")
    
    print("")
    print("最近處理的文件:")
    print("-" * 60)
    for f in files[-10:]:
        status_icon = "✅" if f.get('status') == 'completed' else "❌" if f.get('status') in ['failed', 'error'] else "🔄"
        print(f"{status_icon} [{f.get('file_index', '?')}/{total}] {f.get('file_name', 'Unknown')[:50]} - {f.get('status', 'unknown')}")
    
    print("")
    print(f"最後更新: {data.get('last_update', 'Unknown')}")
    
except Exception as e:
    print(f"讀取進度文件失敗: {e}")
    sys.exit(1)
EOF
        else
            cat "$PROGRESS_FILE" | head -30
        fi
    else
        echo "進度文件不存在: $PROGRESS_FILE"
    fi

    echo ""
    echo "=========================================="
    echo "按 Ctrl+C 停止監控"
    sleep "$REFRESH_INTERVAL"
done
