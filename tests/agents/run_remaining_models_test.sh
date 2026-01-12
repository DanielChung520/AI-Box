#!/bin/bash
# 代碼功能說明: 運行剩餘 5 個模型的測試
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

# 運行剩餘 5 個模型的比較測試（排除 quentinz/bge-large-zh-v1.5:latest）
# 測試時間較長，建議在後台運行

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Router LLM 模型比較測試（剩餘 5 個模型）${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}已排除模型: quentinz/bge-large-zh-v1.5:latest (不適合意圖判斷)${NC}"
echo -e "${YELLOW}測試模型: qwen3-next, gpt-oss:120b-cloud, mistral-nemo:12b, gpt-oss:20b, qwen3-coder:30b${NC}"
echo -e "${YELLOW}測試場景: 15 個場景${NC}"
echo -e "${YELLOW}總測試次數: 5 × 15 = 75 個測試用例${NC}"
echo -e "${YELLOW}預計耗時: 根據模型響應速度，可能需要 30-60 分鐘${NC}"
echo ""

# 檢查 ollama 服務
echo -e "${YELLOW}檢查 ollama 服務...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama 服務未運行，請先啟動 ollama 服務"
    exit 1
fi
echo "✅ Ollama 服務正常"
echo ""

# 創建輸出目錄
OUTPUT_DIR="docs/系统设计文档/核心组件/Agent平台"
mkdir -p "$OUTPUT_DIR"

# 運行測試並保存輸出
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/router_llm_test_remaining_models_${TIMESTAMP}.log"

echo -e "${GREEN}開始運行測試...${NC}"
echo -e "輸出文件: ${OUTPUT_FILE}"
echo -e "JSON 報告將自動保存到: ${OUTPUT_DIR}/router_llm_model_comparison_*.json"
echo ""
echo -e "${YELLOW}注意: 測試需要較長時間，請耐心等待...${NC}"
echo ""

# 運行測試
python3 -m pytest tests/agents/test_router_llm_model_comparison_auto.py::TestRouterLLMModelComparison::test_model_on_scenario \
    -v -s \
    --tb=short \
    2>&1 | tee "$OUTPUT_FILE"

echo ""
echo -e "${GREEN}測試完成！${NC}"
echo -e "輸出文件: ${OUTPUT_FILE}"
echo ""
echo -e "${GREEN}運行分析腳本查看結果:${NC}"
echo "python3 tests/agents/analyze_model_results.py"
