# 代碼功能說明: RE 關係抽取服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-23 00:55 UTC+8

"""RE 關係抽取服務 - 支持 transformers 和 Ollama 模型"""

import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from genai.api.models.ner_models import Entity
from genai.api.models.re_models import Relation, RelationEntity
from genai.api.services.ner_service import NERService
from llm.clients.gemini import GeminiClient
from llm.clients.ollama import OllamaClient, get_ollama_client
from system.infra.config.config import get_config_section

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 標準關係類型定義
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
}


class BaseREModel(ABC):
    """RE 模型抽象基類"""

    @abstractmethod
    async def extract_relations(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Relation]:
        """提取關係"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """檢查模型是否可用"""
        pass


class TransformersREModel(BaseREModel):
    """Transformers RE 模型實現（基於 BERT）"""

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

            logger.info(f"transformers_re_model_loaded: model={self.model_name}")
        except ImportError:
            logger.warning(f"transformers_not_installed: model={self.model_name}")
            self._model = None
            self._tokenizer = None
        except Exception as e:
            logger.error(
                f"transformers_re_model_load_failed: model={self.model_name}, error={str(e)}"
            )
            self._model = None
            self._tokenizer = None

    def is_available(self) -> bool:
        """檢查 transformers 模型是否可用"""
        return self._model is not None and self._tokenizer is not None

    async def extract_relations(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Relation]:
        """使用 transformers 提取關係（簡化實現）（注：transformers 模型不支持 ontology_rules，但為了接口一致性保留此參數）"""
        if self._model is None or self._tokenizer is None:
            raise RuntimeError(f"Transformers RE model {self.model_name} is not available")

        # 簡化實現：基於實體對的關係抽取
        # 實際實現需要更複雜的模型和邏輯
        relations = []
        if entities and len(entities) >= 2:
            # 生成實體對
            for i, subj in enumerate(entities):
                for obj in entities[i + 1 :]:
                    # 檢查實體對之間的距離
                    if abs(subj.start - obj.end) < 50 or abs(obj.start - subj.end) < 50:
                        # 提取上下文
                        start_pos = min(subj.start, obj.start)
                        end_pos = max(subj.end, obj.end)
                        context = text[max(0, start_pos - 20) : min(len(text), end_pos + 20)]

                        # 簡化：使用默認關係類型
                        relations.append(
                            Relation(
                                subject=RelationEntity(text=subj.text, label=subj.label),
                                relation="RELATED_TO",
                                object=RelationEntity(text=obj.text, label=obj.label),
                                confidence=0.75,
                                context=context,
                            )
                        )

        return relations


class OllamaREModel(BaseREModel):
    """Ollama RE 模型實現"""

    def __init__(self, model_name: str = "qwen3-coder:30b", client: Optional[OllamaClient] = None):
        self.model_name = model_name
        self.client = client or get_ollama_client()
        self._prompt_template = """## 任務
從以下文本中抽取實體之間的關係，構建知識圖譜。

