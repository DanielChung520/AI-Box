#!/usr/bin/env python3
# 代碼功能說明: 庫管員Agent服務啟動腳本
# 創建日期: 2026-01-15
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-15

"""庫管員Agent服務啟動腳本"""

import sys
from pathlib import Path

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(datalake_system_dir))

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = datalake_system_dir.parent
sys.path.insert(0, str(ai_box_root))

# 導入並運行 mm_agent 的 main 模塊
if __name__ == "__main__":
    import os

    import uvicorn
    from mm_agent.main import app

    # 從環境變數獲取配置
    host = os.getenv("WAREHOUSE_MANAGER_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("WAREHOUSE_MANAGER_AGENT_SERVICE_PORT", "8003"))

    print(f"啟動庫管員Agent服務: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
