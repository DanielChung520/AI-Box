# 代碼功能說明: RT 關係類型分類服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RT 關係類型分類服務 - 支持 Ollama 和 transformers 模型"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import structlog

from core.config import get_config_section
from genai.api.models.rt_models import RelationType
from llm.clients.ollama import OllamaClient, get_ollama_client
from llm.clients.gemini import GeminiClient

logger = structlog.get_logger(__name__)

# 標準關係類型定義（擴展）
STANDARD_RELATION_TYPES = {
    "LOCATED_IN": "位於",
    "WORKS_FOR": "工作於",
    "PART_OF": "屬於",
    "RELATED_TO": "相關於",
    "OCCURS_AT": "發生於",
    "CREATED_BY": "創建於",
    "OWNED_BY": "擁有於",
    "MANAGES": "管理",
    "COLLABORATES_WITH": "合作於",
    "FOUNDED": "創立",
    "LIVES_IN": "居住於",
    "STUDIES_AT": "就讀於",
    "BORN_IN": "出生於",
    "DIED_IN": "死於",
    "MARRIED_TO": "結婚於",
    "PARENT_OF": "父母",
    "CHILD_OF": "子女",
    "SIBLING_OF": "兄弟姐妹",
    "FRIEND_OF": "朋友",
    "ENEMY_OF": "敵人",
}

# 關係類型層次結構（父類型 -> 子類型列表）
RELATION_TYPE_HIERARCHY: Dict[str, List[str]] = {
    "RELATED_TO": ["WORKS_FOR", "COLLABORATES_WITH", "FRIEND_OF", "ENEMY_OF"],
    "LOCATED_IN": ["LIVES_IN", "STUDIES_AT", "BORN_IN", "DIED_IN", "OCCURS_AT"],
    "PART_OF": ["OWNED_BY", "MANAGES", "CREATED_BY"],
    "FAMILY": ["PARENT_OF", "CHILD_OF", "SIBLING_OF", "MARRIED_TO"],
}


class BaseRTModel(ABC):
    """RT 模型抽象基類"""

    @abstractmethod
    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
    ) -> List[RelationType]:
        """分類關係類型"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """檢查模型是否可用"""
        pass


class OllamaRTModel(BaseRTModel):
    """Ollama RT 模型實現"""

    def __init__(
        self, model_name: str = "qwen3-coder:30b", client: Optional[OllamaClient] = None
    ):
        self.model_name = model_name
        self.client = client or get_ollama_client()
        self._prompt_template = """請對以下關係文本進行分類，識別其關係類型，並以 JSON 格式返回結果。

關係文本：{relation_text}
{context_section}

可選的關係類型包括：
{relation_types_list}

請返回 JSON 格式，包含以下字段：
- type: 關係類型名稱
- confidence: 置信度（0-1之間的浮點數）

注意：一個關係可能屬於多個類型（多標籤分類），請返回所有相關的類型。

返回格式示例：
[
  {{"type": "WORKS_FOR", "confidence": 0.9}},
  {{"type": "RELATED_TO", "confidence": 0.7}}
]"""

    def is_available(self) -> bool:
        """檢查 Ollama 模型是否可用"""
        return self.client is not None

    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
    ) -> List[RelationType]:
        """使用 Ollama 分類關係類型"""
        if self.client is None:
            raise RuntimeError(
                f"Ollama client is not available for model {self.model_name}"
            )

        # 構建上下文
        context_section = ""
        if subject_text and object_text:
            context_section = f"主體：{subject_text}\n客體：{object_text}\n"

        # 構建關係類型列表
        relation_types_list = "\n".join(
            [f"- {k}: {v}" for k, v in STANDARD_RELATION_TYPES.items()]
        )

        prompt = self._prompt_template.format(
            relation_text=relation_text,
            context_section=context_section,
            relation_types_list=relation_types_list,
        )

        try:
            response = await self.client.generate(
                prompt,
                model=self.model_name,
                format="json",
            )

            if response is None:
                logger.error("ollama_rt_no_response", model=self.model_name)
                return []

            # 新接口返回 {"text": "...", "content": "...", "model": "..."}
            result_text = response.get("text") or response.get("content", "")
            # 嘗試從響應中提取 JSON
            try:
                # 移除可能的 markdown 代碼塊標記
                if "```json" in result_text:
                    result_text = (
                        result_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                types_data = json.loads(result_text)

                if not isinstance(types_data, list):
                    logger.error("ollama_rt_invalid_format", model=self.model_name)
                    return []

                relation_types = []
                for item in types_data:
                    if not isinstance(item, dict):
                        continue
                    relation_types.append(
                        RelationType(
                            type=item.get("type", "RELATED_TO"),
                            confidence=float(item.get("confidence", 0.5)),
                        )
                    )

                # 按置信度排序
                relation_types.sort(key=lambda x: x.confidence, reverse=True)

                return relation_types
            except json.JSONDecodeError as e:
                logger.error(
                    "ollama_rt_json_parse_failed", error=str(e), response=result_text
                )
                return []
        except Exception as e:
            logger.error(
                "ollama_rt_classification_failed", error=str(e), model=self.model_name
            )
            return []


class GeminiRTModel(BaseRTModel):
    """Gemini RT 模型實現"""

    def __init__(
        self, model_name: str = "gemini-pro", client: Optional[GeminiClient] = None
    ):
        self.model_name = model_name
        self.client: Optional[GeminiClient] = None
        try:
            self.client = client or GeminiClient()
        except (ImportError, ValueError) as e:
            # Gemini 不可用（缺少依赖或 API key），设置为 None
            logger.warning("gemini_rt_client_unavailable", error=str(e))
            self.client = None
        self._prompt_template = """請對以下關係文本進行分類，識別其關係類型，並以 JSON 格式返回結果。

