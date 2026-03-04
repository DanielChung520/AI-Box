# 代碼功能說明: Schema RAG JP 檢索服務
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10
#
# 職責:
# - 根據用戶查詢檢索相關的 Schema (Concepts, Intents, Bindings)
# - 支持日本 TiTop ERP 系統

"""
Schema RAG JP 檢索服務

功能：
- 根據用戶查詢檢索相關的 Concepts 和 Intents
- 使用關鍵詞匹配（簡單 RAG）
- 支持 Qdrant 向量檢索

使用示例：
    rag = SchemaRAGJP()
    concepts = rag.retrieve_concepts("RM01-005 在 W03 的庫存")
    intents = rag.retrieve_intents("查詢料號庫存")
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConceptRetrievalResult:
    """Concept 檢索結果"""

    name: str
    concept_type: str
    description: str
    labels: List[str]
    score: float
    reason: str


@dataclass
class IntentRetrievalResult:
    """Intent 檢索結果"""

    name: str
    description: str
    filters: List[str]
    metrics: List[str]
    dimensions: List[str]
    score: float
    reason: str


class SchemaRAGJP:
    """
    Schema RAG JP 檢索服務

    簡單實現：
    1. 從 JSON 加載 Concepts, Intents, Bindings
    2. 根據關鍵詞匹配計算相關性
    3. 返回相關的 Concepts 和 Intents
    """

    QUERY_PATTERNS = {
        "QUERY_INVENTORY": [
            (r"庫存、在庫、手持、stock、inventory", ["ITEM_NO", "WAREHOUSE_NO", "QTY"]),
            (r"料號、料號、在製品、product", ["ITEM_NO"]),
            (r"倉庫、倉別、warehousel", ["WAREHOUSE_NO"]),
            (r"W03、W01、W02", ["WAREHOUSE_NO"]),
        ],
        "QUERY_INVENTORY_BY_WAREHOUSE": [
            (r"倉庫別在庫、倉庫別庫存", ["ITEM_NO", "WAREHOUSE_NO", "QTY"]),
        ],
        "QUERY_WORK_ORDER": [
            (r"工單、WO、work order、工別、製造工單", ["MO_DOC_NO", "SFAA010"]),
            (r"工單狀態", ["MO_DOC_NO", "SFAASTUS"]),
        ],
        "QUERY_MANUFACTURING_PROGRESS": [
            (
                r"製造進捗、工序進捗、生產進度、進度",
                ["MO_DOC_NO", "CURRENT_OPERATION", "OPERATION_SEQ"],
            ),
            (r"2024年|2025年|2026年.*工單", ["MO_DOC_NO", "DOC_DATE"]),
        ],
        "QUERY_WORKSTATION_OUTPUT": [
            (r"工作站產出、機台產出、產出", ["WORKSTATION", "STANDARD_OUTPUT"]),
        ],
        "QUERY_QUALITY": [
            (r"品質、quality、不良、pqc", ["PENDING_PQC_QTY"]),
        ],
        "QUERY_OUTSOURCING": [
            (r"外包、委外、outsourcing", ["OUTSOURCING_VENDOR"]),
        ],
        "QUERY_SHIPPING": [
            (r"出貨、出荷、ship、出貨通知", ["XMDGDOCNO", "DOC_NO"]),
            (r"出貨列表", ["XMDGDOCNO", "XMDG_T"]),
        ],
        "QUERY_SHIPPING_BY_CUSTOMER": [
            (r"客戶別出貨、客戶別出荷", ["CUSTOMER_NO", "XMDGDOCNO"]),
        ],
        "QUERY_SHIPPING_DETAILS": [
            (r"出貨明细、出荷明细", ["XMDHDOCNO", "XMDH_T"]),
        ],
        "QUERY_PRICE_APPROVAL": [
            (r"售價、單價、價格、price", ["XMDTDOCNO", "UNIT_PRICE"]),
            (r"售價審核", ["XMDTDOCNO", "XMDT_T"]),
        ],
        "QUERY_PRICE_DETAILS": [
            (r"售價明细、單價明细", ["XMDU_T"]),
        ],
        "QUERY_CUSTOMER_PRICE": [
            (r"客戶售價、客戶單價", ["CUSTOMER_NO", "UNIT_PRICE"]),
        ],
    }

    def __init__(self, metadata_root: Optional[Path] = None):
        """
        初始化 RAG 服務

        Args:
            metadata_root: metadata 目錄路徑
        """
        if metadata_root is None:
            # 修復路徑計算錯誤
            # 從 /home/daniel/ai-box/datalake-system/data_agent/RAG/schema_rag_jp.py
            # 正確目標：/home/daniel/ai-box/datalake-system/metadata/systems/tiptop_jp
            ai_box_root = Path(__file__).resolve().parent.parent.parent
            metadata_root = ai_box_root / "metadata" / "systems" / "tiptop_jp"

        self.metadata_root = Path(metadata_root)
        """
        初始化 RAG 服務

        Args:
            metadata_root: metadata 目錄路徑
        """
        if metadata_root is None:
            # 修復路徑：從 /home/daniel/ai-box/datalake-system/data_agent/RAG/schema_rag_jp.py
            # 到 /home/daniel/ai-box/datalake-system/metadata/systems/tiptop_jp
            ai_box_root = Path(__file__).resolve().parent.parent.parent
            # 正確路徑：直接從 ai_box_root/metadata
            metadata_root = ai_box_root / "metadata" / "systems" / "tiptop_jp"
            # 修復路徑：從 /home/daniel/ai-box/datalake-system/data_agent/RAG/schema_rag_jp.py
            # 到 /home/daniel/ai-box/datalake-system/metadata/systems/tiptop_jp
            ai_box_root = Path(__file__).resolve().parent.parent.parent
            # 正確路徑：直接從 ai_box_root/metadata
            metadata_root = ai_box_root / "metadata" / "systems" / "tiptop_jp"
            # 修復路徑：從 /home/daniel/ai-box/datalake-system/data_agent/RAG/schema_rag_jp.py
            # 到 /home/daniel/ai-box/datalake-system/metadata/systems/tiptop_jp
            ai_box_root = Path(__file__).resolve().parent.parent.parent
            # 正確路徑：直接從 ai_box_root/metadata
            metadata_root = ai_box_root / "metadata" / "systems" / "tiptop_jp"
            ai_box_root = Path(__file__).resolve().parent.parent.parent
            metadata_root = ai_box_root / "datalake-system" / "metadata" / "systems" / "tiptop_jp"

        self.metadata_root = Path(metadata_root)
        self._concepts: Dict[str, Dict] = {}
        self._intents: Dict[str, Dict] = {}
        self._bindings: Dict[str, Dict] = {}

        self._load_schema()

        logger.info(f"SchemaRAGJP 初始化完成: {metadata_root}")

    def _load_schema(self):
        """加載 Schema - 從 Qdrant/ArangoDB 載入
        
        優先順序：
        1. Qdrant: Concepts, Intents
        2. ArangoDB: Bindings
        3. Fallback: JSON 文件
        """
        # ===== 1. 從 Qdrant 載入 Concepts =====
        try:
            from data_agent.services.schema_driven_query.loaders.qdrant_loader import QdrantSchemaLoader
            qdrant_loader = QdrantSchemaLoader()
            concepts_data = qdrant_loader.load_concepts(system_id="tiptop_jp")
            if concepts_data and concepts_data.concepts:
                self._concepts = concepts_data.concepts
                logger.info(f"Loaded {len(self._concepts)} concepts from Qdrant")
        except Exception as e:
            logger.warning(f"Failed to load concepts from Qdrant: {e}")
        
        # ===== 2. 從 Qdrant 載入 Intents =====
        if not self._intents:
            try:
                from data_agent.services.schema_driven_query.loaders.qdrant_loader import QdrantSchemaLoader
                qdrant_loader = QdrantSchemaLoader()
                intents_data = qdrant_loader.load_intents(system_id="tiptop_jp")
                if intents_data and intents_data.intents:
                    self._intents = intents_data.intents
                    logger.info(f"Loaded {len(self._intents)} intents from Qdrant")
            except Exception as e:
                logger.warning(f"Failed to load intents from Qdrant: {e}")
        
        # ===== 3. 從 ArangoDB 載入 Bindings =====
        if not self._bindings:
            try:
                from data_agent.services.schema_driven_query.loaders.arangodb_loader import ArangoDBSchemaLoader
                arango_loader = ArangoDBSchemaLoader()
                bindings_data = arango_loader.load_bindings(system_id="tiptop_jp")
                if bindings_data and bindings_data.bindings:
                    self._bindings = bindings_data.bindings
                    logger.info(f"Loaded {len(self._bindings)} bindings from ArangoDB")
            except Exception as e:
                logger.warning(f"Failed to load bindings from ArangoDB: {e}")
        
        # ===== 4. Fallback: 從 JSON 文件載入 =====
        if not self._concepts or not self._intents or not self._bindings:
            logger.info("Loading from JSON files as fallback...")
            concepts_path = self.metadata_root / "concepts.json"
            intents_path = self.metadata_root / "intents.json"
            bindings_path = self.metadata_root / "bindings.json"

            if concepts_path.exists() and not self._concepts:
                with open(concepts_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, concept in data.get("concepts", {}).items():
                        self._concepts[name] = concept
                logger.info(f"Loaded {len(self._concepts)} concepts from file")

            if intents_path.exists() and not self._intents:
                with open(intents_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, intent in data.get("intents", {}).items():
                        self._intents[name] = intent
                logger.info(f"Loaded {len(self._intents)} intents from file")

            if bindings_path.exists() and not self._bindings:
                with open(bindings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._bindings = data.get("bindings", {})
                logger.info(f"Loaded {len(self._bindings)} bindings from file")
    def _extract_keywords(self, text: str) -> List[str]:
        """提取關鍵詞"""
        if not text:
            return []
        return re.findall(r"\w+", text.lower())

    def _calculate_relevance(self, query: str, concept_data: Dict) -> float:
        """計算查詢與 Concept 的相關性"""
        query_lower = query.lower()
        query_words = set(self._extract_keywords(query))

        score = 0.0

        name = concept_data.get("name", "").lower()
        description = concept_data.get("description", "").lower()
        labels = [l.lower() for l in concept_data.get("labels", [])]

        all_text = f"{name} {description} {' '.join(labels)}"

        for word in query_words:
            if word in all_text:
                score += 1.0
            elif any(word in label for label in labels):
                score += 0.5

        return min(score / max(len(query_words), 1), 1.0)

    def retrieve_concepts(
        self,
        query: str,
        concept_types: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[ConceptRetrievalResult]:
        """
        檢索相關的 Concepts

        Args:
            query: 用戶查詢
            concept_types: 過濾 Concept 類型 (DIMENSION, METRIC, RANGE, ENUM)
            top_k: 返回前 K 個結果

        Returns:
            相關 Concepts 列表
        """
        if not self._concepts:
            logger.warning("No concepts loaded")
            return []

        logger.info(f"RAG JP 檢索 Concepts: query='{query[:50]}...'")

        results = []
        for name, concept in self._concepts.items():
            score = self._calculate_relevance(query, concept)

            if concept_types:
                ctype = concept.get("type", "DIMENSION")
                if ctype not in concept_types:
                    continue

            if score > 0:
                results.append(
                    ConceptRetrievalResult(
                        name=name,
                        concept_type=concept.get("type", "DIMENSION"),
                        description=concept.get("description", ""),
                        labels=concept.get("labels", []),
                        score=score,
                        reason="keyword_match",
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    def retrieve_intents(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[IntentRetrievalResult]:
        """
        檢索相關的 Intents

        Args:
            query: 用戶查詢
            top_k: 返回前 K 個結果

        Returns:
            相關 Intents 列表
        """
        if not self._intents:
            logger.warning("No intents loaded")
            return []

        logger.info(f"RAG JP 檢索 Intents: query='{query[:50]}...'")

        query_lower = query.lower()
        results = []

        for name, intent in self._intents.items():
            score = 0.0
            matched_patterns = []

            for pattern, related_concepts in self.QUERY_PATTERNS.items():
                for regex, concepts in related_concepts:
                    if re.search(regex, query_lower):
                        score += 0.5
                        matched_patterns.append(pattern)
                        break

            description = intent.get("description", "").lower()
            if any(word in description for word in self._extract_keywords(query)):
                score += 0.3

            if score > 0:
                results.append(
                    IntentRetrievalResult(
                        name=name,
                        description=intent.get("description", ""),
                        filters=intent.get("input", {}).get("filters", []),
                        metrics=intent.get("output", {}).get("metrics", []),
                        dimensions=intent.get("output", {}).get("dimensions", []),
                        score=score,
                        reason=",".join(matched_patterns) if matched_patterns else "keyword_match",
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    def get_binding(self, concept_name: str, datasource: str = "JP_TIPTOP_ERP", mart_table: str = None) -> Optional[Dict]:
        """
        獲取 Concept 的 Binding

        Args:
            concept_name: Concept 名稱
            datasource: 數據源名稱
            mart_table: Mart 表名稱（用於選擇正確的綁定）

        Returns:
            Binding 資訊
        """
        if concept_name not in self._bindings:
            return None
        
        concept_bindings = self._bindings[concept_name]
        
        # 統一為 dict 格式（處理 BindingColumn 對象）
        def to_dict(binding):
            if hasattr(binding, 'table'):  # BindingColumn 對象
                return {
                    "table": binding.table,
                    "column": binding.column,
                    "aggregation": getattr(binding, 'aggregation', None),
                    "operator": getattr(binding, 'operator', None),
                }
            return binding  # 已經是 dict
        
        # 如果提供了 mart_table，直接遍歷查找匹配的 table
        if mart_table:
            for ds_name, binding in concept_bindings.items():
                binding_dict = to_dict(binding)
                if binding_dict.get("table") == mart_table:
                    logger.info(f"Found binding for {concept_name}: {ds_name} -> {mart_table}")
                    return binding_dict
            
            # 嘗試通用的 DUCKDB（檢查 table 欄位）
            if "DUCKDB" in concept_bindings:
                binding_dict = to_dict(concept_bindings["DUCKDB"])
                if binding_dict.get("table") == mart_table:
                    return binding_dict
        
        # 默認返回指定的 datasource
        if datasource in concept_bindings:
            binding = concept_bindings[datasource]
            return to_dict(binding)
        
        # 最後嘗試任何可用的 DUCKDB binding
        for ds_name, binding in concept_bindings.items():
            if ds_name.startswith("DUCKDB"):
                return to_dict(binding)
        
        return None

    def get_bindings_by_intent(self, intent_name: str, datasource: str = "JP_TIPTOP_ERP") -> Dict[str, Dict]:
        """
        根據 Intent 獲取相關的 Bindings

        Args:
            intent_name: Intent 名稱

        Returns:
            Bindings 字典
        """
        if intent_name not in self._intents:
            return {}

        intent = self._intents[intent_name]
        filters = intent.get("input", {}).get("filters", [])
        metrics = intent.get("output", {}).get("metrics", [])
        dimensions = intent.get("output", {}).get("dimensions", [])

        all_concepts = set(filters + metrics + dimensions)

        bindings = {}
        for concept_name in all_concepts:
            binding = self.get_binding(concept_name, datasource)
            if binding:
                bindings[concept_name] = binding

        return bindings
