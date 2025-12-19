# 代碼功能說明: 内建 Agent 模組
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""内建 Agent 模組

提供 AI-Box 核心内建 Agent：
- Registry Manager: 注册管理员
- Security Manager: 安全管理员
- Orchestrator Manager: 协调管理员
- Storage Manager: 数据存储员

这些 Agent 是 AI 驱动的任务导向服务，无需注册，与 AI-Box 生命周期一致。
"""

from typing import Dict, Optional

from agents.services.protocol.base import AgentServiceProtocol

from .orchestrator_manager.agent import OrchestratorManagerAgent
from .registry_manager.agent import RegistryManagerAgent
from .security_manager.agent import SecurityManagerAgent
from .storage_manager.agent import StorageManagerAgent

__all__ = [
    "RegistryManagerAgent",
    "SecurityManagerAgent",
    "OrchestratorManagerAgent",
    "StorageManagerAgent",
    "initialize_builtin_agents",
    "get_builtin_agent",
]

# 全局内建 Agent 实例字典
_builtin_agents: Dict[str, AgentServiceProtocol] = {}


def initialize_builtin_agents() -> Dict[str, AgentServiceProtocol]:
    """
    初始化所有内建 Agent

    Returns:
        内建 Agent 实例字典
    """
    global _builtin_agents

    if _builtin_agents:
        # 已经初始化，直接返回
        return _builtin_agents

    # 初始化各个内建 Agent
    _builtin_agents["registry_manager"] = RegistryManagerAgent()
    _builtin_agents["security_manager"] = SecurityManagerAgent()
    _builtin_agents["orchestrator_manager"] = OrchestratorManagerAgent()
    _builtin_agents["storage_manager"] = StorageManagerAgent()

    return _builtin_agents


def get_builtin_agent(agent_id: str) -> Optional[AgentServiceProtocol]:
    """
    获取内建 Agent 实例

    Args:
        agent_id: Agent ID（registry_manager, security_manager, orchestrator_manager, storage_manager）

    Returns:
        内建 Agent 实例，如果不存在返回 None
    """
    if not _builtin_agents:
        # 如果未初始化，先初始化
        initialize_builtin_agents()

    return _builtin_agents.get(agent_id)
