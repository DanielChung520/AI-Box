# 代碼功能說明: NER 命名實體識別服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""NER 命名實體識別服務 - 支持 spaCy 和 Ollama 模型"""

import json
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import structlog

from genai.api.models.ner_models import Entity
from llm.clients.gemini import GeminiClient
from llm.clients.ollama import OllamaClient, get_ollama_client
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 標準實體類型定義
STANDARD_ENTITY_TYPES = {
    "PERSON": "人物",
    "ORG": "組織",
    "LOC": "地點",
    "DATE": "日期",
    "MONEY": "金額",
    "PRODUCT": "產品",
    "EVENT": "事件",
}

# spaCy 實體類型映射到標準類型
SPACY_ENTITY_MAPPING = {
    "PERSON": "PERSON",
    "PER": "PERSON",
    "ORG": "ORG",
    "ORGANIZATION": "ORG",
    "LOC": "LOC",
    "GPE": "LOC",
    "LOCATION": "LOC",
    "DATE": "DATE",
    "TIME": "DATE",
    "MONEY": "MONEY",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
}


class BaseNERModel(ABC):
    """NER 模型抽象基類"""

    @abstractmethod
    async def extract_entities(self, text: str) -> List[Entity]:
        """提取實體"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """檢查模型是否可用"""
        pass


class SpacyNERModel(BaseNERModel):
    """spaCy NER 模型實現"""

    def __init__(self, model_name: str = "zh_core_web_sm", enable_gpu: bool = False):
        self.model_name = model_name
        self.enable_gpu = enable_gpu
        self._model: Optional[Any] = None
        self._load_model()

    def _load_model(self):
        """加載 spaCy 模型"""
        try:
            import spacy

            if self.enable_gpu:
                spacy.require_gpu()

            self._model = spacy.load(self.model_name)
            logger.info("spacy_model_loaded", model=self.model_name)
        except ImportError:
            logger.warning("spacy_not_installed", model=self.model_name)
            self._model = None
        except Exception as e:
            logger.error("spacy_model_load_failed", error=str(e), model=self.model_name)
            self._model = None

    def is_available(self) -> bool:
        """檢查 spaCy 模型是否可用"""
        return self._model is not None

    async def extract_entities(self, text: str) -> List[Entity]:
        """使用 spaCy 提取實體"""
        if self._model is None:
            raise RuntimeError(f"spaCy model {self.model_name} is not available")

        doc = self._model(text)
        entities = []

        for ent in doc.ents:
            # 映射 spaCy 實體類型到標準類型
            standard_label = SPACY_ENTITY_MAPPING.get(ent.label_, ent.label_)
            entities.append(
                Entity(
                    text=ent.text,
                    label=standard_label,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.95,  # spaCy 不提供置信度，使用默認值
                )
            )

        return entities


class OllamaNERModel(BaseNERModel):
    """Ollama NER 模型實現"""

    def __init__(self, model_name: str = "qwen3-coder:30b", client: Optional[OllamaClient] = None):
        self.model_name = model_name
        self.client = client or get_ollama_client()
        self._prompt_template = """請從以下文本中識別命名實體，並以 JSON 格式返回結果。
文本：{text}

請返回 JSON 格式，包含以下字段：
- text: 實體文本
- label: 實體類型（PERSON, ORG, LOC, DATE, MONEY, PRODUCT, EVENT 等）
- start: 實體在文本中的起始位置（字符索引）
- end: 實體在文本中的結束位置（字符索引）
- confidence: 置信度（0-1之間的浮點數）

