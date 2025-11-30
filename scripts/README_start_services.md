# 服務啟動腳本使用說明

## 功能說明

`start_services.sh` 是一個用於啟動 AI-Box 相關服務的腳本，支持：

- ✅ 自動檢查端口占用
- ✅ 自動關閉占用端口的進程並重啟
- ✅ 支持啟動多個服務
- ✅ 服務狀態檢查
- ✅ 停止所有服務

## 使用方法

### 基本用法

```bash
# 顯示幫助信息
./scripts/start_services.sh help

# 檢查服務狀態
./scripts/start_services.sh status

# 啟動所有服務
./scripts/start_services.sh all

# 啟動單個服務
./scripts/start_services.sh fastapi
./scripts/start_services.sh arangodb
./scripts/start_services.sh chromadb
./scripts/start_services.sh mcp

# 啟動多個服務
./scripts/start_services.sh arangodb chromadb fastapi

# 停止所有服務
./scripts/start_services.sh stop
```

## 服務配置

| 服務 | 端口 | 說明 |
|------|------|------|
| ArangoDB | 8529 | 圖數據庫服務 |
| ChromaDB | 8001 | 向量數據庫服務 |
| FastAPI | 8000 | API 網關服務 |
| MCP Server | 8002 | MCP 協議服務器 |

## 注意事項

1. **ArangoDB 和 ChromaDB**:
   - 腳本會嘗試通過 Docker 啟動
   - 如果沒有 Docker 容器，需要手動啟動
   - ArangoDB: `docker run -d -p 8529:8529 -e ARANGO_ROOT_PASSWORD=your_password --name arangodb arangodb/arangodb`
   - ChromaDB: `docker run -d -p 8001:8000 --name chromadb chromadb/chroma`

2. **FastAPI 和 MCP Server**:
   - 需要激活虛擬環境（自動檢測 venv 或 .venv）
   - 需要安裝 uvicorn: `pip install uvicorn`
   - 日誌文件保存在 `logs/` 目錄

3. **端口衝突**:
   - 如果端口已被占用，腳本會自動關閉占用進程
   - 請確保沒有其他重要服務使用相同端口

4. **Ollama 服務**:
   - 本地服務: `localhost:11434` (已配置)
   - 遠程服務: `olm.k84.org` (已配置，不需要端口號)

## 日誌文件

所有服務的日誌文件保存在 `logs/` 目錄：

- `logs/fastapi.log` - FastAPI 服務日誌
- `logs/mcp_server.log` - MCP Server 日誌

## 故障排除

### 服務啟動失敗

1. 檢查虛擬環境是否激活
2. 檢查依賴是否安裝: `pip install -r requirements.txt`
3. 查看日誌文件: `tail -f logs/fastapi.log`

### 端口被占用

腳本會自動處理端口衝突，如果仍有問題：

```bash
# 手動檢查端口占用
lsof -i :8000

# 手動關閉進程
kill -9 <PID>
```

### Docker 容器問題

```bash
# 檢查容器狀態
docker ps -a

# 啟動容器
docker start <container_name>

# 查看容器日誌
docker logs <container_name>
```
