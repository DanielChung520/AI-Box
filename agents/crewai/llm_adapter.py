# 代碼功能說明: CrewAI LLM 適配層
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""封裝 LLM Router 調用，提供 CrewAI 所需的 LLM 接口。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from llm.router import LLMNodeConfig, LLMNodeRouter
from system.infra.config.config import get_config_section

logger = logging.getLogger(__name__)


class OllamaLLMAdapter(BaseChatModel):
    """Ollama LLM 適配器，提供 CrewAI 所需的 ChatOpenAI 兼容接口。"""

    model_name: str
    base_url: Optional[str] = None
    timeout: int = 60
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    def __init__(
        self,
        model_name: str,
        base_url: Optional[str] = None,
        timeout: int = 60,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ):
        """初始化 Ollama LLM 適配器。"""
        # 將必需字段傳入父類初始化
        # BaseChatModel 不接受這些參數，但我們需要存儲它們
        super().__init__(**kwargs)  # type: ignore[call-arg]  # BaseChatModel 不接受這些參數，我們通過屬性存儲
        self._router: Optional[LLMNodeRouter] = None
        self._base_url = self.base_url  # 使用父類設置的 base_url
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

    @property
    def _llm_type(self) -> str:
        """返回 LLM 類型標識。"""
        return "ollama"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """同步生成響應（CrewAI 可能需要）。"""
        # CrewAI 主要使用異步接口，但保留同步接口以備不時之需
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """異步生成響應。"""
        # 選擇節點
        base_url = self._base_url
        if self._router:
            node = self._router.select_node()
            base_url = f"http://{node.host}:{node.port}"

        # 轉換消息格式
        ollama_messages = self._convert_messages(messages)

        # 構建請求
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": ollama_messages,
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
                return self._create_llm_result(message_content)
        except httpx.TimeoutException as exc:
            if self._router:
                node = self._router.select_node()
                self._router.mark_failure(node.name)
            logger.error(f"Ollama request timed out: {exc}")
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}")
            raise
        except Exception as exc:
            if self._router:
                node = self._router.select_node()
                self._router.mark_failure(node.name)
            logger.error(f"Ollama request error: {exc}")
            raise

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """將 LangChain 消息轉換為 Ollama 格式。"""
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                ollama_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                ollama_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                ollama_messages.append({"role": "assistant", "content": msg.content})
            else:
                # 默認作為用戶消息
                ollama_messages.append({"role": "user", "content": str(msg.content)})
        return ollama_messages

    def _create_llm_result(self, content: str) -> Any:
        """創建 LLM 結果對象。"""
        from langchain_core.outputs import ChatGeneration, ChatResult

        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
