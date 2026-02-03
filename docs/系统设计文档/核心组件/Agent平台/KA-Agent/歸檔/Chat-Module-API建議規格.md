# Chat Module API 建議規格（v3.0）

**創建日期**: 2026-01-28
**基於版本**: v2.0（Chat-Module-API規格書.md）
**建議版本**: v3.0
**目標**: 優化架構設計，提升可維護性、可測試性和性能

---

## 📋 執行摘要

本文檔基於現有的 Chat Module API v2.0 規格，提出一系列改進建議，旨在：

1. **強化模塊職責分離**：進一步解耦處理邏輯、業務邏輯和工具函數
2. **改進錯誤處理機制**：統一錯誤處理，提供更友好的錯誤消息
3. **增強性能優化**：引入緩存、批處理和異步優化
4. **提升可測試性**：設計依賴注入和 Mock 友好的架構
5. **擴展 API 功能**：新增請求優先級、限流、批處理等特性

---

## 🏗️ 架構設計建議

### 1. 增強的目錄結構

```
api/routers/chat_module/
├── __init__.py              # 統一導出
├── router.py                # 主路由定義
├── dependencies.py          # 依賴注入服務
├── middleware/              # 🆕 中間件層
│   ├── __init__.py
│   ├── rate_limiter.py      # 請求限流
│   ├── cache_middleware.py  # 緩存中間件
│   └── auth_enhancer.py     # 認證增強（細粒度權限）
├── handlers/               # 處理器層
│   ├── __init__.py
│   ├── base.py             # 🆕 基礎處理器抽象類
│   ├── sync_handler.py     # 同步聊天處理
│   ├── stream_handler.py   # 流式聊天處理
│   ├── async_handler.py    # 異步請求處理
│   └── batch_handler.py    # 🆕 批處理處理器
├── services/               # 業務邏輯層
│   ├── __init__.py
│   ├── chat_pipeline.py    # 核心聊天管道
│   ├── file_operations.py  # 文件操作服務
│   ├── observability.py    # 觀測性服務
│   ├── session_service.py  # 🆕 會話管理服務
│   ├── priority_service.py # 🆕 優先級管理服務
│   └── routing_service.py # 🆕 路由決策服務
├── strategies/             # 🆕 策略模式層
│   ├── __init__.py
│   ├── model_selection.py  # 模型選擇策略
│   ├── agent_routing.py    # Agent 路由策略
│   └── response_formatting.py  # 響應格式化策略
├── validators/             # 🆕 驗證層
│   ├── __init__.py
│   ├── request_validator.py # 請求驗證器
│   ├── permission_validator.py  # 權限驗證器
│   └── quota_validator.py    # 配額驗證器
├── utils/                 # 工具層
│   ├── __init__.py
│   ├── file_detection.py  # 文件意圖檢測
│   ├── file_parsing.py   # 文件路徑解析
│   ├── response_formatter.py  # 🆕 響應格式化工具
│   └── error_helper.py    # 🆕 錯誤處理助手
└── models/                # 🆕 數據模型層
    ├── __init__.py
    ├── request.py        # 請求模型
    ├── response.py       # 響應模型
    └── internal.py       # 內部模型
```

### 2. 模塊職責重定義

| 模塊 | 職責 | 新增功能 |
|------|------|----------|
| `middleware/` | 橫切關注點（限流、緩存、認證） | 🆕 限流、緩存 |
| `handlers/base.py` | 處理器抽象類，定義通用流程 | 🆕 模板方法模式 |
| `handlers/batch_handler.py` | 批處理請求處理 | 🆕 批處理 API |
| `services/session_service.py` | 會話生命周期管理 | 🆕 會話清理、歸檔 |
| `services/priority_service.py` | 請求優先級管理 | 🆕 VIP 隊列 |
| `services/routing_service.py` | 路由決策邏輯 | 🆕 A/B 測試支持 |
| `strategies/` | 可插拔的策略模式 | 🆕 動態策略切換 |
| `validators/` | 請求驗證和權限檢查 | 🆕 統一驗證流程 |
| `models/` | Pydantic 數據模型 | 🆕 統一模型管理 |

