# ArangoDB Web UI 訪問指南

## 功能說明

如何訪問 ArangoDB Web UI 來管理數據庫和執行查詢
創建日期：2025-12-12
創建人：Daniel Chung
最後修改日期：2025-12-12

## 訪問方式

### 默認訪問地址

根據項目配置，ArangoDB Web UI 的默認訪問地址是：

```
http://localhost:8529
```

### 配置說明

從 `database/arangodb/settings.py` 可以看到默認配置：

- **Host**: `localhost` (可通過環境變數 `ARANGODB_HOST` 修改)
- **Port**: `8529` (可通過環境變數 `ARANGODB_PORT` 修改)
- **Protocol**: `http` (可通過環境變數 `ARANGODB_PROTOCOL` 修改)

## 訪問步驟

### 1. 確認 ArangoDB 正在運行

```bash
# 檢查 ArangoDB 是否在運行
curl http://localhost:8529/_api/version

# 或使用 Docker
docker ps | grep arangodb
```

### 2. 打開瀏覽器

在瀏覽器中訪問：

```
http://localhost:8529
```

### 3. 登錄

如果 ArangoDB 設置了認證，需要輸入：

- **Username**: 從環境變數 `ARANGODB_USERNAME` 或配置文件獲取
- **Password**: 從環境變數 `ARANGODB_PASSWORD` 或配置文件獲取

如果沒有設置認證，可能可以直接訪問（取決於 ArangoDB 配置）。

### 4. 使用 Web UI

登錄後，你可以：

- 查看數據庫列表
- 查看集合（Collections）
- 執行 AQL 查詢
- 管理數據
- 查看系統狀態

## 執行 AQL 查詢恢復任務

### 步驟

1. **打開 AQL 編輯器**：
   - 在 Web UI 左側菜單點擊 "Queries" 或 "AQL"
   - 或直接訪問：`http://localhost:8529/_db/ai_box_kg/_admin/aardvark/index.html#query`

2. **選擇數據庫**：
   - 確保選擇了正確的數據庫（通常是 `ai_box_kg`）

3. **執行查詢**：

   **先查看歸檔任務**（可選）：

   ```aql
   FOR task IN user_tasks
       FILTER task.user_id == "daniel@test.com"
       FILTER task.task_status == "archive"
       RETURN {
           _key: task._key,
           task_id: task.task_id,
           title: task.title,
           task_status: task.task_status,
           created_at: task.created_at
       }
   ```

   **批量恢復歸檔任務**：

   ```aql
   FOR task IN user_tasks
       FILTER task.user_id == "daniel@test.com"
       FILTER task.task_status == "archive"
       UPDATE task WITH {
           task_status: "activate",
           updated_at: DATE_ISO8601(DATE_NOW())
       } IN user_tasks
       RETURN {
           task_id: task.task_id,
           title: task.title,
           old_status: "archive",
           new_status: "activate"
       }
   ```

4. **點擊執行**：
   - 點擊 "Execute" 或按 `Ctrl+Enter` (Windows/Linux) / `Cmd+Enter` (Mac)

5. **查看結果**：
   - 查詢結果會顯示在下方
   - 可以看到恢復了多少個任務

## 使用腳本文件

你也可以直接使用項目中的 AQL 文件：

```bash
# 查看 AQL 查詢內容
cat scripts/restore_tasks.aql

# 然後在 Web UI 中複製粘貼執行
```

## 常見問題

### Q1: 無法訪問 <http://localhost:8529>

**可能原因**：

1. ArangoDB 服務未啟動
2. 端口被其他程序占用
3. 防火牆阻止訪問

**解決方法**：

```bash
# 檢查 ArangoDB 是否運行
ps aux | grep arangod

# 或檢查 Docker 容器
docker ps | grep arango

# 檢查端口是否被占用
lsof -i :8529
```

### Q2: 需要認證但不知道用戶名密碼

**解決方法**：

1. 查看環境變數：

   ```bash
   echo $ARANGODB_USERNAME
   echo $ARANGODB_PASSWORD
   ```

2. 查看配置文件：

   ```bash
   cat config/config.json | grep -A 10 arangodb
   ```

3. 查看 `.env` 文件：

   ```bash
   cat .env | grep ARANGODB
   ```

### Q3: 忘記密碼

**解決方法**：

1. 如果是 Docker 部署，可以重置：

   ```bash
   # 停止容器
   docker stop <arangodb-container>

   # 刪除容器（注意：這會刪除數據，除非數據在 volume 中）
   docker rm <arangodb-container>

   # 重新啟動並設置新密碼
   ```

2. 或者使用 ArangoDB 的命令行工具重置

### Q4: 使用 Docker 部署時的訪問

如果 ArangoDB 在 Docker 中運行，確保端口映射正確：

```yaml
# docker-compose.yml 中應該有：
services:
  arangodb:
    ports:
      - "8529:8529"
```

然後訪問：`http://localhost:8529`

## 快速訪問命令

### 在終端中打開瀏覽器

**macOS**:

```bash
open http://localhost:8529
```

**Linux**:

```bash
xdg-open http://localhost:8529
```

**Windows**:

```bash
start http://localhost:8529
```

## 相關文件

- `database/arangodb/settings.py` - ArangoDB 配置
- `scripts/restore_tasks.aql` - 恢復任務的 AQL 查詢
- `../開發過程文件/恢復歸檔任務指南.md` - 恢復歸檔任務指南
