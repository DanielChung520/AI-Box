# 代碼功能說明: RT 關係類型分類服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-23 00:55 UTC+8

"""RT 關係類型分類服務 - 支持 Ollama 和 transformers 模型"""

import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from genai.api.models.rt_models import RelationType
from llm.clients.gemini import GeminiClient
from llm.clients.ollama import OllamaClient, get_ollama_client
from system.infra.config.config import get_config_section

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

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
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[RelationType]:
        """分類關係類型"""
        pass

    async def classify_relation_types_batch(
        self,
        requests: List[Dict[str, Any]],
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[List[RelationType]]:
        """批量分類關係類型（可選覆寫；預設為逐條調用）。"""
        results: List[List[RelationType]] = []
        for req in requests:
            relation_types = await self.classify_relation_type(
                req.get("relation_text", ""),
                req.get("subject_text"),
                req.get("object_text"),
                ontology_rules=ontology_rules,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
            )
            results.append(relation_types)
        return results

    @abstractmethod
    def is_available(self) -> bool:
        """檢查模型是否可用"""
        pass


class OllamaRTModel(BaseRTModel):
    """Ollama RT 模型實現"""

    def __init__(self, model_name: str = "qwen3-coder:30b", client: Optional[OllamaClient] = None):
        self.model_name = model_name
        self.client = client or get_ollama_client()
        self._prompt_template = """## 任務
對以下關係文本進行分類，識別其關係類型。

## 重要規則（必須嚴格遵守）
1. **只返回一個 JSON 數組**，不要返回任何其他內容
2. 不要添加 markdown 代碼塊標記（如 ```json）
3. 不要用額外的對象包裹數組（例如不要返回 {{"types": [...]}} 或 {{"results": [...]}}）
4. 一個關係可能屬於多個類型（多標籤分類），請返回所有相關的類型

## 關係文本
{relation_text}
{context_section}

## 可選的關係類型
{relation_types_list}

## 必須返回的 JSON 格式
直接返回一個 JSON 數組，每個元素包含：
- type: 關係類型名稱（使用上方列出的類型）
- confidence: 置信度（0-1之間的浮點數）

## 正確示例
[
  {{"type": "WORKS_FOR", "confidence": 0.95}},
  {{"type": "RELATED_TO", "confidence": 0.7}}
]

## 錯誤示例（不要這樣返回）
{{"types": [...]}}           <!-- 錯誤：被額外對象包裹 -->
{{"index": 0, "types": [...]}}  <!-- 錯誤：被額外對象包裹 -->
```json [...] ```           <!-- 錯誤：包含 markdown 代碼塊 -->"""

    def is_available(self) -> bool:
        """檢查 Ollama 模型是否可用"""
        return self.client is not None

    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[RelationType]:
        """使用 Ollama 分類關係類型"""
        if self.client is None:
            raise RuntimeError(f"Ollama client is not available for model {self.model_name}")

        # 構建上下文
        context_section = ""
        if subject_text and object_text:
            context_section = f"主體：{subject_text}\n客體：{object_text}\n"

        # 構建關係類型列表（優先使用 Ontology，否則使用標準類型）
        if ontology_rules:
            relationship_types = ontology_rules.get("relationship_types", [])
            if relationship_types:
                relation_types_list = "\n".join([f"- {rt}" for rt in sorted(relationship_types)])
            else:
                relation_types_list = "\n".join(
                    [f"- {k}: {v}" for k, v in STANDARD_RELATION_TYPES.items()]
                )
        else:
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
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
                purpose="rt",
                options={"num_ctx": 32768},  # 設置 context window 為 32k
            )

            if response is None:
                logger.error(f"ollama_rt_no_response: model={self.model_name}")
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

                types_data = json.loads(result_text)

                # 如果返回的是字典，嘗試轉換為列表（類似 RE service 的處理邏輯）
                if not isinstance(types_data, list):
                    logger.error(
                        f"ollama_rt_invalid_format: model={self.model_name}, "
                        f"response_type={type(types_data).__name__}, "
                        f"response_preview={str(types_data)[:500]}"
                    )
                    # 嘗試從字典中提取列表
                    if isinstance(types_data, dict):
                        # 檢查是否有常見的鍵（如 "types", "results", "data", "items"）
                        for key in [
                            "types",
                            "results",
                            "data",
                            "result",
                            "items",
                            "relation_types",
                        ]:
                            if key in types_data and isinstance(types_data[key], list):
                                types_data = types_data[key]
                                logger.info(
                                    f"ollama_rt_format_converted: converted_key={key}, "
                                    f"types_count={len(types_data)}"
                                )
                                break
                        else:
                            # 如果沒有找到列表鍵，檢查是否是單個類型對象
                            if "type" in types_data or (
                                "types" in types_data and not isinstance(types_data["types"], list)
                            ):
                                # 將單個類型對象轉換為列表
                                types_data = [types_data]
                                logger.info(
                                    "ollama_rt_format_converted: converted_key=single_type_object, types_count=1"
                                )
                            else:
                                logger.warning(
                                    f"ollama_rt_format_unknown: response_preview={str(types_data)[:500]}, "
                                    "message=無法識別的 RT 返回格式"
                                )
                                return []
                    else:
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
                logger.error(f"ollama_rt_json_parse_failed: error={str(e)}, response={result_text}")
                return []
        except Exception as e:
            logger.error(
                f"ollama_rt_classification_failed: error={str(e)}, model={self.model_name}"
            )
            return []

    async def classify_relation_types_batch(
        self,
        requests: List[Dict[str, Any]],
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[List[RelationType]]:
        """使用 Ollama 批量分類關係類型（單次 LLM 呼叫）。"""
        if self.client is None:
            raise RuntimeError(f"Ollama client is not available for model {self.model_name}")

        if not requests:
            return []

        # 構建關係類型列表（優先使用 Ontology，否則使用標準類型）
        if ontology_rules:
            relationship_types = ontology_rules.get("relationship_types", [])
            if relationship_types:
                relation_types_list = "\n".join([f"- {rt}" for rt in sorted(relationship_types)])
            else:
                relation_types_list = "\n".join(
                    [f"- {k}: {v}" for k, v in STANDARD_RELATION_TYPES.items()]
                )
        else:
            relation_types_list = "\n".join(
                [f"- {k}: {v}" for k, v in STANDARD_RELATION_TYPES.items()]
            )

        # 組裝批次請求（避免 LLM 失去對應順序）
        batch_items = []
        for idx, req in enumerate(requests):
            batch_items.append(
                {
                    "index": idx,
                    "relation_text": req.get("relation_text", ""),
                    "subject_text": req.get("subject_text"),
                    "object_text": req.get("object_text"),
                }
            )

        prompt = f"""你是一個關係類型分類器（RT）。請根據每筆 relation 的 relation_text +（可選）subject/object 上下文，從下列可選類型中選擇最合適的類型（可多選），並回傳 JSON。

可選的關係類型包括：
{relation_types_list}

輸入（JSON）：
{json.dumps(batch_items, ensure_ascii=False)}

請回傳 JSON 陣列，格式如下：
[
  {{"index": 0, "types": [{{"type":"RELATED_TO","confidence":0.7}}]}},
  {{"index": 1, "types": [{{"type":"LOCATED_IN","confidence":0.9}}, {{"type":"RELATED_TO","confidence":0.6}}]}}
]

規則：
- 必須保留 index 對應
- confidence 為 0~1
- 若無法判斷，回傳 RELATED_TO
"""

        response = await self.client.generate(
            prompt,
            model=self.model_name,
            format="json",
            user_id=user_id,
            file_id=file_id,
            task_id=task_id,
            purpose="rt_batch",
            options={"num_ctx": 32768},  # 設置 context window 為 32k
        )

        if response is None:
            logger.error("ollama_rt_no_response", model=self.model_name)
            return [[] for _ in requests]

        result_text = response.get("text") or response.get("content", "")
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(result_text)
            # 允許 {"results":[...]} 包裝
            if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
                parsed = parsed["results"]

            # 如果返回的是字典，嘗試轉換為列表（類似 RE service 的處理邏輯）
            if not isinstance(parsed, list):
                logger.error(
                    f"ollama_rt_invalid_format: model={self.model_name}, "
                    f"response_type={type(parsed).__name__}, "
                    f"response_preview={str(parsed)[:500]}"
                )
                # 嘗試從字典中提取列表
                if isinstance(parsed, dict):
                    # 檢查是否有常見的鍵（如 "types", "results", "data", "items"）
                    for key in [
                        "types",
                        "results",
                        "data",
                        "result",
                        "items",
                        "relation_types",
                    ]:
                        if key in parsed and isinstance(parsed[key], list):
                            parsed = parsed[key]
                            logger.info(
                                f"ollama_rt_format_converted: converted_key={key}, "
                                f"types_count={len(parsed)}"
                            )
                            break
                    else:
                        # 如果沒有找到列表鍵，檢查是否是單個類型對象（帶有 "index" 和 "types"）
                        if "index" in parsed and "types" in parsed:
                            parsed = [parsed]
                            logger.info(
                                "ollama_rt_format_converted: converted_key=single_type_object, "
                                "types_count=1"
                            )
                        else:
                            logger.warning(
                                f"ollama_rt_format_unknown: response_preview={str(parsed)[:500]}, "
                                "message=無法識別的 RT 返回格式"
                            )
                            return [[] for _ in requests]
                else:
                    return [[] for _ in requests]

            if not isinstance(parsed, list):
                logger.error(
                    f"ollama_rt_invalid_format_after_conversion: model={self.model_name}, "
                    f"response_type={type(parsed).__name__}"
                )
                return [[] for _ in requests]

            # index -> types
            types_by_index: Dict[int, List[RelationType]] = {}
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                idx_raw = item.get("index")
                types = item.get("types")
                if not isinstance(idx_raw, int) or not isinstance(types, list):
                    continue
                # idx_raw 已檢查為 int，用於索引
                item_idx: int = idx_raw  # type: ignore[assignment]  # 已檢查為 int，重命名避免與外層 idx 衝突
                rt_list: List[RelationType] = []
                for t in types:
                    if not isinstance(t, dict):
                        continue
                    rt_list.append(
                        RelationType(
                            type=t.get("type", "RELATED_TO"),
                            confidence=float(t.get("confidence", 0.5)),
                        )
                    )
                rt_list.sort(key=lambda x: x.confidence, reverse=True)
                types_by_index[item_idx] = rt_list

            results: List[List[RelationType]] = []
            for idx in range(len(requests)):
                results.append(types_by_index.get(idx, []))
            return results
        except json.JSONDecodeError as e:
            logger.error(
                "ollama_rt_json_parse_failed",
                error=str(e),
                response=result_text[:500],
            )
            return [[] for _ in requests]


class GeminiRTModel(BaseRTModel):
    """Gemini RT 模型實現"""

    def __init__(
        self, model_name: str = "gemini-pro-latest", client: Optional[GeminiClient] = None
    ):
        self.model_name = model_name
        self.client: Optional[GeminiClient] = None
        try:
            self.client = client or GeminiClient()
        except (ImportError, ValueError) as e:
            # Gemini 不可用（缺少依赖或 API key），设置为 None
            logger.warning(f"gemini_rt_client_unavailable: error={str(e)}")
            self.client = None
        self._prompt_template = """## 任務
對以下關係文本進行分類，識別其關係類型。

## 重要規則（必須嚴格遵守）
1. **只返回一個 JSON 數組**，不要返回任何其他內容
2. 不要添加 markdown 代碼塊標記（如 ```json）
3. 不要用額外的對象包裹數組（例如不要返回 {{"types": [...]}} 或 {{"results": [...]}}）
4. 一個關係可能屬於多個類型（多標籤分類），請返回所有相關的類型

## 關係文本
{relation_text}
{context_section}

## 可選的關係類型
{relation_types_list}

## 必須返回的 JSON 格式
直接返回一個 JSON 數組，每個元素包含：
- type: 關係類型名稱（使用上方列出的類型）
- confidence: 置信度（0-1之間的浮點數）

## 正確示例
[
  {{"type": "WORKS_FOR", "confidence": 0.95}},
  {{"type": "RELATED_TO", "confidence": 0.7}}
]

## 錯誤示例（不要這樣返回）
{{"types": [...]}}           <!-- 錯誤：被額外對象包裹 -->
{{"index": 0, "types": [...]}}  <!-- 錯誤：被額外對象包裹 -->
```json [...] ```           <!-- 錯誤：包含 markdown 代碼塊 -->"""

    def is_available(self) -> bool:
        """檢查 Gemini 模型是否可用"""
        return self.client is not None and self.client.is_available()

    async def classify_relation_type(
        self,
        relation_text: str,
        subject_text: Optional[str] = None,
        object_text: Optional[str] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[RelationType]:
        """使用 Gemini 分類關係類型"""
        if self.client is None or not self.client.is_available():
            raise RuntimeError(f"Gemini client is not available for model {self.model_name}")

        # 構建上下文
        context_section = ""
        if subject_text and object_text:
            context_section = f"主體：{subject_text}\n客體：{object_text}\n"

        # 構建關係類型列表（優先使用 Ontology，否則使用標準類型）
        if ontology_rules:
            relationship_types = ontology_rules.get("relationship_types", [])
            if relationship_types:
                relation_types_list = "\n".join([f"- {rt}" for rt in sorted(relationship_types)])
            else:
                relation_types_list = "\n".join(
                    [f"- {k}: {v}" for k, v in STANDARD_RELATION_TYPES.items()]
                )
        else:
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
                logger.error(f"gemini_rt_no_response: model={self.model_name}")
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

                types_data = json.loads(result_text)

                if not isinstance(types_data, list):
                    logger.error(f"gemini_rt_invalid_format: model={self.model_name}")
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
                logger.error(f"gemini_rt_json_parse_failed: error={str(e)}, response={result_text}")
                return []
        except Exception as e:
            logger.error(
                f"gemini_rt_classification_failed: error={str(e)}, model={self.model_name}"
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
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

            if self.enable_gpu:
                self._model = self._model.cuda()

            logger.info(f"transformers_rt_model_loaded: model={self.model_name}")
        except ImportError:
            logger.warning(f"transformers_not_installed: model={self.model_name}")
            self._model = None
            self._tokenizer = None
        except Exception as e:
            logger.error(
                f"transformers_rt_model_load_failed: model={self.model_name}, error={str(e)}"
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
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[RelationType]:
        """使用 transformers 分類關係類型（簡化實現）（注：transformers 模型不支持 ontology_rules，但為了接口一致性保留此參數）"""
        if self._model is None or self._tokenizer is None:
            raise RuntimeError(f"Transformers RT model {self.model_name} is not available")

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

        # MoE 場景名稱
        self._moe_scene = "knowledge_graph_extraction"
        self._moe_model_config = None

        # 優先使用 MoE 配置
        moe_model = self._get_moe_model_config()
        if moe_model:
            self.model_name = moe_model.model
            self.model_type = "ollama"  # MoE 返回的模型都是 Ollama 格式
            self._moe_model_config = moe_model
            logger.info(
                f"rt_using_moe_config: model={self.model_name}, scene={self._moe_scene}, "
                f"temperature={moe_model.temperature}, timeout={moe_model.timeout}"
            )
        else:
            # 向後兼容：使用原有配置
            self._init_model_from_config()

        self.classification_threshold = self.config.get("classification_threshold", 0.7)
        self.enable_gpu = self.config.get("enable_gpu", False)

        # 初始化模型
        self._primary_model: Optional[BaseRTModel] = None
        self._fallback_model: Optional[BaseRTModel] = None
        self._init_models()

    def _get_moe_model_config(self):
        """從 MoE 獲取模型配置"""
        from llm.moe.moe_manager import LLMMoEManager

        try:
            moe_manager = LLMMoEManager()
            result = moe_manager.select_model(self._moe_scene)
            if result:
                return result
        except Exception as e:
            logger.debug(
                f"failed_to_get_moe_model_config: scene={self._moe_scene}, error={str(e)}, "
                "message=從 MoE 獲取模型配置失敗，使用向後兼容方式"
            )
        return None

    def _init_model_from_config(self):
        """從配置文件初始化模型（向後兼容）"""
        import os

        # 優先級1: 從 ArangoDB system_configs 讀取 model_type 和 model_name
        model_type = None
        model_name = None
        try:
            from services.api.services.config_store_service import ConfigStoreService

            config_service = ConfigStoreService()
            kg_config = config_service.get_config("kg_extraction", tenant_id=None)
            if kg_config and kg_config.config_data:
                model_type = kg_config.config_data.get("rt_model_type")
                model_name = kg_config.config_data.get("rt_model")
                if model_type:
                    logger.debug(
                        f"rt_model_type_from_system_configs: model_type={model_type}, "
                        "message=從 ArangoDB system_configs 讀取 RT model_type 配置"
                    )
                if model_name:
                    logger.debug(
                        f"rt_model_from_system_configs: model={model_name}, "
                        "message=從 ArangoDB system_configs 讀取 RT 模型配置"
                    )
        except Exception as e:
            logger.debug(
                f"failed_to_load_rt_model_from_system_configs: error={str(e)}, "
                "message=從 ArangoDB 讀取 RT 模型配置失敗，使用向後兼容方式"
            )

        # 優先級2: 從環境變量讀取 model_type（允許覆蓋 ArangoDB 配置）
        env_model_type = os.getenv("RT_MODEL_TYPE")
        if env_model_type:
            model_type = env_model_type

        # 優先級3: 從 config.json 讀取 model_type（向後兼容）
        if not model_type:
            model_type = self.config.get("model_type", "ollama")
        self.model_type = model_type or "ollama"

        # 優先級4: 從環境變量讀取（只在 model_type 匹配時覆蓋）
        if self.model_type == "ollama":
            env_model_name = os.getenv("OLLAMA_RT_MODEL") or os.getenv("OLLAMA_NER_MODEL")
            if env_model_name:
                model_name = env_model_name
                logger.debug(
                    f"rt_model_from_env: model={model_name}, " "message=從環境變量讀取 RT 模型配置（覆蓋）"
                )
        elif self.model_type == "gemini":
            env_model_name = os.getenv("GEMINI_RT_MODEL")
            if env_model_name:
                model_name = env_model_name
                logger.debug(
                    f"rt_model_from_env: model={model_name}, " "message=從環境變量讀取 RT 模型配置（覆蓋）"
                )

        # 優先級5: 從 config.json 讀取（向後兼容）
        if not model_name:
            model_name = self.config.get("model_name")
            if model_name:
                logger.debug(
                    f"rt_model_from_config_json: model={model_name}, "
                    "message=從 config.json 讀取 RT 模型配置"
                )

        # 優先級6: 使用硬編碼默認值
        if not model_name:
            model_name = "qwen3-coder:30b"  # 默認使用 Ollama 模型

        # 設置 model_name 屬性
        self.model_name = model_name

    def _init_models(self):
        """初始化主模型和備選模型"""
        # 初始化主模型
        if self.model_type == "ollama":
            model_name = self.model_name if ":" in self.model_name else f"ollama:{self.model_name}"
            if model_name.startswith("ollama:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = OllamaRTModel(model_name=model_name)
        elif self.model_type == "gemini":
            model_name = self.model_name if ":" in self.model_name else f"gemini:{self.model_name}"
            if model_name.startswith("gemini:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = GeminiRTModel(model_name=model_name)
        elif self.model_type == "transformers":
            self._primary_model = TransformersRTModel(
                model_name=self.model_name, enable_gpu=self.enable_gpu
            )
        else:
            logger.warning(f"unknown_rt_model_type: model_type={self.model_type}")
            self._primary_model = None

        # 初始化備選模型
        # 優先使用本地模型（Ollama），外部 provider 作為最後備選
        if self.model_type == "ollama":
            # Ollama 不可用時，嘗試使用 Gemini（外部 provider）
            self._fallback_model = GeminiRTModel(model_name="gemini-pro-latest")
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
            logger.info(f"using_fallback_rt_model: requested={requested_type}")
            return self._fallback_model

        return None

    def _validate_relation_types(self, relation_types: List[RelationType]) -> List[RelationType]:
        """驗證關係類型（確保類型一致性）"""
        # 過濾低置信度的類型
        filtered = [rt for rt in relation_types if rt.confidence >= self.classification_threshold]

        # 檢測類型衝突（如果有多個類型，檢查是否有衝突）
        if len(filtered) > 1:
            # 簡單的衝突檢測：檢查是否有互斥的類型
            # 這裡可以添加更複雜的衝突檢測邏輯
            pass

        return filtered

    def _apply_type_hierarchy(self, relation_types: List[RelationType]) -> List[RelationType]:
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
        ontology_rules: Optional[Dict[str, Any]] = None,
        model_type: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[RelationType]:
        """分類關係類型"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available RT model")

        relation_types = await model.classify_relation_type(
            relation_text,
            subject_text,
            object_text,
            ontology_rules=ontology_rules,
            user_id=user_id,
            file_id=file_id,
            task_id=task_id,
        )
        relation_types = self._validate_relation_types(relation_types)
        relation_types = self._apply_type_hierarchy(relation_types)

        return relation_types

    async def classify_relation_types_batch(
        self,
        requests: List[dict],
        ontology_rules: Optional[Dict[str, Any]] = None,
        model_type: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[List[RelationType]]:
        """批量分類關係類型（優先使用模型原生 batch；否則逐條）。"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available RT model")

        try:
            # 模型原生 batch（單次 LLM 呼叫）
            batch_results = await model.classify_relation_types_batch(
                requests,
                ontology_rules=ontology_rules,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
            )
            results: List[List[RelationType]] = []
            for relation_types in batch_results:
                relation_types = self._validate_relation_types(relation_types)
                relation_types = self._apply_type_hierarchy(relation_types)
                results.append(relation_types)
            return results
        except Exception as e:
            logger.error(f"rt_batch_classification_failed: error={str(e)}")
            # fallback：逐條
            fallback_results: List[List[RelationType]] = []  # 重命名以避免重複定義
            for req in requests:
                try:
                    relation_types = await self.classify_relation_type(
                        req.get("relation_text", ""),
                        req.get("subject_text"),
                        req.get("object_text"),
                        ontology_rules=ontology_rules,
                        model_type=model_type,
                        user_id=user_id,
                        file_id=file_id,
                        task_id=task_id,
                    )
                    fallback_results.append(relation_types)
                except Exception:
                    fallback_results.append([])
            return fallback_results