---

## 🔌 API 端點增強建議

### 1. 主聊天端點增強

**端點**: `POST /api/v1/chat`

**新增請求參數**:
```json
{
  "messages": [...],
  "session_id": "session_123",
  "task_id": "task_456",
  "model_selector": {
    "mode": "auto",
    "model_id": null
  },
  "attachments": [],
  "priority": "normal",  // 🆕 請求優先級：low/normal/high/urgent
  "timeout": 60,         // 🆕 超時時間（秒）
  "cache_ttl": 300,      // 🆕 緩存存活時間（秒），0 = 不緩存
  "metadata": {          // 🆕 自定義元數據
    "client_version": "1.2.0",
    "request_source": "web"
  },
  "experimental": {      // 🆕 實驗性功能開關
    "enable_agent_v2": false
  }
}
```

**新增響應字段**:
```json
{
  "success": true,
  "data": {
    "content": "您的知識庫共有 5 個文件...",
    "request_id": "req_789",
    "session_id": "session_123",
    "task_id": "task_456",
    "routing": {...},
    "observability": {...},
    "actions": [],
    "cache_hit": false,    // 🆕 是否命中緩存
    "priority": "normal",   // 🆕 實際使用的優先級
    "warnings": []          // 🆕 警告信息（如降級）
  },
  "message": "Chat response generated"
}
```

### 2. 批處理端點（🆕 新增）

**端點**: `POST /api/v1/chat/batch`

**描述**: 批量處理多個聊天請求，提高吞吐量

**請求體**:
```json
{
  "requests": [
    {
      "messages": [{"role": "user", "content": "查詢1"}],
      "session_id": "session_1"
    },
    {
      "messages": [{"role": "user", "content": "查詢2"}],
      "session_id": "session_2"
    }
  ],
  "mode": "parallel",  // parallel/sequential
  "max_concurrent": 10,
  "priority": "normal"
}
```

**響應**:
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_123",
    "results": [
      {
        "index": 0,
        "request_id": "req_1",
        "success": true,
        "data": {...}
      },
      {
        "index": 1,
        "request_id": "req_2",
        "success": false,
        "error": {
          "code": "TIMEOUT_ERROR",
          "message": "請求超時"
        }
      }
    ],
    "summary": {
      "total": 2,
      "succeeded": 1,
      "failed": 1,
      "total_time_ms": 1250
    }
  }
}
```

### 3. 請求重試端點（🆕 新增）

**端點**: `POST /api/v1/chat/requests/{request_id}/retry`

**描述**: 重試失敗的請求

**請求體**:
```json
{
  "retry_strategy": "exponential",  // exponential/linear/immediate
  "max_retries": 3,
  "backoff_ms": 1000
}
```

### 4. 請求優先級調整端點（🆕 新增）

**端點**: `PUT /api/v1/chat/requests/{request_id}/priority`

**請求體**:
```json
{
  "priority": "high",
  "reason": "VIP 用戶"
}
```

### 5. 會話歸檔端點（🆕 新增）

**端點**: `POST /api/v1/chat/sessions/{session_id}/archive`

**描述**: 歸檔會話，釋放記憶體

**響應**:
```json
{
  "success": true,
  "data": {
    "session_id": "session_123",
    "archive_id": "archive_456",
    "message_count": 156,
    "archived_at": "2026-01-28T10:00:00Z"
  }
}
```

---

## 🎯 數據模型增強建議

### 1. 增強的請求模型

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class PriorityLevel(str, Enum):
    """請求優先級"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ExperimentalFeatures(BaseModel):
    """實驗性功能開關"""
    enable_agent_v2: bool = False
    enable_streaming_v2: bool = False
    enable_cache_v2: bool = False

class ChatRequestEnhanced(BaseModel):
    """增強的聊天請求模型"""
    messages: List[Message]
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    model_selector: ModelSelector
    attachments: List[Attachment] = []
    priority: PriorityLevel = PriorityLevel.NORMAL
    timeout: int = Field(default=60, ge=10, le=600, description="超時時間（秒）")
    cache_ttl: int = Field(default=300, ge=0, le=3600, description="緩存存活時間（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定義元數據")
    experimental: ExperimentalFeatures = Field(default_factory=ExperimentalFeatures)

    # 驗證器
    @field_validator('metadata')
    def validate_metadata(cls, v):
        # 限制 metadata 的大小
        if len(str(v)) > 1000:
            raise ValueError("metadata 太大，最多 1000 字符")
        return v

    @field_validator('timeout')
    def validate_timeout_for_priority(cls, v, info):
        # 高優先級請求可以設置更長的超時
        if info.data.get('priority') == PriorityLevel.LOW and v > 30:
            raise ValueError("低優先級請求超時時間不能超過 30 秒")
        return v
```

