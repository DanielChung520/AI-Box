# 代碼功能說明: AutoGen LLM 適配層
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""封裝 LLM Router 調用，提供 AutoGen 所需的 LLM 接口。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from core.config import get_config_section
from llm.router import LLMNodeConfig, LLMNodeRouter

logger = logging.getLogger(__name__)


class AutoGenLLMAdapter:
    """AutoGen LLM 適配器，提供 AutoGen 所需的 LLM 接口。"""

    def __init__(
        self,
        model_name: str,
        base_url: Optional[str] = None,
        timeout: int = 60,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """
        初始化 AutoGen LLM 適配器。

        Args:
            model_name: 模型名稱
            base_url: 基礎 URL（可選）
            timeout: 超時時間（秒）
            temperature: 溫度參數
            max_tokens: 最大 token 數
        """
        self.model_name = model_name
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._router: Optional[LLMNodeRouter] = None
        self._base_url = base_url
        self._init_router()

    def _init_router(self) -> None:
        """初始化 LLM 節點路由器。"""
        ollama_cfg = get_config_section("services", "ollama", default={}) or {}
        nodes_cfg: List[LLMNodeConfig] = []

        for idx, node in enumerate(ollama_cfg.get("nodes", [])):
            try:
                nodes_cfg.append(
                    LLMNodeConfig(
                        name=node.get("name", f"ollama-node-{idx+1}"),
                        host=node["host"],
                        port=int(node.get("port", 11434)),
                        weight=int(node.get("weight", 1)),
                    )
                )
            except KeyError as exc:
                logger.warning("忽略不完整的 Ollama 節點設定（index=%s）: %s", idx, exc)

        if nodes_cfg:
            router_cfg = ollama_cfg.get("router", {}) or {}
            self._router = LLMNodeRouter(
                nodes=nodes_cfg,
                strategy=router_cfg.get("strategy", "round_robin"),
                cooldown_seconds=int(router_cfg.get("cooldown_seconds", 30)),
            )
            # 設置第一個節點作為 base_url
            if not self._base_url:
                first_node = self._router.select_node()
                self._base_url = f"http://{first_node.host}:{first_node.port}"
        elif self._base_url:
            # 使用提供的 base_url
            pass
        else:
            # 使用默認配置
            ollama_cfg = get_config_section("services", "ollama", default={}) or {}
            host = ollama_cfg.get("host", "localhost")
            port = ollama_cfg.get("port", 11434)
            self._base_url = f"http://{host}:{port}"

    def _get_base_url(self) -> str:
        """獲取當前可用的 base URL。"""
        if self._router:
            node = self._router.select_node()
            return f"http://{node.host}:{node.port}"
        return self._base_url

    async def generate(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        生成響應（異步）。

        Args:
            messages: 消息列表，格式為 [{"role": "user", "content": "..."}]
            stop: 停止詞列表
            **kwargs: 其他參數

        Returns:
            生成的文本內容
        """
        base_url = self._get_base_url()

        # 構建請求
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }

        options: Dict[str, Any] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.max_tokens is not None:
            options["num_predict"] = self.max_tokens
        if stop:
            options["stop"] = stop

        if options:
            payload["options"] = options

        # 發送請求
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

                if self._router:
                    node = self._router.select_node()
                    self._router.mark_success(node.name)

                # 解析響應
                message_content = result.get("message", {}).get("content", "")
                return message_content
        except httpx.TimeoutException as exc:
            if self._router:
                node = self._router.select_node()
                self._router.mark_failure(node.name)
            logger.error(f"Ollama request timed out: {exc}")
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}"
            )
            raise
        except Exception as exc:
            if self._router:
                node = self._router.select_node()
                self._router.mark_failure(node.name)
            logger.error(f"Ollama request error: {exc}")
            raise

    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        生成響應（同步）。

        Args:
            messages: 消息列表
            stop: 停止詞列表
            **kwargs: 其他參數

        Returns:
            生成的文本內容
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.generate(messages, stop=stop, **kwargs))