返回格式示例：
[
  {{"text": "張三", "label": "PERSON", "start": 0, "end": 2, "confidence": 0.95}},
  {{"text": "北京", "label": "LOC", "start": 5, "end": 7, "confidence": 0.90}}
]"""

    def is_available(self) -> bool:
        """檢查 Ollama 模型是否可用"""
        return self.client is not None

    async def extract_entities(
        self,
        text: str,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
        """使用 Ollama 提取實體"""
        if self.client is None:
            raise RuntimeError(f"Ollama client is not available for model {self.model_name}")

        prompt = self._prompt_template.format(text=text)

        try:
            response = await self.client.generate(
                prompt,
                model=self.model_name,
                format="json",  # 強制JSON格式
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
                purpose="ner",
            )

            if response is None:
                logger.error("ollama_ner_no_response", model=self.model_name)
                return []

            # 新接口返回 {"text": "...", "content": "...", "model": "..."}
            result_text = response.get("text") or response.get("content", "")
            # 嘗試從響應中提取 JSON
            try:
                # 移除可能的 markdown 代碼塊標記
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                # 初始化entities_data
                entities_data = None

                # 尝试多种方式解析JSON
                # 方法1: 查找第一个 '[' 和最后一个 ']'（提取数组）
                start_idx = result_text.find("[")
                end_idx = result_text.rfind("]")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    # 提取数组部分
                    array_text = result_text[start_idx : end_idx + 1]
                    try:
                        entities_data = json.loads(array_text)
                        if isinstance(entities_data, list):
                            # 成功解析为数组
                            pass
                        else:
                            entities_data = None
                    except json.JSONDecodeError:
                        # 如果解析失败，尝试其他方法
                        entities_data = None

                # 方法2: 如果方法1失败，尝试解析整个响应为对象
                if entities_data is None:
                    try:
                        parsed_obj = json.loads(result_text)
                        if isinstance(parsed_obj, dict):
                            # 如果是对象，尝试提取entities字段
                            if "entities" in parsed_obj:
                                entities_data = parsed_obj["entities"]
                            elif "text" in parsed_obj and (
                                "label" in parsed_obj
                                or "type" in parsed_obj
                                or "entity_type" in parsed_obj
                            ):
                                # 單個 entity 物件：轉成 list 以符合下游處理
                                entities_data = [parsed_obj]
                            elif len(parsed_obj) == 1 and isinstance(
                                list(parsed_obj.values())[0], list
                            ):
                                # 如果对象只有一个键，且值是数组，使用该数组
                                entities_data = list(parsed_obj.values())[0]
                            elif all(
                                isinstance(v, dict) and "text" in v for v in parsed_obj.values()
                            ):
                                # 形如 {"id1": {...entity...}, "id2": {...entity...}}
                                entities_data = list(parsed_obj.values())
                        elif isinstance(parsed_obj, list):
                            # 直接是数组
                            entities_data = parsed_obj
                    except json.JSONDecodeError:
                        # 如果整个响应不是有效JSON，尝试提取第一个有效的JSON对象
                        # 查找第一个 '{' 和对应的 '}'
                        obj_start = result_text.find("{")
                        if obj_start != -1:
                            # 尝试找到匹配的 '}'
                            brace_count = 0
                            obj_end = -1
                            for i in range(obj_start, len(result_text)):
                                if result_text[i] == "{":
                                    brace_count += 1
                                elif result_text[i] == "}":
                                    brace_count -= 1
                                    if brace_count == 0:
                                        obj_end = i
                                        break

                            if obj_end != -1:
                                obj_text = result_text[obj_start : obj_end + 1]
                                try:
                                    parsed_obj = json.loads(obj_text)
                                    if isinstance(parsed_obj, dict) and "entities" in parsed_obj:
                                        entities_data = parsed_obj["entities"]
                                except json.JSONDecodeError:
                                    pass

                # 如果仍然无法解析，返回空列表
                if entities_data is None or not isinstance(entities_data, list):
                    logger.warning(
                        "ollama_ner_no_valid_json",
                        model=self.model_name,
                        response_preview=result_text[:300],
                    )
                    return []

                entities = []
                for item in entities_data:
                    if not isinstance(item, dict):
                        continue
                    entities.append(
                        Entity(
                            text=item.get("text", ""),
                            label=item.get("label")
                            or item.get("type")
                            or item.get("entity_type")
                            or "UNKNOWN",
                            start=item.get("start", 0),
                            end=item.get("end", 0),
                            confidence=float(item.get("confidence", 0.5)),
                        )
                    )

                return entities
            except json.JSONDecodeError as e:
                logger.error("ollama_ner_json_parse_failed", error=str(e), response=result_text)
                return []
        except Exception as e:
            logger.error("ollama_ner_extraction_failed", error=str(e), model=self.model_name)
            return []


class GeminiNERModel(BaseNERModel):
    """Gemini NER 模型實現"""

    def __init__(self, model_name: str = "gemini-pro", client: Optional[GeminiClient] = None):
        self.model_name = model_name
        self.client: Optional[GeminiClient] = None
        try:
            self.client = client or GeminiClient()
        except (ImportError, ValueError) as e:
            # Gemini 不可用（缺少依赖或 API key），设置为 None
            logger.warning("gemini_ner_client_unavailable", error=str(e))
            self.client = None
        self._prompt_template = """請從以下文本中識別命名實體，並以 JSON 格式返回結果。