### 2. 增強的響應模型

```python
class WarningInfo(BaseModel):
    """警告信息"""
    code: str
    message: str
    level: str = Field(default="info")  # info/warning/critical

class ChatResponseEnhanced(BaseModel):
    """增強的聊天響應模型"""
    content: str
    request_id: str
    session_id: str
    task_id: Optional[str]
    routing: RoutingInfo
    observability: ObservabilityInfo
    actions: List[Action] = []
    cache_hit: bool = False
    priority: PriorityLevel = PriorityLevel.NORMAL
    warnings: List[WarningInfo] = Field(default_factory=list)

    # 輔助方法
    def has_warning(self, code: str) -> bool:
        """檢查是否有特定警告"""
        return any(w.code == code for w in self.warnings)

    def get_warning_messages(self) -> List[str]:
        """獲取所有警告消息"""
        return [w.message for w in self.warnings]
```

### 3. 統一錯誤模型

```python
class ErrorCode(str, Enum):
    """標準化錯誤代碼"""
    # 驗證錯誤
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST_FORMAT = "INVALID_REQUEST_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # 認證授權錯誤
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # 資源錯誤
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"

    # 限流和配額
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # 服務錯誤
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"

    # 系統錯誤
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

class ChatErrorResponse(BaseModel):
    """統一的錯誤響應模型"""
    success: bool = False
    error_code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_exception(
        cls,
        error: Exception,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        request_id: Optional[str] = None
    ) -> "ChatErrorResponse":
        """從異常創建錯誤響應"""
        return cls(
            error_code=error_code,
            message=str(error),
            details={
                "error_type": type(error).__name__,
                "original_error": str(error)
            },
            request_id=request_id
        )
```

---

## 🛡️ 錯誤處理改進建議

### 1. 統一錯誤處理層

**新建**: `utils/error_helper.py`

