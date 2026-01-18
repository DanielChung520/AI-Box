# 代碼功能說明: Capability Adapter API 調用適配器
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter API 調用適配器

實現 API 調用的適配器，限制端點白名單，記錄審計日誌。
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from agents.services.capability_adapter.adapter import CapabilityAdapter
from agents.services.capability_adapter.models import AdapterResult, ValidationResult

logger = logging.getLogger(__name__)


class APIAdapter(CapabilityAdapter):
    """API 調用適配器"""

    def __init__(self, allowed_endpoints: Optional[List[str]] = None):
        """
        初始化 API 調用適配器

        Args:
            allowed_endpoints: 允許的 API 端點列表（白名單），如果不提供則從配置文件加載
        """
        if allowed_endpoints is None:
            from agents.services.capability_adapter.config_loader import (
                CapabilityAdapterConfigLoader,
            )

            config_loader = CapabilityAdapterConfigLoader()
            allowed_endpoints = config_loader.get_api_adapter_endpoints()

        super().__init__(allowed_scopes=allowed_endpoints or [])
        self.allowed_endpoints = allowed_endpoints or []

    def validate(self, params: Dict[str, Any]) -> ValidationResult:
        """
        驗證參數

        Args:
            params: 參數字典，應包含 "url" 或 "endpoint" 字段

        Returns:
            ValidationResult 對象
        """
        url = params.get("url") or params.get("endpoint")

        if not url:
            return ValidationResult(valid=False, reason="url or endpoint is required")

        # 檢查端點是否在白名單中
        if not self.check_scope(url):
            return ValidationResult(valid=False, reason=f"Endpoint not in allowed list: {url}")

        return ValidationResult(valid=True)

    async def execute(self, capability: str, params: Dict[str, Any]) -> AdapterResult:
        """
        執行 API 調用

        支持的能力：
        - get: GET 請求
        - post: POST 請求
        - put: PUT 請求
        - delete: DELETE 請求

        Args:
            capability: 能力名稱
            params: 參數字典

        Returns:
            AdapterResult 對象
        """
        # 驗證參數
        validation = self.validate(params)
        if not validation.valid:
            return AdapterResult(success=False, error=validation.reason)

        url = params.get("url") or params.get("endpoint")
        method = capability.upper()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, params=params.get("params"))
                elif method == "POST":
                    response = await client.post(
                        url, json=params.get("json"), data=params.get("data")
                    )
                elif method == "PUT":
                    response = await client.put(
                        url, json=params.get("json"), data=params.get("data")
                    )
                elif method == "DELETE":
                    response = await client.delete(url)
                else:
                    return AdapterResult(success=False, error=f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                audit_log = self.create_audit_log(
                    capability,
                    {"url": url, "method": method, "status_code": response.status_code},
                    AdapterResult(success=True),
                )

                return AdapterResult(
                    success=True,
                    result={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                        "response": (
                            response.json()
                            if response.headers.get("content-type", "").startswith(
                                "application/json"
                            )
                            else response.text
                        ),
                    },
                    audit_log=audit_log,
                )
        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            return AdapterResult(success=False, error=str(e))
