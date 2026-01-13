#!/bin/bash
# 代碼功能說明: 運行端到端測試腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

echo "=========================================="
echo "運行階段七：端到端測試 (E2E Tests)"
echo "=========================================="

# 設置測試環境
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ARANGO_DB_TEST="${ARANGO_DB_TEST:-ai_box_test}"

# 運行端到端測試
pytest tests/integration/e2e/test_task_analyzer_v4_e2e.py \
    -v \
    --tb=short \
    --cov=agents/task_analyzer \
    --cov-report=html:htmlcov/e2e \
    --cov-report=term \
    -m "e2e" \
    "$@"

echo "=========================================="
echo "端到端測試完成"
echo "=========================================="
