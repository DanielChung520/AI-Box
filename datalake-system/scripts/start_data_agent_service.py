# 代碼功能說明: Data Agent 服務啟動腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent 獨立服務啟動腳本

使用 FastAPI 和 uvicorn 啟動 Data Agent HTTP 服務，提供 AgentServiceProtocol 接口。
"""

import os
import sys
from pathlib import Path

# 獲取 datalake-system 目錄
DATALAKE_SYSTEM_DIR = Path(__file__).resolve().parent.parent
# 獲取 AI-Box 根目錄
AI_BOX_ROOT = DATALAKE_SYSTEM_DIR.parent

# 添加 AI-Box 根目錄到 Python 路徑
sys.path.insert(0, str(AI_BOX_ROOT))

# 添加 datalake-system 到 Python 路徑
sys.path.insert(0, str(DATALAKE_SYSTEM_DIR))

from dotenv import load_dotenv

# 加載環境變數（使用 data_agent 專屬配置）
# 優先加載 data_agent/.env，如果不存在則使用 AI-Box/.env
agent_env_path = DATALAKE_SYSTEM_DIR / "data_agent" / ".env"
box_env_path = AI_BOX_ROOT / ".env"

if agent_env_path.exists():
    env_path = agent_env_path
    load_dotenv(dotenv_path=env_path)
    print(f"✅ 已加載 Data-Agent 專屬環境配置: {env_path}")
else:
    env_path = box_env_path
    load_dotenv(dotenv_path=env_path)
    print(f"⚠️ Data-Agent 專屬配置不存在，使用 AI-Box 配置: {env_path}")

# 清除 Ollama 設定的緩存，確保環境變數生效
try:
    from api.core.settings import get_ollama_settings

    get_ollama_settings.cache_clear()
    print("✅ 已清除 Ollama 設定緩存")
except Exception as e:
    print(f"⚠️ 清除 Ollama 設定緩存失敗: {e}")

import uvicorn
from data_agent.agent import DataAgent
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from agents.services.protocol.base import AgentServiceRequest, AgentServiceResponse

# 創建 FastAPI 應用
app = FastAPI(
    title="Data Agent Service (Datalake System)",
    description="Data Agent 獨立服務，提供數據查詢、數據字典管理和 Schema 管理功能",
    version="1.0.0",
)

# 初始化 Data Agent
data_agent = DataAgent()


@app.post("/execute", response_model=AgentServiceResponse)
async def execute(request: AgentServiceRequest) -> AgentServiceResponse:
    """執行數據查詢任務

    AgentServiceProtocol HTTP 接口實現
    """
    try:
        result = await data_agent.execute(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health() -> dict:
    """健康檢查端點"""
    try:
        status = await data_agent.health_check()
        return {
            "status": status.value,
            "service": "data_agent",
            "system": "datalake-system",
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "data_agent",
                "system": "datalake-system",
                "error": str(e),
            },
        )


@app.get("/capabilities")
async def capabilities() -> dict:
    """獲取服務能力端點"""
    try:
        caps = await data_agent.get_capabilities()
        return caps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main() -> None:
    """主函數：啟動服務"""
    # 從環境變數讀取配置
    host = os.getenv("DATA_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("DATA_AGENT_SERVICE_PORT", "8004"))

    print(f"Starting Data Agent Service (Datalake System) on {host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Capabilities: http://{host}:{port}/capabilities")
    print(f"Execute endpoint: http://{host}:{port}/execute")

    # 啟動服務
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
