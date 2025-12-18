# Worker 後台任務處理啟動指南

**創建日期**: 2025-12-12
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-12

## 📋 概述

根據目前的系統架構，後台任務處理需要啟動 **Worker 進程**來處理 RQ 任務隊列中的任務。

## 🚀 啟動方式

### 方式一：使用 Worker Service（推薦）⭐

**優點**：
- ✅ 自動監控 Worker 狀態
- ✅ 自動重啟崩潰的 Worker
- ✅ 完整的日誌管理
- ✅ 適合生產環境

**啟動命令**：

```bash
# 基本啟動（監聽所有隊列）
./scripts/start_worker_service.sh

# 啟動並啟用監控模式（推薦）
./scripts/start_worker_service.sh --monitor

# 指定監聽的隊列
./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    --name my_worker

# 後台運行（生產環境）
nohup ./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    > logs/worker_service.log 2>&1 &
```

**或使用 Python 模組**：

```bash
# 基本啟動
python -m workers.service --queues kg_extraction vectorization file_processing

# 啟動並啟用監控（推薦）
python -m workers.service \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    --check-interval 30 \
    --name my_worker

# 後台運行
nohup python -m workers.service \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    > logs/worker_service.log 2>&1 &
```

### 方式二：使用簡單的 RQ Worker 腳本

**優點**：
- ✅ 簡單直接
- ✅ 適合開發環境

**缺點**：
- ❌ 沒有自動監控和重啟功能
- ❌ 崩潰後需要手動重啟

**啟動命令**：

```bash
# 啟動單個隊列的 Worker
./scripts/start_rq_worker.sh kg_extraction

# 啟動多個隊列的 Worker（需要修改腳本）
./scripts/start_rq_worker.sh vectorization
./scripts/start_rq_worker.sh file_processing
```

**或直接使用 RQ CLI**：

```bash
# 激活虛擬環境
source venv/bin/activate

# 啟動單個隊列
rq worker kg_extraction

# 啟動多個隊列
rq worker kg_extraction vectorization file_processing
```

## 📊 隊列說明

系統中定義了三個主要隊列：

| 隊列名稱 | 用途 | 需要啟動 Worker |
|---------|------|----------------|
| `kg_extraction` | 知識圖譜提取（圖譜重新生成） | ✅ 是 |
| `vectorization` | 向量化處理（向量重新生成） | ✅ 是 |
| `file_processing` | 完整文件處理（文件上傳） | ✅ 是 |

## 🎯 推薦配置

### 開發環境

**啟動一個 Worker 監聽所有隊列**：

```bash
./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    --name dev_worker
```

### 生產環境

**啟動多個 Worker（每個監聽不同隊列）**：

```bash
# Worker 1: 處理圖譜提取
nohup ./scripts/start_worker_service.sh \
    --queues kg_extraction \
    --monitor \
    --name worker_kg \
    > logs/worker_kg.log 2>&1 &

# Worker 2: 處理向量化
nohup ./scripts/start_worker_service.sh \
    --queues vectorization \
    --monitor \
    --name worker_vec \
    > logs/worker_vec.log 2>&1 &

# Worker 3: 處理文件處理
nohup ./scripts/start_worker_service.sh \
    --queues file_processing \
    --monitor \
    --name worker_file \
    > logs/worker_file.log 2>&1 &
```

**或啟動一個 Worker 監聽所有隊列**：

```bash
nohup ./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    --name worker_all \
    > logs/worker_all.log 2>&1 &
```

## ✅ 啟動前檢查清單

在啟動 Worker 之前，請確保：

- [ ] **Redis 服務正在運行**
  ```bash
  redis-cli ping
  # 應該返回 PONG
  ```

- [ ] **環境變數已配置**
  ```bash
  # 檢查 .env 文件中的 Redis 配置
  cat .env | grep REDIS
  ```

- [ ] **虛擬環境已激活**（如果使用腳本）
  ```bash
  source venv/bin/activate
  ```

- [ ] **依賴已安裝**
  ```bash
  pip install rq
  ```

## 🔍 驗證 Worker 是否運行

### 方法一：檢查進程

```bash
ps aux | grep "rq worker"
# 或
ps aux | grep "workers.service"
```

### 方法二：使用 RQ 命令

```bash
./scripts/rq_info.sh
```

### 方法三：使用 API

```bash
curl http://localhost:8000/api/v1/rq/workers
```

### 方法四：查看日誌

```bash
tail -f logs/rq_worker_*.log
# 或
tail -f logs/worker_service.log
```

## 🛑 停止 Worker

### 優雅停止

```bash
# 查找 Worker 進程
ps aux | grep "rq worker"

# 發送 SIGTERM 信號
kill -TERM {pid}

# 或停止整個進程組
kill -TERM -{pgid}
```

### 強制停止

```bash
# 查找 Worker 進程
ps aux | grep "rq worker"

# 強制終止
kill -9 {pid}
```

## 📝 日誌位置

- **Worker Service 日誌**: `logs/worker_service.log`
- **RQ Worker 日誌**: `logs/rq_worker_{queue_name}.log`
- **FastAPI 日誌**: `logs/fastapi.log`

## 🎛️ 可選：啟動 RQ Dashboard（監控界面）

如果需要 Web 界面監控任務隊列：

```bash
# 啟動 Dashboard（默認端口 9181）
./scripts/rq_dashboard.sh

# 指定端口
./scripts/rq_dashboard.sh --port 9182
```

訪問：http://localhost:9181

## 📚 相關文檔

- `docs/TASK_QUEUE_SYSTEM_GUIDE.md` - 完整的任務隊列系統指南
- `scripts/rq_commands.md` - RQ 命令參考

## ⚠️ 常見問題

### Q: Worker 啟動後立即退出？

**A**: 檢查：
1. Redis 是否運行：`redis-cli ping`
2. 依賴是否安裝：`python -c "import rq"`
3. 查看日誌：`tail -f logs/rq_worker_*.log`

### Q: 任務一直處於 queued 狀態？

**A**: 檢查：
1. Worker 是否運行：`ps aux | grep "rq worker"`
2. Worker 監聽的隊列名稱是否匹配
3. Redis 連接是否正常

### Q: 如何查看 Worker 狀態？

**A**: 使用以下命令：
```bash
./scripts/rq_info.sh
./scripts/rq_status.sh
curl http://localhost:8000/api/v1/rq/workers
```

## 🎯 總結

**推薦啟動方式**：

```bash
# 開發環境
./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization file_processing \
    --monitor

# 生產環境
nohup ./scripts/start_worker_service.sh \
    --queues kg_extraction vectorization file_processing \
    --monitor \
    > logs/worker_service.log 2>&1 &
```

這樣可以確保：
- ✅ Worker 自動監控和重啟
- ✅ 完整的日誌記錄
- ✅ 處理所有類型的任務（圖譜、向量、文件處理）
