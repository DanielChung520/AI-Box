# 代碼功能說明: Agent Todo 前置條件檢查
# 創建日期: 2026-02-07
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-07

"""Agent Todo 前置條件檢查"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class PreconditionType(str, Enum):
    """前置條件類型"""

    SCHEMA_READY = "SCHEMA_READY"
    DATA_AVAILABLE = "DATA_AVAILABLE"
    AGENT_AVAILABLE = "AGENT_AVAILABLE"
    DEPENDENCY_COMPLETED = "DEPENDENCY_COMPLETED"
    USER_CONFIRMED = "USER_CONFIRMED"


class PreconditionStatus(str, Enum):
    """前置條件狀態"""

    PENDING = "PENDING"
    CHECKING = "CHECKING"
    SATISFIED = "SATISFIED"
    FAILED = "FAILED"


class Precondition(BaseModel):
    """前置條件"""

    type: PreconditionType
    ref: Optional[str] = None
    status: PreconditionStatus = PreconditionStatus.PENDING
    message: str = ""


class PreconditionResult(BaseModel):
    """前置條件檢查結果"""

    all_satisfied: bool
    preconditions: List[Dict[str, Any]]
    failed_checks: List[str] = []


class PreconditionChecker:
    """前置條件檢查器"""

    def __init__(self):
        self._cache: Dict[str, bool] = {}

    async def check(
        self, precondition: Precondition, context: Optional[Dict[str, Any]] = None
    ) -> Precondition:
        """檢查單個前置條件"""
        context = context or {}

        if precondition.type == PreconditionType.SCHEMA_READY:
            return await self._check_schema(precondition, context)
        elif precondition.type == PreconditionType.DATA_AVAILABLE:
            return await self._check_data(precondition, context)
        elif precondition.type == PreconditionType.AGENT_AVAILABLE:
            return await self._check_agent(precondition, context)
        elif precondition.type == PreconditionType.DEPENDENCY_COMPLETED:
            return await self._check_dependency(precondition, context)
        else:
            precondition.status = PreconditionStatus.SATISFIED
            precondition.message = "未知類型，視為已滿足"
            return precondition

    async def check_all(
        self, preconditions: List[Precondition], context: Optional[Dict[str, Any]] = None
    ) -> PreconditionResult:
        """檢查所有前置條件"""
        context = context or {}
        results = []
        failed = []

        for pc in preconditions:
            result = await self.check(pc, context)
            results.append(
                {
                    "type": result.type.value,
                    "status": result.status.value,
                    "message": result.message,
                    "ref": result.ref,
                }
            )
            if result.status == PreconditionStatus.FAILED:
                failed.append(f"{result.type.value}: {result.message}")

        return PreconditionResult(
            all_satisfied=len(failed) == 0,
            preconditions=results,
            failed_checks=failed,
        )

    async def _check_schema(
        self, precondition: Precondition, context: Dict[str, Any]
    ) -> Precondition:
        """檢查 Schema 是否就緒"""
        schema_name = precondition.ref or context.get("schema_name", "unknown")

        if schema_name in self._cache:
            cached = self._cache[schema_name]
            precondition.status = (
                PreconditionStatus.SATISFIED if cached else PreconditionStatus.FAILED
            )
            precondition.message = f"Schema {schema_name}: {'已就緒' if cached else '未就緒'}"
            return precondition

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8004/health")
                if response.status_code == 200:
                    self._cache[schema_name] = True
                    precondition.status = PreconditionStatus.SATISFIED
                    precondition.message = f"Schema {schema_name}: 數據服務可用"
                else:
                    self._cache[schema_name] = False
                    precondition.status = PreconditionStatus.FAILED
                    precondition.message = f"Schema {schema_name}: 數據服務不可用"
        except Exception as e:
            self._cache[schema_name] = False
            precondition.status = PreconditionStatus.FAILED
            precondition.message = f"Schema {schema_name}: 檢查失敗 - {str(e)}"

        return precondition

    async def _check_data(
        self, precondition: Precondition, context: Dict[str, Any]
    ) -> Precondition:
        """檢查數據是否可用"""
        data_ref = precondition.ref or context.get("data_ref")

        if not data_ref:
            precondition.status = PreconditionStatus.SATISFIED
            precondition.message = "無數據需求，視為已滿足"
            return precondition

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "http://localhost:8004/execute",
                    json={
                        "task_id": f"precheck_{id(data_ref)}",
                        "task_type": "data_query",
                        "task_data": {
                            "action": "validate_data",
                            "query": f"確認 {data_ref} 是否存在且有效",
                        },
                    },
                )
                result = response.json()
                if result.get("status") == "completed":
                    precondition.status = PreconditionStatus.SATISFIED
                    precondition.message = f"數據 {data_ref}: 可用"
                else:
                    precondition.status = PreconditionStatus.FAILED
                    precondition.message = f"數據 {data_ref}: 不可用"
        except Exception as e:
            precondition.status = PreconditionStatus.FAILED
            precondition.message = f"數據檢查失敗: {str(e)}"

        return precondition

    async def _check_agent(
        self, precondition: Precondition, context: Dict[str, Any]
    ) -> Precondition:
        """檢查 Agent 是否可用"""
        agent_name = precondition.ref or context.get("agent_name", "unknown")

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                if agent_name == "data-agent":
                    response = await client.get("http://localhost:8004/health")
                    if response.status_code == 200:
                        precondition.status = PreconditionStatus.SATISFIED
                        precondition.message = f"Agent {agent_name}: 可用"
                    else:
                        precondition.status = PreconditionStatus.FAILED
                        precondition.message = f"Agent {agent_name}: 不可用"
                elif agent_name == "llm":
                    response = await client.get("http://localhost:11434/api/tags")
                    if response.status_code == 200:
                        precondition.status = PreconditionStatus.SATISFIED
                        precondition.message = f"Agent {agent_name}: 可用"
                    else:
                        precondition.status = PreconditionStatus.FAILED
                        precondition.message = f"Agent {agent_name}: 不可用"
                else:
                    precondition.status = PreconditionStatus.SATISFIED
                    precondition.message = f"Agent {agent_name}: 未知Agent，視為可用"
        except Exception as e:
            precondition.status = PreconditionStatus.FAILED
            precondition.message = f"Agent {agent_name}: 檢查失敗 - {str(e)}"

        return precondition

    async def _check_dependency(
        self, precondition: Precondition, context: Dict[str, Any]
    ) -> Precondition:
        """檢查依賴是否完成"""
        dep_id = precondition.ref or context.get("dependency_id")

        if not dep_id:
            precondition.status = PreconditionStatus.SATISFIED
            precondition.message = "無依賴需求，視為已滿足"
            return precondition

        completed_deps = context.get("completed_dependencies", [])
        if dep_id in completed_deps:
            precondition.status = PreconditionStatus.SATISFIED
            precondition.message = f"依賴 {dep_id}: 已完成"
        else:
            precondition.status = PreconditionStatus.FAILED
            precondition.message = f"依賴 {dep_id}: 未完成"

        return precondition

    def clear_cache(self):
        """清除緩存"""
        self._cache.clear()
        logger.info("Precondition cache cleared")