```python
import logging
from typing import Tuple, Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class ErrorHandler:
    """統一錯誤處理器"""

    @staticmethod
    def handle_llm_error(error: Exception) -> Tuple[str, ErrorCode]:
        """
        處理 LLM 相關錯誤

        Returns:
            (user_friendly_message, error_code)
        """
        error_str = str(error).lower()

        # API Key 錯誤
        if any(k in error_str for k in ["api key", "unauthorized", "401"]):
            return (
                "哎呀，發生了一些小狀況！🔐 API 授權出現問題，請通知管理員（錯誤代碼：API_INVALID）😅",
                ErrorCode.AUTHENTICATION_ERROR
            )

        # 網路錯誤
        if any(k in error_str for k in ["connection", "timeout", "network"]):
            return (
                "哎呀，發生了一些小狀況！🌐 網路連線出現問題，請檢查網路連線後再試（錯誤代碼：NETWORK_ERROR）😅",
                ErrorCode.LLM_SERVICE_ERROR
            )

        # 超時錯誤
        if any(k in error_str for k in ["timeout", "timed out"]):
            return (
                "哎呀，發生了一些小狀況！⏱️ 請求處理時間過長，請稍後再試或通知管理員（錯誤代碼：TIMEOUT_ERROR）😅",
                ErrorCode.LLM_TIMEOUT
            )

        # 限流錯誤
        if any(k in error_str for k in ["rate limit", "429", "quota"]):
            return (
                "哎呀，發生了一些小狀況！😓 AI 模型服務超出使用限制，請通知管理員（錯誤代碼：LIMIT_EXCEEDED）😅",
                ErrorCode.LLM_RATE_LIMIT
            )

        # 默認錯誤
        return (
            f"哎呀，發生了一些小狀況，我感到很抱歉！請通知管理員（錯誤代碼：{ErrorCode.INTERNAL_SERVER_ERROR.value}）😅",
            ErrorCode.INTERNAL_SERVER_ERROR
        )

    @staticmethod
    def create_http_exception(
        error: Exception,
        error_code: Optional[ErrorCode] = None,
        request_id: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ) -> HTTPException:
        """
        創建 HTTP 異常

        Args:
            error: 原始異常
            error_code: 錯誤代碼（如果未指定，則根據 error 推斷）
            request_id: 請求 ID
            status_code: HTTP 狀態碼

        Returns:
            HTTPException 實例
        """
        message, code = ErrorHandler.handle_llm_error(error)
        if error_code:
            code = error_code

        logger.error(
            f"Error occurred: request_id={request_id}, error_code={code}, error={str(error)}",
            exc_info=True
        )

        return HTTPException(
            status_code=status_code,
            detail=ChatErrorResponse(
                error_code=code,
                message=message,
                request_id=request_id,
                details={
                    "error_type": type(error).__name__,
                    "original_error": str(error)
                }
            ).model_dump()
        )

    @staticmethod
    def wrap_exception(func):
        """
        裝飾器：自動捕獲並處理異常

        Usage:
            @ErrorHandler.wrap_exception
            async def my_function():
                # 可能拋出異常的代碼
                pass
        """
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise  # 已經是 HTTP 異常，直接拋出
            except Exception as e:
                request_id = kwargs.get('request_id')
                raise ErrorHandler.create_http_exception(e, request_id=request_id)
        return wrapper
```

### 2. 全局異常處理器

**新建**: `middleware/error_handler.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from utils.error_helper import ErrorHandler, ErrorCode, ChatErrorResponse

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局異常處理器"""
    request_id = getattr(request.state, "request_id", None)

    # 如果是 HTTPException，直接返回
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    # 其他異常，使用統一錯誤處理
    http_exc = ErrorHandler.create_http_exception(exc, request_id=request_id)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """請求驗證異常處理器"""
    request_id = getattr(request.state, "request_id", None)

    # 檢查是否是空查詢錯誤
    if request.url.path.endswith("/chat") and request.method == "POST":
        errors = exc.errors()
        for error in errors:
            if "content" in str(error.get("loc", [])):
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content=ChatErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message="消息內容不能為空",
                        request_id=request_id,
                        details={"validation_errors": errors}
                    ).model_dump()
                )

    # 默認驗證錯誤
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ChatErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="請求參數驗證失敗",
            request_id=request_id,
            details={"validation_errors": exc.errors()}
        ).model_dump()
    )
```

---

## ⚡ 性能優化建議

### 1. 緩存策略

**新建**: `middleware/cache_middleware.py`

```python
from functools import lru_cache
from typing import Optional, Dict, Any
import hashlib
import json

class CacheMiddleware:
    """緩存中間件"""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.memory_cache: Dict[str, Any] = {}

    def _generate_cache_key(
        self,
        messages: List[Dict],
        model_selector: Dict,
        user_id: str
    ) -> str:
        """生成緩存鍵"""
        # 使用消息的內容、模型選擇器和用戶 ID 生成鍵
        key_data = {
            "messages": messages,
            "model_selector": model_selector,
            "user_id": user_id
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_cached_response(
        self,
        cache_key: str,
        ttl: int
    ) -> Optional[Dict]:
        """獲取緩存響應"""
        if self.redis:
            # 使用 Redis 緩存
            cached = await self.redis.get(f"chat_cache:{cache_key}")
            if cached:
                return json.loads(cached)
        else:
            # 使用內存緩存
            return self.memory_cache.get(cache_key)

        return None

    async def set_cached_response(
        self,
        cache_key: str,
        response: Dict,
        ttl: int
    ) -> None:
        """設置緩存響應"""
        response_str = json.dumps(response)

        if self.redis:
            # 使用 Redis 緩存
            await self.redis.setex(
                f"chat_cache:{cache_key}",
                ttl,
                response_str
            )
        else:
            # 使用內存緩存（簡化版，不支持 TTL）
            self.memory_cache[cache_key] = response
```

