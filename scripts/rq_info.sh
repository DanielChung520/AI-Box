#!/bin/bash
# 代碼功能說明: RQ 隊列信息查看腳本
# 創建日期: 2025-12-12
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-12

# 激活虛擬環境並執行 rq info
cd "$(dirname "$0")/.." || exit 1
source venv/bin/activate
rq info "$@"
