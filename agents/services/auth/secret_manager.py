# 代碼功能說明: Secret Manager 服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Secret Manager - 管理外部 Agent 的 Secret ID/Key

提供以下功能：
1. 生成 Secret ID/Key 對
2. 驗證 Secret ID/Key
3. 檢查 Secret 是否已綁定到 Agent
4. 將 Secret ID 綁定到 Agent ID
5. 撤銷 Secret（未來功能）
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SecretStatus(str, Enum):
    """Secret 狀態"""

    ACTIVE = "active"
    BOUND = "bound"  # 已綁定到 Agent
    REVOKED = "revoked"
    EXPIRED = "expired"


class SecretInfo:
    """Secret 信息（簡化版，未來可以擴展為數據庫模型）"""

    def __init__(
        self,
        secret_id: str,
        secret_key_hash: str,  # 存儲的是哈希值，不是原始值
        status: SecretStatus = SecretStatus.ACTIVE,
        bound_agent_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        bound_at: Optional[datetime] = None,
    ):
        self.secret_id = secret_id
        self.secret_key_hash = secret_key_hash
        self.status = status
        self.bound_agent_id = bound_agent_id
        self.created_at = created_at or datetime.now()
        self.bound_at = bound_at


class SecretManager:
    """Secret Manager - 管理外部 Agent 的 Secret ID/Key"""

    def __init__(self, storage: Optional[Dict[str, SecretInfo]] = None):
        """
        初始化 Secret Manager

        Args:
            storage: 存儲字典（暫時使用內存，未來應使用數據庫）
        """
        self._storage: Dict[str, SecretInfo] = storage or {}
        self._logger = logger

        # 從環境變量加載預設的 Secret（用於測試）
        self._load_secret_from_env()

    def _load_secret_from_env(self) -> None:
        """
        從環境變量加載預設的 Secret（用於測試環境）

        環境變量：
        - AGENT_SECRET_ID: Secret ID
        - AGENT_SECRET_KEY: Secret Key（原始值，用於驗證）
        """
        secret_id = os.getenv("AGENT_SECRET_ID")
        secret_key = os.getenv("AGENT_SECRET_KEY")

        if secret_id and secret_key:
            # 計算 Secret Key 的哈希值
            secret_key_hash = self._hash_secret_key(secret_key)

            # 創建 Secret 信息
            secret_info = SecretInfo(
                secret_id=secret_id,
                secret_key_hash=secret_key_hash,
                status=SecretStatus.ACTIVE,
            )

            # 存儲到內存（如果已經存在，不覆蓋）
            if secret_id not in self._storage:
                self._storage[secret_id] = secret_info
                self._logger.info(f"Loaded default secret from environment: {secret_id}")
            else:
                self._logger.warning(
                    f"Secret ID {secret_id} already exists, skipping environment variable load"
                )
        elif secret_id or secret_key:
            self._logger.warning(
                "AGENT_SECRET_ID and AGENT_SECRET_KEY must both be set, "
                "or both unset. Ignoring partial configuration."
            )

    def generate_secret_pair(self, organization: Optional[str] = None) -> Tuple[str, str]:
        """
        生成 Secret ID 和 Secret Key 對

        Args:
            organization: 組織名稱（用於生成更有意義的 Secret ID）

        Returns:
            (Secret ID, Secret Key) 元組
        """
        # 生成 Secret ID
        # 格式：aibox-{org_prefix}-{timestamp}-{random}
        timestamp = int(time.time())
        random_suffix = secrets.token_hex(4)

        if organization:
            org_prefix = organization[:8].lower().replace(" ", "-")
            secret_id = f"aibox-{org_prefix}-{timestamp}-{random_suffix}"
        else:
            secret_id = f"aibox-{timestamp}-{random_suffix}"

        # 生成 Secret Key（32 字節，Base64 URL Safe）
        secret_key = secrets.token_urlsafe(32)

        # 計算 Secret Key 的哈希值（用於存儲）
        secret_key_hash = self._hash_secret_key(secret_key)

        # 存儲 Secret 信息
        secret_info = SecretInfo(
            secret_id=secret_id,
            secret_key_hash=secret_key_hash,
            status=SecretStatus.ACTIVE,
        )
        self._storage[secret_id] = secret_info

        self._logger.info(f"Generated secret pair for ID: {secret_id}")

        return secret_id, secret_key

    def verify_secret(self, secret_id: str, secret_key: str) -> bool:
        """
        驗證 Secret ID 和 Secret Key

        Args:
            secret_id: Secret ID
            secret_key: Secret Key

        Returns:
            是否驗證通過
        """
        if not secret_id or not secret_key:
            return False

        # 查找 Secret 信息
        secret_info = self._storage.get(secret_id)
        if not secret_info:
            self._logger.warning(f"Secret ID not found: {secret_id}")
            return False

        # 檢查狀態
        if secret_info.status != SecretStatus.ACTIVE:
            self._logger.warning(
                f"Secret ID '{secret_id}' is not active, status: {secret_info.status}"
            )
            return False

        # 驗證 Secret Key
        secret_key_hash = self._hash_secret_key(secret_key)
        if not hmac.compare_digest(secret_key_hash, secret_info.secret_key_hash):
            self._logger.warning(f"Invalid secret key for ID: {secret_id}")
            return False

        self._logger.debug(f"Secret verified successfully for ID: {secret_id}")
        return True

    def is_secret_bound(self, secret_id: str) -> bool:
        """
        檢查 Secret 是否已綁定到 Agent

        Args:
            secret_id: Secret ID

        Returns:
            是否已綁定
        """
        secret_info = self._storage.get(secret_id)
        if not secret_info:
            return False

        return secret_info.status == SecretStatus.BOUND and secret_info.bound_agent_id is not None

    def bind_secret_to_agent(self, secret_id: str, agent_id: str) -> bool:
        """
        將 Secret ID 綁定到 Agent ID

        Args:
            secret_id: Secret ID
            agent_id: Agent ID

        Returns:
            是否綁定成功
        """
        secret_info = self._storage.get(secret_id)
        if not secret_info:
            self._logger.error(f"Secret ID not found: {secret_id}")
            return False

        if secret_info.status != SecretStatus.ACTIVE:
            self._logger.error(f"Cannot bind secret '{secret_id}', status is: {secret_info.status}")
            return False

        if secret_info.bound_agent_id:
            self._logger.warning(
                f"Secret '{secret_id}' is already bound to agent '{secret_info.bound_agent_id}'"
            )
            return False

        # 更新狀態
        secret_info.status = SecretStatus.BOUND
        secret_info.bound_agent_id = agent_id
        secret_info.bound_at = datetime.now()

        self._logger.info(f"Bound secret '{secret_id}' to agent '{agent_id}'")
        return True

    def get_secret_info(self, secret_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取 Secret 信息

        Args:
            secret_id: Secret ID

        Returns:
            Secret 信息字典（不包含敏感信息）
        """
        secret_info = self._storage.get(secret_id)
        if not secret_info:
            return None

        return {
            "secret_id": secret_info.secret_id,
            "status": secret_info.status.value,
            "bound_agent_id": secret_info.bound_agent_id,
            "created_at": (secret_info.created_at.isoformat() if secret_info.created_at else None),
            "bound_at": (secret_info.bound_at.isoformat() if secret_info.bound_at else None),
        }

    def revoke_secret(self, secret_id: str) -> bool:
        """
        撤銷 Secret（未來功能）

        Args:
            secret_id: Secret ID

        Returns:
            是否撤銷成功
        """
        secret_info = self._storage.get(secret_id)
        if not secret_info:
            return False

        secret_info.status = SecretStatus.REVOKED
        self._logger.info(f"Revoked secret: {secret_id}")
        return True

    @staticmethod
    def _hash_secret_key(secret_key: str) -> str:
        """
        計算 Secret Key 的哈希值（用於安全存儲）

        Args:
            secret_key: Secret Key

        Returns:
            哈希值（SHA-256）
        """
        return hashlib.sha256(secret_key.encode("utf-8")).hexdigest()


# 全局 Secret Manager 實例
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """
    獲取 Secret Manager 單例

    Returns:
        SecretManager 實例
    """
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager
