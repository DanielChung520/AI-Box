# 代碼功能說明: 工作流設定載入工具
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""載入 workflows.* 配置並提供 Pydantic 設定結構。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.json"
_TEMPLATE_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.example.json"
_SETTINGS_CACHE: Dict[str, "LangChainGraphSettings"] = {}


class LangGraphStateStoreSettings(BaseModel):
    """狀態儲存相關設定。"""

    backend: str = Field(default="memory", description="checkpoint backend 類型: memory/redis")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis 連線字串")
    namespace: str = Field(default="ai-box:workflow:langgraph", description="Redis key 命名空間")
    ttl_seconds: int = Field(default=3600, ge=60, description="checkpoint 保存時間")


class LangGraphTelemetrySettings(BaseModel):
    """可觀測性開關。"""

    emit_metrics: bool = Field(default=True, description="是否輸出 Prometheus 指標")
    emit_traces: bool = Field(default=True, description="是否輸出 tracing 事件")
    emit_logs: bool = Field(default=True, description="是否輸出結構化日誌")


class LangChainGraphSettings(BaseModel):
    """LangChain/Graph 工作流設定。"""

    enable_memory: bool = Field(
        default=True, description="是否啟用 Working Memory/Context Recorder"
    )
    enable_rag: bool = Field(default=True, description="是否啟用 RAG 擴充")
    enable_tools: bool = Field(default=True, description="是否允許工具/函式呼叫")
    max_iterations: int = Field(default=10, ge=1, le=50, description="執行節點最大迭代數")
    default_llm: str = Field(default="gpt-oss:20b", description="預設 LLM 模型 ID")
    state_store: LangGraphStateStoreSettings = Field(default_factory=LangGraphStateStoreSettings)
    telemetry: LangGraphTelemetrySettings = Field(default_factory=LangGraphTelemetrySettings)
    prompt_template_path: Optional[str] = Field(
        default=None,
        description="自訂 Prompt 模板路徑，若為 None 則使用內建模板",
    )


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _resolve_config_paths(custom_path: Optional[Union[str, Path]]) -> list[Path]:
    paths: list[Path] = []
    if custom_path:
        paths.append(Path(custom_path))
    paths.extend([_DEFAULT_CONFIG_PATH, _TEMPLATE_CONFIG_PATH])
    return paths


def _extract_workflow_section(config: Dict[str, Any]) -> Dict[str, Any]:
    workflows = config.get("workflows") or {}
    return workflows.get("langchain_graph") or {}


def _build_settings_from_sources(
    config_path: Optional[Union[str, Path]],
) -> LangChainGraphSettings:
    merged: Dict[str, Any] = {}
    for path in _resolve_config_paths(config_path):
        if path.exists():
            candidate = _extract_workflow_section(_read_json(path))
            if candidate:
                merged = candidate
                break
    return LangChainGraphSettings(**merged)


def load_langchain_graph_settings(
    config_path: Optional[Union[str, Path]] = None,
    *,
    force_reload: bool = False,
) -> LangChainGraphSettings:
    """
    載入 LangChain/Graph 工作流設定。
    """

    cache_key = str(Path(config_path).resolve()) if config_path else "__default__"
    if not force_reload and cache_key in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[cache_key]

    settings = _build_settings_from_sources(config_path)
    _SETTINGS_CACHE[cache_key] = settings
    return settings


def clear_langchain_graph_settings_cache() -> None:
    """清除設定快取（測試用）。"""

    _SETTINGS_CACHE.clear()
