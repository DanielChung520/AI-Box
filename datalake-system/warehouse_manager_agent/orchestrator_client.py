# 代碼功能說明: AI-Box Orchestrator客戶端
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""AI-Box Orchestrator客戶端 - 用於調用Data Agent"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in os.sys.path:
    os.sys.path.insert(0, str(ai_box_root))

# 顯式加載 .env 文件
env_path = ai_box_root / ".env"
load_dotenv(dotenv_path=env_path)

from agents.services.protocol.base import AgentServiceRequest

logger = logging.getLogger(__name__)


class OrchestratorClient:
    """AI-Box Orchestrator客戶端"""

    def __init__(self) -> None:
        """初始化Orchestrator客戶端"""
        self._ai_box_api_url = os.getenv("AI_BOX_API_URL", "http://localhost:8000")
        self._api_key = os.getenv("AI_BOX_API_KEY", "")
        self._logger = logger
        self._timeout = 30.0

    async def call_data_agent(
        self,
        action: str,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """通過AI-Box Orchestrator調用Data Agent

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
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                return await self._call_data_agent(action, parameters, request)
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

    async def _call_data_agent(
        self,
        action: str,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """調用Data Agent（內部方法）

        Args:
            action: Data Agent操作類型
            parameters: 操作參數
            request: Agent服務請求

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

        # 通過Orchestrator API調用Data Agent
        url = f"{self._ai_box_api_url}/api/v1/agents/execute"
        headers: Dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._logger.debug(f"調用Data Agent: action={action}, url={url}, task_id={request.task_id}")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url,
                    json={
                        "agent_id": "data-agent",  # 外部Data Agent
                        "task": {
                            "task_id": f"{request.task_id}-data-query",
                            "task_data": data_agent_request,
                            "metadata": request.metadata or {},
                        },
                    },
                    headers=headers,
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
                task_result = result.get("result")
                if not task_result:
                    error_msg = "Data Agent響應中缺少result字段"
                    self._logger.error(error_msg)
                    raise RuntimeError(error_msg)

                # 如果result是字典且包含success字段，檢查是否成功
                if isinstance(task_result, dict):
                    if not task_result.get("success", False):
                        error_msg = task_result.get("error", "Data Agent查詢失敗")
                        self._logger.error(f"Data Agent查詢失敗: {error_msg}")
                        raise RuntimeError(f"Data Agent查詢失敗: {error_msg}")

                return task_result

        except httpx.TimeoutException as e:
            error_msg = f"Data Agent調用超時: {e}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Data Agent調用請求錯誤: {e}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Data Agent調用失敗: {e}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
