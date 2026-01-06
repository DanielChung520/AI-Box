#!/bin/bash
# 代碼功能說明: 運行大規模批量測試（100個文件，後台運行）
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

FILE_LIST="${SCRIPT_DIR}/batch_test_100_files.txt"
OUTPUT_FILE="batch_test_100_results.json"
PROGRESS_FILE="batch_test_100_progress.json"
LOG_FILE="batch_test_100.log"

if [ ! -f "$FILE_LIST" ]; then
    echo "錯誤: 文件列表不存在: $FILE_LIST"
    echo "請先創建文件列表或使用 --input-dir 參數"
    exit 1
fi

echo "=========================================="
echo "啟動大規模批量測試（100個文件）"
echo "=========================================="
echo "文件列表: $FILE_LIST"
echo "結果文件: $OUTPUT_FILE"
echo "進度文件: $PROGRESS_FILE"
echo "日誌文件: $LOG_FILE"
echo ""

if [ -d "venv" ]; then
    source venv/bin/activate
fi

nohup python3 "$SCRIPT_DIR/kg_extract_batch_test_100.py" \
    --file-list "$FILE_LIST" \
    --max-files 100 \
    --concurrent 5 \
    --output "$OUTPUT_FILE" \
    --progress "$PROGRESS_FILE" \
    --retry-failed \
    > "$LOG_FILE" 2>&1 &

TEST_PID=$!

echo "測試腳本已啟動（PID: $TEST_PID）"
echo ""
echo "查看實時日誌:"
echo "  tail -f $LOG_FILE"
echo ""
echo "監控進度:"
echo "  $SCRIPT_DIR/monitor_batch_test.sh $PROGRESS_FILE"
echo ""
echo "停止測試:"
echo "  kill $TEST_PID"
echo ""
echo "測試結果將保存到:"
echo "  - $OUTPUT_FILE"
echo "  - $PROGRESS_FILE"
echo ""

echo $TEST_PID > batch_test_100.pid
echo "PID 已保存到: batch_test_100.pid"
