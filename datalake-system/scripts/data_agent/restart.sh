#!/bin/bash
# 代碼功能說明: Data Agent 服務重啟腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 重啟 Data Agent 服務 (Datalake System)..."
echo ""

# 停止服務
"$SCRIPT_DIR/stop.sh"

# 等待一下
sleep 2

# 啟動服務
"$SCRIPT_DIR/start.sh"
