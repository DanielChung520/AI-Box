# 代碼功能說明: Data Agent直接客戶端（獨立測試用）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent直接客戶端 - 用於獨立測試，不通過AI-Box Orchestrator"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

# 顯式加載 .env 文件
env_path = ai_box_root / ".env"
load_dotenv(dotenv_path=env_path)

from agents.services.protocol.base import AgentServiceRequest

logger = logging.getLogger(__name__)


class DataAgentDirectClient:
    """Data Agent直接客戶端 - 用於獨立測試"""

    def __init__(self, use_http: bool = True) -> None:
        """初始化Data Agent直接客戶端

        Args:
            use_http: 是否使用HTTP API調用（True）或直接實例化（False）
        """
        self._use_http = use_http
        self._data_agent_service_url = os.getenv("DATA_AGENT_SERVICE_URL", "http://localhost:8004")
        self._logger = logger
        self._timeout = 30.0
        self._data_agent_instance: Optional[Any] = None

    async def call_data_agent(
        self,
        action: str,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """直接調用Data Agent（不通過Orchestrator）

        Args:
            action: Data Agent操作類型
            parameters: 操作參數
            request: Agent服務請求
            max_retries: 最大重試次數

        Returns:
            Data Agent響應結果

        Raises:
            RuntimeError: 調用失敗時拋出異常
        """
        if self._use_http:
            return await self._call_data_agent_http(action, parameters, request, max_retries)
        else:
            return await self._call_data_agent_direct(action, parameters, request)

    async def _call_data_agent_http(
        self,
        action: str,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """通過HTTP API調用Data Agent

        Args:
            action: Data Agent操作類型
            parameters: 操作參數
            request: Agent服務請求
            max_retries: 最大重試次數

        Returns:
            Data Agent響應結果

        Raises:
            RuntimeError: 調用失敗時拋出異常
        """
        # 構建Data Agent請求
        data_agent_request = {
            "action": action,
            **parameters,
            "user_id": request.metadata.get("user_id") if request.metadata else None,
            "tenant_id": request.metadata.get("tenant_id") if request.metadata else None,
        }

        # 直接調用Data Agent HTTP API
        url = f"{self._data_agent_service_url}/execute"
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                self._logger.debug(
                    f"直接調用Data Agent: action={action}, url={url}, task_id={request.task_id}"
                )

                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        url,
                        json={
                            "task_id": f"{request.task_id}-data-query",
                            "task_type": "data_query",
                            "task_data": data_agent_request,
                            "metadata": request.metadata or {},
                        },
                    )

                    if response.status_code != 200:
                        error_msg = f"Data Agent調用失敗: HTTP {response.status_code}, {response.text}"
                        self._logger.error(error_msg)
                        raise RuntimeError(error_msg)

                    result = response.json()

                    # 檢查響應結構
                    if not isinstance(result, dict):
                        error_msg = f"Data Agent響應格式錯誤: {type(result)}"
                        self._logger.error(error_msg)
                        raise RuntimeError(error_msg)

                    # 檢查執行結果
                    if result.get("status") != "completed":
                        error_msg = result.get("error", "Data Agent查詢失敗")
                        self._logger.error(f"Data Agent查詢失敗: {error_msg}")
                        raise RuntimeError(f"Data Agent查詢失敗: {error_msg}")

                    # Data Agent HTTP API返回格式：
                    # {
                    #   "status": "completed",
                    #   "result": {
                    #     "success": true,
                    #     "action": "query_datalake",
                    #     "result": { "success": true, "rows": [...] }
                    #   }
                    # }
                    # 需要提取内部的result字段
                    task_result = result.get("result", {})
                    if isinstance(task_result, dict):
                        # 如果task_result包含嵌套的result字段（DataAgentResponse格式）
                        if "result" in task_result and isinstance(task_result["result"], dict):
                            # 提取内部的result字段
                            inner_result = task_result["result"]
                            if not inner_result.get("success", True):
                                error_msg = inner_result.get("error", "Data Agent查詢失敗")
                                self._logger.error(f"Data Agent查詢失敗: {error_msg}")
                                raise RuntimeError(f"Data Agent查詢失敗: {error_msg}")
                            return inner_result
                        # 如果task_result本身就是结果（直接格式）
                        elif not task_result.get("success", True):
                            error_msg = task_result.get("error", "Data Agent查詢失敗")
                            self._logger.error(f"Data Agent查詢失敗: {error_msg}")
                            raise RuntimeError(f"Data Agent查詢失敗: {error_msg}")

                    return task_result

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 指數退避
                    self._logger.warning(
                        f"Data Agent調用失敗（嘗試 {attempt + 1}/{max_retries}），{wait_time}秒後重試: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self._logger.error(f"Data Agent調用失敗，已重試{max_retries}次: {e}")
                    raise

        if last_error:
            raise last_error

        raise RuntimeError("Data Agent調用失敗：未知錯誤")

    async def _call_data_agent_direct(
        self,
        action: str,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """直接實例化Data Agent調用（不通過HTTP）

        Args:
            action: Data Agent操作類型
            parameters: 操作參數
            request: Agent服務請求

        Returns:
            Data Agent響應結果

        Raises:
            RuntimeError: 調用失敗時拋出異常
        """
        # 延遲導入，避免循環依賴
        if self._data_agent_instance is None:
            from data_agent.agent import DataAgent

            self._data_agent_instance = DataAgent()

        # 構建Data Agent請求
        data_agent_request = {
            "action": action,
            **parameters,
            "user_id": request.metadata.get("user_id") if request.metadata else None,
            "tenant_id": request.metadata.get("tenant_id") if request.metadata else None,
        }

        # 創建Agent服務請求
        agent_request = AgentServiceRequest(
            task_id=f"{request.task_id}-data-query",
            task_type="data_agent",
            task_data=data_agent_request,
            metadata=request.metadata or {},
        )

        # 直接調用Data Agent
        try:
            self._logger.debug(f"直接實例化調用Data Agent: action={action}, task_id={request.task_id}")

            response = await self._data_agent_instance.execute(agent_request)

            if response.status != "completed":
                error_msg = response.error or "Data Agent查詢失敗"
                self._logger.error(f"Data Agent查詢失敗: {error_msg}")
                raise RuntimeError(f"Data Agent查詢失敗: {error_msg}")

            result = response.result or {}
            if isinstance(result, dict) and not result.get("success", True):
                error_msg = result.get("error", "Data Agent查詢失敗")
                self._logger.error(f"Data Agent查詢失敗: {error_msg}")
                raise RuntimeError(f"Data Agent查詢失敗: {error_msg}")

            return result

        except Exception as e:
            error_msg = f"Data Agent調用失敗: {e}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
