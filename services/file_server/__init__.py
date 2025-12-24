# 代碼功能說明: File Server 服務適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""File Server 服務適配器 - 重新導出 agents.services.file_service 的模組"""

# 從 agents.services 模組重新導出
from agents.services.file_service.agent_file_service import (  # noqa: F401
    AgentFileService,
    get_agent_file_service,
)
from agents.services.file_service.models import AgentFileInfo, FileType  # noqa: F401

__all__ = ["AgentFileService", "get_agent_file_service", "AgentFileInfo", "FileType"]
