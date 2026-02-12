# 代碼功能說明: Data-Agent-JP Pydantic 模型
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""Data-Agent-JP Pydantic 模型

包含：
- API 請求/響應模型
- Concept/Intent/Binding 模型
- Query AST 模型
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ConceptType(str, Enum):
    """Concept 類型"""

    DIMENSION = "DIMENSION"
    METRIC = "METRIC"
    RANGE = "RANGE"
    ENUM = "ENUM"


class AggregationType(str, Enum):
    """聚合類型"""

    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    NONE = "NONE"


class OperatorType(str, Enum):
    """運算符類型"""

    EQUAL = "="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    LIKE = "LIKE"
    IN = "IN"
    BETWEEN = "BETWEEN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"


# ============================================================================
# API 請求/響應模型
# ============================================================================


class QueryOptions(BaseModel):
    """查詢選項"""

    explain: bool = False
    timeout: int = 30
    limit: Optional[int] = None
    offset: Optional[int] = None


class TaskData(BaseModel):
    """任務數據"""

    nlq: str = Field(..., description="完整表達的自然語言查詢")
    intent: Optional[str] = Field(None, description="意圖類型")
    params: Dict[str, Any] = Field(default_factory=dict, description="查詢參數")
    options: QueryOptions = Field(default_factory=QueryOptions)


class ExecuteRequest(BaseModel):
    """執行請求"""

    task_id: str = Field(..., description="任務 ID")
    task_type: str = Field(default="schema_driven_query", description="任務類型")
    task_data: TaskData


class QueryResultRow(BaseModel):
    """查詢結果行"""

    data: Dict[str, Any]


class QueryResult(BaseModel):
    """查詢結果"""

    sql: str = Field(..., description="生成的 SQL")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="結果數據")
    row_count: int = Field(0, description="結果數量")
    execution_time_ms: int = Field(0, description="執行時間（毫秒）")


class ExecuteResponse(BaseModel):
    """執行響應"""

    status: str = Field(..., description="狀態")
    task_id: str = Field(..., description="任務 ID")
    result: Optional[QueryResult] = Field(None, description="查詢結果")
    error_code: Optional[str] = Field(None, description="錯誤碼")
    message: Optional[str] = Field(None, description="訊息")


class HealthResponse(BaseModel):
    """健康檢查響應"""

    status: str = "healthy"
    service: str = "data-agent-jp"
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Concept 模型
# ============================================================================


class ConceptValue(BaseModel):
    """Concept 值定義"""

    labels: List[str] = Field(default_factory=list, description="標籤列表")
    description: Optional[str] = Field(None, description="描述")


class ConceptDefinition(BaseModel):
    """Concept 定義"""

    description: str = Field(..., description="概念描述")
    type: ConceptType = Field(..., description="概念類型")
    values: Optional[Dict[str, ConceptValue]] = Field(None, description="可選值")


class ConceptsContainer(BaseModel):
    """Concepts 容器"""

    version: str = "1.0"
    concepts: Dict[str, ConceptDefinition] = Field(default_factory=dict)


# ============================================================================
# Intent 模型
# ============================================================================


class IntentInput(BaseModel):
    """Intent 輸入定義"""

    filters: List[str] = Field(default_factory=list, description="可用的過濾器")
    required_filters: List[str] = Field(default_factory=list, description="必需的過濾器")


class IntentOutput(BaseModel):
    """Intent 輸出定義"""

    metrics: List[str] = Field(default_factory=list, description="可用的指標")
    dimensions: List[str] = Field(default_factory=list, description="可用的維度")


class IntentConstraint(BaseModel):
    """Intent 約束"""

    require_at_least_one_filter: bool = Field(False, description="是否需要至少一個過濾器")


class IntentDefinition(BaseModel):
    """Intent 定義"""

    description: str = Field(..., description="意圖描述")
    input: IntentInput = Field(default_factory=IntentInput)
    output: IntentOutput = Field(default_factory=IntentOutput)
    constraints: IntentConstraint = Field(default_factory=IntentConstraint)


class IntentsContainer(BaseModel):
    """Intents 容器"""

    version: str = "1.0"
    intents: Dict[str, IntentDefinition] = Field(default_factory=dict)


# ============================================================================
# Binding 模型
# ============================================================================


class BindingColumn(BaseModel):
    """Binding 欄位定義"""

    table: str = Field(..., description="表格名稱")
    column: str = Field(..., description="欄位名稱")
    aggregation: Optional[AggregationType] = Field(None, description="聚合類型")
    operator: Optional[OperatorType] = Field(None, description="運算符")


class BindingDefinition(BaseModel):
    """Binding 定義"""

    datasource: str = Field(default="ORACLE", description="數據源")
    dialect: str = Field(default="ORACLE", description="SQL 方言")
    bindings: Dict[str, BindingColumn] = Field(default_factory=dict)


class BindingsContainer(BaseModel):
    """Bindings 容器"""

    version: str = "1.0"
    datasource: Dict[str, str] = Field(default_factory=dict)
    bindings: Dict[str, Dict[str, BindingColumn]] = Field(default_factory=dict)


# ============================================================================
# Resolver 內部模型
# ============================================================================


class ParsedIntent(BaseModel):
    """解析後的意圖"""

    intent: str
    confidence: float = 1.0
    params: Dict[str, Any] = Field(default_factory=dict)
    token_usage: Optional[Dict[str, int]] = None
    validation_errors: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class MatchedConcept(BaseModel):
    """匹配的概念"""

    concept: str
    value: Any
    source: str = "explicit"


class ResolvedBinding(BaseModel):
    """解析的綁定"""

    concept: str
    table: str
    column: str
    aggregation: Optional[AggregationType] = None
    operator: OperatorType = OperatorType.EQUAL
    value: Optional[Any] = None


class QueryAST(BaseModel):
    """查詢 AST"""

    select: List[Dict[str, str]] = Field(default_factory=list)
    from_tables: List[str] = Field(default_factory=list)
    where_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    group_by: List[str] = Field(default_factory=list)
    order_by: List[str] = Field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None


# ============================================================================
# 錯誤模型
# ============================================================================


class ErrorCode(str, Enum):
    """錯誤碼"""

    SUCCESS = "SUCCESS"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTENT_NOT_FOUND = "INTENT_NOT_FOUND"
    CONCEPT_NOT_FOUND = "CONCEPT_NOT_FOUND"
    BINDING_NOT_FOUND = "BINDING_NOT_FOUND"
    SQL_GENERATION_ERROR = "SQL_GENERATION_ERROR"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    QUERY_TIMEOUT = "QUERY_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
