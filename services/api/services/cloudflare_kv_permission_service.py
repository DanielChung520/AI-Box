# 代碼功能說明: Cloudflare KV Store 權限管理服務
# 創建日期: 2026-01-17 18:48 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:48 UTC+8

"""Cloudflare KV Store 權限管理服務 - 自動化 Agent 權限配置"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class CloudflareKVPermissionService:
    """Cloudflare KV Store 權限管理服務"""

    def __init__(self):
        """初始化 Cloudflare KV Store 權限管理服務"""
        # Cloudflare API 配置（從環境變數讀取）
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.namespace_id = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID")

        # API 基礎 URL
        self.api_base = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces/{self.namespace_id}"

        # HTTP 客戶端配置
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _check_config(self) -> bool:
        """檢查配置是否完整"""
        if not self.api_token or not self.account_id or not self.namespace_id:
            logger.warning(
                "Cloudflare KV Store not configured. Missing: "
                f"API_TOKEN={bool(self.api_token)}, "
                f"ACCOUNT_ID={bool(self.account_id)}, "
                f"NAMESPACE_ID={bool(self.namespace_id)}"
            )
            return False
        return True

    async def set_agent_permissions(
        self,
        tenant_id: str,
        agent_id: str,
        permissions: Dict[str, Any],
    ) -> bool:
        """
        設置 Agent 權限到 Cloudflare KV Store

        Args:
            tenant_id: 租戶 ID
            agent_id: Agent ID
            permissions: 權限配置

        Returns:
            是否設置成功
        """
        if not self._check_config():
            logger.warning(
                f"Cloudflare KV Store not configured, skipping permission set: agent_id={agent_id}"
            )
            return False

        try:
            # KV Key 格式：permissions:{tenant_id}:{agent_id}
            kv_key = f"permissions:{tenant_id}:{agent_id}"
            kv_value = json.dumps(permissions)

            # 調用 Cloudflare KV API 設置 Key-Value
            url = f"{self.api_base}/values/{kv_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    content=kv_value,
                )

                if response.status_code == 200:
                    logger.info(
                        f"Agent permissions set successfully: agent_id={agent_id}, tenant_id={tenant_id}"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to set agent permissions: agent_id={agent_id}, "
                        f"status={response.status_code}, response={response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"Cloudflare KV API timeout: agent_id={agent_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to set agent permissions: agent_id={agent_id}, error={str(e)}",
                exc_info=True,
            )
            return False

    async def get_agent_permissions(
        self,
        tenant_id: str,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        獲取 Agent 權限從 Cloudflare KV Store

        Args:
            tenant_id: 租戶 ID
            agent_id: Agent ID

        Returns:
            權限配置，如果不存在則返回 None
        """
        if not self._check_config():
            logger.warning(
                f"Cloudflare KV Store not configured, skipping permission get: agent_id={agent_id}"
            )
            return None

        try:
            # KV Key 格式：permissions:{tenant_id}:{agent_id}
            kv_key = f"permissions:{tenant_id}:{agent_id}"

            # 調用 Cloudflare KV API 獲取 Value
            url = f"{self.api_base}/values/{kv_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    permissions = json.loads(response.text)
                    logger.info(f"Agent permissions retrieved successfully: agent_id={agent_id}")
                    return permissions
                elif response.status_code == 404:
                    logger.info(f"Agent permissions not found: agent_id={agent_id}")
                    return None
                else:
                    logger.error(
                        f"Failed to get agent permissions: agent_id={agent_id}, "
                        f"status={response.status_code}, response={response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error(f"Cloudflare KV API timeout: agent_id={agent_id}")
            return None
        except Exception as e:
            logger.error(
                f"Failed to get agent permissions: agent_id={agent_id}, error={str(e)}",
                exc_info=True,
            )
            return None

    async def delete_agent_permissions(
        self,
        tenant_id: str,
        agent_id: str,
    ) -> bool:
        """
        刪除 Agent 權限從 Cloudflare KV Store

        Args:
            tenant_id: 租戶 ID
            agent_id: Agent ID

        Returns:
            是否刪除成功
        """
        if not self._check_config():
            logger.warning(
                f"Cloudflare KV Store not configured, skipping permission delete: agent_id={agent_id}"
            )
            return False

        try:
            # KV Key 格式：permissions:{tenant_id}:{agent_id}
            kv_key = f"permissions:{tenant_id}:{agent_id}"

            # 調用 Cloudflare KV API 刪除 Key
            url = f"{self.api_base}/values/{kv_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=self.headers)

                if response.status_code == 200:
                    logger.info(f"Agent permissions deleted successfully: agent_id={agent_id}")
                    return True
                elif response.status_code == 404:
                    logger.info(
                        f"Agent permissions not found (already deleted): agent_id={agent_id}"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to delete agent permissions: agent_id={agent_id}, "
                        f"status={response.status_code}, response={response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"Cloudflare KV API timeout: agent_id={agent_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to delete agent permissions: agent_id={agent_id}, error={str(e)}",
                exc_info=True,
            )
            return False

    async def update_agent_permissions(
        self,
        tenant_id: str,
        agent_id: str,
        permissions: Dict[str, Any],
    ) -> bool:
        """
        更新 Agent 權限（實際上是重新設置）

        Args:
            tenant_id: 租戶 ID
            agent_id: Agent ID
            permissions: 權限配置

        Returns:
            是否更新成功
        """
        # 更新操作等同於設置操作（Cloudflare KV Store 會覆蓋舊值）
        return await self.set_agent_permissions(tenant_id, agent_id, permissions)

    async def list_agent_permissions(
        self,
        tenant_id: str,
        prefix: Optional[str] = None,
    ) -> List[str]:
        """
        列出租戶下所有 Agent 權限的 Key

        Args:
            tenant_id: 租戶 ID
            prefix: Key 前綴過濾

        Returns:
            Agent 權限 Key 列表
        """
        if not self._check_config():
            logger.warning("Cloudflare KV Store not configured, skipping permission list")
            return []

        try:
            # 構建前綴
            key_prefix = f"permissions:{tenant_id}:"
            if prefix:
                key_prefix += prefix

            # 調用 Cloudflare KV API 列出 Keys
            url = f"{self.api_base}/keys"
            params = {"prefix": key_prefix, "limit": 1000}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    keys = [item["name"] for item in data.get("result", [])]
                    logger.info(
                        f"Agent permissions listed successfully: tenant_id={tenant_id}, count={len(keys)}"
                    )
                    return keys
                else:
                    logger.error(
                        f"Failed to list agent permissions: tenant_id={tenant_id}, "
                        f"status={response.status_code}, response={response.text}"
                    )
                    return []

        except httpx.TimeoutException:
            logger.error(f"Cloudflare KV API timeout: tenant_id={tenant_id}")
            return []
        except Exception as e:
            logger.error(
                f"Failed to list agent permissions: tenant_id={tenant_id}, error={str(e)}",
                exc_info=True,
            )
            return []


# 單例服務
_permission_service: Optional[CloudflareKVPermissionService] = None


def get_cloudflare_kv_permission_service() -> CloudflareKVPermissionService:
    """獲取 Cloudflare KV Store 權限管理服務單例"""
    global _permission_service
    if _permission_service is None:
        _permission_service = CloudflareKVPermissionService()
    return _permission_service
