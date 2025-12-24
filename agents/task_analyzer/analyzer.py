# 代碼功能說明: Task Analyzer 核心邏輯實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Task Analyzer 核心實現 - 整合任務分析、分類、路由和工作流選擇"""

import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

from agents.task_analyzer.classifier import TaskClassifier
from agents.task_analyzer.llm_router import LLMRouter
from agents.task_analyzer.models import (
    ConfigIntent,
    LogQueryIntent,
    TaskAnalysisRequest,
    TaskAnalysisResult,
    TaskClassificationResult,
    TaskType,
    WorkflowType,
)
from agents.task_analyzer.workflow_selector import WorkflowSelector

logger = logging.getLogger(__name__)


class TaskAnalyzer:
    """Task Analyzer 核心類"""

    def __init__(self):
        """初始化 Task Analyzer"""
        self.classifier = TaskClassifier()
        self.workflow_selector = WorkflowSelector()
        self.llm_router = LLMRouter()

    async def analyze(self, request: TaskAnalysisRequest) -> TaskAnalysisResult:
        """
        分析任務並返回分析結果

        Args:
            request: 任務分析請求

        Returns:
            任務分析結果
        """
        logger.info(f"Analyzing task: {request.task[:100]}...")

        # 生成任務ID
        task_id = str(uuid.uuid4())

        # 步驟1: 任務分類
        classification = self.classifier.classify(
            request.task,
            request.context,
        )

        # 步驟2: 工作流選擇
        workflow_selection = self.workflow_selector.select(
            classification,
            request.task,
            request.context,
        )

        # 步驟3: LLM 路由選擇
        llm_routing = self.llm_router.route(
            classification,
            request.task,
            request.context,
        )

        # 判斷是否需要啟動 Agent（日誌查詢不需要 Agent）
        if classification.task_type == TaskType.LOG_QUERY:
            requires_agent = False
        else:
            requires_agent = self._should_use_agent(
                classification.task_type,
                request.task,
                request.context,
            )

        # 建議使用的 Agent 列表（日誌查詢不需要 Agent）
        suggested_agents = []
        intent: Optional[Any] = None

        # 如果是日誌查詢，提取日誌查詢意圖
        if classification.task_type == TaskType.LOG_QUERY:
            intent = self._extract_log_query_intent(request.task, request.context)
        # 如果是配置操作，提取配置操作意圖
        elif self._is_config_operation(classification, request.task):
            intent = await self._extract_config_intent(
                request.task, classification, request.context
            )

        # 對於其他任務類型，建議使用的 Agent
        if classification.task_type != TaskType.LOG_QUERY:
            suggested_agents = self._suggest_agents(
                classification.task_type,
                workflow_selection.workflow_type,
            )

        # 構建分析詳情
        analysis_details = {
            "classification": {
                "task_type": classification.task_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            },
            "workflow": {
                "workflow_type": workflow_selection.workflow_type.value,
                "confidence": workflow_selection.confidence,
                "reasoning": workflow_selection.reasoning,
                "config": workflow_selection.config,
            },
            "llm_routing": {
                "provider": llm_routing.provider.value,
                "model": llm_routing.model,
                "confidence": llm_routing.confidence,
                "reasoning": llm_routing.reasoning,
                "fallback_providers": [p.value for p in llm_routing.fallback_providers],
            },
        }

        # 如果是混合模式，添加 strategy 信息
        if workflow_selection.workflow_type == WorkflowType.HYBRID and workflow_selection.strategy:
            strategy = workflow_selection.strategy
            analysis_details["workflow_strategy"] = {
                "mode": strategy.mode,
                "primary": strategy.primary.value,
                "fallback": [f.value for f in strategy.fallback],
                "switch_conditions": strategy.switch_conditions,
                "reasoning": strategy.reasoning,
            }

        # 計算整體置信度（取平均值）
        overall_confidence = (
            classification.confidence + workflow_selection.confidence + llm_routing.confidence
        ) / 3.0

        logger.info(
            f"Task analysis completed: task_id={task_id}, "
            f"type={classification.task_type.value}, "
            f"workflow={workflow_selection.workflow_type.value}, "
            f"llm={llm_routing.provider.value}, "
            f"requires_agent={requires_agent}"
        )

        # 將 intent 添加到 analysis_details 中
        if intent:
            analysis_details["intent"] = intent.dict() if hasattr(intent, "dict") else intent

            # 如果是 ConfigIntent，提取澄清信息並添加到分析詳情中
            if isinstance(intent, ConfigIntent):
                analysis_details["clarification_needed"] = intent.clarification_needed
                analysis_details["clarification_question"] = intent.clarification_question
                analysis_details["missing_slots"] = intent.missing_slots
                # 如果是配置操作，建議使用 System Config Agent
                if "system_config_agent" not in suggested_agents:
                    suggested_agents.insert(0, "system_config_agent")

        return TaskAnalysisResult(
            task_id=task_id,
            task_type=classification.task_type,
            workflow_type=workflow_selection.workflow_type,
            llm_provider=llm_routing.provider,
            confidence=overall_confidence,
            requires_agent=requires_agent,
            analysis_details=analysis_details,
            suggested_agents=suggested_agents,
        )

    def _should_use_agent(
        self,
        task_type: TaskType,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        判斷是否需要啟動 Agent

        Args:
            task_type: 任務類型
            task: 任務描述
            context: 上下文信息

        Returns:
            是否需要啟動 Agent
        """
        # 複雜任務、規劃任務、執行任務通常需要 Agent
        if task_type in [TaskType.COMPLEX, TaskType.PLANNING, TaskType.EXECUTION]:
            return True

        # 簡單查詢可能不需要 Agent
        if task_type == TaskType.QUERY:
            # 檢查任務複雜度
            complexity_keywords = [
                "多步驟",
                "多個",
                "綜合",
                "協作",
                "複雜",
                "multi-step",
                "multiple",
                "comprehensive",
                "collaborate",
                "complex",
            ]
            if any(keyword in task.lower() for keyword in complexity_keywords):
                return True
            return False

        # 審查任務通常需要 Agent
        if task_type == TaskType.REVIEW:
            return True

        # 默認需要 Agent
        return True

    def _suggest_agents(
        self,
        task_type: TaskType,
        workflow_type: Any,  # WorkflowType
    ) -> list[str]:
        """
        建議使用的 Agent 列表

        Args:
            task_type: 任務類型
            workflow_type: 工作流類型

        Returns:
            Agent 名稱列表
        """
        agents = []

        # 根據任務類型建議 Agent
        if task_type == TaskType.PLANNING:
            agents.append("planning_agent")
        if task_type == TaskType.EXECUTION:
            agents.append("execution_agent")
        if task_type == TaskType.REVIEW:
            agents.append("review_agent")

        # 複雜任務可能需要所有 Agent
        if task_type == TaskType.COMPLEX:
            agents.extend(["planning_agent", "execution_agent", "review_agent"])

        # 如果沒有特定建議，至少包含 orchestrator
        if not agents:
            agents.append("orchestrator")

        return agents

    def _extract_log_query_intent(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> LogQueryIntent:
        """
        提取日誌查詢意圖

        從自然語言指令中提取日誌查詢參數（類型、時間範圍、執行者等）

        Args:
            task: 自然語言任務描述
            context: 上下文信息

        Returns:
            LogQueryIntent 對象
        """
        import re
        from datetime import datetime, timedelta

        task_lower = task.lower()

        # 識別日誌類型
        log_type = None
        if re.search(r"任務.*日誌|task.*log", task_lower):
            log_type = "TASK"
        elif re.search(r"審計.*日誌|audit.*log", task_lower):
            log_type = "AUDIT"
        elif re.search(r"安全.*日誌|security.*log", task_lower):
            log_type = "SECURITY"

        # 識別時間範圍
        start_time = None
        end_time = None

        # 昨天
        if re.search(r"昨天|yesterday", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
        # 今天
        elif re.search(r"今天|today", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        # 最近 N 天/週/月
        elif match := re.search(r"最近\s*(\d+)\s*(天|週|月|day|week|month)", task_lower):
            days = int(match.group(1))
            unit = match.group(2)
            if unit in ["週", "week"]:
                days = days * 7
            elif unit in ["月", "month"]:
                days = days * 30
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
        # 上週/本月等
        elif re.search(r"上週|last.*week", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(weeks=1)
        elif re.search(r"本月|this.*month", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 識別執行者（actor）
        actor = None
        if match := re.search(r"(?:用戶|user|執行者|actor)\s*[:：]?\s*(\w+)", task_lower):
            actor = match.group(1)
        elif context and "user_id" in context:
            actor = context.get("user_id")

        # 識別租戶 ID
        tenant_id = None
        if match := re.search(r"(?:租戶|tenant)\s*[:：]?\s*(\w+)", task_lower):
            tenant_id = match.group(1)
        elif context and "tenant_id" in context:
            tenant_id = context.get("tenant_id")

        # 識別 trace_id
        trace_id = None
        if match := re.search(r"trace[_-]?id\s*[:：]?\s*([a-zA-Z0-9\-]+)", task_lower):
            trace_id = match.group(1)
        elif context and "trace_id" in context:
            trace_id = context.get("trace_id")

        # 識別限制數量
        limit = 100
        if match := re.search(r"(?:限制|limit|數量)\s*[:：]?\s*(\d+)", task_lower):
            limit = int(match.group(1))

        return LogQueryIntent(
            log_type=log_type,
            actor=actor,
            level=None,  # 日誌查詢的 level 是可選的
            tenant_id=tenant_id,
            user_id=context.get("user_id") if context else None,
            start_time=start_time,
            end_time=end_time,
            trace_id=trace_id,
            limit=limit,
        )

    def _is_config_operation(self, classification: TaskClassificationResult, task: str) -> bool:
        """
        判斷是否為配置操作

        Args:
            classification: 任務分類結果
            task: 任務描述

        Returns:
            是否為配置操作
        """
        config_keywords = [
            "配置",
            "設置",
            "系統設置",
            "config",
            "setting",
            "policy",
            "策略",
            "限流",
            "模型",
            "ontology",
            "知識架構",
        ]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in config_keywords)

    async def _extract_config_intent(
        self,
        instruction: str,
        classification: TaskClassificationResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConfigIntent:
        """
        提取配置操作意圖（使用 LLM）

        從自然語言指令中提取結構化的配置操作參數，生成 ConfigIntent 對象。

        Args:
            instruction: 自然語言指令
            classification: 任務分類結果
            context: 上下文信息

        Returns:
            ConfigIntent 對象
        """
        logger.info(f"Extracting config intent from instruction: {instruction[:100]}...")

        try:
            # 使用 LLM Router 選擇合適的模型
            llm_routing = self.llm_router.route(classification, instruction, context)

            # 獲取 LLM 客戶端
            from llm.clients.factory import LLMClientFactory

            client = LLMClientFactory.create_client(llm_routing.provider, use_cache=True)

            # 構建 System Prompt（詳細版本，參考 Orchestrator 規格書 3.1.4 節）
            system_prompt = """Role: 你是 AI-Box 的 Task Analyzer。
Objective: 分析管理員指令，提取系統設置所需的參數。

## 1. 識別動作 (Action)

- **query**: 查詢配置、查看狀態、讀取設置、顯示、查看、查詢
- **create**: 創建、新增、建立
- **update**: 修改、調整、變更、設定、改為、更新、設置
- **delete**: 刪除、移除、清除
- **list**: 列出、清單、有哪些、顯示所有
- **rollback**: 復原、回滾、撤銷、取消、恢復

## 2. 提取層級 (Level)

- **system**: 涉及「全系統」、「默認」、「全域」、「系統級」、「系統默認」
- **tenant**: 涉及「租戶」、「公司」、「Tenant ID」、「租戶級」、「tenant_xxx」
- **user**: 涉及「個人」、「特定用戶」、「用戶級」、「user_xxx」

## 3. 定義範圍 (Scope)

根據關鍵字歸類到對應的 scope：

- **genai.policy**: 模型、限流、API 限流、rate_limit、allowed_providers、allowed_models、default_model、GenAI 策略
- **genai.model_registry**: 模型註冊表、模型列表、model registry
- **genai.tenant_secrets**: API Key、密鑰、tenant secrets
- **llm.provider_config**: LLM 提供商、API 端點、provider config、endpoint
- **llm.moe_routing**: MoE 路由、模型路由、routing strategy
- **ontology.base**: Base Ontology、基礎知識架構、base ontology
- **ontology.domain**: Domain Ontology、領域知識架構、domain ontology
- **ontology.major**: Major Ontology、主要知識架構、major ontology
- **system.security**: 安全配置、安全策略、security policy
- **system.storage**: 存儲配置、存儲路徑、storage config
- **system.logging**: 日誌配置、日誌級別、logging config

## 4. 輸出格式要求

必須嚴格遵守 ConfigIntent 格式，返回 JSON：

```json
{
  "action": "query|create|update|delete|list|rollback",
  "scope": "genai.policy|llm.provider_config|ontology.base|...",
  "level": "system|tenant|user",
  "tenant_id": "tenant_xxx" | null,
  "user_id": "user_xxx" | null,
  "config_data": {...} | null,
  "clarification_needed": true|false,
  "clarification_question": "..." | null,
  "missing_slots": ["level", "config_data"] | [],
  "original_instruction": "原始指令"
}
```

## 5. 澄清機制

若資訊不足，請標註 `clarification_needed: true` 並生成 `clarification_question`。

常見缺失的槽位：
- **level**: 未明確指定是系統級、租戶級還是用戶級
- **scope**: 未明確指定配置範圍
- **config_data**: 更新操作時未明確指定要修改的具體配置項
- **tenant_id**: 租戶級操作時未指定租戶 ID
- **user_id**: 用戶級操作時未指定用戶 ID

## 6. 實務範例

**範例 1**：
指令：「幫我把租戶 A 的限流改為 500」
輸出：
```json
{
  "action": "update",
  "scope": "genai.policy",
  "level": "tenant",
  "tenant_id": "tenant_a",
  "config_data": {
    "rate_limit": 500
  },
  "clarification_needed": false,
  "missing_slots": [],
  "clarification_question": null,
  "original_instruction": "幫我把租戶 A 的限流改為 500"
}
```

**範例 2**：
指令：「查看系統的 LLM 配置」
輸出：
```json
{
  "action": "query",
  "scope": "genai.policy",
  "level": "system",
  "tenant_id": null,
  "user_id": null,
  "config_data": null,
  "clarification_needed": false,
  "missing_slots": [],
  "clarification_question": null,
  "original_instruction": "查看系統的 LLM 配置"
}
```

**範例 3**：
指令：「修改 LLM 配置」
輸出：
```json
{
  "action": "update",
  "scope": "genai.policy",
  "level": null,
  "tenant_id": null,
  "user_id": null,
  "config_data": null,
  "clarification_needed": true,
  "clarification_question": "請確認：1. 要修改哪一層配置？(系統級/租戶級/用戶級) 2. 要修改哪些具體配置項？",
  "missing_slots": ["level", "config_data"],
  "original_instruction": "修改 LLM 配置"
}
```

重要：必須只返回 JSON，不要包含任何其他文字或說明。"""

            # 構建用戶提示詞
            user_prompt = f"""分析以下配置操作指令，提取結構化意圖：

指令：{instruction}

請嚴格按照 System Prompt 的要求，返回符合 ConfigIntent 格式的 JSON。必須只返回 JSON，不要包含任何其他文字。"""

            # 構建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # 調用 LLM
            response = await client.chat(messages=messages, model=llm_routing.model)

            # 提取響應內容
            content = response.get("content") or response.get("text", "")
            if not content:
                raise ValueError("LLM 返回空響應")

            # 嘗試從響應中提取 JSON（可能包含 markdown 代碼塊）
            json_str = content.strip()
            if json_str.startswith("```"):
                # 移除 markdown 代碼塊標記
                json_str = re.sub(r"```(?:json)?\s*\n?", "", json_str)
                json_str = re.sub(r"\n?```\s*$", "", json_str).strip()

            # 解析 JSON
            try:
                intent_dict = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {json_str[:200]}")
                raise ValueError(f"LLM 返回的 JSON 格式錯誤: {e}") from e

            # 確保 original_instruction 字段存在
            if "original_instruction" not in intent_dict:
                intent_dict["original_instruction"] = instruction

            # 構建並返回 ConfigIntent
            config_intent = ConfigIntent(**intent_dict)

            logger.info(
                f"Config intent extracted: action={config_intent.action}, "
                f"scope={config_intent.scope}, level={config_intent.level}"
            )

            return config_intent

        except Exception as e:
            logger.error(f"Failed to extract config intent: {e}", exc_info=True)
            # 返回一個默認的 ConfigIntent，標記為需要澄清
            return ConfigIntent(
                action="query",
                scope="unknown",
                level=None,
                tenant_id=None,
                user_id=None,
                config_data=None,
                clarification_needed=True,
                clarification_question=f"無法解析配置指令，請提供更多信息。錯誤：{str(e)}",
                missing_slots=["scope", "level"],
                original_instruction=instruction,
            )
