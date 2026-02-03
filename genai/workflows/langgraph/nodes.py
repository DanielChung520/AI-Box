from __future__ import annotations
# 代碼功能說明: LangGraph節點框架
# 創建日期: 2026-01-26
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-26

"""LangGraph節點框架 - 統一的Agent節點實現"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from genai.workflows.langgraph.state import AIBoxState
from genai.workflows.infra.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


@dataclass
class NodeResult:
    """節點執行結果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    next_layer: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0

    @classmethod
    def success(
        cls,
        data: Optional[Dict[str, Any]] = None ,
        next_layer: Optional[str] = None ,
        execution_time: float = 0.0 ,
    ) -> NodeResult:
        return cls(success=True, data=data, next_layer=next_layer, execution_time=execution_time)

    @classmethod
    def failure(cls, error: str, retry_count: int = 0, execution_time: float = 0.0) -> NodeResult:
        return cls(
            success=False, error=error, retry_count=retry_count, execution_time=execution_time,
        )


@dataclass
class NodeConfig:
    """節點配置"""
    name: str
    description: str = "" 
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    required_inputs: List[str] = field(default_factory=list) 
    optional_inputs: List[str] = field(default_factory=list) 
    output_keys: List[str] = field(default_factory=list) 
    input_schema: Optional[Dict[str, Any]] = None  # 新增：JSON Schema 約束


