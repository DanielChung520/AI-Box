from __future__ import annotations
# 代碼功能說明: LangGraph Agents初始化模組
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-03

"""LangGraph Agents初始化和註冊模組"""
import logging
from typing import Callable, Dict, Optional, Type

from genai.workflows.langgraph.agents.audit_logger import (
    AuditLogger,
    create_audit_logger_config,
)
from genai.workflows.langgraph.agents.capability_agent import (
    CapabilityAgent,
    create_capability_agent_config,
)
from genai.workflows.langgraph.agents.clarification_agent import (
    ClarificationAgent,
    create_clarification_agent_config,
)
from genai.workflows.langgraph.agents.context_manager_agent import (
    ContextManagerAgent,
    create_context_manager_agent_config,
)
from genai.workflows.langgraph.agents.hybrid_rag_agent import (
    HybridRAGAgent,
    create_hybrid_rag_agent_config,
)
from genai.workflows.langgraph.agents.intent_agent import (
    IntentAgent,
    create_intent_agent_config,
)
from genai.workflows.langgraph.agents.long_term_memory_agent import (
    LongTermMemoryAgent,
    create_long_term_memory_agent_config,
)
from genai.workflows.langgraph.agents.memory_manager_agent import (
    MemoryManagerAgent,
    create_memory_manager_agent_config,
)
from genai.workflows.langgraph.agents.orchestrator_agent import (
    OrchestratorAgent,
    create_orchestrator_agent_config,
)
from genai.workflows.langgraph.agents.policy_agent import (
    PolicyAgent,
    create_policy_agent_config,
)
from genai.workflows.langgraph.agents.resource_manager import (
    ResourceManager,
    create_resource_manager_config,
)
from genai.workflows.langgraph.agents.semantic_agent import (
    SemanticAgent,
    create_semantic_agent_config,
)
from genai.workflows.langgraph.agents.simple_response_agent import (
    SimpleResponseAgent,
    create_simple_response_agent_config,
)
from genai.workflows.langgraph.agents.task_executor_agent import (
    TaskExecutorAgent,
    create_task_executor_agent_config,
)
from genai.workflows.langgraph.agents.task_manager_agent import (
    TaskManagerAgent,
    create_task_manager_agent_config,
)
from genai.workflows.langgraph.agents.user_confirmation_agent import (
    UserConfirmationAgent,
    create_user_confirmation_agent_config,
)
from genai.workflows.langgraph.agents.workspace_manager_agent import (
    WorkspaceManagerAgent,
    create_workspace_manager_agent_config,
)
from genai.workflows.langgraph.agents.file_task_binder_agent import (
    FileTaskBinderAgent,
    create_file_task_binder_agent_config,
)
from genai.workflows.langgraph.agents.file_upload_agent import (
    FileUploadAgent,
    create_file_upload_agent_config,
)
from genai.workflows.langgraph.agents.intent_agent import (
    IntentAgent,
    create_intent_agent_config,
)
from genai.workflows.langgraph.agents.kg_extraction_agent import (
    KGExtractionAgent,
    create_kg_extraction_agent_config,
)
from genai.workflows.langgraph.agents.observer_agent import (
    ObserverAgent,
    create_observer_agent_config,
)
from genai.workflows.langgraph.agents.orchestrator_agent import (
    OrchestratorAgent,
    create_orchestrator_agent_config,
)
from genai.workflows.langgraph.agents.performance_optimizer_agent import (
    PerformanceOptimizerAgent,
    create_performance_optimizer_agent_config,
)
from genai.workflows.langgraph.agents.retrieval_integration_agent import (
    RetrievalIntegrationAgent,
    create_retrieval_integration_agent_config,
)
from genai.workflows.langgraph.agents.vectorization_agent import (
    VectorizationAgent,
    create_vectorization_agent_config,
)
from genai.workflows.langgraph.agents.vision_agent import (
    VisionAgent,
    create_vision_agent_config,
)
from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, get_node_registry

logger = logging.getLogger(__name__)


