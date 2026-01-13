# 代碼功能說明: Task Planner - 生成 Task DAG
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Task Planner

實現 LLM-based Planner，生成 Task DAG（包含依賴關係）。
集成 RAG-2 檢索，確保 Planner 只能使用註冊表中的 Capability。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog

from agents.task_analyzer.models import (
    RouterDecision,
    TaskDAG,
    TaskNode,
)
from agents.task_analyzer.rag_service import get_rag_service

logger = structlog.get_logger(__name__)


class TaskPlanner:
    """Task Planner 類 - 生成 Task DAG"""

    # Planner System Prompt（防幻覺版）
    PLANNER_SYSTEM_PROMPT = """你是一個任務規劃器（Task Planner），負責根據用戶需求和可用能力生成任務執行計劃（Task DAG）。

## 重要規則（必須嚴格遵守）

1. **禁止發明能力**：
   - 你只能使用提供的「可用能力列表」中的能力
   - 絕對不能發明或使用未在列表中的能力
   - 如果沒有合適的能力，應該明確說明無法完成任務

2. **能力來源**：
   - 所有能力都來自「能力註冊表」（Capability Registry）
   - 只有從 RAG-2 檢索到的能力才是真實存在的
   - 沒有檢索到的能力 = 不存在

3. **任務規劃原則**：
   - 根據任務複雜度，將任務分解為多個子任務
   - 每個子任務對應一個 Capability
   - 明確標註任務之間的依賴關係（depends_on）
   - 確保 DAG 無環（不能有循環依賴）

4. **輸出格式**：
   - 必須輸出有效的 JSON 格式
   - 遵循 TaskDAG Schema：
     ```json
     {
       "task_graph": [
         {
           "id": "T1",
           "capability": "capability_name",
           "agent": "agent_name",
           "depends_on": []
         },
         {
           "id": "T2",
           "capability": "capability_name",
           "agent": "agent_name",
           "depends_on": ["T1"]
         }
       ],
       "reasoning": "規劃理由"
     }
     ```

5. **驗證要求**：
   - 每個任務節點的 capability 和 agent 必須在「可用能力列表」中
   - 如果無法找到合適的能力，返回空 task_graph 並說明原因
   - 確保所有 depends_on 引用的任務 ID 都存在

## 輸出要求

- 只輸出 JSON，不要包含其他文字
- 確保 JSON 格式正確
- 所有 capability 必須來自「可用能力列表」
"""

    def __init__(self, llm_service: Optional[Any] = None):
        """
        初始化 Task Planner

        Args:
            llm_service: LLM 服務（可選，如果為 None 則使用默認服務）
        """
        self._llm_service = llm_service
        self._rag_service = get_rag_service()

        # 嘗試獲取 LLM 服務（如果未提供）
        if self._llm_service is None:
            try:
                from services.api.services.llm_service import get_llm_service

                self._llm_service = get_llm_service()
            except ImportError:
                logger.warning(
                    "task_planner_llm_service_not_available",
                    message="LLM service not available, planner will use fallback",
                )

    def build_planner_prompt(
        self,
        user_query: str,
        router_decision: RouterDecision,
        retrieved_capabilities: List[Dict[str, Any]],
    ) -> str:
        """
        構建 Planner Prompt（防幻覺版）

        Args:
            user_query: 用戶查詢
            router_decision: Router 決策結果
            retrieved_capabilities: 從 RAG-2 檢索到的 Capability 列表

        Returns:
            完整的 Planner Prompt
        """
        # 格式化可用能力列表
        capabilities_text = self._rag_service.format_capabilities_for_prompt(retrieved_capabilities)

        # 構建用戶查詢和上下文
        query_context = f"""## 用戶查詢

{user_query}

## 語義理解結果

- **主題**: {', '.join(router_decision.topics) if router_decision.topics else 'N/A'}
- **實體**: {', '.join(router_decision.entities) if router_decision.entities else 'N/A'}
- **動作信號**: {', '.join(router_decision.action_signals) if router_decision.action_signals else 'N/A'}
- **複雜度**: {router_decision.complexity}
- **風險等級**: {router_decision.risk_level}

{capabilities_text}

## 任務規劃要求

請根據用戶查詢和可用能力，生成任務執行計劃（Task DAG）。

**重要提醒**：
- 只能使用上述「可用能力列表」中的能力
- 不能發明或使用未在列表中的能力
- 如果沒有合適的能力，返回空 task_graph 並說明原因
"""

        return query_context

    def format_capabilities_for_prompt(self, retrieved_capabilities: List[Dict[str, Any]]) -> str:
        """
        格式化 Capability 列表為 Prompt 文本

        Args:
            retrieved_capabilities: 檢索到的 Capability 列表

        Returns:
            格式化後的文本
        """
        return self._rag_service.format_capabilities_for_prompt(retrieved_capabilities)

    def validate_planner_output(
        self,
        task_dag: TaskDAG,
        retrieved_capabilities: List[Dict[str, Any]],
    ) -> tuple[bool, List[str]]:
        """
        驗證 Planner 輸出（防幻覺檢查）

        Args:
            task_dag: Planner 生成的 Task DAG
            retrieved_capabilities: 從 RAG-2 檢索到的 Capability 列表

        Returns:
            (是否有效, 錯誤信息列表)
        """
        errors: List[str] = []

        # 構建可用能力映射（用於快速查找）
        available_capabilities: Dict[str, Dict[str, Any]] = {}
        for result in retrieved_capabilities:
            metadata = result.get("metadata", {})
            capability_name = metadata.get("capability_name")
            agent = metadata.get("agent")
            if capability_name and agent:
                key = f"{agent}:{capability_name}"
                available_capabilities[key] = {
                    "capability_name": capability_name,
                    "agent": agent,
                }

        # 驗證每個任務節點
        task_ids = set()
        for task_node in task_dag.task_graph:
            task_ids.add(task_node.id)

            # 檢查 capability 和 agent 是否在可用列表中
            key = f"{task_node.agent}:{task_node.capability}"
            if key not in available_capabilities:
                errors.append(
                    f"任務 {task_node.id} 使用了不存在的能力: "
                    f"agent={task_node.agent}, capability={task_node.capability}"
                )

            # 檢查依賴關係
            for dep_id in task_node.depends_on:
                if dep_id not in task_ids:
                    errors.append(f"任務 {task_node.id} 依賴的任務 {dep_id} 不存在")

        # 檢查循環依賴（簡單檢查：如果任務 A 依賴 B，B 不能依賴 A）
        for task_node in task_dag.task_graph:
            for dep_id in task_node.depends_on:
                dep_task = next((t for t in task_dag.task_graph if t.id == dep_id), None)
                if dep_task and task_node.id in dep_task.depends_on:
                    errors.append(f"檢測到循環依賴: {task_node.id} <-> {dep_id}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def plan(
        self,
        user_query: str,
        router_decision: RouterDecision,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> TaskDAG:
        """
        生成任務計劃（Task DAG）

        Args:
            user_query: 用戶查詢
            router_decision: Router 決策結果
            top_k: 檢索 Capability 的數量
            similarity_threshold: 相似度閾值

        Returns:
            Task DAG
        """
        try:
            # 1. 從 RAG-2 檢索相關 Capability
            # 構建檢索查詢（結合用戶查詢和語義理解結果）
            retrieval_query = user_query
            if router_decision.topics:
                retrieval_query += " " + " ".join(router_decision.topics)
            if router_decision.action_signals:
                retrieval_query += " " + " ".join(router_decision.action_signals)

            retrieved_capabilities = self._rag_service.retrieve_capabilities(
                query=retrieval_query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            if not retrieved_capabilities:
                logger.warning(
                    "task_planner_no_capabilities_found",
                    query=user_query[:100],
                    message="未找到匹配的能力，返回空 DAG",
                )
                return TaskDAG(
                    task_graph=[],
                    reasoning="未找到匹配的能力，無法生成任務計劃",
                )

            # 2. 構建 Planner Prompt
            planner_prompt = self.build_planner_prompt(
                user_query, router_decision, retrieved_capabilities
            )

            # 3. 調用 LLM 生成 Task DAG
            if self._llm_service is None:
                logger.error(
                    "task_planner_llm_service_not_available",
                    message="LLM service not available, cannot generate DAG",
                )
                return TaskDAG(
                    task_graph=[],
                    reasoning="LLM 服務不可用，無法生成任務計劃",
                )

            # 調用 LLM（這裡需要根據實際的 LLM 服務接口調整）
            llm_response = self._call_llm(planner_prompt)

            # 4. 解析 LLM 響應為 TaskDAG
            task_dag = self._parse_llm_response(llm_response)

            # 5. 驗證 Task DAG（防幻覺檢查）
            is_valid, errors = self.validate_planner_output(task_dag, retrieved_capabilities)

            if not is_valid:
                logger.warning(
                    "task_planner_validation_failed",
                    errors=errors,
                    message="Task DAG 驗證失敗，返回空 DAG",
                )
                return TaskDAG(
                    task_graph=[],
                    reasoning=f"任務計劃驗證失敗: {'; '.join(errors)}",
                )

            logger.info(
                "task_planner_dag_generated",
                task_count=len(task_dag.task_graph),
                reasoning=task_dag.reasoning,
            )

            return task_dag

        except Exception as exc:
            logger.error(
                "task_planner_plan_failed",
                query=user_query[:100],
                error=str(exc),
            )
            return TaskDAG(
                task_graph=[],
                reasoning=f"任務規劃失敗: {str(exc)}",
            )

    def _call_llm(self, prompt: str) -> str:
        """
        調用 LLM 生成響應

        Args:
            prompt: 完整的 Prompt

        Returns:
            LLM 響應文本
        """
        if self._llm_service is None:
            raise RuntimeError("LLM service not available")

        # 構建完整的 Prompt（System + User）
        full_prompt = f"{self.PLANNER_SYSTEM_PROMPT}\n\n{prompt}"

        # 調用 LLM（這裡需要根據實際的 LLM 服務接口調整）
        # 假設 LLM 服務有 generate 方法
        try:
            if hasattr(self._llm_service, "generate"):
                response = self._llm_service.generate(
                    prompt=full_prompt,
                    temperature=0.3,  # 較低溫度以確保穩定性
                    max_tokens=2000,
                )
                return response
            else:
                # 如果 LLM 服務接口不同，需要適配
                logger.warning(
                    "task_planner_llm_service_interface_unknown",
                    message="LLM service interface unknown, using fallback",
                )
                # Fallback: 返回空響應
                return '{"task_graph": [], "reasoning": "LLM service interface not supported"}'
        except Exception as exc:
            logger.error(
                "task_planner_llm_call_failed",
                error=str(exc),
            )
            raise

    def _parse_llm_response(self, response: str) -> TaskDAG:
        """
        解析 LLM 響應為 TaskDAG

        Args:
            response: LLM 響應文本

        Returns:
            TaskDAG 對象
        """
        try:
            # 嘗試提取 JSON（LLM 可能返回包含其他文字的響應）
            # 查找第一個 { 和最後一個 }
            start_idx = response.find("{")
            end_idx = response.rfind("}")

            if start_idx == -1 or end_idx == -1:
                raise ValueError("無法在響應中找到 JSON")

            json_str = response[start_idx : end_idx + 1]
            data = json.loads(json_str)

            # 解析 task_graph
            task_graph = []
            for node_data in data.get("task_graph", []):
                task_node = TaskNode(
                    id=node_data.get("id", ""),
                    capability=node_data.get("capability", ""),
                    agent=node_data.get("agent", ""),
                    depends_on=node_data.get("depends_on", []),
                    description=node_data.get("description"),
                    metadata=node_data.get("metadata", {}),
                )
                task_graph.append(task_node)

            return TaskDAG(
                task_graph=task_graph,
                reasoning=data.get("reasoning"),
                metadata=data.get("metadata", {}),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error(
                "task_planner_parse_response_failed",
                response=response[:200],
                error=str(exc),
            )
            # 返回空 DAG
            return TaskDAG(
                task_graph=[],
                reasoning=f"解析 LLM 響應失敗: {str(exc)}",
            )


def get_task_planner(llm_service: Optional[Any] = None) -> TaskPlanner:
    """
    獲取 Task Planner 實例（單例模式）

    Args:
        llm_service: LLM 服務（可選）

    Returns:
        Task Planner 實例
    """
    global _task_planner_instance
    if _task_planner_instance is None:
        _task_planner_instance = TaskPlanner(llm_service)
    return _task_planner_instance


# 全局單例實例
_task_planner_instance: Optional[TaskPlanner] = None
