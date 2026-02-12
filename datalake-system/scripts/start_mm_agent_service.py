#!/usr/bin/env python3
# 代碼功能說明: 庫管員Agent服務啟動腳本
# 創建日期: 2026-01-15
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""庫管員Agent服務啟動腳本"""

import sys
from pathlib import Path

# 獲取 datalake-system 目錄
DATALAKE_SYSTEM_DIR = Path(__file__).resolve().parent.parent
# 獲取 AI-Box 根目錄
AI_BOX_ROOT = DATALAKE_SYSTEM_DIR.parent

# 激活 venv（如果存在）
venv_path = DATALAKE_SYSTEM_DIR / "venv" / "bin" / "python"
if venv_path.exists():
    # 使用 venv 的 Python 解釋器
    import subprocess
    import os

    os.execv(str(venv_path), [sys.executable, __file__] + sys.argv[1:])

# 添加 AI-Box 根目錄到 Python 路徑
sys.path.insert(0, str(AI_BOX_ROOT))

# 添加 datalake-system 到 Python 路徑
sys.path.insert(0, str(DATALAKE_SYSTEM_DIR))

from dotenv import load_dotenv

# 加載環境變數（使用 mm_agent 專屬配置）
agent_env_path = DATALAKE_SYSTEM_DIR / "mm_agent" / ".env"
box_env_path = AI_BOX_ROOT / ".env"

if agent_env_path.exists():
    env_path = agent_env_path
    load_dotenv(dotenv_path=env_path)
    print(f"✅ 已加載 MM-Agent 專屬環境配置: {env_path}")
else:
    env_path = box_env_path
    load_dotenv(dotenv_path=env_path)
    print(f"⚠️ MM-Agent 專屬配置不存在，使用 AI-Box 配置: {env_path}")

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
