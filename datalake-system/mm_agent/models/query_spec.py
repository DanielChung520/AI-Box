# 代碼功能說明: 查詢規範模型
# 創建日期: 2026-02-05
# 創建人: AI-Box 開發團隊

"""QuerySpec - 結構化查詢參數模型"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class TimeType(str, Enum):
    """時間表達式類型"""

    SPECIFIC_DATE = "specific_date"  # 2024-04-14
    DATE_RANGE = "date_range"  # 2024-04-01 到 2024-04-30
    LAST_WEEK = "last_week"  # 最近7天
    LAST_MONTH = "last_month"  # 上月
    THIS_MONTH = "this_month"  # 本月
    LAST_YEAR = "last_year"  # 去年
    THIS_YEAR = "this_year"  # 今年


class TaskType(str, Enum):
    """任務類型枚舉"""

    GREETING = "greeting"  # 打招呼
    ERROR_INPUT = "error_input"  # 錯誤輸入
    QUERY = "query"  # 簡單查詢
    COMPLEX = "complex"  # 複雜任務


class QueryIntent(str, Enum):
    """查詢意圖枚舉"""

    QUERY_STOCK = "QUERY_STOCK"  # 庫存查詢
    QUERY_PURCHASE = "QUERY_PURCHASE"  # 採購交易查詢
    QUERY_SALES = "QUERY_SALES"  # 銷售交易查詢
    ANALYZE_SHORTAGE = "ANALYZE_SHORTAGE"  # 缺料分析
    GENERATE_ORDER = "GENERATE_ORDER"  # 生成訂單
    CLARIFICATION = "CLARIFICATION"  # 需要澄清


class QuerySpec(BaseModel):
    """查詢規範 - 結構化參數

    用於在 Router、Extractor、SQL Generator 之间传递查询参数
    """

    # 意圖（必填）
    intent: QueryIntent = QueryIntent.QUERY_PURCHASE

    # 料號（可選）
    material_id: Optional[str] = Field(default=None, description="料號，如 RM05-008")

    # 倉庫（可選）
    warehouse: Optional[str] = Field(default=None, description="倉庫代碼，如 W01")

    # 時間（可選）
    time_type: Optional[TimeType] = Field(default=None, description="時間類型")
    time_value: Optional[str] = Field(
        default=None, description="時間值，如 2024-04-14 或 2024-04-01~2024-04-30"
    )

    # 交易類型（可選）
    transaction_type: Optional[str] = Field(
        default=None, description="交易類型：101/102/201/202/301"
    )

    # 物料類別（可選）
    material_category: Optional[str] = Field(
        default=None, description="物料類別：plastic/finished/raw"
    )

    # 聚合運算（可選）
    aggregation: Optional[Literal["SUM", "COUNT", "AVG"]] = Field(
        default=None, description="聚合函數"
    )

    # 排序（可選）
    order_by: Optional[str] = Field(default=None, description="排序字段，如 tlf06 DESC")

    # 限制數量
    limit: int = Field(default=100, description="結果限制數量")

    # 置信度
    confidence: float = Field(default=1.0, ge=0, le=1, description="意圖識別置信度")

    # 缺失字段
    missing_fields: List[str] = Field(default_factory=list, description="缺失的必要字段")

    # 原始輸入（用於調試）
    raw_input: str = Field(default="", description="原始用戶輸入")

    class Config:
        use_enum_values = True


class RouterResult(BaseModel):
    """路由器結果"""

    task_type: TaskType
    query_spec: Optional[QuerySpec] = None
    response: Optional[str] = None  # 直接回覆（如打招呼）
    needs_llm: bool = False  # 是否需要 LLM 處理
