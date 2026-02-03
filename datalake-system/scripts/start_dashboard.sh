#!/bin/bash
# 啟動 Tiptop Dashboard（端口 8502）
# 代碼已移至 datalake-system/dashboard/

cd "$(dirname "$0")/.."
exec ./dashboard/start.sh
