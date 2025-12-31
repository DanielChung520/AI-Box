# 代碼功能說明: 工具註冊清單載入器
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊清單載入器

從 JSON 文件或 ArangoDB 讀取工具註冊清單，供 AI 任務分析使用。
優先從 ArangoDB 讀取，如果不可用則從 JSON 文件讀取。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# 工具註冊清單 JSON 文件路徑
TOOLS_REGISTRY_JSON = Path(__file__).parent / "tools_registry.json"

# 是否優先使用 ArangoDB（默認 True）
USE_ARANGODB_FIRST = True


def _load_from_arangodb() -> Optional[Dict[str, Any]]:
    """
    從 ArangoDB 載入工具註冊清單

    Returns:
        工具註冊清單字典，如果失敗返回 None
    """
    try:
        from services.api.services.tool_registry_store_service import (
            get_tool_registry_store_service,
        )

        service = get_tool_registry_store_service()
        tools = service.list_tools(is_active=True)

        # 轉換為 JSON 格式
        tools_list = []
        for tool in tools:
            tools_list.append(
                {
                    "name": tool.name,
                    "version": tool.version,
                    "category": tool.category,
                    "description": tool.description,
                    "purpose": tool.purpose,
                    "use_cases": tool.use_cases,
                    "input_parameters": tool.input_parameters,
                    "output_fields": tool.output_fields,
                    "example_scenarios": tool.example_scenarios,
                }
            )

        return {
            "version": "1.0.0",
            "last_updated": (
                tools[0].updated_at.isoformat() if tools and tools[0].updated_at else None
            ),
            "description": "AI-Box 工具註冊清單，從 ArangoDB 載入",
            "tools": tools_list,
        }
    except Exception as e:
        logger.warning("tools_registry_arangodb_load_failed", error=str(e))
        return None


def _load_from_json() -> Dict[str, Any]:
    """
    從 JSON 文件載入工具註冊清單

    Returns:
        工具註冊清單字典

    Raises:
        FileNotFoundError: JSON 文件不存在
        json.JSONDecodeError: JSON 解析失敗
    """
    if not TOOLS_REGISTRY_JSON.exists():
        raise FileNotFoundError(f"工具註冊清單文件不存在: {TOOLS_REGISTRY_JSON}")

    try:
        with open(TOOLS_REGISTRY_JSON, "r", encoding="utf-8") as f:
            registry = json.load(f)
        logger.info("tools_registry_loaded_from_json", path=str(TOOLS_REGISTRY_JSON))
        return registry
    except json.JSONDecodeError as e:
        logger.error("tools_registry_json_error", error=str(e))
        raise


def load_tools_registry() -> Dict[str, Any]:
    """
    載入工具註冊清單

    優先從 ArangoDB 讀取，如果不可用則從 JSON 文件讀取。

    Returns:
        工具註冊清單字典

    Raises:
        FileNotFoundError: JSON 文件不存在（當 ArangoDB 和 JSON 都不可用時）
        json.JSONDecodeError: JSON 解析失敗
    """
    # 優先從 ArangoDB 讀取
    if USE_ARANGODB_FIRST:
        registry = _load_from_arangodb()
        if registry is not None:
            logger.info("tools_registry_loaded_from_arangodb")
            return registry
        logger.info("tools_registry_fallback_to_json")

    # 回退到 JSON 文件
    return _load_from_json()


def get_tool_info(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    獲取指定工具的詳細信息

    Args:
        tool_name: 工具名稱

    Returns:
        工具信息字典，如果不存在返回 None
    """
    registry = load_tools_registry()
    tools = registry.get("tools", [])

    for tool in tools:
        if tool.get("name") == tool_name:
            return tool

    return None


def list_all_tools() -> List[Dict[str, Any]]:
    """
    列出所有工具的詳細信息

    Returns:
        工具信息列表
    """
    registry = load_tools_registry()
    return registry.get("tools", [])


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    """
    根據類別獲取工具列表

    Args:
        category: 工具類別（如 "時間與日期"、"天氣" 等）

    Returns:
        該類別下的工具列表
    """
    registry = load_tools_registry()
    tools = registry.get("tools", [])

    return [tool for tool in tools if tool.get("category") == category]


def search_tools(keyword: str) -> List[Dict[str, Any]]:
    """
    根據關鍵字搜索工具

    Args:
        keyword: 搜索關鍵字（會搜索名稱、描述、用途、使用場景）

    Returns:
        匹配的工具列表
    """
    registry = load_tools_registry()
    tools = registry.get("tools", [])
    keyword_lower = keyword.lower()

    results = []
    for tool in tools:
        # 搜索名稱
        if keyword_lower in tool.get("name", "").lower():
            results.append(tool)
            continue

        # 搜索描述
        if keyword_lower in tool.get("description", "").lower():
            results.append(tool)
            continue

        # 搜索用途
        if keyword_lower in tool.get("purpose", "").lower():
            results.append(tool)
            continue

        # 搜索使用場景
        use_cases = tool.get("use_cases", [])
        for use_case in use_cases:
            if keyword_lower in use_case.lower():
                results.append(tool)
                break

    return results


def get_tools_for_task_analysis() -> Dict[str, Any]:
    """
    獲取用於 AI 任務分析的工具清單

    返回格式化的工具清單，包含每個工具的用途、使用場景等信息，
    方便 AI 任務分析時理解工具的用途和選擇合適的工具。

    Returns:
        格式化的工具清單字典
    """
    registry = load_tools_registry()
    tools = registry.get("tools", [])

    # 格式化為更適合 AI 分析的結構
    formatted_tools = []
    for tool in tools:
        formatted_tool = {
            "name": tool.get("name"),
            "category": tool.get("category"),
            "description": tool.get("description"),
            "purpose": tool.get("purpose"),
            "use_cases": tool.get("use_cases", []),
            "example_scenarios": tool.get("example_scenarios", []),
            "input_parameters": tool.get("input_parameters", {}),
            "output_fields": tool.get("output_fields", {}),
        }
        formatted_tools.append(formatted_tool)

    return {
        "version": registry.get("version"),
        "last_updated": registry.get("last_updated"),
        "description": registry.get("description"),
        "tools": formatted_tools,
        "total_count": len(formatted_tools),
    }
