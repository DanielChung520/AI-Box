# 代碼功能說明: API 路由模組初始化文件
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""API 路由模組 - 提供所有 API 端點的路由定義"""

from . import (
    health,
    agents,
    task_analyzer,
    orchestrator,
    planning,
    execution,
    review,
    mcp,
    chromadb,
    llm,
    file_upload,
    chunk_processing,
    file_metadata,
    file_management,
    user_tasks,
    ner,
    re,
    rt,
    triple_extraction,
    kg_builder,
    kg_query,
    workflows,
    agent_registry,
    agent_catalog,
    agent_files,
    reports,
)

__all__ = [
    "health",
    "agents",
    "task_analyzer",
    "orchestrator",
    "planning",
    "execution",
    "review",
    "mcp",
    "chromadb",
    "llm",
    "file_upload",
    "chunk_processing",
    "file_metadata",
    "file_management",
    "user_tasks",
    "ner",
    "re",
    "rt",
    "triple_extraction",
    "kg_builder",
    "kg_query",
    "workflows",
    "agent_registry",
    "agent_catalog",
    "agent_files",
    "reports",
]