關係文本：{relation_text}
{context_section}

可選的關係類型包括：
{relation_types_list}

請返回 JSON 格式，包含以下字段：
- type: 關係類型名稱
- confidence: 置信度（0-1之間的浮點數）

注意：一個關係可能屬於多個類型（多標籤分類），請返回所有相關的類型。

返回格式示例：
[
  {{"type": "WORKS_FOR", "confidence": 0.9}},
  {{"type": "RELATED_TO", "confidence": 0.7}}
]"""

    def is_available(self) -> bool:
        """檢查 Gemini 模型是否可用"""
        return self.client is not None and self.client.is_available()

    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
    ) -> List[RelationType]:
        """使用 Gemini 分類關係類型"""
        if self.client is None or not self.client.is_available():
            raise RuntimeError(
                f"Gemini client is not available for model {self.model_name}"
            )

        # 構建上下文
        context_section = ""
        if subject_text and object_text:
            context_section = f"主體：{subject_text}\n客體：{object_text}\n"

        # 構建關係類型列表
        relation_types_list = "\n".join(
            [f"- {k}: {v}" for k, v in STANDARD_RELATION_TYPES.items()]
        )

        prompt = self._prompt_template.format(
            relation_text=relation_text,
            context_section=context_section,
            relation_types_list=relation_types_list,
        )

        try:
            response = await self.client.generate(
                prompt,
                model=self.model_name,
            )

            if response is None:
                logger.error("gemini_rt_no_response", model=self.model_name)
                return []

            # 新接口返回 {"text": "...", "content": "...", "model": "..."}
            result_text = response.get("text") or response.get("content", "")
            # 嘗試從響應中提取 JSON
            try:
                # 移除可能的 markdown 代碼塊標記
                if "```json" in result_text:
                    result_text = (
                        result_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                types_data = json.loads(result_text)

                if not isinstance(types_data, list):
                    logger.error("gemini_rt_invalid_format", model=self.model_name)
                    return []

                relation_types = []
                for item in types_data:
                    if not isinstance(item, dict):
                        continue
                    relation_types.append(
                        RelationType(
                            type=item.get("type", "RELATED_TO"),
                            confidence=float(item.get("confidence", 0.5)),
                        )
                    )

                # 按置信度排序
                relation_types.sort(key=lambda x: x.confidence, reverse=True)

                return relation_types
            except json.JSONDecodeError as e:
                logger.error(
                    "gemini_rt_json_parse_failed", error=str(e), response=result_text
                )
                return []
        except Exception as e:
            logger.error(
                "gemini_rt_classification_failed", error=str(e), model=self.model_name
            )
            return []


class TransformersRTModel(BaseRTModel):
    """Transformers RT 模型實現（簡化實現）"""

    def __init__(self, model_name: str = "bert-base-chinese", enable_gpu: bool = False):
        self.model_name = model_name
        self.enable_gpu = enable_gpu
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self._load_model()

    def _load_model(self):
        """加載 transformers 模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )

            if self.enable_gpu:
                self._model = self._model.cuda()

            logger.info("transformers_rt_model_loaded", model=self.model_name)
        except ImportError:
            logger.warning("transformers_not_installed", model=self.model_name)
            self._model = None
            self._tokenizer = None
        except Exception as e:
            logger.error(
                "transformers_rt_model_load_failed", error=str(e), model=self.model_name
            )
            self._model = None
            self._tokenizer = None

    def is_available(self) -> bool:
        """檢查 transformers 模型是否可用"""
        return self._model is not None and self._tokenizer is not None

    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
    ) -> List[RelationType]:
        """使用 transformers 分類關係類型（簡化實現）"""
        if self._model is None or self._tokenizer is None:
            raise RuntimeError(
                f"Transformers RT model {self.model_name} is not available"
            )

        # 簡化實現：基於關鍵詞匹配
        relation_types = []
        relation_text_lower = relation_text.lower()

        # 簡單的關鍵詞匹配
        keyword_mapping = {
            "工作": "WORKS_FOR",
            "位於": "LOCATED_IN",
            "屬於": "PART_OF",
            "創建": "CREATED_BY",
            "擁有": "OWNED_BY",
            "管理": "MANAGES",
        }

        for keyword, rel_type in keyword_mapping.items():
            if keyword in relation_text_lower:
                relation_types.append(RelationType(type=rel_type, confidence=0.8))

        if not relation_types:
            relation_types.append(RelationType(type="RELATED_TO", confidence=0.5))

        return relation_types


