#!/usr/bin/env python3
# 代碼功能說明: Tiptop Dashboard 導向腳本（已遷移至 dashboard/）
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30 UTC+8
#
# [已棄用] 此腳本為導向腳本，實際代碼已移至 datalake-system/dashboard/
# 請使用 ./dashboard/start.sh 或 ./scripts/start_dashboard.sh 啟動

"""導向至 dashboard/app.py"""

import runpy
import sys
from pathlib import Path

# 確保 datalake-system 在 path 中
_script_dir = Path(__file__).resolve().parent
_datalake_root = _script_dir.parent
if str(_datalake_root) not in sys.path:
    sys.path.insert(0, str(_datalake_root))

# 執行新 dashboard
_app_path = _datalake_root / "dashboard" / "app.py"
runpy.run_path(str(_app_path), run_name="__main__")
