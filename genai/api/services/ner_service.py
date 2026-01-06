# 代碼功能說明: NER 命名實體識別服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""NER 命名實體識別服務 - 支持 spaCy 和 Ollama 模型"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
    async def extract_entities(
        self,
        text: str,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
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

    async def extract_entities(
        self,
        text: str,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
        """使用 spaCy 提取實體（注：spaCy 不支持 ontology_rules，但為了接口一致性保留此參數）"""
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
        self._prompt_template = """你是一個專業的命名實體識別（NER）助手。請仔細閱讀以下文本，識別並提取所有命名實體。

重要規則：
1. **必須識別盡可能多的實體**：不要遺漏任何重要的實體。即使文本簡短，也要盡力識別所有可能的概念、材料、設備、過程、產物、參數、組織、產品、地點、時間等。
2. **至少識別 2-3 個實體**：即使文本很短，也要嘗試識別多個不同的實體，包括主體、客體、屬性、關係、過程、產物等。
3. **僅返回一個 JSON 數組**：不要包含任何解釋、註釋或額外文字。
4. **嚴格遵守 JSON 格式**：確保輸出是有效的 JSON 數組，格式為 [{{"text": "...", "label": "...", "start": 0, "end": 0, "confidence": 0.0}}]。
5. **處理中文文本**：特別注意識別中文實體，包括公司名稱、產品名稱、技術術語、材料名稱、食品名稱、品牌名稱等。
6. **處理亂碼字符**：如果文本中包含特殊字符或亂碼，請忽略這些字符，專注於識別有效的實體。
7. **實體類型必須來自 Ontology**：如果提供了 Ontology 實體類型列表，必須使用列表中的類型標註實體，不要使用通用類型（如 PERSON, ORG, LOC 等）。

Few-Shot 示例（通用格式，實體類型將根據 Ontology 動態調整）：

示例 1（食品加工文本）：
文本：中央廚房採用真空包裝技術生產預製菜產品，保質期可達 30 天。生產線使用自動化設備，每日產能約 5000 份。
輸出：
[
  {{"text": "中央廚房", "label": "Central_Kitchen", "start": 0, "end": 4, "confidence": 0.95}},
  {{"text": "真空包裝", "label": "Packaging_Method", "start": 5, "end": 9, "confidence": 0.90}},
  {{"text": "預製菜", "label": "Prepared_Food", "start": 11, "end": 14, "confidence": 0.92}},
  {{"text": "30 天", "label": "Shelf_Life", "start": 19, "end": 23, "confidence": 0.85}},
  {{"text": "生產線", "label": "Production_Line", "start": 26, "end": 29, "confidence": 0.88}},
  {{"text": "5000 份", "label": "Production_Capacity", "start": 35, "end": 41, "confidence": 0.90}}
]

示例 2（技術設備描述）：
文本：氣化反應器用於將生質材料在高溫下轉化為合成氣。反應器操作溫度約 800-1000°C，壓力為常壓，產生的合成氣主要成分為一氧化碳和氫氣。
輸出：
[
  {{"text": "氣化反應器", "label": "Gasification_Reactor", "start": 0, "end": 4, "confidence": 0.95}},
  {{"text": "生質材料", "label": "Biomass_Feedstock", "start": 8, "end": 12, "confidence": 0.90}},
  {{"text": "合成氣", "label": "Syngas", "start": 18, "end": 21, "confidence": 0.92}},
  {{"text": "800-1000°C", "label": "Measurement", "start": 30, "end": 40, "confidence": 0.88}},
  {{"text": "一氧化碳", "label": "Gas", "start": 47, "end": 51, "confidence": 0.90}},
  {{"text": "氫氣", "label": "Gas", "start": 54, "end": 56, "confidence": 0.90}}
]

示例 3（組織與時間描述）：
文本：東方伊廚公司於 2024 年推出新的預製菜產品線，市場反響熱烈。該公司計劃在未來三年內將產能擴展至年產 100 萬份。
輸出：
[
  {{"text": "東方伊廚", "label": "Organization", "start": 0, "end": 4, "confidence": 0.95}},
  {{"text": "2024 年", "label": "TimePoint", "start": 7, "end": 12, "confidence": 0.90}},
  {{"text": "預製菜", "label": "Prepared_Food", "start": 15, "end": 18, "confidence": 0.92}},
  {{"text": "產品線", "label": "Product_Line", "start": 19, "end": 22, "confidence": 0.88}},
  {{"text": "三年", "label": "TimePeriod", "start": 33, "end": 35, "confidence": 0.85}},
  {{"text": "100 萬份", "label": "Production_Capacity", "start": 40, "end": 46, "confidence": 0.90}}
]

待分析的文本內容：
{text}

請返回 JSON 數組格式的實體列表："""

    def is_available(self) -> bool:
        """檢查 Ollama 模型是否可用"""
        return self.client is not None

    async def extract_entities(
        self,
        text: str,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
        """使用 Ollama 提取實體"""
        if self.client is None:
            raise RuntimeError(f"Ollama client is not available for model {self.model_name}")

        # 如果提供了 ontology_rules，使用 Ontology 中的實體類型列表
        prompt = self._prompt_template.format(text=text)
        
        # 記錄即將發送的 prompt（調試用）
        logger.info(
            "ollama_ner_prompt_prepared",
            model=self.model_name,
            prompt_length=len(prompt),
            prompt_preview=prompt[:300],  # 記錄前 300 字符
            text_preview=text[:100],  # 記錄前 100 字符
            has_ontology=ontology_rules is not None,
        )
        
        if ontology_rules:
            entity_classes = ontology_rules.get("entity_classes", [])
            if entity_classes:
                # 構建實體類型列表說明（限制顯示數量，避免 prompt 過長）
                entity_classes_sorted = sorted(entity_classes)
                entity_types_list = "\n".join([f"- {ec}" for ec in entity_classes_sorted[:50]])  # 最多顯示50個
                if len(entity_classes_sorted) > 50:
                    entity_types_list += f"\n- ... (共 {len(entity_classes_sorted)} 個實體類型)"
                
                # 在 prompt 中添加 Ontology 實體類型約束（更明確的指導）
                ontology_section = f"""

**⚠️ 重要約束：必須使用以下 Ontology 定義的實體類型**

請**僅使用**以下實體類型來標註文本中的實體，不要使用任何其他類型（如 PERSON, ORG, LOC 等標準類型）：

{entity_types_list}

**規則說明**：
1. 如果文本中的實體可以歸類到上述類型，請使用相應的 Ontology 類型
2. 如果無法歸類，可以嘗試使用最接近的父類型（如 Material, Process, Asset 等）
3. **必須識別盡可能多的實體**：不要遺漏任何重要概念，包括材料、設備、過程、產物等
4. 每個實體都應該使用上述 Ontology 類型列表中的類型，而不是示例中提到的標準類型"""
                
                # 在 prompt 中插入 Ontology 約束（在"待分析的文本內容"之前，但在 Few-Shot 示例之後）
                if "待分析的文本內容：" in prompt:
                    prompt = prompt.replace(
                        "待分析的文本內容：", f"{ontology_section}\n\n待分析的文本內容："
                    )
                else:
                    prompt = f"{prompt}{ontology_section}"

        try:
            # 記錄即將調用模型
            logger.info(
                "ollama_ner_calling_model",
                model=self.model_name,
                prompt_length=len(prompt),
            )
            
            response = await self.client.generate(
                prompt,
                model=self.model_name,
                format="json",  # 強制JSON格式
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
                purpose="ner",
                temperature=0.0,  # 降低隨機性，提高穩定性
                max_tokens=2048,  # 增加最大 token 數，確保完整輸出
                options={
                    "num_ctx": 32768,  # 設置 context window 為 32k
                    "top_p": 0.9,  # 核採樣參數
                    "top_k": 40,  # Top-K 採樣參數
                },
            )
            
            # 記錄模型調用完成
            logger.info(
                "ollama_ner_model_call_completed",
                model=self.model_name,
                response_is_none=response is None,
                response_type=type(response).__name__ if response else None,
            )

            if response is None:
                logger.error("ollama_ner_no_response", model=self.model_name)
                return []

            # 新接口返回 {"text": "...", "content": "...", "model": "..."}
            result_text = response.get("text") or response.get("content", "")
            
            # 記錄原始響應（調試用）- 使用 info 級別以便在日誌中看到
            logger.info(
                "ollama_ner_raw_response",
                model=self.model_name,
                response_length=len(result_text),
                response_preview=result_text[:500],  # 記錄前 500 字符以便調試
            )
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
                            # 優先處理 entities 字段（即使同時有 text 字段）
                            if "entities" in parsed_obj and isinstance(parsed_obj["entities"], list):
                                entities_data = parsed_obj["entities"]
                                # 如果 entities 數組中有對象，且缺少 label，嘗試從外層對象繼承
                                if entities_data and isinstance(entities_data[0], dict):
                                    # 檢查是否需要從外層對象繼承 label
                                    for entity in entities_data:
                                        if isinstance(entity, dict) and "text" in entity:
                                            if "label" not in entity and "label" in parsed_obj:
                                                entity["label"] = parsed_obj["label"]
                            # 如果沒有 entities 字段，但有一個單個 entity 對象
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
                            elif all(isinstance(v, list) for v in parsed_obj.values()):
                                # Handle groupings like {"PERSON": ["Alice"], "LOC": ["Paris"]}
                                new_list = []
                                for label, items in parsed_obj.items():
                                    for item_text in items:
                                        if isinstance(item_text, str):
                                             new_list.append({"text": item_text, "label": label, "confidence": 0.8})
                                        elif isinstance(item_text, dict):
                                             if "text" in item_text:
                                                 item_text.setdefault("label", label)
                                                 new_list.append(item_text)
                                             elif "value" in item_text: # Handle {"text": "...", "value": "..."} variations
                                                 item_text["text"] = item_text["value"]
                                                 item_text.setdefault("label", label)
                                                 new_list.append(item_text)
                                entities_data = new_list
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
                                    if isinstance(parsed_obj, dict):
                                        # 優先處理 entities 字段
                                        if "entities" in parsed_obj and isinstance(parsed_obj["entities"], list):
                                            entities_data = parsed_obj["entities"]
                                        # 如果是單個 entity 對象
                                        elif "text" in parsed_obj and (
                                            "label" in parsed_obj
                                            or "type" in parsed_obj
                                            or "entity_type" in parsed_obj
                                        ):
                                            entities_data = [parsed_obj]
                                except json.JSONDecodeError:
                                    pass

                # 如果仍然无法解析，返回空列表
                if entities_data is None or not isinstance(entities_data, list):
                    logger.warning(
                        "ollama_ner_no_valid_json",
                        model=self.model_name,
                        response_preview=result_text[:500],  # 增加預覽長度
                        response_full=result_text,  # 記錄完整響應以便調試
                    )
                    return []
                
                # 記錄成功解析的情況
                if isinstance(entities_data, list) and len(entities_data) == 0:
                    logger.info(
                        "ollama_ner_empty_result",
                        model=self.model_name,
                        response_preview=result_text[:300],
                        message="模型返回空實體列表",
                    )

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
                            confidence=float(item.get("confidence") or 0.8),
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

    async def extract_entities(
        self,
        text: str,
        ontology_rules: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
        """使用 Gemini 提取實體（注：Gemini 模型不支持 ontology_rules，但為了接口一致性保留此參數）"""
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
        import os

        # 優先級1: 從 ArangoDB system_configs 讀取 model_type 和 model_name
        model_type = None
        model_name = None
        try:
            from services.api.services.config_store_service import ConfigStoreService

            config_service = ConfigStoreService()
            kg_config = config_service.get_config("kg_extraction", tenant_id=None)
            if kg_config and kg_config.config_data:
                model_type = kg_config.config_data.get("ner_model_type")
                model_name = kg_config.config_data.get("ner_model")
                if model_type:
                    logger.debug(
                        "ner_model_type_from_system_configs",
                        model_type=model_type,
                        message="從 ArangoDB system_configs 讀取 NER model_type 配置",
                    )
                if model_name:
                    logger.debug(
                        "ner_model_from_system_configs",
                        model=model_name,
                        message="從 ArangoDB system_configs 讀取 NER 模型配置",
                    )
        except Exception as e:
            logger.debug(
                "failed_to_load_ner_model_from_system_configs",
                error=str(e),
                message="從 ArangoDB 讀取 NER 模型配置失敗，使用向後兼容方式",
            )

        # 優先級2: 從環境變量讀取 model_type（允許覆蓋 ArangoDB 配置）
        env_model_type = os.getenv("NER_MODEL_TYPE")
        if env_model_type:
            model_type = env_model_type
        
        # 優先級3: 從 config.json 讀取 model_type（向後兼容）
        if not model_type:
            model_type = self.config.get("model_type", "ollama")
        self.model_type = model_type or "ollama"

        # 優先級2: 從環境變量讀取（只在 model_type 匹配時覆蓋）
        # 注意：OLLAMA_NER_MODEL 只在 model_type=ollama 時使用
        # 對於其他 model_type（如 gemini），應該使用對應的環境變量或 ArangoDB 配置
        if self.model_type == "ollama":
            env_model_name = os.getenv("OLLAMA_NER_MODEL")
            if env_model_name:
                model_name = env_model_name
                logger.debug(
                    "ner_model_from_env",
                    model=model_name,
                    message="從環境變量讀取 NER 模型配置（覆蓋）",
                )
        # 對於 gemini，可以從 GEMINI_NER_MODEL 環境變量讀取（如果設置）
        elif self.model_type == "gemini":
            env_model_name = os.getenv("GEMINI_NER_MODEL")
            if env_model_name:
                model_name = env_model_name
                logger.debug(
                    "ner_model_from_env",
                    model=model_name,
                    message="從環境變量讀取 NER 模型配置（覆蓋）",
                )

        # 優先級3: 從 config.json 讀取（向後兼容）
        if not model_name:
            model_name = self.config.get("model_name")
            if model_name:
                logger.debug(
                    "ner_model_from_config_json",
                    model=model_name,
                    message="從 config.json 讀取 NER 模型配置",
                )

        # 優先級4: 使用硬編碼默認值
        self.model_name = model_name or "mistral-nemo:12b"

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
        ontology_rules: Optional[Dict[str, Any]] = None,
        model_type: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Entity]:
        """提取實體"""
        model = self._get_model(model_type)
        if not model:
            raise RuntimeError("No available NER model")

        # 调用底层模型的 extract_entities，传递 ontology_rules
        return await model.extract_entities(
            text,
            ontology_rules=ontology_rules,
            user_id=user_id,
            file_id=file_id,
            task_id=task_id,
        )

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
