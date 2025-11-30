# 代碼功能說明: AutoGen 工作流設定載入工具
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""載入 workflows.autogen 配置並提供 Pydantic 設定結構。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.json"
_TEMPLATE_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.example.json"
_SETTINGS_CACHE: Dict[str, "AutoGenSettings"] = {}


class AutoGenSettings(BaseModel):
    """AutoGen 工作流設定。"""

    enable_planning: bool = Field(default=True, description="是否啟用 Execution Planning")
    max_steps: int = Field(default=20, ge=1, le=100, description="最大執行步驟數")
    planning_mode: str = Field(
        default="auto",
        description="規劃模式: auto/manual/hybrid",
    )
    auto_retry: bool = Field(default=True, description="是否啟用自動重試")
    max_rounds: int = Field(default=10, ge=1, le=50, description="最大迭代輪數")
    budget_tokens: int = Field(default=100000, ge=1000, description="Token 預算上限")
    default_llm: str = Field(default="gpt-oss:20b", description="預設 LLM 模型 ID")
    enable_tools: bool = Field(default=True, description="是否啟用工具/函式呼叫")
    enable_memory: bool = Field(
        default=True, description="是否啟用 Working Memory/Context Recorder"
    )
    checkpoint_enabled: bool = Field(default=True, description="是否啟用狀態持久化")
    checkpoint_dir: str = Field(
        default="./data/data/datasets/autogen/checkpoints",
        description="Checkpoint 保存目錄",
    )


def _read_json(path: Path) -> Dict[str, Any]:
    """讀取 JSON 配置文件。"""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _resolve_config_paths(custom_path: Optional[Union[str, Path]]) -> list[Path]:
    """解析配置路徑列表。"""
    paths: list[Path] = []
    if custom_path:
        paths.append(Path(custom_path))
    paths.extend([_DEFAULT_CONFIG_PATH, _TEMPLATE_CONFIG_PATH])
    return paths


def _extract_workflow_section(config: Dict[str, Any]) -> Dict[str, Any]:
    """提取 workflows.autogen 配置區塊。"""
    workflows = config.get("workflows") or {}
    return workflows.get("autogen") or {}


def _build_settings_from_sources(
    config_path: Optional[Union[str, Path]],
) -> AutoGenSettings:
    """從配置源構建設定對象。"""
    merged: Dict[str, Any] = {}
    for path in _resolve_config_paths(config_path):
        if path.exists():
            candidate = _extract_workflow_section(_read_json(path))
            if candidate:
                merged = candidate
                break
    return AutoGenSettings(**merged)


def load_autogen_settings(
    config_path: Optional[Union[str, Path]] = None,
    *,
    force_reload: bool = False,
) -> AutoGenSettings:
    """
    載入 AutoGen 工作流設定。

    Args:
        config_path: 自定義配置路徑
        force_reload: 是否強制重新載入

    Returns:
        AutoGenSettings 實例
    """
    cache_key = str(Path(config_path).resolve()) if config_path else "__default__"
    if not force_reload and cache_key in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[cache_key]

    settings = _build_settings_from_sources(config_path)
    _SETTINGS_CACHE[cache_key] = settings
    return settings


def clear_autogen_settings_cache() -> None:
    """清除設定快取（測試用）。"""
    _SETTINGS_CACHE.clear()
