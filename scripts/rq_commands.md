# RQ 命令使用指南

## 問題：無法執行 rq 命令

**原因**：`rq` 和 `rq-dashboard` 命令安裝在虛擬環境中，需要先激活虛擬環境。

## 解決方案

### 方法一：使用提供的腳本（推薦）

```bash
# 查看隊列信息
./scripts/rq_info.sh

# 查看指定隊列
./scripts/rq_info.sh kg_extraction

# 啟動 RQ Dashboard
./scripts/rq_dashboard.sh
```

### 方法二：手動激活虛擬環境

```bash
# 1. 進入項目目錄
cd /Users/daniel/GitHub/AI-Box

# 2. 激活虛擬環境
source venv/bin/activate

# 3. 執行 RQ 命令
rq info
rq info kg_extraction
rq-dashboard --redis-url redis://localhost:6379/0 --port 9181
```

### 方法三：使用 Python 模組方式

```bash
# 查看隊列信息（需要激活虛擬環境）
python -m rq.cli info

# 啟動 Worker
python -m rq.cli worker kg_extraction vectorization file_processing
```

## 常用命令

### 查看隊列信息
```bash
./scripts/rq_info.sh                    # 查看所有隊列
./scripts/rq_info.sh kg_extraction      # 查看指定隊列
```

### 啟動 RQ Dashboard
```bash
./scripts/rq_dashboard.sh               # 使用默認配置
./scripts/rq_dashboard.sh --port 9182  # 指定端口
```

### 啟動 Worker
```bash
# 方法一：使用腳本（如果存在）
./scripts/start_rq_worker.sh

# 方法二：手動啟動
source venv/bin/activate
python -m rq.cli worker kg_extraction vectorization file_processing
```

## 注意事項

1. **虛擬環境**：所有 RQ 相關命令都需要在虛擬環境中執行
2. **Redis 連接**：確保 Redis 服務正在運行
3. **端口衝突**：如果 9181 端口被占用，可以使用 `--port` 參數指定其他端口
