#!/bin/bash
# 代碼功能說明: 運行回歸測試腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

echo "=========================================="
echo "運行階段七：回歸測試 (Regression Tests)"
echo "=========================================="

# 設置測試環境
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ARANGO_DB_TEST="${ARANGO_DB_TEST:-ai_box_test}"

# 運行回歸測試
pytest tests/regression/test_task_analyzer_v3_compatibility.py \
    -v \
    --tb=short \
    -m "regression" \
    "$@"

echo "=========================================="
echo "回歸測試完成"
echo "=========================================="
