#!/bin/bash
# 代碼功能說明: 庫管員Agent整合測試腳本執行器
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
AI_BOX_ROOT="$(cd "$DATALAKE_SYSTEM_DIR/.." && pwd)"

echo "🧪 庫管員Agent整合測試執行器"
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
if [ -f "$AI_BOX_ROOT/scripts/check_environment.py" ]; then
    python3 "$AI_BOX_ROOT/scripts/check_environment.py" || {
        echo "⚠️  環境配置檢查有警告，但繼續執行測試..."
    }
fi

echo ""
echo "📋 測試說明："
echo "   - 本測試包含 20 個工作應用場景"
echo "   - 測試會實際調用 Data-Agent 進行查詢"
echo "   - 確保 Data-Agent 服務已啟動（端口 8004）"
echo "   - 確保 SeaweedFS Datalake 服務運行正常"
echo ""

read -p "是否繼續執行測試？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "測試已取消"
    exit 0
fi

echo ""
echo "🚀 開始執行整合測試..."
echo ""

# 執行測試
python3 "$SCRIPT_DIR/test_integration_scenarios.py"

echo ""
echo "✅ 測試完成！"
echo ""
echo "💡 查看詳細結果:"
echo "   cat $SCRIPT_DIR/integration_test_results.json | python3 -m json.tool"
