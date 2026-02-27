# 代碼功能說明: Schema RAG 檢索服務
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10
#
# 職責:
# - 根據用戶查詢檢索相關的 Table
# - 支持關鍵詞匹配（簡單 RAG）
# - 可擴展支持 Qdrant/ArangoDB

"""
Schema RAG 檢索服務

功能：
- 根據用戶查詢檢索相關的 Table
- 使用關鍵詞匹配（簡單 RAG）
- 可選升級到 Qdrant/ArangoDB

使用示例：
    rag = SchemaRAGService()
    results = rag.retrieve("料號 10-0001 的庫存")
    # 返回: [{"table": "item_master", "score": 0.9}, {"table": "inventory", "score": 0.8}]
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """檢索結果"""

    table: str
    score: float
    reason: str


class SchemaRAGService:
    """
    Schema RAG 檢索服務

    簡單實現：
    1. 從 YAML 加載所有 Table
    2. 根據關鍵詞匹配計算相關性
    3. 返回 Top-K 相關表格
    """

    # 常見查詢模式 → 相關表格（使用 canonical_name）
    QUERY_PATTERNS = [
        # 庫存相關
        (r"庫存", ["inventory", "item_master"]),
        (r"倉庫", ["inventory", "warehouse_master"]),
        (r"儲位", ["inventory", "ime_file"]),
        (r"料件|料號|物料", ["item_master"]),
        (r"成品|原料|半成品", ["item_master"]),
        # 採購相關
        (r"採購", ["purchase_header", "purchase_line"]),
        (r"供應商", ["supplier"]),
        (r"收料|進貨|驗收", ["rvb_file", "purchase_line"]),
        (r"PO|採購單", ["purchase_header", "purchase_line"]),
        (r"採購數量|採購金額|採購總", ["purchase_header", "purchase_line", "supplier"]),
        # 交易相關
        (r"交易|異動|銷貨|出貨|入庫", ["mart_work_order_wide"]),
        (r"歷史交易|交易記錄", ["mart_work_order_wide"]),
        (r"消耗|消耗量|用量|出庫", ["mart_work_order_wide", "item_master"]),
        (r"最大|最多|最高", ["item_master", "mart_work_order_wide"]),
        # 客戶相關
        (r"客戶", ["customer"]),
        (r"訂單", ["coptc_file", "coptd_file"]),
        # 價格相關
        (r"單價|價格|報價", ["prc_file", "item_master", "purchase_line"]),
        (r"歷史價格", ["prc_file"]),
        # 數量統計
        (r"有多少筆|有多少筆交易|筆數|數量統計", ["mart_work_order_wide"]),
        (r"總數量|總計|總和", ["mart_work_order_wide", "inventory"]),
        # 日期相關
        (r"2024年|2025年|2026年", ["mart_work_order_wide", "purchase_header", "coptd_file"]),
        (r"上月|上月|去年|今年", ["mart_work_order_wide"]),
        (r"最近.*天|最近.*月", ["mart_work_order_wide"]),
    ]

    def __init__(self, metadata_root: Optional[Path] = None):
        """
        初始化 RAG 服務

        Args:
            metadata_root: metadata 目錄路徑
        """
        if metadata_root is None:
            ai_box_root = Path(__file__).resolve().parent.parent.parent
            metadata_root = ai_box_root / "datalake-system" / "metadata"

        self.metadata_root = Path(metadata_root)
        self._tables: Dict[str, Dict] = {}
        self._table_keywords: Dict[str, List[str]] = {}

        logger.info(f"SchemaRAGService 初始化完成: {metadata_root}")

    def _load_tables(self, system_id: str = "tiptop_erp"):
        """加載系統的所有 Table"""
        import yaml

        registry_path = self.metadata_root / "schema_registry.json"
        if not registry_path.exists():
            logger.warning(f"Registry not found: {registry_path}")
            return

        with open(registry_path, "r") as f:
            registry = yaml.safe_load(f)

        # 從 systems 加載（優先使用 YAML schema）
        systems = registry.get("systems", {})
        if system_id not in systems:
            system_id = "tiptop_erp"

        system_config = systems.get(system_id, {})
        system_path_str = system_config.get("path", "")
        system_path = self.metadata_root / system_path_str

        if not system_path.exists():
            logger.warning(f"System schema not found: {system_path}")
            return

        with open(system_path, "r") as f:
            system_schema = yaml.safe_load(f)

        for table in system_schema.get("tables", []):
            canonical_name = table.get("name")
            tiptop_name = table.get("names", {}).get("tiptop", "")

            # 同時使用 canonical_name 和 tiptop_name 作為 key
            self._tables[canonical_name] = table
            if tiptop_name:
                self._tables[tiptop_name] = table

            self._table_keywords[canonical_name] = self._extract_keywords(canonical_name, table)

        logger.info(f"Loaded {len(self._tables)} tables from {system_id} (YAML schema)")

    def _extract_keywords(self, table_name: str, table_info: Any) -> List[str]:
        """提取 Table 的關鍵詞"""
        keywords = set()

        # 添加表名
        keywords.add(table_name.lower())

        if isinstance(table_info, dict):
            # 新格式
            names = table_info.get("names", {})
            keywords.add(names.get("tiptop", "").lower())
            keywords.add(names.get("oracle", "").lower())

            # 添加 tiptop_name
            tiptop_name = table_info.get("tiptop_name", "")
            if tiptop_name:
                keywords.add(tiptop_name.lower())

            # 添加 aliases
            for alias in table_info.get("aliases", []):
                keywords.add(alias.lower())

            # 添加 description
            desc = table_info.get("description", "")
            if desc:
                keywords.update(desc.lower().split())

            # 添加欄位名（支援新舊格式）
            for col in table_info.get("columns", []):
                col_id = col.get("id", "")
                col_names = col.get("names", {})

                keywords.add(col_id.lower())
                keywords.add(col_names.get("tiptop", "").lower())
                keywords.add(col_names.get("oracle", "").lower())

                # 舊格式：使用 "name"
                col_name = col.get("name", "")
                if col_name:
                    keywords.add(col_name.lower())

                # 新格式：使用 "description"
                col_desc = col.get("description", "")
                if col_desc:
                    keywords.update(col_desc.lower().split())
        else:
            # 舊格式 - table_name 是字串
            keywords.add(str(table_info).lower())

        return list(keywords)

    def _calculate_relevance(self, query: str, table_name: str) -> float:
        """計算查詢與 Table 的相關性"""
        if table_name not in self._table_keywords:
            return 0.0

        keywords = self._table_keywords[table_name]
        query_lower = query.lower()
        query_words = set(re.findall(r"\w+", query_lower))

        score = 0.0
        matched = []

        for keyword in keywords:
            if not keyword:
                continue

            # 完全匹配
            if keyword in query_lower:
                score += 1.0
                matched.append(f"exact:{keyword}")
            # 模糊匹配
            elif any(keyword in word for word in query_words):
                score += 0.5
                matched.append(f"partial:{keyword}")
            # 包含查詢詞
            elif any(word in keyword for word in query_words):
                score += 0.3

        # 計算 normalized score
        if keywords:
            score = score / len(keywords)

        return min(score, 1.0)

    def retrieve(
        self,
        query: str,
        system_id: str = "tiptop_erp",
        top_k: int = 5,
        min_score: float = 0.01,
    ) -> List[RetrievalResult]:
        """
        檢索相關的 Table

        Args:
            query: 用戶查詢
            system_id: 系統 ID
            top_k: 返回前 K 個結果
            min_score: 最小相關性分數

        Returns:
            相關表格列表，按分數排序
        """
        # 加載 tables（懒加载）
        if not self._tables:
            self._load_tables(system_id)

        if not self._tables:
            logger.warning("No tables loaded")
            return []

        logger.info(f"RAG 檢索: query='{query[:30]}...', top_k={top_k}")

        # 計算所有表格的相關性
        results = []
        for table_name in self._tables.keys():
            score = self._calculate_relevance(query, table_name)

            if score >= min_score:
                results.append(
                    RetrievalResult(
                        table=table_name,
                        score=score,
                        reason=f"keyword match",
                    )
                )

        # 應用查詢模式boost
        for pattern, related_tables in self.QUERY_PATTERNS:
            if re.search(pattern, query):
                for table in related_tables:
                    if table in self._tables:
                        # Boost 分數
                        for r in results:
                            if r.table == table:
                                r.score += 0.5
                                r.reason = f"pattern:{pattern}"
                                break
                        else:
                            results.append(
                                RetrievalResult(
                                    table=table,
                                    score=0.5,
                                    reason=f"pattern:{pattern}",
                                )
                            )

        # 按分數排序
        results.sort(key=lambda x: x.score, reverse=True)

        # 如果沒有結果，返回所有表格（按默認順序）
        if not results:
            for table_name in list(self._tables.keys())[:top_k]:
                results.append(
                    RetrievalResult(
                        table=table_name,
                        score=0.0,
                        reason="fallback",
                    )
                )

        # 返回 Top-K
        top_results = results[:top_k]

        logger.info(f"RAG 返回 {len(top_results)} 個相關表格")
        for r in top_results:
            logger.info(f"  - {r.table}: {r.score:.2f} ({r.reason})")

        return top_results

    def get_table_names(self, results: List[RetrievalResult]) -> List[str]:
        """從檢索結果提取表名列表"""
        return [r.table for r in results]

    def get_table_info(self, table_name: str, system_id: str = "tiptop_erp") -> Optional[Dict]:
        """獲取表格詳細資訊"""
        if not self._tables:
            self._load_tables(system_id)

        return self._tables.get(table_name)


class HybridSchemaRAGService:
    """
    混合 RAG 服務

    支持：
    1. 關鍵詞匹配（簡單 RAG）
    2. 可選 Qdrant（如果可用）
    3. 可選 ArangoDB（如果可用）
    """

    def __init__(self, metadata_root: Optional[Path] = None):
        self.metadata_root = (
            metadata_root
            or Path(__file__).resolve().parent.parent.parent / "datalake-system" / "metadata"
        )
        self.simple_rag = SchemaRAGService(self.metadata_root)
        self.qdrant_rag = None
        self._init_qdrant()

    def _init_qdrant(self):
        """初始化 Qdrant（可選）"""
        try:
            from qdrant_client import QdrantClient

            self.qdrant_client = QdrantClient(host="localhost", port=6333)
            self.qdrant_rag = True
            logger.info("Qdrant 可用")
        except Exception as e:
            logger.warning(f"Qdrant 不可用，使用簡單 RAG: {e}")
            self.qdrant_rag = False

    def retrieve(
        self,
        query: str,
        system_id: str = "tiptop_erp",
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """檢索相關表格"""

        if self.qdrant_rag:
            # 使用 Qdrant（未來實現）
            logger.info("使用 Qdrant RAG")

        # 回退到簡單 RAG
        return self.simple_rag.retrieve(
            query=query,
            system_id=system_id,
            top_k=top_k,
        )
