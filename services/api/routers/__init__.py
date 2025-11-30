# 代碼功能說明: API 路由適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""API 路由適配器 - 重新導出 api.routers 的模組"""

from api.routers import (
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