## 重要規則（必須嚴格遵守）
1. **只返回一個 JSON 數組**，不要返回任何其他內容
2. 不要添加 markdown 代碼塊標記（如 ```json）
3. 不要用額外的對象包裹數組（例如不要返回 {{"relations": [...]}} 或 {{"results": [...]}}）
4. 不要解釋你的答案
5. 識別 API 文檔中的邏輯關係，例如：
   - API 端點 BELONGS_TO 模塊
   - 參數 PART_OF API
   - 錯誤碼 RETURNED_BY API
   - 實體 HAS_PROPERTY 屬性
6. 忽略純 JSON 示例數據，專注於描述性文本中的關係

## 文本內容
{text}

{entities_section}

## 必須返回的 JSON 格式
直接返回一個 JSON 數組，每個元素包含：
- subject: 實體對象，格式為 {{"text": "實體名稱", "label": "實體類型"}}
- relation: 關係類型
- object: 實體對象，格式為 {{"text": "實體名稱", "label": "實體類型"}}
- confidence: 置信度（0-1之間的浮點數）
- context: 關係所在的上下文描述

## 正確示例
[
  {{
    "subject": {{"text": "GET /api/v1/users", "label": "API_ENDPOINT"}},
    "relation": "RETURNED_BY",
    "object": {{"text": "404 Not Found", "label": "STATUS_CODE"}},
    "confidence": 0.95,
    "context": "如果用戶不存在，接口將返回 404"
  }}
]

## 錯誤示例（不要這樣返回）
{{"relations": [...]}}           <!-- 錯誤：被額外對象包裹 -->
{{"subject": {{...}}, "relation": "...", "object": {{...}}}}  <!-- 錯誤：不是數組，是單個對象 -->
```json [...] ```           <!-- 錯誤：包含 markdown 代碼塊 -->"""

    def is_available(self) -> bool:
        """檢查 Ollama 模型是否可用"""
        return self.client is not None

    async def extract_relations(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Relation]:
        """使用 Ollama 提取關係"""
        if self.client is None:
            raise RuntimeError(f"Ollama client is not available for model {self.model_name}")

        # 構建提示詞
        entities_section = ""
        if entities:
            entities_text = "\n".join([f"- {e.text} ({e.label})" for e in entities])
            entities_section = f"已識別的實體：\n{entities_text}\n"

        prompt = self._prompt_template.format(text=text, entities_section=entities_section)

        # 如果提供了 ontology_rules，使用 Ontology 中的關係類型列表
        if ontology_rules:
            relationship_types = ontology_rules.get("relationship_types", [])
            if relationship_types:
                # 構建關係類型列表說明
                rel_types_list = "\n".join([f"- {rt}" for rt in sorted(relationship_types)])
                # 在 prompt 末尾添加 Ontology 關係類型約束
                ontology_section = f"""

**重要：請使用以下 Ontology 定義的關係類型（而非其他類型）：**
{rel_types_list}

請確保抽取的關係類型必須屬於上述 Ontology 定義的類型之一。"""
                prompt = f"{prompt}{ontology_section}"

        try:
            response = await self.client.generate(
                prompt,
                model=self.model_name,
                format="json",
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
                purpose="re",
                options={"num_ctx": 32768},  # 設置 context window 為 32k
            )

            if response is None:
                logger.error("ollama_re_no_response", model=self.model_name)
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

                relations_data = json.loads(result_text)

                if not isinstance(relations_data, list):
                    # 修改時間：2025-12-12 - 記錄實際返回內容以便調試
                    logger.error(
                        f"ollama_re_invalid_format: model={self.model_name}, "
                        f"response_type={type(relations_data).__name__}, "
                        f"response_preview={str(relations_data)[:500]}"
                    )
                    # 如果返回的是字典，嘗試轉換為列表
                    if isinstance(relations_data, dict):
                        # 檢查是否有常見的鍵（如 "relations", "data", "result", "extracted_triples"）
                        for key in [
                            "relations",
                            "results",
                            "data",
                            "result",
                            "items",
                            "extracted_triples",
                            "entities",
                            "status_codes",
                        ]:
                            if key in relations_data and isinstance(relations_data[key], list):
                                relations_data = relations_data[key]
                                logger.info(
                                    f"ollama_re_format_converted: converted_key={key}, "
                                    f"relations_count={len(relations_data)}"
                                )
                                break
                        else:
                            # 如果沒有找到列表鍵，檢查是否是單個關係對象
                            # 單個關係對象應該有 "subject", "relation", "object" 等字段
                            if (
                                "subject" in relations_data
                                and "relation" in relations_data
                                and "object" in relations_data
                            ):
                                # 將單個關係對象轉換為列表
                                relations_data = [relations_data]
                                logger.info(
                                    "ollama_re_format_converted: converted_key=single_relation_object, relations_count=1"
                                )
                            else:
                                # 如果沒有找到列表鍵且不是單個關係對象，返回空列表
                                return []
                    else:
                        return []

                relations = []
                for item in relations_data:
                    if not isinstance(item, dict):
                        continue

                    # 處理兩種格式：
                    # 1. RE service 格式: {"subject": {"text": "...", "label": "..."}, ...}
                    # 2. Ontology 格式: {"subject": "...", "subject_type": "...", ...}
                    subject_data = item.get("subject", {})
                    object_data = item.get("object", {})

                    # 檢查是否是 ontology 格式（subject 是字符串）
                    if isinstance(subject_data, str):
                        # Ontology 格式：轉換為 RE service 格式
                        subject_text = subject_data
                        subject_label = item.get("subject_type", "UNKNOWN")
                        object_text = object_data if isinstance(object_data, str) else ""
                        object_label = item.get("object_type", "UNKNOWN")
                    elif isinstance(subject_data, dict) and isinstance(object_data, dict):
                        # RE service 格式：直接使用
                        subject_text = subject_data.get("text", "")
                        subject_label = subject_data.get("label", "UNKNOWN")
                        object_text = object_data.get("text", "")
                        object_label = object_data.get("label", "UNKNOWN")
                    else:
                        # 格式不正確，跳過
                        continue

                    relations.append(
                        Relation(
                            subject=RelationEntity(
                                text=subject_text,
                                label=subject_label,
                            ),
                            relation=item.get("relation", "RELATED_TO"),
                            object=RelationEntity(
                                text=object_text,
                                label=object_label,
                            ),
                            confidence=float(item.get("confidence") or 0.8),
                            context=item.get("context", text),
                        )
                    )

                return relations
            except json.JSONDecodeError as e:
                logger.error(f"ollama_re_json_parse_failed: error={str(e)}, response={result_text}")
                return []
        except Exception as e:
            logger.error(f"ollama_re_extraction_failed: model={self.model_name}, error={str(e)}")
            return []


class GeminiREModel(BaseREModel):
    """Gemini RE 模型實現"""

    def __init__(
        self, model_name: str = "gemini-pro-latest", client: Optional[GeminiClient] = None
    ):
        self.model_name = model_name
        self.client: Optional[GeminiClient] = None
        try:
            self.client = client or GeminiClient()
        except (ImportError, ValueError) as e:
            # Gemini 不可用（缺少依赖或 API key），设置为 None
            logger.warning(f"gemini_re_client_unavailable: error={str(e)}")
            self.client = None
        self._prompt_template = """## 任務
從以下文本中抽取實體之間的關係，構建知識圖譜。

## 重要規則（必須嚴格遵守）
1. **只返回一個 JSON 數組**，不要返回任何其他內容
2. 不要添加 markdown 代碼塊標記（如 ```json）
3. 不要用額外的對象包裹數組（例如不要返回 {{"relations": [...]}} 或 {{"results": [...]}}）
4. 不要解釋你的答案
5. 識別文本中的邏輯關係，例如：
   - API 端點 BELONGS_TO 模塊
   - 參數 PART_OF API
   - 錯誤碼 RETURNED_BY API
   - 實體 HAS_PROPERTY 屬性
