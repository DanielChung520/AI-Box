#!/bin/bash
# 代碼功能說明: 整合測試運行腳本
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "AI-Box 整合測試執行腳本"
echo "=========================================="
echo ""

# 檢查環境
echo "檢查測試環境..."
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}錯誤: pytest 未安裝${NC}"
    exit 1
fi

# 設置測試環境變量
export TEST_BASE_URL=${TEST_BASE_URL:-"http://localhost:8000"}
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 運行測試
echo ""
echo "開始執行整合測試..."
echo ""

# 階段一測試
echo -e "${YELLOW}執行階段一測試（基礎架構）...${NC}"
pytest tests/integration/phase1/ -v --tb=short -m integration || true

# 階段二測試
echo -e "${YELLOW}執行階段二測試（Agent 核心）...${NC}"
pytest tests/integration/phase2/ -v --tb=short -m integration || true

# 階段三測試
echo -e "${YELLOW}執行階段三測試（工作流引擎）...${NC}"
pytest tests/integration/phase3/ -v --tb=short -m integration || true

# 階段四測試
echo -e "${YELLOW}執行階段四測試（數據處理）...${NC}"
pytest tests/integration/phase4/ -v --tb=short -m integration || true

# 階段五測試
echo -e "${YELLOW}執行階段五測試（LLM MoE）...${NC}"
pytest tests/integration/phase5/ -v --tb=short -m integration || true

# 端到端測試
echo -e "${YELLOW}執行端到端測試...${NC}"
pytest tests/integration/e2e/ -v --tb=short -m integration || true

echo ""
echo -e "${GREEN}所有測試執行完成！${NC}"
echo ""
echo "生成測試報告..."
pytest tests/integration/ -v --tb=short -m integration --junitxml=tests/integration_test_results.xml || true

echo ""
echo "測試結果已保存到: tests/integration_test_results.xml"
echo "請查看測試報告模板: tests/integration_test_report_template.md"
