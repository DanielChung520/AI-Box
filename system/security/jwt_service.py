# 代碼功能說明: JWT Token 服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""JWT Token 服務 - 提供 Token 簽發、驗證、刷新和黑名單管理功能。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import jwt, JWTError  # type: ignore[import-untyped]
import structlog

from system.security.config import get_security_settings, JWTConfig
from database.redis import get_redis_client

logger = structlog.get_logger(__name__)


class JWTService:
    """JWT Token 服務類"""

    def __init__(self, config: Optional[JWTConfig] = None):
        """初始化 JWT 服務。

        Args:
            config: JWT 配置，如果不提供則從全局配置讀取
        """
        settings = get_security_settings()
        self.config = config or settings.jwt
        self._redis = None

    @property
    def redis(self):
        """獲取 Redis 客戶端（懶加載）。"""
        if self._redis is None:
            try:
                self._redis = get_redis_client()
            except RuntimeError as e:
                logger.warning(
                    "Redis not available, blacklist will not work", error=str(e)
                )
        return self._redis

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """創建 Access Token。

        Args:
            data: Token payload 數據（通常包含 user_id, username 等）
            expires_delta: 過期時間增量，如果不提供則使用配置的默認值

        Returns:
            JWT Token 字符串
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.config.expiration_hours)

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access",
            }
        )

        encoded_jwt = jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )
        return encoded_jwt

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """創建 Refresh Token。

        Args:
            data: Token payload 數據（通常包含 user_id）
            expires_delta: 過期時間增量，如果不提供則使用配置的默認值

        Returns:
            JWT Refresh Token 字符串
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=self.config.refresh_expiration_days
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh",
            }
        )

        encoded_jwt = jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )
        return encoded_jwt

    def verify_token(
        self, token: str, token_type: str = "access"
    ) -> Optional[Dict[str, Any]]:
        """驗證 Token 並返回 payload。

        Args:
            token: JWT Token 字符串
            token_type: Token 類型（"access" 或 "refresh"）

        Returns:
            Token payload 字典，如果驗證失敗則返回 None
        """
        try:
            # 解碼 Token
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
            )

            # 檢查 Token 類型
            if payload.get("type") != token_type:
                logger.warning(
                    "Token type mismatch",
                    expected=token_type,
                    actual=payload.get("type"),
                )
                return None

            # 檢查 Token 是否在黑名單中
            if self.is_blacklisted(token):
                logger.warning("Token is blacklisted", token_id=payload.get("jti"))
                return None

            return payload

        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error during token verification", error=str(e))
            return None

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解碼 Token（不驗證簽名，僅用於獲取 payload）。

        注意：此方法不驗證簽名和過期時間，僅用於測試或特殊場景。

        Args:
            token: JWT Token 字符串

        Returns:
            Token payload 字典，如果解碼失敗則返回 None
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
            return payload
        except JWTError as e:
            logger.warning("Token decode failed", error=str(e))
            return None

    def add_to_blacklist(self, token: str, ttl: Optional[int] = None) -> bool:
        """將 Token 加入黑名單。

        Args:
            token: JWT Token 字符串
            ttl: Token 的 TTL（秒），如果不提供則從 Token 中提取

        Returns:
            是否成功添加到黑名單
        """
        if self.redis is None:
            logger.warning("Redis not available, cannot add token to blacklist")
            return False

        try:
            # 如果沒有提供 TTL，從 Token 中提取過期時間
            if ttl is None:
                payload = self.decode_token(token)
                if payload and "exp" in payload:
                    exp = datetime.fromtimestamp(payload["exp"])
                    now = datetime.utcnow()
                    if exp > now:
                        ttl = int((exp - now).total_seconds())
                    else:
                        # Token 已過期，不需要加入黑名單
                        return True
                else:
                    # 無法獲取過期時間，使用默認 TTL（24小時）
                    ttl = self.config.expiration_hours * 3600

            # 使用 Token 的 hash 作為 key（避免存儲完整 Token）
            token_hash = self._hash_token(token)
            key = f"jwt:blacklist:{token_hash}"

            self.redis.setex(key, ttl, "1")
            logger.info("Token added to blacklist", token_hash=token_hash, ttl=ttl)
            return True

        except Exception as e:
            logger.error("Failed to add token to blacklist", error=str(e))
            return False

    def is_blacklisted(self, token: str) -> bool:
        """檢查 Token 是否在黑名單中。

        修改時間：2025-12-09 - 修復 Redis 連接失敗時的錯誤處理

        Args:
            token: JWT Token 字符串

        Returns:
            如果 Token 在黑名單中則返回 True
        """
        # 修改時間：2025-12-09 - 開發模式下跳過黑名單檢查
        settings = get_security_settings()
        if settings.should_bypass_auth:
            logger.debug("Bypassing blacklist check in development mode")
            return False
        
        if self.redis is None:
            # Redis 不可用時，假設 Token 不在黑名單中
            # 這允許系統在 Redis 不可用時繼續工作（用於開發/測試環境）
            logger.debug("Redis not available, assuming token is not blacklisted")
            return False

        try:
            token_hash = self._hash_token(token)
            key = f"jwt:blacklist:{token_hash}"
            result = self.redis.get(key)
            return result is not None

        except Exception as e:
            logger.warning("Failed to check blacklist", error=str(e))
            # 修改時間：2025-12-09 - 修復：當 Redis 連接失敗時，不應該阻止所有 token 驗證
            # 如果 Redis 連接失敗，假設 token 不在黑名單中，允許驗證繼續
            # 這樣可以在 Redis 不可用時（如開發環境或網絡問題）系統仍能正常工作
            # 在生產環境中，應該確保 Redis 可用，但這裡採用寬鬆策略以確保系統可用性
            logger.warning(
                "Redis blacklist check failed, allowing token verification to proceed",
                error=str(e)
            )
            return False  # 連接失敗時，假設 token 不在黑名單中

    @staticmethod
    def _hash_token(token: str) -> str:
        """計算 Token 的哈希值（用於黑名單 key）。

        Args:
            token: JWT Token 字符串

        Returns:
            Token 的哈希值（SHA256）
        """
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()


# 全局 JWT 服務實例（單例模式）
_jwt_service: Optional[JWTService] = None


def get_jwt_service() -> JWTService:
    """獲取 JWT 服務實例（單例模式）。

    Returns:
        JWTService 實例
    """
    global _jwt_service

    if _jwt_service is None:
        _jwt_service = JWTService()

    return _jwt_service