6. 忽略純 JSON 示例數據，專注於描述性文本中的關係

## 文本
{text}

{entities_section}

## 必須返回的 JSON 格式
直接返回一個 JSON 數組，每個元素包含：
- subject: 實體對象，格式為 {{"text": "實體名稱", "label": "實體類型"}}
- relation: 關係類型
- object: 實體對象，格式為 {{"text": "實體名稱", "label": "實體類型"}}
- confidence: 置信度（0-1之間的浮點數）
- context: 關係所在的上下文描述

## 正確示例
[
  {{
    "subject": {{"text": "張三", "label": "PERSON"}},
    "relation": "WORKS_FOR",
    "object": {{"text": "微軟", "label": "ORG"}},
    "confidence": 0.88,
    "context": "張三在微軟公司工作"
  }}
]

## 錯誤示例（不要這樣返回）
{{"relations": [...]}}           <!-- 錯誤：被額外對象包裹 -->
{{"subject": {{...}}, "relation": "...", "object": {{...}}}}  <!-- 錯誤：不是數組，是單個對象 -->
```json [...] ```           <!-- 錯誤：包含 markdown 代碼塊 -->"""

    def is_available(self) -> bool:
        """檢查 Gemini 模型是否可用"""
        return self.client is not None and self.client.is_available()

    async def extract_relations(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Relation]:
        """使用 Gemini 提取關係"""
        if self.client is None or not self.client.is_available():
            raise RuntimeError(f"Gemini client is not available for model {self.model_name}")

        # 構建提示詞
        entities_section = ""
        if entities:
            entities_text = "\n".join([f"- {e.text} ({e.label})" for e in entities])
            entities_section = f"已識別的實體：\n{entities_text}\n"

        prompt = self._prompt_template.format(text=text, entities_section=entities_section)

        # 如果提供了 ontology_rules，使用 Ontology 中的關係類型列表
        if ontology_rules:
            relationship_types = ontology_rules.get("relationship_types", [])
            if relationship_types:
                # 構建關係類型列表說明
                rel_types_list = "\n".join([f"- {rt}" for rt in sorted(relationship_types)])
                # 在 prompt 末尾添加 Ontology 關係類型約束
                ontology_section = f"""

**重要：請使用以下 Ontology 定義的關係類型（而非其他類型）：**
{rel_types_list}

