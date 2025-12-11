# Redis/RQ 任務隊列系統開發指南

**創建日期**: 2025-12-10  
**創建人**: Daniel Chung  
**最後修改日期**: 2025-12-10

## 📋 目錄

1. [概述](#概述)
2. [Redis 服務功能](#redis-服務功能)
3. [RQ 任務隊列架構](#rq-任務隊列架構)
4. [現有代碼功能](#現有代碼功能)
5. [任務提交指南](#任務提交指南)
6. [任務查詢指南](#任務查詢指南)
7. [開發指南](#開發指南)
8. [最佳實踐](#最佳實踐)
9. [故障排查](#故障排查)

---

## 概述

### Redis 與 RQ 的關係

**重要說明**：
- **Redis** 是獨立的服務，用於數據存儲和緩存
- **RQ (Redis Queue)** 是 Python 庫，**使用現有的 Redis 服務**來存儲任務隊列
- **RQ 不是獨立服務**，它通過 Redis 來管理任務隊列
- **RQ Worker** 是獨立進程，從 Redis 拉取任務並執行

### 架構圖

```
┌─────────────────┐
│  FastAPI API    │
│     Server      │
└────────┬────────┘
         │ (提交任務)
         ↓
┌─────────────────┐
│   RQ Queue      │  ← Python 庫
│   (客戶端)      │
└────────┬────────┘
         │ (存儲任務)
         ↓
┌─────────────────┐
│     Redis       │  ← 現有服務
│   (存儲層)      │
└────────┬────────┘
         │ (Worker 拉取)
         ↓
┌─────────────────┐
│  RQ Worker      │  ← 獨立進程
│   (執行任務)    │
└─────────────────┘
```

---

## Redis 服務功能

### 1. 文件處理狀態追蹤

**用途**: 追蹤文件上傳和處理的實時進度

**Key 格式**:
- `upload:progress:{file_id}` - 文件上傳進度（TTL: 1小時）
- `processing:status:{file_id}` - 文件處理狀態（TTL: 2小時）

**數據結構**:
```json
{
  "file_id": "xxx",
  "status": "processing",
  "progress": 50,
  "chunking": {"status": "completed", "progress": 100},
  "vectorization": {"status": "processing", "progress": 50},
  "storage": {"status": "pending", "progress": 0},
  "kg_extraction": {"status": "pending", "progress": 0},
  "message": "正在處理..."
}
```

**使用位置**:
- `api/routers/file_upload.py` - `_update_upload_progress()`, `_update_processing_status()`

### 2. JWT Token 黑名單管理

**用途**: 管理已登出或失效的 JWT Token

**Key 格式**:
- `jwt:blacklist:{token_hash}` - Token 黑名單（TTL: 與 Token 過期時間一致）

**使用位置**:
- `system/security/jwt_service.py` - `add_to_blacklist()`, `is_blacklisted()`

### 3. Agent 記憶管理 (AAM)

**用途**: 為 Agent 提供短期記憶存儲

**Key 格式**:
- `aam:memory:{key}` - Agent 記憶數據（TTL: 3600秒，1小時）

**使用位置**:
- `agents/infra/memory/aam/storage_adapter.py`

### 4. RQ 任務隊列存儲

**用途**: RQ 使用 Redis 存儲任務隊列數據

**Key 格式**:
- `rq:queue:{queue_name}` - 任務隊列
- `rq:job:{job_id}` - 任務數據
- `rq:worker:{worker_name}` - Worker 註冊信息

**使用位置**:
- `database/rq/queue.py` - RQ 隊列客戶端
- `database/rq/monitor.py` - 隊列監控工具

---

## RQ 任務隊列架構

### 隊列定義

系統中定義了三個主要隊列：

| 隊列名稱 | 用途 | 處理任務 |
|---------|------|---------|
| `file_processing` | 文件處理隊列 | 分塊 + 向量化 + 圖譜提取 |
| `vectorization` | 向量化專用隊列 | 僅向量化處理 |
| `kg_extraction` | 知識圖譜提取專用隊列 | 僅圖譜提取 |

### 組件說明

#### 1. 隊列客戶端 (`database/rq/queue.py`)

**功能**:
- 提供 `get_task_queue()` 函數獲取隊列實例（單例模式）
- 封裝 Redis 連接管理
- 支持多個隊列實例

**使用示例**:
```python
from database.rq.queue import get_task_queue, FILE_PROCESSING_QUEUE

queue = get_task_queue(FILE_PROCESSING_QUEUE)
```

#### 2. Worker 任務函數 (`workers/tasks.py`)

**功能**:
- 定義所有需要在 Worker 中執行的任務函數
- 處理異步函數的執行（使用 `asyncio.run()`）
- 提供錯誤處理和日誌記錄

**現有任務函數**:
- `process_file_chunking_and_vectorization_task()` - 文件處理任務
- `process_vectorization_only_task()` - 向量化任務
- `process_kg_extraction_only_task()` - 圖譜提取任務

#### 3. 監控工具 (`database/rq/monitor.py`)

**功能**:
- 查詢所有隊列列表
- 查詢隊列統計信息
- 查詢 Worker 信息
- 查詢任務列表

#### 4. 監控 API (`api/routers/rq_monitor.py`)

**功能**:
- 提供 RESTful API 接口查詢隊列狀態
- 支持認證和權限控制

---

## 現有代碼功能

### 1. Redis 客戶端 (`database/redis/client.py`)

**功能**:
- 單例模式的 Redis 客戶端管理
- 自動連接管理和重連
- 支持環境變數配置

**配置方式**:
```bash
# .env 文件
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0
```

**使用示例**:
```python
from database.redis import get_redis_client

redis_client = get_redis_client()
redis_client.setex("key", 3600, "value")
value = redis_client.get("key")
```

### 2. RQ 隊列客戶端 (`database/rq/queue.py`)

**功能**:
- 隊列實例管理（單例模式）
- Redis 連接封裝
- 隊列名稱常量定義

**使用示例**:
```python
from database.rq.queue import get_task_queue, FILE_PROCESSING_QUEUE

queue = get_task_queue(FILE_PROCESSING_QUEUE)
```

### 3. RQ 監控工具 (`database/rq/monitor.py`)

**功能函數**:
- `get_all_queues()` - 獲取所有隊列列表
- `get_queue_stats(queue_name)` - 獲取隊列統計
- `get_all_queues_stats()` - 獲取所有隊列統計
- `get_workers_info()` - 獲取 Worker 信息
- `get_queue_jobs(queue_name, status, limit)` - 獲取任務列表

### 4. Worker 啟動腳本 (`scripts/start_rq_worker.sh`)

**功能**:
- 自動檢測虛擬環境
- 檢查 Redis 連接
- 啟動 RQ Worker 進程
- 日誌記錄

**使用方法**:
```bash
./scripts/start_rq_worker.sh file_processing
```

### 5. 狀態查詢腳本 (`scripts/rq_status.sh`)

**功能**:
- 查詢所有隊列狀態
- 顯示隊列統計信息
- 顯示 Worker 信息

**使用方法**:
```bash
./scripts/rq_status.sh
```

---

## 任務提交指南

### 基本用法

#### 1. 導入必要的模組

```python
from database.rq.queue import get_task_queue, FILE_PROCESSING_QUEUE
from workers.tasks import process_file_chunking_and_vectorization_task
```

#### 2. 獲取隊列實例

```python
queue = get_task_queue(FILE_PROCESSING_QUEUE)
```

#### 3. 提交任務

```python
job = queue.enqueue(
    process_file_chunking_and_vectorization_task,
    file_id=file_id,
    file_path=file_path,
    file_type=file_type,
    user_id=user_id,
)
```

### 完整示例

#### 文件上傳處理

```python
from database.rq.queue import get_task_queue, FILE_PROCESSING_QUEUE
from workers.tasks import process_file_chunking_and_vectorization_task

# 在文件上傳路由中
@router.post("/upload")
async def upload_file(...):
    # ... 文件上傳邏輯 ...
    
    # 提交處理任務到 RQ
    queue = get_task_queue(FILE_PROCESSING_QUEUE)
    job = queue.enqueue(
        process_file_chunking_and_vectorization_task,
        file_id=file_id,
        file_path=file_path,
        file_type=file_type,
        user_id=current_user.user_id,
    )
    
    return APIResponse.success(
        data={
            "file_id": file_id,
            "job_id": job.id,
            "status": "queued",
        },
        message="文件上傳成功，處理任務已提交",
    )
```

#### 向量重新生成

```python
from database.rq.queue import get_task_queue, VECTORIZATION_QUEUE
from workers.tasks import process_vectorization_only_task

@router.post("/{file_id}/regenerate")
async def regenerate_vector(...):
    # ... 驗證邏輯 ...
    
    queue = get_task_queue(VECTORIZATION_QUEUE)
    job = queue.enqueue(
        process_vectorization_only_task,
        file_id=file_id,
        file_path=file_path,
        file_type=file_metadata.file_type,
        user_id=current_user.user_id,
    )
    
    return APIResponse.success(
        data={"job_id": job.id, "status": "queued"},
        message="向量重新生成任務已提交",
    )
```

#### 圖譜重新生成

```python
from database.rq.queue import get_task_queue, KG_EXTRACTION_QUEUE
from workers.tasks import process_kg_extraction_only_task

@router.post("/{file_id}/regenerate")
async def regenerate_graph(...):
    # ... 驗證邏輯 ...
    
    queue = get_task_queue(KG_EXTRACTION_QUEUE)
    job = queue.enqueue(
        process_kg_extraction_only_task,
        file_id=file_id,
        file_path=file_path,
        file_type=file_metadata.file_type,
        user_id=current_user.user_id,
        force_rechunk=False,
    )
    
    return APIResponse.success(
        data={"job_id": job.id, "status": "queued"},
        message="圖譜重新生成任務已提交",
    )
```

### 任務選項

#### 任務優先級

```python
from rq import Queue

queue = get_task_queue(FILE_PROCESSING_QUEUE)
job = queue.enqueue(
    task_function,
    arg1, arg2,
    job_timeout=3600,  # 任務超時時間（秒）
    result_ttl=86400,  # 結果保留時間（秒）
    failure_ttl=86400,  # 失敗任務保留時間（秒）
)
```

#### 延遲執行

```python
from datetime import datetime, timedelta

# 延遲 5 分鐘執行
job = queue.enqueue_in(
    timedelta(minutes=5),
    task_function,
    arg1, arg2,
)
```

#### 定時執行

```python
from rq import Queue
from datetime import datetime

# 在指定時間執行
job = queue.enqueue_at(
    datetime(2025, 12, 10, 22, 0, 0),
    task_function,
    arg1, arg2,
)
```

### 任務狀態追蹤

```python
# 獲取任務狀態
job = queue.fetch_job(job_id)
status = job.get_status()  # 'queued', 'started', 'finished', 'failed'

# 獲取任務結果
if job.is_finished:
    result = job.result

# 獲取任務錯誤信息
if job.is_failed:
    error = job.exc_info
```

---

## 任務查詢指南

### 1. 命令行查詢

#### 使用狀態查詢腳本

```bash
./scripts/rq_status.sh
```

**輸出示例**:
```
======================================================================
RQ 隊列狀態
======================================================================

📋 所有隊列:
----------------------------------------------------------------------
找到 3 個隊列:
  ✅ file_processing
  ✅ vectorization
  ✅ kg_extraction

📊 隊列統計:
----------------------------------------------------------------------

  file_processing:
    等待中: 5
    執行中: 2
    已完成: 100
    失敗: 1
    總計: 108

👷 Worker 信息:
----------------------------------------------------------------------
找到 2 個 Worker:
  ✅ rq_worker_file_processing_12345
    狀態: busy
    隊列: file_processing
    當前任務: abc123-def456-...
```

### 2. API 查詢

#### 獲取所有隊列列表

```bash
GET /api/v1/rq/queues
```

**響應**:
```json
{
  "success": true,
  "data": {
    "queues": ["file_processing", "vectorization", "kg_extraction"],
    "count": 3
  },
  "message": "隊列列表獲取成功"
}
```

#### 獲取所有隊列統計

```bash
GET /api/v1/rq/queues/stats
```

**響應**:
```json
{
  "success": true,
  "data": {
    "queues": {
      "file_processing": {
        "queue_name": "file_processing",
        "queued": 5,
        "started": 2,
        "finished": 100,
        "failed": 1,
        "total": 108
      },
      "vectorization": {
        "queue_name": "vectorization",
        "queued": 0,
        "started": 0,
        "finished": 50,
        "failed": 0,
        "total": 50
      }
    }
  }
}
```

#### 獲取指定隊列統計

```bash
GET /api/v1/rq/queues/file_processing/stats
```

#### 獲取隊列任務列表

```bash
GET /api/v1/rq/queues/file_processing/jobs?status=queued&limit=10
```

**參數**:
- `status` (可選): `queued`, `started`, `finished`, `failed`
- `limit` (可選): 返回任務數量限制（1-100，默認 10）

#### 獲取 Worker 信息

```bash
GET /api/v1/rq/workers
```

**響應**:
```json
{
  "success": true,
  "data": {
    "workers": [
      {
        "name": "rq_worker_file_processing_12345",
        "state": "busy",
        "queues": ["file_processing"],
        "current_job_id": "abc123-def456-...",
        "birth_date": "2025-12-10T20:00:00"
      }
    ],
    "count": 1
  }
}
```

### 3. Python 代碼查詢

#### 查詢所有隊列

```python
from database.rq.monitor import get_all_queues

queues = get_all_queues()
print(f"找到 {len(queues)} 個隊列: {queues}")
```

#### 查詢隊列統計

```python
from database.rq.monitor import get_queue_stats

stats = get_queue_stats("file_processing")
print(f"等待中: {stats['queued']}")
print(f"執行中: {stats['started']}")
print(f"已完成: {stats['finished']}")
print(f"失敗: {stats['failed']}")
```

#### 查詢所有隊列統計

```python
from database.rq.monitor import get_all_queues_stats

all_stats = get_all_queues_stats()
for queue_name, stats in all_stats.items():
    print(f"{queue_name}: {stats['total']} 個任務")
```

#### 查詢 Worker 信息

```python
from database.rq.monitor import get_workers_info

workers = get_workers_info()
for worker in workers:
    print(f"{worker['name']}: {worker['state']}")
```

#### 查詢任務列表

```python
from database.rq.monitor import get_queue_jobs

# 查詢等待中的任務
queued_jobs = get_queue_jobs("file_processing", status="queued", limit=10)

# 查詢執行中的任務
started_jobs = get_queue_jobs("file_processing", status="started", limit=10)

# 查詢失敗的任務
failed_jobs = get_queue_jobs("file_processing", status="failed", limit=10)
```

---

## 開發指南

### 添加新任務類型

#### 步驟 1: 在 `workers/tasks.py` 中添加任務函數

```python
def my_new_task(
    param1: str,
    param2: int,
) -> dict:
    """
    新任務處理函數

    Args:
        param1: 參數1
        param2: 參數2

    Returns:
        處理結果字典
    """
    try:
        # 如果是異步函數，使用 asyncio.run()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                async_task_function(param1, param2)
            )
            return {"success": True, "result": result}
        finally:
            loop.close()
    except Exception as e:
        logger.error("Task failed", error=str(e))
        return {"success": False, "error": str(e)}
```

#### 步驟 2: 在路由中提交任務

```python
from database.rq.queue import get_task_queue
from workers.tasks import my_new_task

@router.post("/my-endpoint")
async def my_endpoint(...):
    queue = get_task_queue("my_queue")
    job = queue.enqueue(
        my_new_task,
        param1=value1,
        param2=value2,
    )
    return APIResponse.success(data={"job_id": job.id})
```

#### 步驟 3: 啟動對應的 Worker

```bash
./scripts/start_rq_worker.sh my_queue
```

### 創建新隊列

#### 步驟 1: 在 `database/rq/queue.py` 中定義隊列常量

```python
MY_NEW_QUEUE = "my_new_queue"  # 新隊列名稱
```

#### 步驟 2: 在 `database/rq/__init__.py` 中導出

```python
from database.rq.queue import MY_NEW_QUEUE

__all__ = [
    # ... 其他導出 ...
    "MY_NEW_QUEUE",
]
```

#### 步驟 3: 使用新隊列

```python
from database.rq.queue import get_task_queue, MY_NEW_QUEUE

queue = get_task_queue(MY_NEW_QUEUE)
```

### 處理異步任務

**重要**: RQ Worker 是同步的，如果任務函數是異步的，需要在 Worker 任務函數中使用 `asyncio.run()`:

```python
def async_task_wrapper(param1: str) -> dict:
    """異步任務包裝函數"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                async_function(param1)
            )
            return {"success": True, "result": result}
        finally:
            loop.close()
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 任務錯誤處理

#### 在任務函數中處理錯誤

```python
def my_task(param: str) -> dict:
    try:
        # 任務邏輯
        result = do_something(param)
        return {"success": True, "result": result}
    except ValueError as e:
        logger.error("Validation error", error=str(e))
        return {"success": False, "error": f"Validation failed: {e}"}
    except Exception as e:
        logger.error("Task failed", error=str(e))
        raise  # 重新拋出異常，讓 RQ 記錄為失敗任務
```

#### 查詢失敗任務

```python
from database.rq.monitor import get_queue_jobs

failed_jobs = get_queue_jobs("file_processing", status="failed", limit=10)
for job_info in failed_jobs:
    print(f"任務 {job_info['job_id']} 失敗: {job_info.get('exc_info')}")
```

### 任務重試

#### 使用 RQ 的重試機制

```python
from rq import Retry

job = queue.enqueue(
    task_function,
    arg1, arg2,
    retry=Retry(max=3, interval=60),  # 最多重試3次，間隔60秒
)
```

#### 手動重試失敗任務

```python
from database.rq.queue import get_task_queue

queue = get_task_queue("file_processing")
failed_jobs = get_queue_jobs("file_processing", status="failed")

for job_info in failed_jobs:
    job = queue.fetch_job(job_info['job_id'])
    if job:
        job.requeue()  # 重新加入隊列
```

---

## 最佳實踐

### 1. 任務設計原則

#### ✅ 推薦做法

- **任務函數應該是純函數**: 盡量避免副作用，易於測試和調試
- **參數應該是可序列化的**: 使用基本類型（str, int, dict, list）
- **任務應該有明確的輸入和輸出**: 返回結構化的結果字典
- **處理異步函數**: 在 Worker 任務函數中使用 `asyncio.run()`

#### ❌ 避免做法

- **不要傳遞不可序列化的對象**: 如文件句柄、數據庫連接等
- **不要使用全局狀態**: 任務應該是無狀態的
- **不要在任務中進行長時間阻塞**: 使用異步操作

### 2. 隊列選擇策略

| 任務類型 | 推薦隊列 | 原因 |
|---------|---------|------|
| 文件上傳後的完整處理 | `file_processing` | 包含分塊、向量化、圖譜提取 |
| 僅向量化處理 | `vectorization` | 專用隊列，資源隔離 |
| 僅圖譜提取 | `kg_extraction` | 專用隊列，資源隔離 |
| 批量處理 | 創建專用隊列 | 避免影響實時任務 |

### 3. 錯誤處理策略

#### 任務級別錯誤處理

```python
def robust_task(param: str) -> dict:
    """健壯的任務函數"""
    try:
        # 主要邏輯
        result = process(param)
        return {"success": True, "result": result}
    except RecoverableError as e:
        # 可恢復的錯誤，記錄但不拋出
        logger.warning("Recoverable error", error=str(e))
        return {"success": False, "error": str(e), "recoverable": True}
    except Exception as e:
        # 不可恢復的錯誤，拋出讓 RQ 記錄
        logger.error("Fatal error", error=str(e))
        raise
```

#### 監控失敗任務

```python
# 定期檢查失敗任務
from database.rq.monitor import get_queue_jobs

failed_jobs = get_queue_jobs("file_processing", status="failed", limit=100)
if failed_jobs:
    logger.warning(f"發現 {len(failed_jobs)} 個失敗任務")
    # 發送告警或自動重試
```

### 4. 性能優化

#### Worker 進程數量

```bash
# 啟動多個 Worker（不同終端）
./scripts/start_rq_worker.sh file_processing
./scripts/start_rq_worker.sh file_processing
./scripts/start_rq_worker.sh vectorization
```

#### 任務優先級

```python
# 使用不同的隊列實現優先級
high_priority_queue = get_task_queue("high_priority")
normal_queue = get_task_queue("file_processing")

# 高優先級任務
high_priority_queue.enqueue(urgent_task, ...)

# 普通任務
normal_queue.enqueue(normal_task, ...)
```

### 5. 監控和日誌

#### 任務日誌

```python
import structlog

logger = structlog.get_logger(__name__)

def my_task(param: str) -> dict:
    logger.info("Task started", param=param)
    try:
        result = process(param)
        logger.info("Task completed", result=result)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("Task failed", error=str(e))
        raise
```

#### 監控指標

- **隊列長度**: 監控等待中的任務數量
- **Worker 狀態**: 監控 Worker 是否運行
- **失敗率**: 監控任務失敗比例
- **處理時間**: 監控任務平均處理時間

---

## 故障排查

### 常見問題

#### 1. Redis 連接失敗

**症狀**:
```
RuntimeError: Failed to connect to Redis: Connection refused
```

**解決方法**:
1. 檢查 Redis 服務是否運行: `docker ps | grep redis`
2. 檢查 Redis 配置: `.env` 文件中的 `REDIS_HOST` 和 `REDIS_PORT`
3. 測試連接: `redis-cli -h localhost -p 6379 ping`

#### 2. Worker 無法啟動

**症狀**:
```
錯誤: 無法連接到 Redis
```

**解決方法**:
1. 確保 Redis 服務正在運行
2. 檢查 `.env` 文件配置
3. 查看 Worker 日誌: `tail -f logs/rq_worker_*.log`

#### 3. 任務一直處於 queued 狀態

**症狀**:
- 任務提交成功，但一直不執行

**解決方法**:
1. 檢查是否有 Worker 運行: `./scripts/rq_status.sh`
2. 檢查 Worker 是否監聽正確的隊列
3. 查看 Worker 日誌是否有錯誤

#### 4. 任務執行失敗

**症狀**:
- 任務狀態為 `failed`

**解決方法**:
1. 查詢失敗任務: `GET /api/v1/rq/queues/{queue_name}/jobs?status=failed`
2. 查看任務錯誤信息: `job.exc_info`
3. 檢查任務函數邏輯和參數

#### 5. 異步函數執行問題

**症狀**:
```
RuntimeError: This event loop is already running
```

**解決方法**:
- 確保在 Worker 任務函數中使用 `asyncio.new_event_loop()` 和 `loop.run_until_complete()`

### 調試技巧

#### 1. 查看隊列狀態

```bash
# 命令行查詢
./scripts/rq_status.sh

# 或使用 Python
python3 -c "
from database.rq.monitor import get_all_queues_stats
import json
print(json.dumps(get_all_queues_stats(), indent=2))
"
```

#### 2. 查看 Worker 日誌

```bash
tail -f logs/rq_worker_file_processing.log
```

#### 3. 查看任務詳情

```python
from database.rq.queue import get_task_queue

queue = get_task_queue("file_processing")
job = queue.fetch_job("job_id")
print(f"狀態: {job.get_status()}")
print(f"結果: {job.result}")
print(f"錯誤: {job.exc_info}")
```

#### 4. 測試任務函數

```python
# 直接調用任務函數測試
from workers.tasks import process_file_chunking_and_vectorization_task

result = process_file_chunking_and_vectorization_task(
    file_id="test",
    file_path="/path/to/file",
    file_type="text/plain",
    user_id="test_user",
)
print(result)
```

---

## 後續開發建議

### 短期改進（1-2周）

1. **替換 BackgroundTasks 為 RQ**
   - 修改 `api/routers/file_upload.py`
   - 修改 `api/routers/file_management.py`
   - 測試任務提交和執行

2. **實現任務優先級**
   - 添加優先級隊列
   - 實現用戶配額管理

3. **增強監控**
   - 添加任務處理時間統計
   - 實現失敗任務自動告警

### 中期改進（1-2月）

1. **資源管理**
   - 實現 Worker 資源限制（CPU、內存）
   - 添加任務超時管理

2. **任務調度優化**
   - 實現公平調度算法
   - 添加任務去重機制

3. **可視化監控**
   - 集成 RQ Dashboard
   - 創建自定義監控面板

### 長期規劃（3-6月）

1. **混合架構**
   - 支持用戶本地 Worker（可選）
   - 實現任務路由策略

2. **高級功能**
   - 任務依賴管理
   - 任務鏈（Chain）
   - 任務組（Group）

3. **擴展性**
   - 支持多 Redis 實例
   - 實現任務分片
   - 支持任務遷移

---

## 參考資源

### 官方文檔

- **RQ 官方文檔**: https://python-rq.org/
- **RQ Dashboard**: https://github.com/nvie/rq-dashboard
- **Redis 官方文檔**: https://redis.io/docs/

### 項目相關文件

- `database/redis/client.py` - Redis 客戶端實現
- `database/rq/queue.py` - RQ 隊列客戶端
- `database/rq/monitor.py` - 隊列監控工具
- `workers/tasks.py` - Worker 任務函數
- `api/routers/rq_monitor.py` - 監控 API
- `scripts/start_rq_worker.sh` - Worker 啟動腳本
- `scripts/rq_status.sh` - 狀態查詢腳本

### 相關配置

- `.env` - Redis 連接配置
- `docker-compose.yml` - Redis 服務配置

---

## 附錄

### A. Redis Key 命名規範

| 用途 | Key 格式 | TTL | 說明 |
|------|---------|-----|------|
| 上傳進度 | `upload:progress:{file_id}` | 1小時 | 文件上傳進度 |
| 處理狀態 | `processing:status:{file_id}` | 2小時 | 文件處理狀態 |
| JWT 黑名單 | `jwt:blacklist:{token_hash}` | 與 Token 一致 | Token 黑名單 |
| Agent 記憶 | `aam:memory:{key}` | 1小時 | Agent 短期記憶 |
| RQ 隊列 | `rq:queue:{queue_name}` | 永久 | RQ 任務隊列 |
| RQ 任務 | `rq:job:{job_id}` | 根據配置 | RQ 任務數據 |
| RQ Worker | `rq:worker:{worker_name}` | 永久 | Worker 註冊信息 |

### B. 任務狀態說明

| 狀態 | 說明 | 可操作 |
|------|------|--------|
| `queued` | 任務已加入隊列，等待執行 | 可取消 |
| `started` | 任務正在執行中 | 無 |
| `finished` | 任務執行成功 | 可查看結果 |
| `failed` | 任務執行失敗 | 可重試 |
| `deferred` | 任務延遲執行 | 可取消 |
| `scheduled` | 任務已安排執行 | 可取消 |

### C. 環境變數配置

```bash
# Redis 配置
REDIS_HOST=localhost          # Redis 主機
REDIS_PORT=6379               # Redis 端口
REDIS_DB=0                    # Redis 數據庫編號
REDIS_PASSWORD=               # Redis 密碼（可選）
REDIS_URL=redis://localhost:6379/0  # Redis 連接 URL（優先）
```

---

**文檔版本**: 1.0  
**最後更新**: 2025-12-10  
**維護者**: Daniel Chung
