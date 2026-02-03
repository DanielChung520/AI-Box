# 代碼功能說明: FastAPI 服務設定載入與 Ollama 參數封裝
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""提供 API 服務使用的設定與 OLLAMA 參數。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple

from llm.router import LLMNodeConfig
from system.infra.config.config import get_config_section


@dataclass(frozen=True)
class OllamaSettings:
    """Ollama 相關設定。"""

    scheme: str
    host: str
    port: int
    timeout: float
    default_model: str
    embedding_model: str
    health_timeout: int
    api_token: str | None
    nodes: Tuple[LLMNodeConfig, ...]
    router_strategy: str
    router_cooldown: int

    @property
    def base_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


def _load_node_configs(
    raw_nodes: List[dict], fallback_host: str, fallback_port: int
) -> Tuple[LLMNodeConfig, ...]:
    if not raw_nodes:
        return (
            LLMNodeConfig(name="ollama-default", host=fallback_host, port=fallback_port, weight=1),
        )

    configs: List[LLMNodeConfig] = []
    for idx, node in enumerate(raw_nodes):
        try:
            configs.append(
                LLMNodeConfig(
                    name=node.get("name", f"ollama-node-{idx+1}"),
                    host=node["host"],
                    port=int(node.get("port", fallback_port)),
                    weight=int(node.get("weight", 1)),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Ollama node config missing key: {exc}") from exc
    return tuple(configs)


@lru_cache
def get_ollama_settings() -> OllamaSettings:
    """載入 Ollama 設定並允許環境變數覆寫."""

    section = get_config_section("services", "ollama", default={}) or {}
    scheme = os.getenv("OLLAMA_SCHEME", section.get("scheme", "http"))
    host = os.getenv("OLLAMA_REMOTE_HOST", section.get("host", "localhost"))
    port = int(os.getenv("OLLAMA_REMOTE_PORT", section.get("port", 11434)))
    timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", section.get("request_timeout", 60)))
    default_model = os.getenv("OLLAMA_DEFAULT_MODEL", section.get("default_model", "gpt-oss:120b"))
    embedding_model = os.getenv(
        "OLLAMA_EMBEDDING_MODEL", section.get("embedding_model", "nomic-embed-text")
    )
    health_timeout = int(section.get("health_timeout", 10))
    api_token = os.getenv("OLLAMA_API_TOKEN")
    router_cfg = section.get("router", {})
    router_strategy = router_cfg.get("strategy", "round_robin")
    router_cooldown = int(router_cfg.get("cooldown_seconds", 30))
    nodes = _load_node_configs(section.get("nodes", []), host, port)

    return OllamaSettings(
        scheme=scheme,
        host=host,
        port=port,
        timeout=timeout,
        default_model=default_model,
        embedding_model=embedding_model,
        health_timeout=health_timeout,
        api_token=api_token,
        nodes=nodes,
        router_strategy=router_strategy,
        router_cooldown=router_cooldown,
    )
