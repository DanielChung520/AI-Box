#!/bin/bash
# 代碼功能說明: 運行性能測試腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

echo "=========================================="
echo "運行階段七：性能測試 (Performance Tests)"
echo "=========================================="

# 設置測試環境
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ARANGO_DB_TEST="${ARANGO_DB_TEST:-ai_box_test}"

# 運行性能測試
pytest tests/performance/test_task_analyzer_v4_performance.py \
    -v \
    --tb=short \
    --benchmark-only \
    --benchmark-json=benchmark_results.json \
    -m "performance" \
    "$@"

echo "=========================================="
echo "性能測試完成，結果已保存至 benchmark_results.json"
echo "=========================================="
