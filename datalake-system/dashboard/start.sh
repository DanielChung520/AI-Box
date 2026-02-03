#!/bin/bash
# 代碼功能說明: Tiptop Dashboard 啟動腳本
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-29 UTC+8

# 啟動 Tiptop 模擬系統 Dashboard（端口 8502）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$DATALAKE_ROOT"

# 激活虛擬環境（datalake-system 獨立部署，優先使用本目錄 venv）
if [ -f "$DATALAKE_ROOT/venv/bin/activate" ]; then
    source "$DATALAKE_ROOT/venv/bin/activate"
fi

DASHBOARD_PORT="${DASHBOARD_PORT:-8502}"
echo "正在啟動 Tiptop Dashboard..."
echo "訪問: http://0.0.0.0:${DASHBOARD_PORT}"

streamlit run dashboard/app.py --server.port="${DASHBOARD_PORT}" --server.address="0.0.0.0"