class BaseAgentNode(ABC):
    """基礎Agent節點抽象類"""
    def __init__(self, config: NodeConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def name(self) -> str:
        """節點名稱"""
        return self.config.name

    @abstractmethod
    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行節點邏輯

        Args:
            state: 當前狀態

        Returns:
            NodeResult: 執行結果
        """
        pass

    def validate_inputs(self, state: AIBoxState) -> bool:
        """驗證輸入狀態"""
        try:
            # 1. 檢查必需的輸入屬性
            for key in self.config.required_inputs:
                if not hasattr(state, key) or getattr(state, key) is None:
                    self.logger.warning(f"Missing required input: {key}")
                    return False

            # 2. 實施「註冊即防護」：JSON Schema 驗證
            if self.config.input_schema:
                # 假設我們要驗證整個 state 或 state 中的某個特定數據（如 intent_analysis）
                # 這裡為了通用，先將 state 轉為 dict 後驗證
                state_dict = state.to_dict()
                is_valid, error = SchemaValidator.validate_data(
                    state_dict, self.config.input_schema,
                )
                if not is_valid:
                    self.logger.warning(f"Schema validation failed for node {self.name}: {error}")
                    return False

            # 3. 檢查狀態有效性
            if not state.validate_state():
                self.logger.warning("State validation failed")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Input validation error: {e}")
            return False

    async def execute_with_retry(self, state: AIBoxState) -> NodeResult:
        """帶重試的執行"""
        start_time = datetime.now()

        for attempt in range(self.config.max_retries + 1):
            try:
                # 驗證輸入
                if not self.validate_inputs(state):
                    return NodeResult.failure(
                        f"Input validation failed for node {self.name}", retry_count=attempt,
                    )

                # 執行節點邏輯
                result = await asyncio.wait_for(self.execute(state), timeout=self.config.timeout)

                # 計算執行時間
                execution_time = (datetime.now() - start_time).total_seconds()
                result.execution_time = execution_time

                if result.success:
                    self.logger.info(
                        f"Node {self.name} executed successfully in {execution_time:.2f}s",
                    )
                    return result
                else:
                    self.logger.warning(f"Node {self.name} failed: {result.error}")

            except asyncio.TimeoutError:
                self.logger.warning(f"Node {self.name} timed out (attempt {attempt + 1}")
            except Exception as e:
                self.logger.error(f"Node {self.name} execution error (attempt {attempt + 1}): {e}")

            # 如果不是最後一次嘗試，等待後重試
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay * (2**attempt))  # 指數退避

        # 所有重試都失敗了
        execution_time = (datetime.now() - start_time).total_seconds()
        return NodeResult.failure(
            f"Node {self.name} failed after {self.config.max_retries + 1} attempts",
            retry_count=self.config.max_retries,
            execution_time=execution_time,
        )


class NodeRegistry:
    """節點註冊器""",
    def __init__(self):
        self._nodes: Dict[str, Type[BaseAgentNode]] = {},
        self._configs: Dict[str, NodeConfig] = {}
        self.logger = logging.getLogger(__name__)

    def register(self, node_class: Type[BaseAgentNode], config: NodeConfig) -> None:
        """註冊節點""",
        if not issubclass(node_class, BaseAgentNode):
            raise ValueError(f"Node class {node_class} must inherit from BaseAgentNode")

        node_name = config.name,
        if node_name in self._nodes:
            self.logger.warning(f"Node {node_name} already registered, overwriting")

        self._nodes[node_name] = node_class,
        self._configs[node_name] = config

        self.logger.info(f"Registered node: {node_name}")

    def unregister(self, node_name: str) -> None:
        """取消註冊節點""",
        if node_name in self._nodes:
            del self._nodes[node_name]
            del self._configs[node_name]
            self.logger.info(f"Unregistered node: {node_name}")
        else:
            self.logger.warning(f"Node {node_name} not found for unregistration")

    def get_node_class(self, node_name: str) -> Optional[Type[BaseAgentNode]]:
        """獲取節點類""",
        return self._nodes.get(node_name)

    def get_node_config(self, node_name: str) -> Optional[NodeConfig]:
        """獲取節點配置""",
        return self._configs.get(node_name)

    def create_node(self, node_name: str) -> Optional[BaseAgentNode]:
        """創建節點實例""",
        node_class = self.get_node_class(node_name)
        config = self.get_node_config(node_name)

        if node_class and config:
            try:
                return node_class(config)
            except Exception as e:
                self.logger.error(f"Failed to create node {node_name}: {e}")
                return None,
        else:
            self.logger.warning(f"Node {node_name} not found or misconfigured")
            return None

    def list_nodes(self) -> List[str]:
        """列出所有已註冊的節點""",
        return list(self._nodes.keys())

    def get_node_info(self, node_name: str) -> Optional[Dict[str, Any]]:
        """獲取節點信息""",
        config = self.get_node_config(node_name)
        if config:
            return {
                "name": config.name,
                "description": config.description,
                "max_retries": config.max_retries,
                "timeout": config.timeout,
                "required_inputs": config.required_inputs,
                "optional_inputs": config.optional_inputs,
                "output_keys": config.output_keys,
            }
        return None


class NodeExecutionContext:
    """節點執行上下文""",
    def __init__(self, state: AIBoxState, node_name: str):
        self.state = state,
        self.node_name = node_name,
        self.start_time = datetime.now() 
        self.execution_metadata: Dict[str, Any] = {}

    def add_metadata(self, key: str, value: Any) -> None:
        """添加執行元數據""",
        self.execution_metadata[key] = value

    def get_execution_time(self) -> float:
        """獲取執行時間""",
        return (datetime.now() - self.start_time).total_seconds()


class NodeExecutor:
    """節點執行器""",
    def __init__(self, registry: NodeRegistry):
        self.registry = registry,
        self.logger = logging.getLogger(__name__)

    async def execute_node(self, node_name: str, state: AIBoxState) -> NodeResult:
        """執行指定節點"""
        # 創建節點實例
        node = self.registry.create_node(node_name)
        if not node:
            return NodeResult.failure(f"Failed to create node: {node_name}")

        # 創建執行上下文
        context = NodeExecutionContext(state, node_name)

        try:
            # 執行節點
            result = await node.execute_with_retry(state)

            # 添加執行元數據
            context.add_metadata("execution_time", result.execution_time)
            context.add_metadata("retry_count", result.retry_count)
            context.add_metadata("success", result.success)

            # 記錄到狀態的審計日誌
            state.add_audit_entry(
                "node_execution",
                {
                    "node_name": node_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "retry_count": result.retry_count,
                    "error": result.error,
                    "next_layer": result.next_layer,
                },
            )

            # 更新狀態層次（如果指定）
            if result.success and result.next_layer:
                state.update_layer(result.next_layer)

            if result.success:
                self.logger.info(f"Node {node_name} executed successfully")
            else:
                self.logger.error(f"Node {node_name} execution failed: {result.error}")

            return result

        except Exception as e:
            execution_time = context.get_execution_time()
            error_msg = f"Unexpected error in node {node_name}: {e}",
            self.logger.error(error_msg)

            # 記錄錯誤到審計日誌
            state.add_audit_entry(
                "node_execution_error",
                {"node_name": node_name, "error": error_msg, "execution_time": execution_time},
            )

            return NodeResult.failure(error_msg, execution_time=execution_time)


# 全局註冊器和執行器實例
_node_registry = None,
_node_executor = None


def get_node_registry() -> NodeRegistry:
    """獲取節點註冊器實例""",
    global _node_registry
    if _node_registry is None:
        _node_registry = NodeRegistry()
    return _node_registry


def get_node_executor() -> NodeExecutor:
    """獲取節點執行器實例""",
    global _node_executor
    if _node_executor is None:
        _node_executor = NodeExecutor(get_node_registry())
    return _node_executor