請確保抽取的關係類型必須屬於上述 Ontology 定義的類型之一。"""
                prompt = f"{prompt}{ontology_section}"

        try:
            response = await self.client.generate(
                prompt,
                model=self.model_name,
            )

            if response is None:
                logger.error(f"gemini_re_no_response: model={self.model_name}")
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

                relations_data = json.loads(result_text)

                if not isinstance(relations_data, list):
                    logger.error(f"gemini_re_invalid_format: model={self.model_name}")
                    return []

                relations = []
                for item in relations_data:
                    if not isinstance(item, dict):
                        continue

                    subject_data = item.get("subject", {})
                    object_data = item.get("object", {})

                    if not isinstance(subject_data, dict) or not isinstance(object_data, dict):
                        continue

                    relations.append(
                        Relation(
                            subject=RelationEntity(
                                text=subject_data.get("text") or subject_data.get("name") or "",
                                label=subject_data.get("label")
                                or subject_data.get("type")
                                or "UNKNOWN",
                            ),
                            relation=item.get("relation", "RELATED_TO"),
                            object=RelationEntity(
                                text=object_data.get("text") or object_data.get("name") or "",
                                label=object_data.get("label")
                                or object_data.get("type")
                                or "UNKNOWN",
                            ),
                            confidence=float(item.get("confidence", 0.5)),
                            context=item.get("context", text),
                        )
                    )

                return relations
            except json.JSONDecodeError as e:
                logger.error(f"gemini_re_json_parse_failed: error={str(e)}, response={result_text}")
                return []
        except Exception as e:
            logger.error(f"gemini_re_extraction_failed: model={self.model_name}, error={str(e)}")
            return []


class REService:
    """RE 服務主類"""

    def __init__(self, ner_service: Optional[NERService] = None):
        self.config = get_config_section("text_analysis", "re", default={}) or {}

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
                f"re_using_moe_config: model={self.model_name}, scene={self._moe_scene}, "
                f"temperature={moe_model.temperature}, timeout={moe_model.timeout}"
            )
        else:
            # 向後兼容：使用原有配置
            self._init_model_from_config()

        # Fallback 順序：本地模型優先，外部 provider 作為最後備選
        self.fallback_model = self.config.get("fallback_model", "gemini:gemini-pro-latest")
        self.max_relation_length = self.config.get("max_relation_length", 128)
        self.enable_gpu = self.config.get("enable_gpu", False)

        # NER 服務（用於自動實體識別）
        self.ner_service = ner_service or NERService()

        # 初始化模型
        self._primary_model: Optional[BaseREModel] = None
        self._fallback_model: Optional[BaseREModel] = None
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
                model_type = kg_config.config_data.get("re_model_type")
                model_name = kg_config.config_data.get("re_model")
                if model_type:
                    logger.debug(
                        f"re_model_type_from_system_configs: model_type={model_type}, "
                        "message=從 ArangoDB system_configs 讀取 RE model_type 配置"
                    )
                if model_name:
                    logger.debug(
                        f"re_model_from_system_configs: model={model_name}, "
                        "message=從 ArangoDB system_configs 讀取 RE 模型配置"
                    )
        except Exception as e:
            logger.debug(
                f"failed_to_load_re_model_from_system_configs: error={str(e)}, "
                "message=從 ArangoDB 讀取 RE 模型配置失敗，使用向後兼容方式"
            )

        # 優先級2: 從環境變量讀取 model_type（允許覆蓋 ArangoDB 配置）
        env_model_type = os.getenv("RE_MODEL_TYPE")
        if env_model_type:
            model_type = env_model_type

        # 優先級3: 從 config.json 讀取 model_type（向後兼容）
        if not model_type:
            model_type = self.config.get("model_type", "ollama")
        self.model_type = model_type or "ollama"

        # 優先級4: 從環境變量讀取（只在 model_type 匹配時覆蓋）
        if self.model_type == "ollama":
            env_model_name = os.getenv("OLLAMA_RE_MODEL") or os.getenv("OLLAMA_NER_MODEL")
            if env_model_name:
                model_name = env_model_name
                logger.debug(
                    f"re_model_from_env: model={model_name}, " "message=從環境變量讀取 RE 模型配置（覆蓋）"
                )
        elif self.model_type == "gemini":
            env_model_name = os.getenv("GEMINI_RE_MODEL")
            if env_model_name:
                model_name = env_model_name
                logger.debug(
                    f"re_model_from_env: model={model_name}, " "message=從環境變量讀取 RE 模型配置（覆蓋）"
                )

        # 優先級5: 從 config.json 讀取（向後兼容）
        if not model_name:
            model_name = self.config.get("model_name")
            if model_name:
                logger.debug(
                    f"re_model_from_config_json: model={model_name}, "
                    "message=從 config.json 讀取 RE 模型配置"
                )

        # 優先級6: 使用硬編碼默認值
        if not model_name:
            model_name = "qwen3-coder:30b"  # 默認使用 Ollama 模型

        # 設置 model_name 屬性
        self.model_name = model_name

    def _init_models(self):
        """初始化主模型和備選模型"""
        # 初始化主模型
        if self.model_type == "transformers":
            self._primary_model = TransformersREModel(
                model_name=self.model_name, enable_gpu=self.enable_gpu
            )
        elif self.model_type == "ollama":
            model_name = self.model_name if ":" in self.model_name else f"ollama:{self.model_name}"
            if model_name.startswith("ollama:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = OllamaREModel(model_name=model_name)
        elif self.model_type == "gemini":
            model_name = self.model_name if ":" in self.model_name else f"gemini:{self.model_name}"
            if model_name.startswith("gemini:"):
                model_name = model_name.split(":", 1)[1]
            self._primary_model = GeminiREModel(model_name=model_name)
        else:
            logger.warning(f"unknown_re_model_type: model_type={self.model_type}")
            self._primary_model = None

        # 初始化備選模型
        # 優先使用本地模型（Ollama），外部 provider 作為最後備選
        if self.fallback_model:
            if self.fallback_model.startswith("ollama:"):
                fallback_name = self.fallback_model.split(":", 1)[1]
                self._fallback_model = OllamaREModel(model_name=fallback_name)
            elif self.fallback_model.startswith("gemini:"):
                fallback_name = self.fallback_model.split(":", 1)[1]
                self._fallback_model = GeminiREModel(model_name=fallback_name)
            else:
                self._fallback_model = None
        else:
            # 如果未配置 fallback，根據主模型類型自動選擇
            # 優先使用本地模型作為 fallback
            if self.model_type == "gemini":
                # 如果主模型是外部 provider，fallback 使用本地模型
                self._fallback_model = OllamaREModel(model_name="qwen3-coder:30b")
            elif self.model_type != "ollama":
                # 如果主模型不是 Ollama，fallback 優先使用本地模型
                self._fallback_model = OllamaREModel(model_name="qwen3-coder:30b")

    def _get_model(self, model_type: Optional[str] = None) -> Optional[BaseREModel]:
        """獲取可用的模型"""
        requested_type = model_type or self.model_type

        model: Optional[BaseREModel] = None
        if requested_type == "transformers":
            if isinstance(self._primary_model, TransformersREModel):
                model = self._primary_model
        elif requested_type == "ollama":
            if isinstance(self._primary_model, OllamaREModel):
                model = self._primary_model
        elif requested_type == "gemini":
            if isinstance(self._primary_model, GeminiREModel):
                model = self._primary_model
        else:
            model = self._primary_model

        # 如果請求的模型不可用，嘗試使用備選模型
        if model and model.is_available():
            return model

        if self._fallback_model and self._fallback_model.is_available():
            logger.info(f"using_fallback_re_model: requested={requested_type}")
            return self._fallback_model

        return None

    async def extract_relations(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        ontology_rules: Optional[Dict[str, Any]] = None,
        model_type: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Relation]:
        """提取關係"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available RE model")

        # 如果沒有提供實體，自動識別
        if entities is None:
            if self.ner_service is None:
                raise RuntimeError("NER service is not available for automatic entity extraction")
            entities = await self.ner_service.extract_entities(
                text,
                ontology_rules=ontology_rules,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
            )

        return await model.extract_relations(
            text,
            entities,
            ontology_rules=ontology_rules,
            user_id=user_id,
            file_id=file_id,
            task_id=task_id,
        )

    async def extract_relations_batch(
        self, texts: List[str], model_type: Optional[str] = None
    ) -> List[List[Relation]]:
        """批量提取關係"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available RE model")

        results = []
        for text in texts:
            try:
                relations = await self.extract_relations(text, model_type=model_type)
                results.append(relations)
            except Exception as e:
                logger.error(f"re_batch_extraction_failed: error={str(e)}, text={text[:50]}")
                results.append([])

        return results
