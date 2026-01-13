#!/bin/bash
# 代碼功能說明: Data Agent 依賴安裝腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📦 安裝 Data Agent 服務依賴 (Datalake System)"
echo "=============================="
echo ""

# 進入 datalake-system 目錄
cd "$DATALAKE_SYSTEM_DIR"

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤: 未找到 python3"
    exit 1
fi

echo "Python 版本: $(python3 --version)"
echo "Datalake System 目錄: $DATALAKE_SYSTEM_DIR"
echo ""

# 檢查 pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo "❌ 錯誤: 未找到 pip"
    exit 1
fi

# 安裝依賴
echo "📥 安裝核心依賴..."
echo ""

# 核心依賴
CORE_DEPS=(
    "fastapi"
    "uvicorn"
    "boto3>=1.28.0"
    "jsonschema>=4.0.0"
    "structlog>=25.0.0"
    "python-dotenv>=1.0.0"
    "httpx>=0.25.0"
    "pydantic>=2.0.0"
)

for dep in "${CORE_DEPS[@]}"; do
    echo "  安裝: $dep"
    python3 -m pip install "$dep" --quiet || {
        echo "  ❌ 安裝失敗: $dep"
        exit 1
    }
done

echo ""
echo "✅ 核心依賴安裝完成"
echo ""

# 可選：安裝所有 requirements.txt 中的依賴
read -p "是否安裝所有 requirements.txt 中的依賴？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📥 安裝所有項目依賴..."
    if [ -f "$DATALAKE_SYSTEM_DIR/requirements.txt" ]; then
        python3 -m pip install -r "$DATALAKE_SYSTEM_DIR/requirements.txt" || {
            echo "  ⚠️  部分依賴安裝失敗，但核心依賴已安裝"
        }
        echo "✅ 項目依賴安裝完成"
    else
        echo "⚠️  requirements.txt 不存在"
    fi
fi

echo ""
echo "🎉 依賴安裝完成！"
echo ""
echo "💡 下一步："
echo "   檢查環境: cd $DATALAKE_SYSTEM_DIR && python3 scripts/check_environment.py"
echo "   啟動服務: cd $DATALAKE_SYSTEM_DIR && ./scripts/data_agent/start.sh"
