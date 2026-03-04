# 代碼功能說明: 時間分詞器工具 - 基於向量檢索的時間表達識別
# 創建日期: 2026-02-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-24

"""時間分詞器工具 (TimePeriodRAG)

基於向量檢索的時間表達識別工具，支持中英文各種時間表達方式的結構化解析。

功能：
1. 將時間表達模板向量化後存入 Qdrant 向量資料庫
2. 用戶查詢時通過向量相似度匹配最接近的模板
3. 將匹配結果解析為結構化的時間參數

使用方式：
    from tools.time.time_period_rag import TimePeriodRAGTool, TimePeriodRAGInput, TimePeriodRAGOutput

    tool = TimePeriodRAGTool()

    # 構建索引（首次使用時）
    await tool.build_index()

    # 查詢時間表達
    result = await tool.execute(TimePeriodRAGInput(time_expression="2025年度庫存"))
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog

from database.qdrant.client import get_qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError

logger = structlog.get_logger(__name__)

# 配置常量
COLLECTION_NAME = "time_period_templates"
EMBEDDING_MODEL = "qwen3-embedding:latest"
EMBEDDING_URL = "http://localhost:11434/api/embeddings"
VECTOR_DIMENSION = 4096
SIMILARITY_THRESHOLD = 0.75


class TimePeriodRAGInput(ToolInput):
    """時間分詞器輸入參數"""

    time_expression: str  # 時間表達文字，如 "2025年"、"最近一周"
    current_year: Optional[int] = None  # 當前年份，用於計算相對時間


class TimePeriodRAGOutput(ToolOutput):
    """時間分詞器輸出結果"""

    original_expression: str  # 原始輸入
    matched_expression: str  # 匹配的模板表達
    category: str  # 時間類別（year/month/year_month/date_range/decade）
    granularity: str  # 時間粒度
    parsed: Dict[str, Any]  # 解析後的結構化參數
    confidence: float  # 匹配置信度（0-1）
    start_date: Optional[str] = None  # 計算後的開始日期（ISO格式）
    end_date: Optional[str] = None  # 計算後的結束日期（ISO格式）


class TimePeriodRAGTool(BaseTool[TimePeriodRAGInput, TimePeriodRAGOutput]):
    """時間分詞器工具

    基於 RAG 架構的時間表達識別工具。
    通過向量相似度匹配，將自然語言時間表達轉換為結構化參數。
    """

    def __init__(self):
        self._qdrant_client = None
        self._templates: Dict[str, Any] = {}
        self._initialized = False

    @property
    def name(self) -> str:
        """工具名稱"""
        return "time_period_rag"

    @property
    def description(self) -> str:
        """工具描述"""
        return "時間分詞器 - 通過向量檢索識別中英文時間表達，並解析為結構化時間參數"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    @property
    def qdrant_client(self):
        """獲取 Qdrant 客戶端"""
        if self._qdrant_client is None:
            self._qdrant_client = get_qdrant_client()
        return self._qdrant_client

    def _load_templates(self) -> Dict[str, Any]:
        """載入時間表達模板庫"""
        if not self._templates:
            template_path = Path(__file__).parent / "time_period_templates.json"
            with open(template_path, "r", encoding="utf-8") as f:
                self._templates = json.load(f)
        return self._templates

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """調用 Ollama 獲取文本嵌入向量"""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    EMBEDDING_URL,
                    json={"model": EMBEDDING_MODEL, "prompt": text},
                )
                response.raise_for_status()
                return response.json().get("embedding")
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e), text=text)
            return None

    def _ensure_collection(self):
        """確保 Qdrant 集合存在"""
        client = self.qdrant_client
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if COLLECTION_NAME not in collection_names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE),
            )
            logger.info("qdrant_collection_created", collection=COLLECTION_NAME)

    def _parse_relative_time(
        self, parsed: Dict[str, Any], current_year: Optional[int] = None
    ) -> tuple:
        """解析相對時間為具體日期範圍"""
        if current_year is None:
            current_year = datetime.now().year

        relative = parsed.get("relative")
        if not relative:
            return None, None

        today = datetime.now()
        start_date: Optional[datetime] = None
        end_date: Optional[datetime] = None

        relative_map = {
            "today": (today.replace(hour=0, minute=0, second=0), today),
            "yesterday": (today - timedelta(days=1), today - timedelta(days=1)),
            "tomorrow": (today + timedelta(days=1), today + timedelta(days=1)),
            "this_week": (today - timedelta(days=today.weekday()), today),
            "last_week": (
                today - timedelta(days=today.weekday() + 7),
                today - timedelta(days=today.weekday() + 1),
            ),
            "next_week": (
                today + timedelta(days=7 - today.weekday()),
                today + timedelta(days=13 - today.weekday()),
            ),
            "current_month": (today.replace(day=1), today),
            "last_month": (
                today.replace(day=1) - timedelta(days=1),
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
            ),
            "next_month": (
                today.replace(day=28) + timedelta(days=4),
                (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
            ),
            "current_year": (datetime(current_year, 1, 1), datetime(current_year, 12, 31)),
            "last_year": (datetime(current_year - 1, 1, 1), datetime(current_year - 1, 12, 31)),
            "next_year": (datetime(current_year + 1, 1, 1), datetime(current_year + 1, 12, 31)),
            "year_before_last": (
                datetime(current_year - 2, 1, 1),
                datetime(current_year - 2, 12, 31),
            ),
            "year_after_next": (
                datetime(current_year + 2, 1, 1),
                datetime(current_year + 2, 12, 31),
            ),
            "last_7_days": (today - timedelta(days=6), today),
            "last_30_days": (today - timedelta(days=29), today),
            "last_90_days": (today - timedelta(days=89), today),
            "last_180_days": (today - timedelta(days=179), today),
            "last_365_days": (today - timedelta(days=364), today),
            "year_start": (datetime(current_year, 1, 1), datetime(current_year, 1, 31)),
            "year_end": (datetime(current_year, 12, 1), datetime(current_year, 12, 31)),
            "month_start": (today.replace(day=1), today),
            "month_end": (today, today + timedelta(days=31 - today.day)),
        }

        if relative in relative_map:
            start_date, end_date = relative_map[relative]

        return (
            start_date.isoformat() if start_date else None,
            end_date.isoformat() if end_date else None,
        )

    def _parse_absolute_time(self, parsed: Dict[str, Any]) -> tuple:
        """解析絕對時間為具體日期範圍"""
        year = parsed.get("year")
        month = parsed.get("month")
        day = parsed.get("day")

        if not year:
            return None, None

        try:
            if day:
                date = datetime(int(year), int(month or 1), int(day))
                return date.isoformat(), date.isoformat()
            elif month:
                start = datetime(int(year), int(month), 1)
                if int(month) == 12:
                    end = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    end = datetime(int(year), int(month) + 1, 1) - timedelta(days=1)
                return start.isoformat(), end.isoformat()
            else:
                return f"{year}-01-01", f"{year}-12-31"
        except (ValueError, TypeError):
            return None, None

    def build_index(self) -> Dict[str, Any]:
        """構建時間模板向量索引

        將 JSON 模板庫中的所有時間表達向量化後存入 Qdrant。

        Returns:
            構建結果統計
        """
        self._ensure_collection()
        templates = self._load_templates()

        total_templates = 0
        success_count = 0
        failed_expressions = []

        client = self.qdrant_client

        # 清除舊索引
        try:
            client.delete(collection_name=COLLECTION_NAME, points_selector=[1, 2, 3, 4, 5])
        except Exception:
            pass

        for category, category_data in templates.get("categories", {}).items():
            granularity = category_data.get("granularity", "UNKNOWN")
            for template in category_data.get("templates", []):
                expression = template.get("expression", "")
                parsed = template.get("parsed", {})

                if not expression:
                    continue

                total_templates += 1

                # 生成向量
                embedding = self._get_embedding(expression)
                if not embedding:
                    failed_expressions.append(expression)
                    continue

                # 存入 Qdrant
                point_id = hash(expression) % 1000000
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        {
                            "id": point_id,
                            "vector": embedding,  # 使用默认向量
                            "payload": {
                                "expression": expression,
                                "category": category,
                                "granularity": granularity,
                                "parsed": parsed,
                            },
                        }
                    ],
                )
                success_count += 1

        self._initialized = True
        logger.info(
            "time_period_rag_index_built",
            total=total_templates,
            success=success_count,
            failed=len(failed_expressions),
        )

        return {
            "status": "completed",
            "total_templates": total_templates,
            "success_count": success_count,
            "failed_count": len(failed_expressions),
            "failed_expressions": failed_expressions,
        }

    async def execute(self, input_data: TimePeriodRAGInput) -> TimePeriodRAGOutput:
        """執行時間分詞

        將輸入的時間表達通過向量相似度匹配，輸出結構化時間參數。

        Args:
            input_data: 時間表達輸入

        Returns:
            結構化時間解析結果
        """
        expression = input_data.time_expression.strip()
        current_year = input_data.current_year or datetime.now().year

        # 首次使用時自動構建索引
        if not self._initialized:
            try:
                self.build_index()
            except Exception as e:
                logger.warning("auto_build_index_failed", error=str(e))

        # ========== 改進：先提取時間相關內容 ==========
        # 使用多個正則模式提取時間關鍵詞（順序很重要！）
        # 優先匹配：年份+時間關鍵詞 > 相對時間 > 純數字
        time_patterns = [
            # ====== 高優先：年份 + 時間關鍵詞 ======
            r"20\d{2}年\s*\d{1,2}月\s*\d{1,2}日",   # 2025年1月1日 (優先)
            r"20\d{2}年\s*\d{1,2}月",              # 2025年1月
            r"20\d{2}年\s*",                        # 2025年 或 2025年 (帶空格)
            r"20\d{2}\s*年",                        # 2025 年 (空格在年前)
            r"20\d{2}[./-]\d{1,2}[./-]\d{1,2}", # 2025/01/15
            
            # ====== 中優先：相對時間 ======
            r"[最近上前今往後][一二三四五六七八九十]+[天週月年]",  # 最近一週、上一年
            r"[最近上前今往後]半?[一二三四五六七八九十]+[天週月年]",  # 最近兩週
            r"[上下]個?[天週月年]",               # 上個月
            r"[本今上下去][天週月年季]",          # 今年
            
            # ====== 低優先：純數字（最後才匹配）======
            r"\d{1,2}月",                      # 1月（單獨的月份）
            r"\d{1,2}[./-]\d{1,2}[./-]\d{1,2}",  # 日期格式
        ]
        
        extracted_time_expr = None
        for pattern in time_patterns:
            match = re.search(pattern, expression)
            if match:
                extracted_time_expr = match.group(0)
                # 過濾掉料號中的數字（如 0139 from A01396000）
                if extracted_time_expr and len(extracted_time_expr) >= 2:
                    logger.info(f"Extracted time expression: {extracted_time_expr}")
                    break
        
        # ========== 改進結束 ==========
        
        # 使用提取的時間表達進行向量匹配，而非整個句子
        search_expr = extracted_time_expr if extracted_time_expr else expression
        # 去除空格以匹配模板（"2025 年" -> "2025年"）
        search_expr = search_expr.replace(" ", "")

        # 生成查詢向量
        # 生成查詢向量
        embedding = self._get_embedding(search_expr)
        if not embedding:
            raise ToolExecutionError(f"Failed to generate embedding for: {expression}")

        # 向量相似度搜索
        client = self.qdrant_client
        try:
            results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=embedding,
                limit=1,
                score_threshold=SIMILARITY_THRESHOLD,
            ).points
        except Exception as e:
            logger.error("qdrant_search_failed", error=str(e))
            # 如果 Qdrant 搜索失敗，返回原始解析嘗試
            results = []

        if not results:
            # 未找到匹配，返回原始解析嘗試
            return TimePeriodRAGOutput(
                original_expression=expression,
                matched_expression=expression,
                category="unknown",
                granularity="UNKNOWN",
                parsed={"raw": expression},
                confidence=0.0,
                start_date=None,
                end_date=None,
            )

        # 解析最佳匹配結果
        best_match = results[0]
        payload = best_match.payload

        matched_expression = payload.get("expression", "")
        category = payload.get("category", "unknown")
        granularity = payload.get("granularity", "UNKNOWN")
        parsed = payload.get("parsed", {})

        # 計算具體日期範圍
        start_date, end_date = self._parse_relative_time(parsed, current_year)
        if not start_date:
            start_date, end_date = self._parse_absolute_time(parsed)

        # 處理相對時間關鍵字
        if "relative" in parsed:
            relative_key = parsed["relative"]
            # 動態計算相對時間
            if "last_" in relative_key or "next_" in relative_key:
                pass  # 已在 _parse_relative_time 中處理
            else:
                # 處理今年/去年等
                relative_map = {
                    "current_year": (datetime(current_year, 1, 1), datetime(current_year, 12, 31)),
                    "last_year": (
                        datetime(current_year - 1, 1, 1),
                        datetime(current_year - 1, 12, 31),
                    ),
                    "next_year": (
                        datetime(current_year + 1, 1, 1),
                        datetime(current_year + 1, 12, 31),
                    ),
                }
                if relative_key in relative_map:
                    start_date, end_date = relative_map[relative_key]
                    start_date = start_date.isoformat()
                    end_date = end_date.isoformat()

        return TimePeriodRAGOutput(
            original_expression=expression,
            matched_expression=matched_expression,
            category=category,
            granularity=granularity,
            parsed=parsed,
            confidence=float(best_match.score),
            start_date=start_date,
            end_date=end_date,
        )


# 全局單例
_time_period_rag_tool: Optional[TimePeriodRAGTool] = None


def get_time_period_rag_tool() -> TimePeriodRAGTool:
    """獲取時間分詞器工具實例（單例模式）"""
    global _time_period_rag_tool
    if _time_period_rag_tool is None:
        _time_period_rag_tool = TimePeriodRAGTool()
    return _time_period_rag_tool
