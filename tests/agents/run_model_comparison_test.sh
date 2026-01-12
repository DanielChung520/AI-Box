#!/bin/bash
# 代碼功能說明: Router LLM 模型比較測試運行腳本
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

# Router LLM 模型比較測試運行腳本
# 用於快速運行模型比較測試

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Router LLM 模型比較測試${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 檢查 ollama 服務
echo -e "${YELLOW}檢查 ollama 服務...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama 服務未運行，請先啟動 ollama 服務"
    exit 1
fi
echo "✅ Ollama 服務正常"
echo ""

# 顯示可用的模型
echo -e "${YELLOW}檢查已安裝的模型...${NC}"
ollama list | grep -E "(quentinz/bge-large-zh-v1.5|qwen3-next|gpt-oss:120b-cloud|mistral-nemo:12b|gpt-oss:20b|qwen3-coder:30b)" || echo "⚠️  部分模型可能未安裝"
echo ""

# 詢問運行模式
echo "請選擇運行模式："
echo "1. 運行所有模型比較測試（90 個測試用例，耗時較長，使用 pytest）"
echo "2. 只測試一個模型（15 個場景，推薦用於快速測試）"
echo "3. 只測試一個場景（6 個模型，推薦用於驗證）"
echo "4. 自定義測試（指定模型和場景）"
echo "5. 依序測試所有場景（每個場景測試所有 6 個模型，推薦）"
echo ""
read -p "請輸入選項 (1-5): " choice

case $choice in
    1)
        echo -e "${GREEN}運行所有模型比較測試...${NC}"
        python3 -m pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s
        ;;
    2)
        echo "可用的模型："
        echo "1. quentinz/bge-large-zh-v1.5:latest"
        echo "2. qwen3-next:latest"
        echo "3. gpt-oss:120b-cloud"
        echo "4. mistral-nemo:12b"
        echo "5. gpt-oss:20b"
        echo "6. qwen3-coder:30b"
        read -p "請選擇模型 (1-6): " model_choice
        case $model_choice in
            1) model="quentinz/bge-large-zh-v1.5:latest" ;;
            2) model="qwen3-next:latest" ;;
            3) model="gpt-oss:120b-cloud" ;;
            4) model="mistral-nemo:12b" ;;
            5) model="gpt-oss:20b" ;;
            6) model="qwen3-coder:30b" ;;
            *) echo "無效選項"; exit 1 ;;
        esac
        echo -e "${GREEN}測試模型: $model${NC}"
        python3 -m pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s -k "$model"
        ;;
    3)
        echo "可用的場景："
        echo "類別 2（產生/創建文件）："
        echo "  FE-011: 幫我產生一個 README.md 文件"
        echo "  FE-012: 創建一個新的配置文件 config.json"
        echo "  FE-013: 幫我寫一個 Python 腳本"
        echo "  FE-014: 生成一份報告文件"
        echo "  FE-015: 幫我建立一個新的文件"
        echo "類別 3（隱含編輯意圖）："
        echo "  FE-021: 幫我在 README.md 中加入安裝說明"
        echo "  FE-022: 在文件裡添加註釋"
        echo "  FE-023: 把這個函數改成新的實現"
        echo "  FE-024: 幫我整理一下這個文件"
        echo "  FE-025: 優化這個代碼文件"
        read -p "請輸入場景 ID (例如 FE-011): " scenario_id
        echo -e "${GREEN}測試場景: $scenario_id${NC}"
        python3 -m pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s -k "$scenario_id"
        ;;
    4)
        read -p "請輸入模型名稱（例如 qwen3-next）: " model_name
        read -p "請輸入場景 ID（例如 FE-011，留空表示所有場景）: " scenario_id
        if [ -z "$scenario_id" ]; then
            echo -e "${GREEN}測試模型: $model_name (所有場景)${NC}"
            python3 -m pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s -k "$model_name"
        else
            echo -e "${GREEN}測試模型: $model_name, 場景: $scenario_id${NC}"
            python3 -m pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s -k "$model_name and $scenario_id"
        fi
        ;;
    5)
        echo -e "${GREEN}依序測試所有場景（每個場景測試所有 6 個模型）...${NC}"
        echo -e "${YELLOW}測試模式：按場景分組，依序運行所有模型${NC}"
        echo -e "${YELLOW}總測試次數：15 個場景 × 6 個模型 = 90 個測試用例${NC}"
        echo ""
        python3 tests/agents/test_router_llm_model_comparison_auto.py --sequential
        ;;
    *)
        echo "無效選項"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}測試完成！${NC}"
echo "報告已自動生成到: docs/系统设计文档/核心组件/Agent平台/"
