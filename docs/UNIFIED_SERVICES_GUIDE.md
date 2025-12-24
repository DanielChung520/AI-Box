# 統一服務管理指南

**創建日期**: 2025-12-12
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-12

## 📋 概述

所有服務（包括 Worker）現在都統一由 `scripts/start_services.sh` 管理，無需使用多個分散的腳本。

## 🚀 使用方法

### 啟動 Worker

```bash
# 單獨啟動 Worker
./scripts/start_services.sh worker

# 啟動所有服務（包括 Worker）
./scripts/start_services.sh all
```

### 查看服務狀態

```bash
# 查看所有服務狀態（包括 Worker）
./scripts/start_services.sh status
```

### 停止所有服務

```bash
# 停止所有服務（包括 Worker）
./scripts/start_services.sh stop
```

## 📊 可用選項

| 選項 | 說明 |
|------|------|
| `all` | 啟動所有服務（ArangoDB, ChromaDB, Redis, FastAPI, Frontend, Worker） |
| `worker` | 啟動 RQ Worker（後台任務處理） |
| `arangodb` | 啟動 ArangoDB |
| `chromadb` | 啟動 ChromaDB |
| `redis` | 啟動 Redis |
| `fastapi` | 啟動 FastAPI |
| `frontend` | 啟動前端服務 |
| `status` | 檢查所有服務狀態 |
| `stop` | 停止所有服務 |
| `help` | 顯示幫助信息 |

## 🎯 推薦使用方式

### 開發環境

```bash
# 啟動所有服務（包括 Worker）
./scripts/start_services.sh all

# 或只啟動 Worker
./scripts/start_services.sh worker
```

### 生產環境

```bash
# 後台啟動所有服務
nohup ./scripts/start_services.sh all > logs/services.log 2>&1 &

# 或只啟動 Worker
nohup ./scripts/start_services.sh worker > logs/worker.log 2>&1 &
```

## ✅ Worker 功能說明

當使用 `./scripts/start_services.sh worker` 時，會：

1. **自動檢查 Redis**：如果 Redis 未運行，會自動啟動
2. **啟動 Worker Service**：使用 `workers/service.py` 啟動 Worker
3. **監聽所有隊列**：`kg_extraction`, `vectorization`, `file_processing`
4. **啟用監控模式**：自動監控和重啟崩潰的 Worker
5. **日誌記錄**：日誌保存在 `logs/worker_service.log`

## 🔍 驗證 Worker 運行

```bash
# 方法一：使用 status 命令
./scripts/start_services.sh status

# 方法二：檢查進程
ps aux | grep "rq worker"

# 方法三：查看日誌
tail -f logs/worker_service.log
```

## 📝 注意事項

1. **Worker 依賴 Redis**：啟動 Worker 前會自動檢查並啟動 Redis
2. **Worker 日誌**：所有 Worker 輸出都記錄在 `logs/worker_service.log`
3. **停止服務**：使用 `./scripts/start_services.sh stop` 會停止所有服務，包括 Worker

## 🎉 優勢

- ✅ **統一管理**：所有服務由一個腳本管理
- ✅ **自動依賴檢查**：Worker 會自動檢查並啟動 Redis
- ✅ **狀態監控**：`status` 命令可以查看所有服務狀態
- ✅ **一鍵停止**：`stop` 命令可以停止所有服務
- ✅ **無需記憶多個腳本**：只需記住 `start_services.sh`

## 📚 相關文檔

- `docs/TASK_QUEUE_SYSTEM_GUIDE.md` - 完整的任務隊列系統指南
- `docs/WORKER_STARTUP_GUIDE.md` - Worker 啟動詳細指南