class RTService:
    """RT 服務主類"""

    def __init__(self):
        self.config = get_config_section("text_analysis", "rt", default={}) or {}
        # 優先使用本地模型（Ollama），只有在無法達成時才使用外部 provider
        self.model_type = self.config.get("model_type", "ollama")
        self.model_name = self.config.get("model_name", "qwen3-coder:30b")
        self.classification_threshold = self.config.get("classification_threshold", 0.7)
        self.enable_gpu = self.config.get("enable_gpu", False)

        # 初始化模型
        self._primary_model: Optional[BaseRTModel] = None
        self._fallback_model: Optional[BaseRTModel] = None
        self._init_models()

    def _init_models(self):
        """初始化主模型和備選模型"""
        # 初始化主模型
        if self.model_type == "ollama":
            model_name = (
                self.model_name
                if ":" in self.model_name
                else f"ollama:{self.model_name}"
            )
            if model_name.startswith("ollama:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = OllamaRTModel(model_name=model_name)
        elif self.model_type == "gemini":
            model_name = (
                self.model_name
                if ":" in self.model_name
                else f"gemini:{self.model_name}"
            )
            if model_name.startswith("gemini:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = GeminiRTModel(model_name=model_name)
        elif self.model_type == "transformers":
            self._primary_model = TransformersRTModel(
                model_name=self.model_name, enable_gpu=self.enable_gpu
            )
        else:
            logger.warning("unknown_rt_model_type", model_type=self.model_type)
            self._primary_model = None

        # 初始化備選模型
        # 優先使用本地模型（Ollama），外部 provider 作為最後備選
        if self.model_type == "ollama":
            # Ollama 不可用時，嘗試使用 Gemini（外部 provider）
            self._fallback_model = GeminiRTModel(model_name="gemini-pro")
        elif self.model_type == "gemini":
            # Gemini 不可用時，優先嘗試本地 Ollama
            self._fallback_model = OllamaRTModel(model_name="qwen3-coder:30b")
        else:
            # 其他類型（如 transformers）不可用時，優先嘗試本地 Ollama
            self._fallback_model = OllamaRTModel(model_name="qwen3-coder:30b")

    def _get_model(self, model_type: Optional[str] = None) -> Optional[BaseRTModel]:
        """獲取可用的模型"""
        requested_type = model_type or self.model_type

        model: Optional[BaseRTModel] = None
        if requested_type == "ollama":
            if isinstance(self._primary_model, OllamaRTModel):
                model = self._primary_model
        elif requested_type == "gemini":
            if isinstance(self._primary_model, GeminiRTModel):
                model = self._primary_model
        elif requested_type == "transformers":
            if isinstance(self._primary_model, TransformersRTModel):
                model = self._primary_model
        else:
            model = self._primary_model

        # 如果請求的模型不可用，嘗試使用備選模型
        if model and model.is_available():
            return model

        if self._fallback_model and self._fallback_model.is_available():
            logger.info("using_fallback_rt_model", requested=requested_type)
            return self._fallback_model

        return None

    def _validate_relation_types(
        self, relation_types: List[RelationType]
    ) -> List[RelationType]:
        """驗證關係類型（確保類型一致性）"""
        # 過濾低置信度的類型
        filtered = [
            rt
            for rt in relation_types
            if rt.confidence >= self.classification_threshold
        ]

        # 檢測類型衝突（如果有多個類型，檢查是否有衝突）
        if len(filtered) > 1:
            # 簡單的衝突檢測：檢查是否有互斥的類型
            # 這裡可以添加更複雜的衝突檢測邏輯
            pass

        return filtered

    def _apply_type_hierarchy(
        self, relation_types: List[RelationType]
    ) -> List[RelationType]:
        """應用關係類型層次結構"""
        # 如果子類型存在，移除父類型
        type_names = [rt.type for rt in relation_types]
        filtered = []

        for rt in relation_types:
            # 檢查是否有子類型
            has_child = False
            for parent, children in RELATION_TYPE_HIERARCHY.items():
                if rt.type == parent:
                    # 檢查是否有子類型在列表中
                    if any(child in type_names for child in children):
                        has_child = True
                        break

            if not has_child:
                filtered.append(rt)

        return filtered

    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[RelationType]:
        """分類關係類型"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available RT model")

        relation_types = await model.classify_relation_type(
            relation_text, subject_text, object_text
        )
        relation_types = self._validate_relation_types(relation_types)
        relation_types = self._apply_type_hierarchy(relation_types)

        return relation_types

    async def classify_relation_types_batch(
        self, requests: List[dict], model_type: Optional[str] = None
    ) -> List[List[RelationType]]:
        """批量分類關係類型"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available RT model")

        results = []
        for req in requests:
            try:
                relation_types = await self.classify_relation_type(
                    req.get("relation_text", ""),
                    req.get("subject_text"),
                    req.get("object_text"),
                    model_type,
                )
                results.append(relation_types)
            except Exception as e:
                logger.error("rt_batch_classification_failed", error=str(e))
                results.append([])

        return results