### 2. 請求限流

**新建**: `middleware/rate_limiter.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """限流處理器"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": f"請求過於頻繁，請在 {exc.retry_after} 秒後重試",
            "retry_after": exc.retry_after
        }
    )
```

### 3. 異步優化

**改進**: `handlers/base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, AsyncContextManager

class BaseHandler(ABC):
    """處理器基類，定義通用流程"""

    def __init__(
        self,
        moe_manager,
        context_manager,
        cache_middleware,
        rate_limiter
    ):
        self.moe = moe_manager
        self.context = context_manager
        self.cache = cache_middleware
        self.limiter = rate_limiter

    @abstractmethod
    async def handle(self, request: ChatRequest) -> ChatResponse:
        """處理請求（子類實現）"""
        pass

    async def pre_process(self, request: ChatRequest) -> ChatRequest:
        """前置處理（可覆寫）"""
        # 1. 限流檢查
        await self._check_rate_limit(request)

        # 2. 權限檢查
        await self._check_permissions(request)

        # 3. 配額檢查
        await self._check_quota(request)

        return request

    async def post_process(self, response: ChatResponse) -> ChatResponse:
        """後置處理（可覆寫）"""
        # 1. 設置緩存
        if request.cache_ttl > 0:
            await self._set_cache(request, response)

        # 2. 記錄指標
        self._record_metrics(response)

        # 3. 清理資源
        await self._cleanup(request, response)

        return response

    async def _check_rate_limit(self, request: ChatRequest) -> None:
        """檢查限流"""
        # 根據用戶 ID 和優先級設置不同的限流策略
        key = f"chat:{request.user_id}:{request.priority}"
        await self.limiter.hit(key)

    async def _check_permissions(self, request: ChatRequest) -> None:
        """檢查權限"""
        # 檢查文件訪問權限
        for attachment in request.attachments:
            if not await self._check_file_permission(attachment.file_id, request.user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="無權訪問附件文件"
                )

    async def _check_quota(self, request: ChatRequest) -> None:
        """檢查配額"""
        # 檢查用戶的請求配額
        # ...

    async def _set_cache(self, request: ChatRequest, response: ChatResponse) -> None:
        """設置緩存"""
        cache_key = self.cache._generate_cache_key(
            request.messages,
            request.model_selector.model_dump(),
            request.user_id
        )
        await self.cache.set_cached_response(
            cache_key,
            response.model_dump(),
            request.cache_ttl
        )

    async def _cleanup(self, request: ChatRequest, response: ChatResponse) -> None:
        """清理資源"""
        # 清理臨時文件、釋放連接等
        pass
```

---

## 🧪 測試策略建議

### 1. 測試層級設計

```
tests/
├── unit/                    # 單元測試
│   ├── services/
│   │   ├── test_chat_pipeline.py
│   │   ├── test_session_service.py
│   │   └── test_routing_service.py
│   ├── handlers/
│   │   ├── test_sync_handler.py
│   │   └── test_stream_handler.py
│   ├── middleware/
│   │   ├── test_cache_middleware.py
│   │   └── test_rate_limiter.py
│   └── utils/
│       ├── test_error_helper.py
│       └── test_file_detection.py
├── integration/             # 集成測試
│   ├── test_chat_end_to_end.py
│   ├── test_session_lifecycle.py
│   └── test_observability.py
└── performance/            # 性能測試
    ├── test_concurrent_requests.py
    ├── test_cache_effectiveness.py
    └── test_streaming_latency.py
```

### 2. 測試工具函數

