# 代碼功能說明: RAG Namespace 管理器
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""RAG Namespace 管理器

定義和管理三個獨立的 RAG Namespace：
- RAG-1: Architecture Awareness（架構感知）
- RAG-2: Capability Discovery（能力發現）- 最重要
- RAG-3: Policy & Constraint Knowledge（策略與約束知識）
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RAGNamespace(str, Enum):
    """RAG Namespace 枚舉"""

    RAG_1_ARCHITECTURE_AWARENESS = "rag_architecture_awareness"
    RAG_2_CAPABILITY_DISCOVERY = "rag_capability_discovery"
    RAG_3_POLICY_CONSTRAINT = "rag_policy_constraint"


class NamespaceConfig(BaseModel):
    """Namespace 配置模型"""

    namespace_id: str = Field(..., description="Namespace ID")
    name: str = Field(..., description="Namespace 名稱")
    description: str = Field(..., description="Namespace 描述")
    purpose: str = Field(..., description="用途說明")
    storage_location: str = Field(..., description="存儲位置（ChromaDB Collection 名稱）")
    usage_location: List[str] = Field(default_factory=list, description="使用位置（L1-L5 層級）")
    is_core: bool = Field(default=False, description="是否為核心 Namespace（最重要）")


# Namespace 配置定義
NAMESPACE_CONFIGS: Dict[str, NamespaceConfig] = {
    RAGNamespace.RAG_1_ARCHITECTURE_AWARENESS: NamespaceConfig(
        namespace_id=RAGNamespace.RAG_1_ARCHITECTURE_AWARENESS,
        name="Architecture Awareness",
        description="系統架構和拓撲信息",
        purpose="讓 LLM 知道「世界長怎樣」",
        storage_location="rag_architecture_awareness",
        usage_location=["L2", "L3"],
        is_core=False,
    ),
    RAGNamespace.RAG_2_CAPABILITY_DISCOVERY: NamespaceConfig(
        namespace_id=RAGNamespace.RAG_2_CAPABILITY_DISCOVERY,
        name="Capability Discovery",
        description="Agent Capability 信息",
        purpose="唯一合法的「能力來源」",
        storage_location="rag_capability_discovery",
        usage_location=["L3"],
        is_core=True,  # 最重要
    ),
    RAGNamespace.RAG_3_POLICY_CONSTRAINT: NamespaceConfig(
        namespace_id=RAGNamespace.RAG_3_POLICY_CONSTRAINT,
        name="Policy & Constraint Knowledge",
        description="策略和約束知識",
        purpose="防止系統自殺",
        storage_location="rag_policy_constraint",
        usage_location=["L4"],
        is_core=False,
    ),
}


class RAGNamespaceManager:
    """RAG Namespace 管理器"""

    @staticmethod
    def get_namespace(namespace_id: str) -> Optional[NamespaceConfig]:
        """
        獲取 Namespace 配置

        Args:
            namespace_id: Namespace ID

        Returns:
            Namespace 配置，如果不存在返回 None
        """
        return NAMESPACE_CONFIGS.get(namespace_id)

    @staticmethod
    def list_namespaces() -> List[NamespaceConfig]:
        """
        列出所有 Namespace

        Returns:
            Namespace 配置列表
        """
        return list(NAMESPACE_CONFIGS.values())

    @staticmethod
    def validate_namespace(namespace_id: str) -> bool:
        """
        驗證 Namespace ID 是否有效

        Args:
            namespace_id: Namespace ID

        Returns:
            是否有效
        """
        return namespace_id in NAMESPACE_CONFIGS

    @staticmethod
    def get_core_namespace() -> NamespaceConfig:
        """
        獲取核心 Namespace（RAG-2: Capability Discovery）

        Returns:
            核心 Namespace 配置
        """
        return NAMESPACE_CONFIGS[RAGNamespace.RAG_2_CAPABILITY_DISCOVERY]

    @staticmethod
    def get_namespace_by_layer(layer: Literal["L1", "L2", "L3", "L4", "L5"]) -> List[NamespaceConfig]:
        """
        根據層級獲取適用的 Namespace

        Args:
            layer: 層級（L1-L5）

        Returns:
            適用的 Namespace 配置列表
        """
        result = []
        for config in NAMESPACE_CONFIGS.values():
            if layer in config.usage_location:
                result.append(config)
        return result

    @staticmethod
    def get_storage_location(namespace_id: str) -> Optional[str]:
        """
        獲取 Namespace 的存儲位置

        Args:
            namespace_id: Namespace ID

        Returns:
            存儲位置（ChromaDB Collection 名稱），如果不存在返回 None
        """
        config = NAMESPACE_CONFIGS.get(namespace_id)
        if config is None:
            return None
        return config.storage_location


# 便捷函數
def get_rag_namespace_manager() -> RAGNamespaceManager:
    """
    獲取 RAG Namespace Manager 實例

    Returns:
        RAG Namespace Manager 實例
    """
    return RAGNamespaceManager()
