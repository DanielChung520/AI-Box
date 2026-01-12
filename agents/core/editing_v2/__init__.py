# 代碼功能說明: 文件編輯 v2.0 核心服務層
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""文件編輯 v2.0 核心服務層

提供 Intent DSL 解析、Markdown AST 解析、目標定位、上下文裝配、
內容生成、Patch 生成、驗證和錯誤處理等核心功能。
"""

from agents.core.editing_v2.workspace_integration import WorkspaceIntegration

__all__ = ["WorkspaceIntegration"]
