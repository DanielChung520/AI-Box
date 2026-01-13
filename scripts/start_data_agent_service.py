# 代碼功能說明: Data Agent 服務啟動腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent 獨立服務啟動腳本

使用 FastAPI 和 uvicorn 啟動 Data Agent HTTP 服務，提供 AgentServiceProtocol 接口。
"""

import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv

# 加載環境變數（使用絕對路徑）
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from agents.builtin.data_agent.agent import DataAgent
from agents.services.protocol.base import AgentServiceRequest, AgentServiceResponse

# 創建 FastAPI 應用
app = FastAPI(
    title="Data Agent Service",
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
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "data_agent",
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

    print(f"Starting Data Agent Service on {host}:{port}")
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