# Agent類型映射
AGENT_CLASSES: Dict[str, Type[BaseAgentNode]] = {
    "SemanticAgent": SemanticAgent,
    "IntentAgent": IntentAgent,
    "AuditLogger": AuditLogger,
    "ObserverAgent": ObserverAgent,
    "PerformanceOptimizerAgent": PerformanceOptimizerAgent,
    "CapabilityAgent": CapabilityAgent,
    "ResourceManager": ResourceManager,
    "PolicyAgent": PolicyAgent,
    "OrchestratorAgent": OrchestratorAgent,
    "TaskExecutorAgent": TaskExecutorAgent,
    "UserConfirmationAgent": UserConfirmationAgent,
    "ClarificationAgent": ClarificationAgent,
    "SimpleResponseAgent": SimpleResponseAgent,
    "TaskManagerAgent": TaskManagerAgent,
    "WorkspaceManagerAgent": WorkspaceManagerAgent,
    "FileTaskBinderAgent": FileTaskBinderAgent,
    "ContextManagerAgent": ContextManagerAgent,
    "FileUploadAgent": FileUploadAgent,
    "VectorizationAgent": VectorizationAgent,
    "VisionAgent": VisionAgent,
    "KGExtractionAgent": KGExtractionAgent,
    "HybridRAGAgent": HybridRAGAgent,
    "RetrievalIntegrationAgent": RetrievalIntegrationAgent,
    "MemoryManagerAgent": MemoryManagerAgent,
    "LongTermMemoryAgent": LongTermMemoryAgent,
}

# Agent配置工廠
AGENT_CONFIGS: Dict[str, Callable] = {
    "SemanticAgent": create_semantic_agent_config,
    "IntentAgent": create_intent_agent_config,
    "AuditLogger": create_audit_logger_config,
    "ObserverAgent": create_observer_agent_config,
    "PerformanceOptimizerAgent": create_performance_optimizer_agent_config,
    "CapabilityAgent": create_capability_agent_config,
    "ResourceManager": create_resource_manager_config,
    "PolicyAgent": create_policy_agent_config,
    "OrchestratorAgent": create_orchestrator_agent_config,
    "TaskExecutorAgent": create_task_executor_agent_config,
    "UserConfirmationAgent": create_user_confirmation_agent_config,
    "ClarificationAgent": create_clarification_agent_config,
    "SimpleResponseAgent": create_simple_response_agent_config,
    "TaskManagerAgent": create_task_manager_agent_config,
    "WorkspaceManagerAgent": create_workspace_manager_agent_config,
    "FileTaskBinderAgent": create_file_task_binder_agent_config,
    "ContextManagerAgent": create_context_manager_agent_config,
    "FileUploadAgent": create_file_upload_agent_config,
    "VectorizationAgent": create_vectorization_agent_config,
    "VisionAgent": create_vision_agent_config,
    "KGExtractionAgent": create_kg_extraction_agent_config,
    "HybridRAGAgent": create_hybrid_rag_agent_config,
    "RetrievalIntegrationAgent": create_retrieval_integration_agent_config,
    "MemoryManagerAgent": create_memory_manager_agent_config,
    "LongTermMemoryAgent": create_long_term_memory_agent_config,
}


def register_all_agents() -> None:
    """註冊所有Agent到節點系統"""
    registry = get_node_registry()

    for agent_name, agent_class in AGENT_CLASSES.items():
        try:
            # 獲取配置
            config_factory = AGENT_CONFIGS.get(agent_name)
            if not config_factory:
                logger.warning(f"No config factory found for agent: {agent_name}")
                continue

            config = config_factory()

            # 註冊Agent
            registry.register(agent_class, config)
            logger.info(f"Registered agent: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to register agent {agent_name}: {e}")


def get_agent_class(agent_name: str) -> Optional[Type[BaseAgentNode]]:
    """獲取Agent類"""
    return AGENT_CLASSES.get(agent_name)


def get_agent_config_factory(agent_name: str) -> callable | None:
    """獲取Agent配置工廠"""
    return AGENT_CONFIGS.get(agent_name)


def list_available_agents() -> list[str]:
    """列出所有可用的Agent"""
    return list(AGENT_CLASSES.keys())


# 初始化時自動註冊所有Agent
try:
    register_all_agents()
    logger.info("All LangGraph agents registered successfully")
except Exception as e:
    logger.error(f"Failed to register LangGraph agents: {e}")