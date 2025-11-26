# 代碼功能說明: LLM 路由選擇器實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""LLM 路由選擇器 - 實現 LLM 路由選擇邏輯"""

import logging
from typing import Dict, Any, Optional, List

from core.config import get_config_section
from llm.router import LLMNodeConfig, LLMNodeRouter

from agents.task_analyzer.models import (
    TaskType,
    LLMProvider,
    LLMRoutingResult,
    TaskClassificationResult,
)

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 路由選擇器"""

    def __init__(self):
        """初始化 LLM 路由選擇器"""
        self.local_router: Optional[LLMNodeRouter] = None

        # 定義任務類型到 LLM 提供商的映射規則
        self.provider_rules = {
            TaskType.QUERY: {
                LLMProvider.CHATGPT: 0.8,
                LLMProvider.GEMINI: 0.7,
                LLMProvider.QWEN: 0.6,
                LLMProvider.OLLAMA: 0.5,
            },
            TaskType.EXECUTION: {
                LLMProvider.CHATGPT: 0.9,
                LLMProvider.GEMINI: 0.8,
                LLMProvider.QWEN: 0.7,
                LLMProvider.OLLAMA: 0.6,
            },
            TaskType.REVIEW: {
                LLMProvider.GEMINI: 0.8,
                LLMProvider.CHATGPT: 0.7,
                LLMProvider.QWEN: 0.6,
                LLMProvider.OLLAMA: 0.5,
            },
            TaskType.PLANNING: {
                LLMProvider.CHATGPT: 0.9,
                LLMProvider.GEMINI: 0.8,
                LLMProvider.QWEN: 0.7,
                LLMProvider.GROK: 0.6,
            },
            TaskType.COMPLEX: {
                LLMProvider.CHATGPT: 0.9,
                LLMProvider.GEMINI: 0.8,
                LLMProvider.QWEN: 0.7,
                LLMProvider.OLLAMA: 0.5,
            },
        }

        # 定義模型映射
        self.model_mapping = {
            LLMProvider.CHATGPT: "gpt-4-turbo-preview",
            LLMProvider.GEMINI: "gemini-pro",
            LLMProvider.GROK: "grok-beta",
            LLMProvider.QWEN: "qwen-turbo",
            LLMProvider.OLLAMA: "llama2",
        }

        # 定義備用提供商
        self.fallback_mapping = {
            LLMProvider.CHATGPT: [LLMProvider.GEMINI, LLMProvider.QWEN],
            LLMProvider.GEMINI: [LLMProvider.CHATGPT, LLMProvider.QWEN],
            LLMProvider.GROK: [LLMProvider.CHATGPT, LLMProvider.GEMINI],
            LLMProvider.QWEN: [LLMProvider.CHATGPT, LLMProvider.GEMINI],
            LLMProvider.OLLAMA: [LLMProvider.QWEN, LLMProvider.CHATGPT],
        }

        self._init_local_llm_settings()

    def _init_local_llm_settings(self) -> None:
        """依 config/services/ollama 設定本地模型與節點資訊。"""
        ollama_cfg = get_config_section("services", "ollama", default={}) or {}
        default_model = ollama_cfg.get("default_model")
        if default_model:
            self.model_mapping[LLMProvider.OLLAMA] = default_model

        nodes_cfg: List[LLMNodeConfig] = []
        for idx, node in enumerate(ollama_cfg.get("nodes", [])):
            try:
                nodes_cfg.append(
                    LLMNodeConfig(
                        name=node.get("name", f"ollama-node-{idx+1}"),
                        host=node["host"],
                        port=int(node.get("port", 11434)),
                        weight=int(node.get("weight", 1)),
                    )
                )
            except KeyError as exc:
                logger.warning("忽略不完整的 Ollama 節點設定（index=%s）: %s", idx, exc)

        if nodes_cfg:
            router_cfg = ollama_cfg.get("router", {}) or {}
            self.local_router = LLMNodeRouter(
                nodes=nodes_cfg,
                strategy=router_cfg.get("strategy", "round_robin"),
                cooldown_seconds=int(router_cfg.get("cooldown_seconds", 30)),
            )

    def route(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LLMRoutingResult:
        """
        選擇合適的 LLM 提供商

        Args:
            task_classification: 任務分類結果
            task: 任務描述
            context: 上下文信息

        Returns:
            LLM 路由選擇結果
        """
        logger.info(f"Routing LLM for task type: {task_classification.task_type.value}")

        task_type = task_classification.task_type

        # 獲取該任務類型的提供商規則
        target_node: Optional[str] = None

        if task_type not in self.provider_rules:
            # 默認使用 ChatGPT
            provider = LLMProvider.CHATGPT
            confidence = 0.5
            reasoning = f"未知任務類型 {task_type.value}，默認使用 ChatGPT"
        else:
            rules = self.provider_rules[task_type]

            # 考慮上下文中的提供商偏好
            if context:
                if "preferred_provider" in context:
                    preferred = context["preferred_provider"]
                    if preferred in rules:
                        rules[LLMProvider(preferred)] += 0.2

                # 考慮成本因素
                if context.get("cost_sensitive", False):
                    # 成本敏感時優先使用本地或便宜的提供商
                    if LLMProvider.OLLAMA in rules:
                        rules[LLMProvider.OLLAMA] += 0.3
                    if LLMProvider.QWEN in rules:
                        rules[LLMProvider.QWEN] += 0.2

                # 考慮延遲要求
                if context.get("low_latency", False):
                    # 低延遲要求時優先使用本地提供商
                    if LLMProvider.OLLAMA in rules:
                        rules[LLMProvider.OLLAMA] += 0.3

            # 選擇得分最高的提供商
            provider = max(rules.items(), key=lambda x: x[1])[0]
            confidence = rules[provider]
            reasoning = (
                f"根據任務類型 {task_type.value}，選擇 {provider.value} 提供商，"
                f"置信度 {confidence:.2f}"
            )

        # 獲取模型名稱
        model = self.model_mapping.get(provider, "default")

        # 獲取備用提供商列表
        fallback_providers = self.fallback_mapping.get(provider, [])

        if provider == LLMProvider.OLLAMA and self.local_router:
            node = self.local_router.select_node()
            target_node = node.name
            reasoning += f"，指派節點 {target_node}"

        logger.info(
            f"Routed to {provider.value} ({model}) with confidence {confidence:.2f}"
        )

        return LLMRoutingResult(
            provider=provider,
            model=model,
            confidence=confidence,
            reasoning=reasoning,
            fallback_providers=fallback_providers,
            target_node=target_node,
        )
