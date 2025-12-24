#!/bin/bash
# 代碼功能說明: 清理指定用戶的所有數據（任務、文件、目錄）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-09 12:45 (UTC+8)

# 修改時間：2025-12-09 - 整合測試版本，移除 dev_user 相關邏輯

set -euo pipefail

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

# 檢查參數
USER_EMAIL="${1:-}"

if [ -z "$USER_EMAIL" ]; then
    echo -e "${RED}[ERROR]${NC} 請提供用戶郵箱作為參數"
    echo "用法: $0 <user_email>"
    echo "範例: $0 daniel@test.com"
    exit 1
fi

# 修改時間：2025-12-09 - 整合測試：禁止清理 dev_user
if [ "$USER_EMAIL" == "dev_user" ]; then
    echo -e "${RED}[ERROR]${NC} 整合測試環境禁止清理 dev_user 數據"
    echo "如需清理其他用戶，請使用實際的用戶郵箱"
    exit 1
fi

# 確認操作
echo -e "${YELLOW}[WARN]${NC} ⚠️  即將清理用戶: ${USER_EMAIL}"
echo -e "${YELLOW}[WARN]${NC} 這將刪除以下數據："
echo -e "${YELLOW}[WARN]${NC}   - ArangoDB 中的所有任務、文件元數據、文件夾元數據"
echo -e "${YELLOW}[WARN]${NC}   - 文件系統中的任務工作區目錄 (data/tasks/)"
echo -e "${YELLOW}[WARN]${NC}   - 相關的實際文件"
echo ""
read -p "請確認是否繼續？(輸入 'yes' 確認): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${GREEN}[INFO]${NC} 操作已取消"
    exit 0
fi

# 檢查並激活虛擬環境
PYTHON_CMD="python3"
if [ -d "venv" ]; then
    source venv/bin/activate
    PYTHON_CMD="venv/bin/python"
    echo -e "${GREEN}[INFO]${NC} 使用虛擬環境: venv"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    PYTHON_CMD=".venv/bin/python"
    echo -e "${GREEN}[INFO]${NC} 使用虛擬環境: .venv"
else
    echo -e "${YELLOW}[WARN]${NC} 未找到虛擬環境，使用系統 Python"
fi

# 執行清理腳本
echo -e "${GREEN}[INFO]${NC} 執行清理腳本..."
"$PYTHON_CMD" "$SCRIPT_DIR/clear_user_data.py" "$USER_EMAIL"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}[INFO]${NC} ✅ 用戶數據清理完成"
else
    echo -e "${RED}[ERROR]${NC} ❌ 用戶數據清理失敗"
    exit $EXIT_CODE
fi
