# 代碼功能說明: 外部 Agent 認證服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""外部 Agent 認證服務 - 實現嚴格的外部認證機制

外部 Agent 使用多層認證機制：
1. mTLS 證書驗證
2. API Key 驗證
3. 請求簽名驗證（HMAC-SHA256）
4. IP 白名單檢查
5. 服務器指紋驗證
"""

import logging
import hashlib
import hmac
from typing import Optional, Dict, Any
from ipaddress import ip_address, ip_network

from agents.services.auth.models import (
    AuthenticationResult,
    AuthenticationStatus,
    ExternalAuthConfig,
)
from agents.services.registry.registry import get_agent_registry

logger = logging.getLogger(__name__)


async def authenticate_external_agent(
    agent_id: str,
    request_ip: Optional[str] = None,
    request_signature: Optional[str] = None,
    request_body: Optional[Dict[str, Any]] = None,
    client_certificate: Optional[str] = None,
    api_key_header: Optional[str] = None,
    server_fingerprint: Optional[str] = None,
) -> AuthenticationResult:
    """
    認證外部 Agent

    執行多層認證檢查：
    1. 檢查 Agent 是否為外部 Agent
    2. 驗證服務器證書（mTLS）
    3. 驗證 API Key
    4. 驗證請求簽名
    5. 檢查 IP 白名單
    6. 驗證服務器指紋

    Args:
        agent_id: Agent ID
        request_ip: 請求來源 IP 地址
        request_signature: 請求簽名（HMAC-SHA256）
        request_body: 請求體（用於簽名驗證）
        client_certificate: 客戶端證書（用於 mTLS）

    Returns:
        認證結果
    """
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_id)

        if not agent_info:
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                agent_id=agent_id,
                message="Agent not found",
                error=f"Agent '{agent_id}' is not registered",
            )

        # 檢查是否為外部 Agent
        if agent_info.endpoints.is_internal:
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                agent_id=agent_id,
                message="Not an external agent",
                error=f"Agent '{agent_id}' is marked as internal agent",
            )

        permissions = agent_info.permissions
        config = ExternalAuthConfig(
            api_key=permissions.api_key,
            server_certificate=permissions.server_certificate,
            ip_whitelist=permissions.ip_whitelist,
            server_fingerprint=permissions.server_fingerprint,
            require_mtls=bool(permissions.server_certificate),
            require_signature=bool(permissions.api_key),
            require_ip_check=bool(permissions.ip_whitelist),
        )

        # 1. 驗證服務器證書（mTLS）
        if config.require_mtls or config.server_certificate:
            if not await verify_server_certificate(client_certificate, config):
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="Server certificate verification failed",
                    error="Invalid or missing server certificate",
                )

        # 2. 驗證 API Key
        if config.api_key:
            # 從請求頭或參數中獲取 API Key
            provided_api_key = api_key_header
            if not provided_api_key:
                logger.warning(f"API Key not provided for agent '{agent_id}'")
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="API Key verification failed",
                    error="API Key not provided",
                )

            # 驗證 API Key
            if not await verify_api_key(provided_api_key, config.api_key):
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="API Key verification failed",
                    error="Invalid API Key",
                )
            logger.debug(f"API Key verified for agent '{agent_id}'")

        # 3. 驗證請求簽名
        if config.require_signature and request_signature and request_body:
            if not await verify_signature(
                request_body, request_signature, config.api_key
            ):
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="Request signature verification failed",
                    error="Invalid request signature",
                )

        # 4. 檢查 IP 白名單
        if config.require_ip_check or config.ip_whitelist:
            if not check_ip_whitelist(request_ip, config.ip_whitelist):
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="IP address not in whitelist",
                    error=f"IP '{request_ip}' is not allowed",
                )

        # 5. 驗證服務器指紋
        if config.server_fingerprint:
            if not server_fingerprint:
                logger.warning(
                    f"Server fingerprint not provided for agent '{agent_id}'"
                )
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="Server fingerprint verification failed",
                    error="Server fingerprint not provided",
                )

            if not await verify_server_fingerprint(
                server_fingerprint, config.server_fingerprint
            ):
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    agent_id=agent_id,
                    message="Server fingerprint verification failed",
                    error="Server fingerprint mismatch",
                )
            logger.debug(f"Server fingerprint verified for agent '{agent_id}'")

        return AuthenticationResult(
            status=AuthenticationStatus.SUCCESS,
            agent_id=agent_id,
            message="External agent authenticated successfully",
            error=None,
        )

    except Exception as e:
        logger.error(f"External agent authentication error for '{agent_id}': {e}")
        return AuthenticationResult(
            status=AuthenticationStatus.ERROR,
            agent_id=agent_id,
            error=str(e),
        )


async def verify_api_key(provided_api_key: str, expected_api_key: str) -> bool:
    """
    驗證 API Key

    Args:
        provided_api_key: 提供的 API Key
        expected_api_key: 期望的 API Key

    Returns:
        API Key 是否有效
    """
    if not expected_api_key:
        return False

    # 使用時間安全的比較函數防止時間攻擊
    return hmac.compare_digest(
        provided_api_key.encode("utf-8"), expected_api_key.encode("utf-8")
    )


async def verify_server_certificate(
    client_certificate: Optional[str], config: ExternalAuthConfig
) -> bool:
    """
    驗證服務器證書（mTLS）

    Args:
        client_certificate: 客戶端提供的證書（PEM 格式）
        config: 外部認證配置

    Returns:
        證書是否有效

    實現完整的證書驗證邏輯：
    - 驗證證書格式
    - 檢查證書是否與配置的服務器證書匹配
    - 驗證證書簽名（簡化實現，實際生產環境應使用完整的證書鏈驗證）
    """
    if not config.server_certificate:
        # 如果未配置服務器證書，跳過驗證
        return True

    if not client_certificate:
        logger.warning("Client certificate not provided")
        return False

    try:
        # 簡化實現：直接比較證書內容
        # 實際生產環境應該：
        # 1. 使用 cryptography 庫解析證書
        # 2. 驗證證書鏈
        # 3. 檢查證書過期時間
        # 4. 驗證證書簽名
        # 5. 檢查證書的 Subject/Issuer 等信息

        # 這裡使用簡單的字符串比較（實際應使用證書指紋比較）
        # 為了安全，使用時間安全的比較
        return hmac.compare_digest(
            client_certificate.strip().encode("utf-8"),
            config.server_certificate.strip().encode("utf-8"),
        )
    except Exception as e:
        logger.error(f"Certificate verification error: {e}")
        return False


async def verify_signature(
    request_body: Dict[str, Any], signature: str, api_key: Optional[str]
) -> bool:
    """
    驗證請求簽名（HMAC-SHA256）

    Args:
        request_body: 請求體
        signature: 提供的簽名
        api_key: API Key（用於簽名）

    Returns:
        簽名是否有效
    """
    if not api_key:
        logger.warning("API Key not provided for signature verification")
        return False

    try:
        # 將請求體轉換為字符串（按鍵排序以確保一致性）
        import json

        request_str = json.dumps(request_body, sort_keys=True, separators=(",", ":"))

        # 計算 HMAC-SHA256 簽名
        expected_signature = hmac.new(
            api_key.encode("utf-8"), request_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # 使用時間安全的比較函數
        return hmac.compare_digest(expected_signature, signature)

    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def check_ip_whitelist(request_ip: Optional[str], ip_whitelist: list[str]) -> bool:
    """
    檢查 IP 地址是否在白名單中

    Args:
        request_ip: 請求來源 IP 地址
        ip_whitelist: IP 白名單列表（支持 CIDR 格式）

    Returns:
        IP 是否在白名單中
    """
    if not ip_whitelist:
        # 如果白名單為空，允許所有 IP
        return True

    if not request_ip:
        logger.warning("Request IP not provided")
        return False

    try:
        request_ip_obj = ip_address(request_ip)

        for allowed_ip in ip_whitelist:
            try:
                # 嘗試解析為單個 IP 地址
                allowed_ip_obj = ip_address(allowed_ip)
                if request_ip_obj == allowed_ip_obj:
                    return True
            except ValueError:
                # 如果不是單個 IP，嘗試解析為 CIDR 網絡
                try:
                    network = ip_network(allowed_ip, strict=False)
                    if request_ip_obj in network:
                        return True
                except ValueError:
                    logger.warning(f"Invalid IP whitelist entry: {allowed_ip}")

        return False

    except ValueError as e:
        logger.error(f"Invalid request IP '{request_ip}': {e}")
        return False


async def verify_server_fingerprint(
    server_fingerprint: str, expected_fingerprint: str
) -> bool:
    """
    驗證服務器指紋

    Args:
        server_fingerprint: 提供的服務器指紋
        expected_fingerprint: 期望的服務器指紋

    Returns:
        指紋是否匹配

    TODO: 實現服務器指紋驗證邏輯
    """
    if not expected_fingerprint:
        return True

    # 使用時間安全的比較函數
    return hmac.compare_digest(server_fingerprint.lower(), expected_fingerprint.lower())


def validate_external_agent_config(config: ExternalAuthConfig) -> bool:
    """
    驗證外部 Agent 認證配置

    Args:
        config: 外部認證配置

    Returns:
        配置是否有效
    """
    # 如果要求 mTLS，則必須提供服務器證書
    if config.require_mtls and not config.server_certificate:
        return False

    # 如果要求簽名，則必須提供 API Key
    if config.require_signature and not config.api_key:
        return False

    return True
