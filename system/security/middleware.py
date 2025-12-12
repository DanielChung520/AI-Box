# 代碼功能說明: 安全中間件
# 創建日期: 2025-11-26 01:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:30 (UTC+8)

"""安全中間件 - 提供請求級別的安全檢查。

此中間件可以在應用層面進行安全相關的檢查，例如：
- 請求速率限制（Rate Limiting）
- IP 白名單/黑名單
- 請求大小限制
- 安全頭設置

TODO (WBS 1.6.6): 實現輸入驗證框架
  - 實現請求速率限制（Rate Limiting）
  - 實現請求大小驗證
  - 實現安全頭設置（CSP, X-Frame-Options 等）

相關文件：
  - services/security/middleware.py (此文件)
  - services/security/rate_limit.py (待創建)
  - services/security/input_validation.py (待創建)
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from system.security.config import get_security_settings

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中間件 - 提供請求級別的安全檢查。

    此中間件會對每個請求進行安全相關的檢查。
    在開發模式下，某些檢查可能會被繞過。

    TODO (WBS 1.6.6): 實現完整的安全檢查功能
      - 請求速率限制
      - IP 白名單/黑名單檢查
      - 請求大小驗證
      - 安全頭設置
      - 輸入驗證
    """

    async def dispatch(self, request: Request, call_next):
        """處理請求並進行安全檢查。

        Args:
            request: FastAPI Request 對象
            call_next: 下一個中間件或路由處理器

        Returns:
            Response 對象
        """
        settings = get_security_settings()

        # 開發模式下，跳過大部分安全檢查
        if settings.should_bypass_auth:
            logger.debug(
                f"Security middleware bypassed for {request.url.path} (development mode)"
            )
            response = await call_next(request)
            # 即使繞過檢查，也設置一些基本的安全頭
            return self._add_security_headers(response)

        # 生產模式下的安全檢查
        # TODO (WBS 1.6.6): 實現以下安全檢查
        # - 速率限制檢查
        # - IP 白名單/黑名單檢查
        # - 請求大小驗證

        response = await call_next(request)

        # 添加安全頭
        response = self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> Response:
        """添加安全相關的 HTTP 頭。

        設置基本的安全 HTTP 頭，包括：
        - X-Content-Type-Options: 防止 MIME 類型嗅探
        - X-Frame-Options: 防止點擊劫持
        - Content-Security-Policy: 內容安全策略（基本配置）
        - Referrer-Policy: 控制引用信息
        - Strict-Transport-Security: 強制 HTTPS（僅在生產環境）
        """
        # 基本安全頭
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        # Content-Security-Policy（基本配置，允許自定義）
        # 注意：嚴格的 CSP 可能會影響應用功能，建議根據實際需求調整
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Strict-Transport-Security (HSTS) - 僅在生產環境啟用
        settings = get_security_settings()
        if not settings.is_development_mode:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
