# 代碼功能說明: SupervisionLayer - 行動監督層（timeout + 錯誤捕獲 + 重試）
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SupervisionConfig:
    """監督層配置"""

    timeout_seconds: float = 60.0
    max_retries: int = 1
    retry_delay_seconds: float = 1.0


@dataclass
class SupervisionResult:
    """監督層執行結果"""

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    retries_used: int = 0
    total_time_ms: float = 0.0


class SupervisionLayer:
    """
    非同步監督層

    提供 timeout + 錯誤捕獲 + 重試機制，用於包裝 BPA Agent 調用
    """

    def __init__(self) -> None:
        """初始化監督層"""
        self.logger = logger

    async def supervise(
        self,
        action_coro: Awaitable[Any],
        config: Optional[SupervisionConfig] = None,
        action_factory: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> SupervisionResult:
        """
        監督執行非同步行動，支援 timeout 和重試

        Args:
            action_coro: 主要執行的協程
            config: 監督配置（若為 None 則使用預設值）
            action_factory: 重試用的協程工廠函數。若提供，則重試時使用此工廠生成新協程

        Returns:
            SupervisionResult 包含執行結果、錯誤信息和重試次數
        """
        if config is None:
            config = SupervisionConfig()

        start_time = time.time()
        attempt = 0
        last_error: Optional[str] = None
        result: Optional[Any] = None
        max_attempts = config.max_retries + 1

        # 嘗試迴圈
        while attempt < max_attempts:
            try:
                self.logger.info(
                    "監督層開始執行行動",
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                )

                # 第一次嘗試使用主協程，後續使用工廠生成
                if attempt == 0:
                    current_coro = action_coro
                else:
                    if action_factory is None:
                        # 無工廠，無法重試，中止
                        self.logger.debug(
                            "停止重試：未提供 action_factory",
                            attempt=attempt + 1,
                        )
                        break
                    current_coro = action_factory()

                # 執行協程，應用 timeout
                result = await asyncio.wait_for(
                    current_coro,
                    timeout=config.timeout_seconds,
                )

                # 成功
                elapsed_ms = (time.time() - start_time) * 1000
                self.logger.info(
                    "監督層行動執行成功",
                    attempt=attempt + 1,
                    elapsed_ms=f"{elapsed_ms:.2f}",
                )

                return SupervisionResult(
                    success=True,
                    result=result,
                    retries_used=attempt,
                    total_time_ms=elapsed_ms,
                )

            except asyncio.TimeoutError:
                last_error = f"操作超時（{config.timeout_seconds}秒）"
                self.logger.warning(
                    "監督層行動超時",
                    attempt=attempt + 1,
                    timeout_seconds=config.timeout_seconds,
                )
                attempt += 1

            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    "監督層行動失敗",
                    attempt=attempt + 1,
                    error=last_error,
                    exc_info=True,
                )
                attempt += 1

            # 如果還有重試次數，等待後重試
            if attempt < max_attempts:
                self.logger.info(
                    "監督層等待後重試",
                    retry_delay_seconds=config.retry_delay_seconds,
                    next_attempt=attempt + 1,
                )
                await asyncio.sleep(config.retry_delay_seconds)

        # 所有嘗試都失敗
        elapsed_ms = (time.time() - start_time) * 1000
        self.logger.error(
            "監督層行動最終失敗",
            total_attempts=attempt,
            error=last_error,
            elapsed_ms=f"{elapsed_ms:.2f}",
        )

        return SupervisionResult(
            success=False,
            error=last_error or "未知錯誤",
            retries_used=max(0, attempt - 1),
            total_time_ms=elapsed_ms,
        )
