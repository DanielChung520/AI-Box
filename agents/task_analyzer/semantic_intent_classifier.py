# 代码功能说明: 语义意图分类器 - 基于 Embedding 的轻量级意图分类
# 创建日期: 2026-02-27
# 创建人: Daniel Chung
# 最后修改日期: 2026-02-27

"""语义意图分类器 - 基于 Embedding 的轻量级意图分类

产品特点：
1. 一次 Embedding 调用，延迟 < 100ms
2. 不依赖 LLM，成本低
3. 支持多语言
4. 示例库可配置，可持续学习
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class IntentCategory(Enum):
    """意图类别枚举

    非业务意图：顶层 Orchestrator 直接处理
    业务意图：转发给 BPA/Agent 处理
    """

    # 非业务/非 Agent 工作（顶层直接处理）
    GREETING = "greeting"  # 问候：你好、嗨、早安
    THANKS = "thanks"  # 感谢：谢谢、感谢
    GENERAL_QA = "general_qa"  # 通用问答：知识性问答（非业务）
    CHITCHAT = "chitchat"  # 闲聊

    # 业务/Agent 工作（转发给 BPA/Agent）
    BUSINESS_QUERY = "business_query"  # 业务查询：库存、订单
    BUSINESS_ACTION = "business_action"  # 业务操作：创建、修改
    AGENT_WORK = "agent_work"  # Agent 工作


# ===== 产品设计：意图类别示例库 =====
# 这些示例用于计算各类别的语义中心向量
INTENT_EXAMPLES: Dict[IntentCategory, List[str]] = {
    IntentCategory.GREETING: [
        # 中文
        "你好",
        "嗨",
        "早安",
        "午安",
        "晚安",
        "哈囉",
        "日安",
        "您好",
        "上好",
        "reeting",
        "在嗎",
        "好早",
        "好晚",
        # 英文
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "howdy",
        "greetings",
        # 越南文/泰文/日文等
        "xin chào",
        "sa-wat-dee",
        "konnichiwa",
        "annyeonghaseyo",
        "namaste",
    ],
    IntentCategory.THANKS: [
        # 中文
        "謝謝",
        "感謝",
        "多謝",
        "感激",
        "謝謝你",
        "謝謝您",
        "感謝您",
        "感恩",
        "致謝",
        # 英文
        "thanks",
        "thank you",
        "thank you very much",
        "appreciate",
        "much appreciated",
        "grateful",
        "thanks a lot",
    ],
    IntentCategory.GENERAL_QA: [
        # 知识性问答（不涉及业务系统，纯粹的知识/概念提问）
        # 中文 - 概念性、定义性提问
        "什麼是",
        "怎麼樣",
        "如何",
        "为什么",
        "什麼叫",
        "怎麼說",
        "介绍一下",
        "说明一下",
        "解释一下",
        "告訴我",
        "為什麼",
        "啥是",
        "啥叫",
        "这个是什么",
        "那个怎么做",
        "原理是什么",
        "怎么使用",
        "教我",
        "教學",
        # 英文
        "what is",
        "how to",
        "why does",
        "what's",
        "how does",
        "can you explain",
        "tell me about",
        "what do you mean",
        "define",
    ],
    IntentCategory.CHITCHAT: [
        # 闲聊（不涉及业务）
        # 中文
        "今天天气",
        "你怎么样",
        "最近如何",
        "有空吗",
        "聊聊",
        "今天好嗎",
        "在做什麼",
        "忙嗎",
        "最近好嗎",
        "天氣怎樣",
        # 英文
        "how are you",
        "what's up",
        "nice weather",
        "how's it going",
        "any plans",
        "what are you doing",
        "talk later",
    ],
    IntentCategory.BUSINESS_QUERY: [
        # 业务查询（具体、明确的业务需求）
        # 中文 - 完整句子示例
        "查询库存",
        "查看库存",
        "看看库存",
        "有多少库存",
        "库存多少",
        "查询订单",
        "订单状态",
        "查看料号",
        "料号库存",
        "料号规格",
        "单价多少",
        "采购单查询",
        "销售单查询",
        "帮我查库存",
        "帮我查一下订单",
        "还有货吗",
        "价格查询",
        "查詢料號庫存",
        "查看品名",
        "料號 12345 庫存",
        "訂單編號 67890 狀態",
        "帮我检查料号",
        "帮我查一下料号",
        "查一下库存",
        # 英文
        "check inventory",
        "query stock",
        "find order status",
        "show me inventory",
        "get stock level",
        "how many in stock",
        "inventory quantity",
        "stock availability",
        "order status check",
        "price query",
        "item availability",
    ],
}


class SemanticIntentClassifier:
    """基于 Embedding 的轻量级语义意图分类器

    产品特点：
    1. 一次 Embedding 调用，延迟 < 100ms
    2. 不依赖 LLM，成本低
    3. 支持多语言
    4. 示例库可配置，可持续学习

    使用方式：
    ```python
    classifier = SemanticIntentClassifier()
    category = await classifier.classify("你好")
    # -> IntentCategory.GREETING

    category = await classifier.classify("查询库存")
    # -> IntentCategory.BUSINESS_QUERY
    ```
    """

    # 置信度阈值：高于此值认为是该类别，低于则默认走业务路径
    DEFAULT_THRESHOLD = 0.75

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        embedding_service=None,
    ):
        """初始化语义意图分类器

        Args:
            threshold: 置信度阈值，低于此值默认走业务路径
            embedding_service: Embedding 服务实例（可选，默认使用全局服务）
        """
        self.threshold = threshold
        self.embedding_service = embedding_service
        self._category_embeddings: Optional[Dict[IntentCategory, np.ndarray]] = None
        self._embedding_lock = asyncio.Lock()

    async def _get_embedding_service(self):
        """获取 Embedding 服务（延迟初始化）"""
        if self.embedding_service is None:
            from services.api.services.embedding_service import get_embedding_service

            self.embedding_service = get_embedding_service()
        return self.embedding_service

    async def _ensure_category_embeddings(self) -> Dict[IntentCategory, np.ndarray]:
        """确保类别 embeddings 已计算（带缓存）"""
        if self._category_embeddings is None:
            async with self._embedding_lock:
                if self._category_embeddings is None:
                    self._category_embeddings = await self._compute_category_embeddings()
        return self._category_embeddings

    async def _compute_category_embeddings(self) -> Dict[IntentCategory, np.ndarray]:
        """计算所有类别的 embedding 向量"""
        service = await self._get_embedding_service()
        category_embeddings = {}

        for category, examples in INTENT_EXAMPLES.items():
            try:
                # 批量获取示例的 embedding
                embeddings = []
                for example in examples:
                    embedding = await service.generate_embedding(example)
                    embeddings.append(np.array(embedding))

                # 计算平均向量作为类别中心
                category_embeddings[category] = np.mean(embeddings, axis=0)
                logger.debug(
                    "category_embedding_computed",
                    category=category.value,
                    example_count=len(examples),
                )
            except Exception as e:
                logger.warning(
                    "category_embedding_computation_failed",
                    category=category.value,
                    error=str(e),
                )

        return category_embeddings

    async def classify(self, user_input: str) -> IntentCategory:
        """分类用户输入

        Args:
            user_input: 用户输入文本

        Returns:
            IntentCategory: 意图类别
        """
        if not user_input or not user_input.strip():
            logger.warning("empty_input_default_to_business")
            return IntentCategory.BUSINESS_QUERY

        user_input = user_input.strip()

        try:
            # 1. 获取用户输入的 embedding
            service = await self._get_embedding_service()
            user_embedding = await service.generate_embedding(user_input)
            user_vector = np.array(user_embedding)

            # 2. 计算与各类别的相似度
            category_embeddings = await self._ensure_category_embeddings()

            best_category = IntentCategory.BUSINESS_QUERY  # 默认
            best_score = 0.0

            for category, category_vector in category_embeddings.items():
                # 计算余弦相似度
                score = self._cosine_similarity(user_vector, category_vector)

                if score > best_score:
                    best_score = score
                    best_category = category

            # 3. 阈值判断
            if best_score >= self.threshold:
                logger.info(
                    "intent_classified",
                    input=user_input[:50],
                    category=best_category.value,
                    confidence=best_score,
                )
                return best_category
            else:
                # 低于阈值，默认走业务路径
                logger.debug(
                    "intent_below_threshold_default_to_business",
                    input=user_input[:50],
                    best_category=best_category.value,
                    best_score=best_score,
                    threshold=self.threshold,
                )
                return IntentCategory.BUSINESS_QUERY

        except Exception as e:
            logger.error(
                "intent_classification_failed",
                input=user_input[:50],
                error=str(e),
            )
            # 出错时默认走业务路径（保守策略）
            return IntentCategory.BUSINESS_QUERY

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度

        Args:
            a: 向量 A
            b: 向量 B

        Returns:
            余弦相似度 (-1 到 1)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def is_non_business_intent(self, category: IntentCategory) -> bool:
        """判断是否为非业务意图

        Args:
            category: 意图类别

        Returns:
            True: 非业务意图，顶层直接处理
            False: 业务意图，转发给 Agent
        """
        return category in [
            IntentCategory.GREETING,
            IntentCategory.THANKS,
            IntentCategory.GENERAL_QA,
            IntentCategory.CHITCHAT,
        ]


# ===== 预定义回复模板 =====
INTENT_RESPONSES: Dict[IntentCategory, str] = {
    IntentCategory.GREETING: "您好！我是 AI-Box 智能助手，很高兴为您服务。请问有什么可以帮您？",
    IntentCategory.THANKS: "不客气！很高兴能帮到您。请问还有其他需要吗？",
    IntentCategory.GENERAL_QA: "让我来帮您解答这个问题...",
    IntentCategory.CHITCHAT: "是的，我在这里。有什么我可以帮您的吗？",
}


async def get_intent_response(category: IntentCategory, user_input: str) -> Optional[str]:
    """获取意图对应的预设回复

    Args:
        category: 意图类别
        user_input: 用户输入（用于更智能的回复）

    Returns:
        预设回复，如果无预设则返回 None
    """
    # 对于 GREETING，可以根据时间智能回复
    if category == IntentCategory.GREETING:
        from datetime import datetime

        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "早上好"
        elif 12 <= hour < 14:
            greeting = "午安"
        elif 14 <= hour < 18:
            greeting = "下午好"
        else:
            greeting = "晚安"

        return f"{greeting}！我是 AI-Box 智能助手，很高兴为您服务。请问有什么可以帮您？"

    return INTENT_RESPONSES.get(category)


# ===== 全局单例 =====
_classifier: Optional[SemanticIntentClassifier] = None


def get_semantic_intent_classifier() -> SemanticIntentClassifier:
    """获取语义意图分类器单例

    Returns:
        SemanticIntentClassifier 实例
    """
    global _classifier
    if _classifier is None:
        _classifier = SemanticIntentClassifier()
    return _classifier
