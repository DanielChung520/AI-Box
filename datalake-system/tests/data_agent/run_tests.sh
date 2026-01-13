#!/bin/bash
# 代碼功能說明: Data Agent 測試腳本執行器
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
AI_BOX_ROOT="$(cd "$DATALAKE_SYSTEM_DIR/.." && pwd)"

echo "🧪 Data Agent 測試劇本執行器"
echo "=============================="
echo ""

# 進入 datalake-system 目錄
cd "$DATALAKE_SYSTEM_DIR"

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤: 未找到 python3"
    exit 1
fi

# 檢查環境配置
echo "📋 檢查環境配置..."
python3 "$DATALAKE_SYSTEM_DIR/scripts/check_environment.py" || {
    echo "⚠️  環境配置檢查有警告，但繼續執行測試..."
}

echo ""
echo "🚀 開始執行測試劇本..."
echo ""

# 執行測試
python3 "$SCRIPT_DIR/test_data_agent_scenarios.py"

echo ""
echo "✅ 測試完成！"
echo ""
echo "💡 查看詳細結果:"
echo "   cat $SCRIPT_DIR/test_results.json | python3 -m json.tool"