**新建**: `tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def mock_moe_manager():
    """Mock MoE Manager"""
    manager = Mock()
    manager.select_model = AsyncMock(return_value=Mock(
        model="gpt-oss:120b-cloud",
        provider="ollama",
        temperature=0.7
    ))
    manager.chat = AsyncMock(return_value={
        "content": "測試響應",
        "_routing": {
            "provider": "ollama",
            "model": "gpt-oss:120b-cloud"
        }
    })
    return manager

@pytest.fixture
def mock_context_manager():
    """Mock Context Manager"""
    manager = Mock()
    manager.record_message = AsyncMock()
    manager.get_messages = AsyncMock(return_value=[])
    return manager

@pytest.fixture
def mock_cache_middleware():
    """Mock Cache Middleware"""
    cache = Mock()
    cache.get_cached_response = AsyncMock(return_value=None)
    cache.set_cached_response = AsyncMock()
    return cache

@pytest.fixture
def sample_chat_request():
    """示例聊天請求"""
    return ChatRequestEnhanced(
        messages=[{"role": "user", "content": "測試消息"}],
        session_id="test_session",
        task_id="test_task",
        model_selector=ModelSelector(mode="auto"),
        priority=PriorityLevel.NORMAL,
        cache_ttl=300
    )
```

### 3. 單元測試示例

**新建**: `tests/unit/handlers/test_sync_handler.py`

```python
import pytest
from handlers.sync_handler import SyncHandler
from utils.error_helper import ErrorCode

@pytest.mark.asyncio
async def test_sync_handler_success(mock_moe_manager, mock_context_manager, mock_cache_middleware):
    """測試成功處理"""
    handler = SyncHandler(
        moe_manager=mock_moe_manager,
        context_manager=mock_context_manager,
        cache_middleware=mock_cache_middleware,
        rate_limiter=Mock()
    )

    request = sample_chat_request()
    response = await handler.handle(request)

    assert response.content == "測試響應"
    assert response.cache_hit is False
    mock_context_manager.record_message.assert_called_once()

@pytest.mark.asyncio
async def test_sync_handler_cache_hit(mock_cache_middleware):
    """測試緩存命中"""
    mock_cache_middleware.get_cached_response = AsyncMock(
        return_value=ChatResponseEnhanced(
            content="緩存響應",
            request_id="cached_req",
            session_id="test_session",
            routing=RoutingInfo(provider="ollama", model="gpt-oss:120b-cloud"),
            observability=ObservabilityInfo(request_id="cached_req", session_id="test_session"),
            cache_hit=True
        ).model_dump()
    )

    handler = SyncHandler(
        moe_manager=Mock(),
        context_manager=Mock(),
        cache_middleware=mock_cache_middleware,
        rate_limiter=Mock()
    )

    request = sample_chat_request()
    response = await handler.handle(request)

    assert response.cache_hit is True
    mock_moe_manager.chat.assert_not_called()
```

---

## 📊 遷移計畫建議

### 階段 1: 基礎架構重構（1-2 週）

**目標**: 建立新架構基礎，不影響現有功能

**任務**:
1. 創建新目錄結構
2. 實現 `middleware/` 層
3. 實現 `validators/` 層
4. 實現 `strategies/` 層
5. 實現 `models/` 層
6. 更新 `dependencies.py`

**驗收標準**:
- ✅ 新架構可導入，無語法錯誤
- ✅ 單元測試覆蓋新模塊
- ✅ 舊代碼不受影響

### 階段 2: 核心處理器遷移（2-3 週）

**目標**: 實現核心聊天處理器，支持基本功能

**任務**:
1. 實現 `services/chat_pipeline.py`
2. 實現 `handlers/base.py`
3. 實現 `handlers/sync_handler.py`
4. 實現 `handlers/stream_handler.py`
5. 實現 `handlers/async_handler.py`
6. 更新 `router.py` 註冊新端點

**驗收標準**:
- ✅ 所有核心端點可訪問
- ✅ 功能與舊代碼一致
- ✅ 集成測試通過

### 階段 3: 進階功能實現（1-2 週）

**目標**: 實現增進功能，提升用戶體驗

**任務**:
1. 實現批處理端點
2. 實現請求優先級管理
3. 實現會話歸檔功能
4. 實現請求重試功能
5. 實現緩存策略

**驗收標準**:
- ✅ 新端點可正常使用
- ✅ 性能指標符合預期
- ✅ 用戶反饋良好

### 階段 4: Worker 和測試遷移（1 週）

**目標**: 更新 Worker 和所有測試，使用新架構

