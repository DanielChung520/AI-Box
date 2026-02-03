#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 快速啟動庫管員Agent服務..."
"$SCRIPT_DIR/start.sh"
sleep 5
"$SCRIPT_DIR/status.sh"
"$SCRIPT_DIR/view_logs.sh"
