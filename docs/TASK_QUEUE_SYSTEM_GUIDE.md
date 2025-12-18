# 任務隊列系統完整指南

**創建日期**: 2025-12-12
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-12

## 📋 目錄

1. [系統概述](#系統概述)
2. [架構說明](#架構說明)
3. [Redis 服務](#redis-服務)
4. [RQ 任務隊列](#rq-任務隊列)
5. [Worker 服務](#worker-服務)
6. [使用指南](#使用指南)
7. [監控與管理](#監控與管理)
8. [最佳實踐](#最佳實踐)
9. [故障排查](#故障排查)

---

## 系統概述

### 核心組件

AI-Box 的任務隊列系統由三個核心組件組成：

1. **Redis** - 數據存儲和緩存服務
2. **RQ (Redis Queue)** - Python 任務隊列庫
3. **Worker** - 後台任務執行進程

### 工作流程

```
┌─────────────────────────────────────────────────────────┐
│  前端/API 請求                                           │
│  (文件上傳、圖譜重新生成等)                                │
└──────────────────┬──────────────────────────────────────┘
                   │ 1. 提交任務
                   ↓
┌─────────────────────────────────────────────────────────┐
│  FastAPI API Server                                     │
│  (api/routers/file_management.py)                       │
│  - queue.enqueue() 將任務放入隊列                        │
│  - 立即返回響應（不等待任務完成）                          │
└──────────────────┬──────────────────────────────────────┘
                   │ 2. 存儲任務
                   ↓
┌─────────────────────────────────────────────────────────┐
│  Redis (數據存儲)                                        │
│  - 存儲任務隊列數據                                       │
│  - 存儲任務狀態和結果                                     │
│  - Key 格式: rq:queue:{queue_name}                     │
└──────────────────┬──────────────────────────────────────┘
                   │ 3. Worker 拉取任務
                   ↓
┌─────────────────────────────────────────────────────────┐
│  RQ Worker 進程                                         │
│  (workers/service.py)                                   │
│  - 持續監聽 Redis 隊列                                    │
│  - 從隊列取出任務                                         │
│  - 執行任務函數 (workers/tasks.py)                      │
│  - 更新任務狀態                                           │
└──────────────────┬──────────────────────────────────────┘
                   │ 4. 執行任務
                   ↓
┌─────────────────────────────────────────────────────────┐
│  任務處理邏輯                                            │
│  - 文件分塊和向量化                                       │
│  - 知識圖譜提取 (NER-RE-RT)                              │
│  - 數據庫寫入                                             │
└─────────────────────────────────────────────────────────┘
```

---

## 架構說明

### 組件關係圖

```
┌─────────────────────────────────────────────────────────────┐
│                    Redis 服務層                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  任務隊列存儲 (rq:queue:*)                            │  │
│  │  任務數據存儲 (rq:job:*)                              │  │
│  │  Worker 註冊 (rq:worker:*)                            │  │
│  │  文件處理狀態 (processing:status:*)                    │  │
│  │  JWT 黑名單 (jwt:blacklist:*)                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↑                              ↑
         │                              │
┌────────┴────────┐            ┌────────┴────────┐
│  RQ Queue      │            │  RQ Worker      │
│  (客戶端)       │            │  (執行者)        │
│                 │            │                 │
│ database/rq/    │            │ workers/service │
│ queue.py        │            │ workers/tasks.py│
└─────────────────┘            └─────────────────┘
         ↑                              ↑
         │                              │
┌────────┴────────┐            ┌────────┴────────┐
│  FastAPI API    │            │  Worker Service │
│  (任務提交)      │            │  (進程管理)      │
└─────────────────┘            └─────────────────┘
```

### 代碼結構

```
AI-Box/
├── database/
│   ├── redis/
│   │   └── client.py          # Redis 客戶端（單例模式）
│   └── rq/
│       ├── queue.py           # RQ 隊列客戶端
│       └── monitor.py         # 隊列監控工具
├── workers/
│   ├── service.py             # Worker Service 管理
│   └── tasks.py               # Worker 任務函數
├── api/
│   └── routers/
│       ├── file_management.py # 任務提交（enqueue）
│       └── rq_monitor.py      # 監控 API
└── scripts/
    ├── start_worker_service.sh  # Worker 啟動腳本
    ├── rq_info.sh              # 隊列信息查詢
    └── rq_dashboard.sh         # RQ Dashboard 啟動
```

---

## Redis 服務

### 功能概述

Redis 在系統中承擔多個角色：

1. **任務隊列存儲** - RQ 使用 Redis 存儲任務隊列
2. **文件處理狀態追蹤** - 實時追蹤文件處理進度
3. **JWT Token 黑名單** - 管理已登出的 Token
4. **Agent 記憶管理** - 為 Agent 提供短期記憶存儲

### 配置

**環境變數** (`.env`):

```bash
# Redis 連接配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0
```

**Redis 客戶端** (`database/redis/client.py`):

```python
from database.redis import get_redis_client

# 獲取 Redis 客戶端（單例模式）
redis_client = get_redis_client()

# 使用 Redis
redis_client.set("key", "value")
value = redis_client.get("key")
```

### Redis Key 命名規範

| Key 格式 | 用途 | TTL |
|---------|------|-----|
| `rq:queue:{queue_name}` | RQ 任務隊列 | 永久 |
| `rq:job:{job_id}` | RQ 任務數據 | 永久 |
| `rq:worker:{worker_name}` | Worker 註冊信息 | 永久 |
| `processing:status:{file_id}` | 文件處理狀態 | 2小時 |
| `upload:progress:{file_id}` | 文件上傳進度 | 1小時 |
| `jwt:blacklist:{token_hash}` | JWT 黑名單 | 與 Token 過期時間一致 |
| `aam:memory:{key}` | Agent 記憶 | 1小時 |

### 重要注意事項

⚠️ **RQ 需要二進制模式**：
- RQ 使用 `pickle` 序列化任務數據（二進制）
- Redis 客戶端必須設置 `decode_responses=False`
- 系統中為 RQ 創建了獨立的 Redis 連接（`database/rq/queue.py`）

---

## RQ 任務隊列

### 隊列定義

系統中定義了三個主要隊列：

| 隊列名稱 | 用途 | 處理任務 | 使用場景 |
|---------|------|---------|---------|
| `file_processing` | 文件處理隊列 | 分塊 + 向量化 + 圖譜提取 | 文件上傳 |
| `vectorization` | 向量化專用隊列 | 僅向量化處理 | 向量重新生成 |
| `kg_extraction` | 知識圖譜提取專用隊列 | 僅圖譜提取 | 圖譜重新生成 |

### 隊列客戶端 (`database/rq/queue.py`)

**功能**:
- 提供 `get_task_queue()` 函數獲取隊列實例（單例模式）
- 封裝 Redis 連接管理（二進制模式）
- 支持多個隊列實例

**使用示例**:

```python
from database.rq.queue import (
    get_task_queue,
    FILE_PROCESSING_QUEUE,
    VECTORIZATION_QUEUE,
    KG_EXTRACTION_QUEUE,
)

# 獲取隊列實例
queue = get_task_queue(KG_EXTRACTION_QUEUE)

# 提交任務
job = queue.enqueue(
    process_kg_extraction_only_task,
    file_id=file_id,
    file_path=file_path,
    file_type=file_type,
    user_id=user_id,
    force_rechunk=False,
)

# 獲取任務 ID
job_id = job.id
```

### 任務提交流程

**在 API 中提交任務** (`api/routers/file_management.py`):

```python
from database.rq.queue import get_task_queue, KG_EXTRACTION_QUEUE
from workers.tasks import process_kg_extraction_only_task

# 獲取隊列
queue = get_task_queue(KG_EXTRACTION_QUEUE)

# 提交任務
job = queue.enqueue(
    process_kg_extraction_only_task,
    file_id=file_id,
    file_path=file_path,
    file_type=file_metadata.file_type,
    user_id=current_user.user_id,
    force_rechunk=False,
)

# 立即返回響應（不等待任務完成）
return APIResponse.success(
    data={
        "file_id": file_id,
        "type": "graph",
        "status": "queued",
        "job_id": job.id,
    },
    message="圖譜重新生成已提交到隊列，處理將在後台進行",
)
```

### 任務狀態

任務在 Redis 中的狀態流轉：

```
queued (等待中)
  ↓ Worker 取出任務
started (執行中)
  ↓ 任務完成
finished (已完成) 或 failed (失敗)
```

---

## Worker 服務

### Worker 架構

Worker 系統包含兩個層次：

1. **Worker Service** (`workers/service.py`) - 進程管理層
   - 啟動和管理 Worker 進程
   - 監控 Worker 狀態
   - 自動重啟崩潰的 Worker

2. **Worker 進程** (`rq worker`) - 任務執行層
   - 監聽 Redis 隊列
   - 執行任務函數
   - 更新任務狀態

### Worker Service (`workers/service.py`)

**功能**:
- ✅ 自動啟動 Worker
- ✅ 進程監控（檢測崩潰）
- ✅ 自動重啟（可配置最大重啟次數）
- ✅ 日誌管理
- ✅ 優雅停止

**使用方式**:

```python
from workers.service import WorkerService

# 創建 Worker Service
service = WorkerService(
    queue_names=["kg_extraction", "vectorization"],
    worker_name="my_worker",
    redis_url="redis://localhost:6379/0",
)

# 啟動 Worker
if service.start():
    print(f"Worker 已啟動，PID: {service.process.pid}")

    # 啟用監控（自動重啟）
    service.monitor(check_interval=30)
```

### Worker 任務函數 (`workers/tasks.py`)

**定義的任務函數**:

1. **`process_file_chunking_and_vectorization_task()`**
   - 處理文件分塊和向量化
   - 隊列: `file_processing`

2. **`process_vectorization_only_task()`**
   - 僅處理向量化
   - 隊列: `vectorization`

3. **`process_kg_extraction_only_task()`**
   - 僅處理知識圖譜提取
   - 隊列: `kg_extraction`
   - 包含完整的 NER-RE-RT 流程

**任務函數特點**:
- 同步函數（RQ Worker 要求）
- 內部使用 `asyncio.new_event_loop()` 運行異步邏輯
- 包含錯誤處理和日誌記錄

**示例**:

```python
def process_kg_extraction_only_task(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
    force_rechunk: bool = False,
) -> dict:
    """處理知識圖譜提取任務"""
    try:
        from api.routers.file_upload import process_kg_extraction_only

        # 創建事件循環運行異步函數
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                process_kg_extraction_only(
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=user_id,
                    force_rechunk=force_rechunk,
                )
            )
            return {"success": True, "file_id": file_id}
        finally:
            loop.close()
    except Exception as e:
        logger.error("Failed to process KG extraction", ...)
        return {"success": False, "file_id": file_id, "error": str(e)}
```

### 啟動 Worker

**方法一：使用 Python 模組（推薦）**

```bash
# 基本啟動（不監控）
python -m workers.service --queues kg_extraction vectorization

# 啟動並啟用監控模式（自動重啟）
python -m workers.service \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    --check-interval 30 \
    --name my_worker
```

**方法二：使用 Shell 腳本**

```bash
# 基本啟動
./scripts/start_worker_service.sh

# 啟動並啟用監控
./scripts/start_worker_service.sh --monitor

# 指定隊列和 Worker 名稱
./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization \
    --name my_worker \
    --monitor \
    --check-interval 60
```

**方法三：使用 RQ CLI（簡單模式）**

```bash
# 啟動單個隊列的 Worker
rq worker kg_extraction

# 啟動多個隊列的 Worker
rq worker kg_extraction vectorization file_processing
```

### 監控模式

啟用監控模式後，Worker Service 會：

1. **定期檢查**：每 30 秒（可配置）檢查一次 Worker 是否還在運行
2. **自動重啟**：如果發現 Worker 崩潰，自動重啟
3. **重啟限制**：最多重啟 10 次（可配置），避免無限重啟
4. **重啟延遲**：重啟前等待 5 秒（可配置），避免頻繁重啟

**配置參數**:

```python
service.max_restarts = 10      # 最大重啟次數
service.restart_delay = 5      # 重啟延遲（秒）
service.monitor(check_interval=30)  # 檢查間隔（秒）
```

---

## 使用指南

### 1. 提交任務

**在 API 路由中提交任務**:

```python
from database.rq.queue import get_task_queue, KG_EXTRACTION_QUEUE
from workers.tasks import process_kg_extraction_only_task

@router.post("/files/{file_id}/regenerate")
async def regenerate_file_data(...):
    # 獲取隊列
    queue = get_task_queue(KG_EXTRACTION_QUEUE)

    # 提交任務
    job = queue.enqueue(
        process_kg_extraction_only_task,
        file_id=file_id,
        file_path=file_path,
        file_type=file_metadata.file_type,
        user_id=current_user.user_id,
        force_rechunk=False,
    )

    # 立即返回（不等待任務完成）
    return APIResponse.success(
        data={"job_id": job.id, "status": "queued"},
        message="任務已提交到隊列",
    )
```

### 2. 查詢任務狀態

**使用 RQ API**:

```python
from database.rq.queue import get_task_queue

queue = get_task_queue(KG_EXTRACTION_QUEUE)
job = queue.fetch_job(job_id)

print(job.get_status())  # queued, started, finished, failed
print(job.result)        # 任務結果（如果已完成）
```

**使用監控 API**:

```bash
# 獲取所有隊列統計
GET /api/v1/rq/queues/stats

# 獲取特定隊列的任務列表
GET /api/v1/rq/queues/{queue_name}/jobs?limit=10

# 獲取 Worker 信息
GET /api/v1/rq/workers
```

### 3. 啟動 Worker

**開發環境**:

```bash
# 前台運行，方便查看日誌
python -m workers.service --queues kg_extraction
```

**生產環境**:

```bash
# 後台運行，啟用監控
nohup python -m workers.service \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    --check-interval 30 \
    > logs/worker_service.log 2>&1 &
```

### 4. 停止 Worker

**優雅停止**:

```bash
# 查找 Worker 進程
ps aux | grep "rq worker"

# 發送 SIGTERM 信號
kill -TERM {pid}

# 或停止整個進程組
kill -TERM -{pgid}
```

**使用 Python API**:

```python
service.stop()  # 優雅停止
```

---

## 監控與管理

### 1. 命令行工具

**查看隊列信息** (`scripts/rq_info.sh`):

```bash
./scripts/rq_info.sh

# 查看特定隊列
./scripts/rq_info.sh kg_extraction
```

**查看 Worker 狀態** (`scripts/rq_status.sh`):

```bash
./scripts/rq_status.sh
```

### 2. RQ Dashboard

**啟動 Dashboard** (`scripts/rq_dashboard.sh`):

```bash
# 使用默認端口 9181
./scripts/rq_dashboard.sh

# 指定端口
./scripts/rq_dashboard.sh --port 9182
```

**訪問**: http://localhost:9181

**功能**:
- 查看所有隊列和任務
- 查看 Worker 狀態
- 查看任務詳情和錯誤信息
- 重試失敗的任務

### 3. API 監控接口

**隊列統計**:

```bash
GET /api/v1/rq/queues/stats

# 響應
{
  "success": true,
  "data": {
    "kg_extraction": {
      "queued": 3,
      "started": 0,
      "finished": 10,
      "failed": 1
    },
    ...
  }
}
```

**任務列表**:

```bash
GET /api/v1/rq/queues/kg_extraction/jobs?limit=10&status=queued

# 響應
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "xxx",
        "status": "queued",
        "file_id": "xxx",
        "user_id": "xxx",
        "created_at": "2025-12-12T12:00:00Z"
      },
      ...
    ],
    "count": 3
  }
}
```

**Worker 信息**:

```bash
GET /api/v1/rq/workers

# 響應
{
  "success": true,
  "data": {
    "workers": [
      {
        "name": "rq_worker_12345",
        "queues": ["kg_extraction"],
        "state": "idle",
        "current_job": null
      },
      ...
    ]
  }
}
```

### 4. 日誌管理

**Worker 日誌**:

```bash
# 實時查看日誌
tail -f logs/rq_worker_*.log

# 查看最近的日誌
tail -n 100 logs/rq_worker_*.log

# 搜索錯誤
grep -i error logs/rq_worker_*.log
```

**API 日誌**:

```bash
# FastAPI 日誌
tail -f logs/fastapi.log
```

---

## 最佳實踐

### 1. 任務設計

✅ **推薦**:
- 任務函數應該是純函數（無副作用）
- 任務參數應該可以被 pickle 序列化
- 任務應該有明確的錯誤處理
- 長時間運行的任務應該定期更新進度

❌ **避免**:
- 在任務函數中直接使用全局變量
- 任務函數依賴外部狀態
- 任務函數執行時間過長（超過 1 小時）

### 2. Worker 部署

✅ **生產環境**:
- 使用 Worker Service 並啟用監控模式
- 為不同隊列啟動獨立的 Worker
- 使用 `nohup` 或 `systemd` 在後台運行
- 設置適當的日誌輪轉

❌ **避免**:
- 在生產環境中不使用監控模式
- 多個 Worker 監聽同一個隊列（除非需要並行處理）
- Worker 進程直接在前台運行

### 3. 隊列選擇

✅ **推薦**:
- 根據任務類型選擇合適的隊列
- 圖譜重新生成使用 `kg_extraction` 隊列
- 向量重新生成使用 `vectorization` 隊列
- 完整文件處理使用 `file_processing` 隊列

### 4. 錯誤處理

✅ **推薦**:
- 任務函數應該捕獲所有異常
- 記錄詳細的錯誤日誌
- 返回明確的錯誤信息
- 失敗的任務應該可以重試

### 5. 性能優化

✅ **推薦**:
- 根據任務量調整 Worker 數量
- 使用多個 Worker 並行處理任務
- 監控 Redis 內存使用
- 定期清理完成的任務

---

## 故障排查

### 1. Worker 無法啟動

**症狀**: Worker 啟動失敗或立即退出

**檢查步驟**:

1. **檢查 Redis 連接**:
   ```bash
   redis-cli ping
   # 應該返回 PONG
   ```

2. **檢查依賴**:
   ```bash
   python -c "import rq"
   # 應該沒有錯誤
   ```

3. **檢查日誌**:
   ```bash
   tail -f logs/rq_worker_*.log
   ```

4. **檢查環境變數**:
   ```bash
   echo $REDIS_URL
   ```

### 2. 任務一直處於 queued 狀態

**症狀**: 任務提交成功，但一直不執行

**可能原因**:
- Worker 沒有運行
- Worker 監聽的隊列名稱不匹配
- Redis 連接問題

**解決方法**:

1. **檢查 Worker 是否運行**:
   ```bash
   ps aux | grep "rq worker"
   ```

2. **檢查 Worker 監聽的隊列**:
   ```bash
   ./scripts/rq_info.sh
   ```

3. **確認隊列名稱匹配**:
   - 任務提交的隊列名稱
   - Worker 監聽的隊列名稱
   - 必須完全一致

### 3. Worker 頻繁重啟

**症狀**: Worker 不斷重啟，無法穩定運行

**可能原因**:
- 任務函數有錯誤
- 資源不足（內存、CPU）
- Redis 連接不穩定

**解決方法**:

1. **查看日誌**:
   ```bash
   tail -f logs/rq_worker_*.log
   ```

2. **檢查系統資源**:
   ```bash
   top
   free -h
   ```

3. **檢查 Redis**:
   ```bash
   redis-cli info
   ```

4. **減少 Worker 數量**:
   - 如果多個 Worker 競爭資源，減少 Worker 數量

### 4. 任務執行失敗

**症狀**: 任務狀態為 `failed`

**檢查步驟**:

1. **查看任務詳情**:
   ```bash
   # 使用 RQ Dashboard
   # 或使用 API
   GET /api/v1/rq/queues/{queue_name}/jobs/{job_id}
   ```

2. **查看錯誤信息**:
   - RQ Dashboard 會顯示完整的錯誤堆棧
   - 日誌文件中也會記錄錯誤

3. **重試任務**:
   ```bash
   # 使用 RQ Dashboard 重試
   # 或重新提交任務
   ```

### 5. Redis 連接錯誤

**症狀**: `redis.exceptions.ConnectionError` 或 `ReadOnlyError`

**解決方法**:

1. **檢查 Redis 服務**:
   ```bash
   redis-cli ping
   ```

2. **檢查 Redis 配置**:
   - 確認 Redis 不是 slave 模式
   - 檢查 Redis 內存限制
   - 檢查網絡連接

3. **重啟 Redis**:
   ```bash
   # 如果使用 Docker
   docker restart redis

   # 如果使用系統服務
   sudo systemctl restart redis
   ```

### 6. 任務序列化錯誤

**症狀**: `pickle.PicklingError` 或 `TypeError: can't pickle`

**原因**: 任務參數包含不可序列化的對象

**解決方法**:
- 確保任務參數都是基本類型（str, int, dict, list）
- 避免傳遞文件對象、數據庫連接等不可序列化的對象
- 使用 ID 或路徑代替對象引用

---

## 總結

任務隊列系統是 AI-Box 的核心組件，提供了：

- ✅ **異步任務處理**：API 快速響應，任務在後台執行
- ✅ **可靠性**：任務持久化，Worker 崩潰不丟失任務
- ✅ **可擴展性**：可以啟動多個 Worker 並行處理
- ✅ **監控能力**：完整的監控和管理工具
- ✅ **自動恢復**：Worker Service 自動重啟崩潰的 Worker

通過合理使用任務隊列系統，可以大大提高系統的性能和可靠性。

---

## 相關文件

- `database/redis/client.py` - Redis 客戶端
- `database/rq/queue.py` - RQ 隊列客戶端
- `database/rq/monitor.py` - 隊列監控工具
- `workers/service.py` - Worker Service 管理
- `workers/tasks.py` - Worker 任務函數
- `api/routers/rq_monitor.py` - 監控 API
- `scripts/start_worker_service.sh` - Worker 啟動腳本