**任務**:
1. 更新 `workers/genai_chat_job.py`
2. 更新所有測試文件
3. 添加性能測試
4. 添加壓力測試

**驗收標準**:
- ✅ Worker 正常處理請求
- ✅ 所有測試通過
- ✅ 性能指標達標

### 階段 5: 完全遷移（1 週）

**目標**: 完全替換舊代碼

**任務**:
1. 停用舊端點
2. 清理舊代碼
3. 更新文檔
4. 培訓開發人員

**驗收標準**:
- ✅ 舊代碼已刪除或歸檔
- ✅ 生產環境穩定運行
- ✅ 文檔完整

---

## 📈 監控和觀測性建議

### 1. 關鍵指標

| 指標 | 描述 | 目標 | 告警閾值 |
|------|------|------|----------|
| `chat_request_total` | 請求總數 | - | - |
| `chat_request_duration_seconds` | 請求延遲 | < 2s | > 5s |
| `chat_request_cache_hit_rate` | 緩存命中率 | > 30% | < 10% |
| `chat_llm_latency_seconds` | LLM 調用延遲 | < 1s | > 3s |
| `chat_error_rate` | 錯誤率 | < 1% | > 5% |
| `chat_concurrent_requests` | 並發請求數 | < 100 | > 80 |

### 2. 分佈式追蹤

**建議**: 使用 OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# 配置 Jaeger
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))

# 在處理器中使用
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("chat_request"):
    with tracer.start_as_current_span("llm_call"):
        # LLM 調用
        pass
```

---

## 🔒 安全性增強建議

### 1. 輸入驗證

```python
from pydantic import validator, constr
import re

class ChatRequestSecure(BaseModel):
    """安全的聊天請求模型"""
    messages: List[Message]

    @validator('messages')
    def validate_messages(cls, v):
        """驗證消息列表"""
        if len(v) == 0:
            raise ValueError("消息不能為空")

        if len(v) > 100:
            raise ValueError("消息數量不能超過 100 條")

        for msg in v:
            if not isinstance(msg.content, str):
                raise ValueError("消息內容必須是字符串")

            if len(msg.content) > 10000:
                raise ValueError("單條消息內容不能超過 10000 字符")

            # 檢測惡意內容
            if cls._detect_malicious_content(msg.content):
                raise ValueError("消息包含違規內容")

        return v

    @staticmethod
    def _detect_malicious_content(content: str) -> bool:
        """檢測惡意內容"""
        # SQL 注入檢測
        sql_patterns = [
            r"('\s*(OR|AND)\s*')",
            r"(;\s*(DROP|DELETE|UPDATE|INSERT))",
            r"(UNION\s+SELECT)"
        ]
        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # XSS 檢測
        xss_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"on\w+\s*="
        ]
        for pattern in xss_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        return False
```

### 2. 權限檢查增強

```python
class PermissionValidator:
    """權限驗證器"""

    @staticmethod
    async def validate_file_access(
        user: User,
        file_id: str,
        required_permission: str
    ) -> None:
        """驗證文件訪問權限"""
        permission_service = get_file_permission_service()

        # 檢查權限
        try:
            permission_service.check_file_access(
                user=user,
                file_id=file_id,
                required_permission=required_permission
            )
        except PermissionDeniedError as e:
            # 記錄審計日誌
            await audit_logger.log(
                event="file_access_denied",
                user_id=user.user_id,
                file_id=file_id,
                required_permission=required_permission,
                reason=str(e)
            )
            raise

    @staticmethod
    async def validate_quota(
        user: User,
        request: ChatRequest
    ) -> None:
        """驗證配額"""
        quota_service = get_quota_service()

        # 檢查用戶配額
        quota = await quota_service.get_user_quota(user.user_id)

        if quota.remaining_requests <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="請求配額已用完"
            )

        # 扣減配額
        await quota_service.deduct_quota(user.user_id, amount=1)