文本：{text}

請返回 JSON 格式，包含以下字段：
- text: 實體文本
- label: 實體類型（PERSON, ORG, LOC, DATE, MONEY, PRODUCT, EVENT 等）
- start: 實體在文本中的起始位置（字符索引）
- end: 實體在文本中的結束位置（字符索引）
- confidence: 置信度（0-1之間的浮點數）

返回格式示例：
[
  {{"text": "張三", "label": "PERSON", "start": 0, "end": 2, "confidence": 0.95}},
  {{"text": "北京", "label": "LOC", "start": 5, "end": 7, "confidence": 0.90}}
]"""

    def is_available(self) -> bool:
        """檢查 Gemini 模型是否可用"""
        return self.client is not None and self.client.is_available()

    async def extract_entities(self, text: str) -> List[Entity]:
        """使用 Gemini 提取實體"""
        if self.client is None or not self.client.is_available():
            raise RuntimeError(f"Gemini client is not available for model {self.model_name}")

        prompt = self._prompt_template.format(text=text)

        try:
            response = await self.client.generate(
                prompt,
                model=self.model_name,
            )

            if response is None:
                logger.error("gemini_ner_no_response", model=self.model_name)
                return []

            # 新接口返回 {"text": "...", "content": "...", "model": "..."}
            result_text = response.get("text") or response.get("content", "")
            # 嘗試從響應中提取 JSON
            try:
                # 移除可能的 markdown 代碼塊標記
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                entities_data = json.loads(result_text)

                if not isinstance(entities_data, list):
                    logger.error("gemini_ner_invalid_format", model=self.model_name)
                    return []

                entities = []
                for item in entities_data:
                    if not isinstance(item, dict):
                        continue
                    entities.append(
                        Entity(
                            text=item.get("text", ""),
                            label=item.get("label", "UNKNOWN"),
                            start=item.get("start", 0),
                            end=item.get("end", 0),
                            confidence=float(item.get("confidence", 0.5)),
                        )
                    )

                return entities
            except json.JSONDecodeError as e:
                logger.error("gemini_ner_json_parse_failed", error=str(e), response=result_text)
                return []
        except Exception as e:
            logger.error("gemini_ner_extraction_failed", error=str(e), model=self.model_name)
            return []


class NERService:
    """NER 服務主類"""

    def __init__(self):
        self.config = get_config_section("text_analysis", "ner", default={}) or {}
        # 優先使用本地模型（Ollama），只有在無法達成時才使用外部 provider
        self.model_type = self.config.get("model_type", "ollama")
        # 优先从环境变量读取，然后从配置读取，最后使用默认值
        import os

        self.model_name = os.getenv("OLLAMA_NER_MODEL") or self.config.get(
            "model_name", "gpt-oss:20b"
        )
        # Fallback 順序：本地模型優先，外部 provider 作為最後備選
        self.fallback_model = self.config.get("fallback_model", "gemini:gemini-pro")
        self.batch_size = self.config.get("batch_size", 32)
        self.enable_gpu = self.config.get("enable_gpu", False)

        # 初始化模型
        self._primary_model: Optional[BaseNERModel] = None
        self._fallback_model: Optional[BaseNERModel] = None
        self._init_models()

    def _init_models(self):
        """初始化主模型和備選模型"""
        # 初始化主模型
        if self.model_type == "spacy":
            self._primary_model = SpacyNERModel(
                model_name=self.model_name, enable_gpu=self.enable_gpu
            )
        elif self.model_type == "ollama":
            model_name = self.model_name if ":" in self.model_name else f"ollama:{self.model_name}"
            if model_name.startswith("ollama:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = OllamaNERModel(model_name=model_name)
        elif self.model_type == "gemini":
            model_name = self.model_name if ":" in self.model_name else f"gemini:{self.model_name}"
            if model_name.startswith("gemini:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = GeminiNERModel(model_name=model_name)
        else:
            logger.warning("unknown_ner_model_type", model_type=self.model_type)
            self._primary_model = None

        # 初始化備選模型
        # 優先使用本地模型（Ollama），外部 provider 作為最後備選
        if self.fallback_model:
            if self.fallback_model.startswith("ollama:"):
                fallback_name = self.fallback_model.split(":", 1)[1]
                self._fallback_model = OllamaNERModel(model_name=fallback_name)
            elif self.fallback_model.startswith("gemini:"):
                fallback_name = self.fallback_model.split(":", 1)[1]
                self._fallback_model = GeminiNERModel(model_name=fallback_name)
            else:
                self._fallback_model = None
        else:
            # 如果未配置 fallback，根據主模型類型自動選擇
            # 優先使用本地模型作為 fallback
            if self.model_type == "gemini":
                # 如果主模型是外部 provider，fallback 使用本地模型
                self._fallback_model = OllamaNERModel(model_name="qwen3-coder:30b")
            elif self.model_type != "ollama":
                # 如果主模型不是 Ollama，fallback 優先使用本地模型
                self._fallback_model = OllamaNERModel(model_name="qwen3-coder:30b")

    def _get_model(self, model_type: Optional[str] = None) -> Optional[BaseNERModel]:
        """獲取可用的模型"""
        requested_type = model_type or self.model_type

        model: Optional[BaseNERModel] = None
        if requested_type == "spacy":
            if isinstance(self._primary_model, SpacyNERModel):
                model = self._primary_model
        elif requested_type == "ollama":
            if isinstance(self._primary_model, OllamaNERModel):
                model = self._primary_model
        elif requested_type == "gemini":
            if isinstance(self._primary_model, GeminiNERModel):
                model = self._primary_model
        else:
            model = self._primary_model

        # 如果請求的模型不可用，嘗試使用備選模型
        if model and model.is_available():
            return model

        if self._fallback_model and self._fallback_model.is_available():
            logger.info("using_fallback_ner_model", requested=requested_type)
            return self._fallback_model

        return None

    async def extract_entities(
        self,
        text: str,
        model_type: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
        """提取實體"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available NER model")

        # 只有Ollama模型支持追踪参数
        from genai.api.services.ner_service import OllamaNERModel

        if isinstance(model, OllamaNERModel):
            return await model.extract_entities(
                text, user_id=user_id, file_id=file_id, task_id=task_id
            )
        else:
            return await model.extract_entities(text)

    async def extract_entities_batch(
        self, texts: List[str], model_type: Optional[str] = None
    ) -> List[List[Entity]]:
        """批量提取實體"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available NER model")

        results = []
        for text in texts:
            try:
                entities = await model.extract_entities(text)
                results.append(entities)
            except Exception as e:
                logger.error("ner_batch_extraction_failed", error=str(e), text=text[:50])
                results.append([])

        return results