```

---

## 📚 文檔建議

### 1. API 文檔自動化

使用 FastAPI 自動生成 OpenAPI 文檔，並添加額外說明：

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="AI Box Chat API",
        version="3.0.0",
        description="""
        # Chat Module API

        ## 概述
        提供 AI 聊天功能，支持同步、流式和異步處理。

        ## 認證
        所有端點需要 Bearer Token 認證。

        ## 限流
        - 普通用戶：10 請求/分鐘
        - VIP 用戶：100 請求/分鐘

        ## 錯誤處理
        所有錯誤響應遵循統一格式。

        ## 緩存
        默認緩存 300 秒，可通過 `cache_ttl` 參數控制。

        ## 優先級
        支持 `low`/`normal`/`high`/`urgent` 四個優先級。
        """,
        routes=app.routes,
    )

    # 添加安全方案
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### 2. 開發者指南

**新建**: `docs/開發文檔/Chat-Module-開發者指南.md`

```markdown
# Chat Module 開發者指南

## 快速開始

### 1. 添加新的端點

```python
# api/routers/chat_module/router.py

@router.post("/my-endpoint", status_code=status.HTTP_200_OK)
async def my_endpoint(
    request: MyRequest,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """我的端點"""
    # 1. 驗證請求
    # 2. 處理業務邏輯
    # 3. 返回響應
    pass
```

### 2. 添加新的服務

```python
# api/routers/chat_module/services/my_service.py

class MyService:
    def __init__(self, config):
        self.config = config

    async def do_something(self, param: str) -> Dict:
        """做一些事情"""
        result = await self._internal_method(param)
        return {"result": result}

    async def _internal_method(self, param: str) -> str:
        """內部方法"""
        return f"processed: {param}"
```

### 3. 添加新的策略

```python
# api/routers/chat_module/strategies/my_strategy.py

class MyStrategy:
    """我的策略"""

    async def execute(self, context: Dict) -> Dict:
        """執行策略"""
        # 1. 分析上下文
        # 2. 決策
        # 3. 返回結果
        pass
```

## 測試指南

### 單元測試

```python
# tests/unit/services/test_my_service.py

import pytest
from services.my_service import MyService

@pytest.mark.asyncio
async def test_do_something():
    service = MyService(config={})
    result = await service.do_something("test")
    assert result["result"] == "processed: test"
```

### 集成測試

```python
# tests/integration/test_my_endpoint.py

import pytest
from fastapi.testclient import TestClient

def test_my_endpoint_success(app_client):
    response = app_client.post(
        "/api/v1/chat/my-endpoint",
        json={"param": "test"}
    )
    assert response.status_code == 200
```

## 性能優化指南

### 緩存使用

```python
# 使用緩存
async def my_function(param: str):
    cache_key = f"my_function:{param}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await expensive_computation(param)
    await cache.set(cache_key, result, ttl=300)
    return result
```

### 異步處理

```python
import asyncio

async def process_multiple(items: List[str]):
    """並發處理多個項目"""
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results
```
```

---

## 🎯 總結

### 改進亮點

1. **架構清晰**: 7 層架構，職責分明
2. **錯誤處理**: 統一錯誤碼，友好錯誤消息
3. **性能優化**: 緩存、限流、批處理
4. **可測試性**: Mock 友好，測試覆蓋全面
5. **安全增強**: 輸入驗證，權限檢查
6. **擴展性**: 策略模式，易於添加新功能
7. **觀測性**: 關鍵指標，分佈式追蹤

### 預期收益

| 指標 | 改進前 | 改進後 | 提升 |
|------|--------|--------|------|
| 代碼行數 | 5,467 行 | ~2,500 行 | -54% |
| 平均響應時間 | 2.5s | 1.8s | -28% |
| 緩存命中率 | 0% | 30% | +30% |
| 錯誤率 | 1.5% | 0.5% | -67% |
| 代碼可維護性 | 低 | 高 | ⭐⭐⭐⭐⭐ |

### 下一步行動

1. **評估建議**: 與團隊討論，確定採納的建議
2. **制定計畫**: 根據優先級制定詳細遷移計畫
3. **原型驗證**: 實現關鍵功能進行驗證
4. **逐步遷移**: 按階段執行遷移計畫
5. **持續優化**: 根據實際情況調整和優化

---

**建議文檔生成時間**: 2026-01-28
**下次審查**: 原型驗證完成後
**聯繫人**: Daniel Chung
