# 恢復歸檔任務指南

## 功能說明

將歸檔的任務狀態重新更新為 activate
創建日期：2025-12-12
創建人：Daniel Chung
最後修改日期：2025-12-12

## 方法一：通過 API 恢復（推薦）

### 前提條件

- API 服務正在運行（<http://localhost:8000）>

### 步驟

1. **使用自動恢復腳本**（無需確認）：

   ```bash
   python3 scripts/auto_restore_tasks.py
   ```

2. **或使用交互式腳本**（需要確認）：

   ```bash
   python3 scripts/quick_restore_tasks.py
   ```

3. **或使用完整功能腳本**：

   ```bash
   # 預覽
   python3 scripts/restore_archived_tasks.py --email daniel@test.com --dry-run

   # 實際執行
   python3 scripts/restore_archived_tasks.py --email daniel@test.com --no-dry-run
   ```

## 方法二：手動通過 API 恢復

### 步驟

1. **登錄獲取 Token**：

   ```bash
   TOKEN=$(curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "daniel@test.com", "password": "any"}' \
     | jq -r '.data.access_token')
   ```

2. **查詢所有任務（包括歸檔的）**：

   ```bash
   curl -X GET "http://localhost:8000/user-tasks?include_archived=true&limit=1000" \
     -H "Authorization: Bearer $TOKEN" \
     | jq '.data.tasks[] | select(.task_status == "archive") | {task_id, title, task_status}'
   ```

3. **恢復單個任務**：

   ```bash
   curl -X PUT "http://localhost:8000/user-tasks/{task_id}" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"task_status": "activate"}'
   ```

4. **批量恢復所有歸檔任務**（使用腳本）：

   ```bash
   # 獲取所有歸檔任務的 task_id
   ARCHIVED_TASK_IDS=$(curl -X GET "http://localhost:8000/user-tasks?include_archived=true&limit=1000" \
     -H "Authorization: Bearer $TOKEN" \
     | jq -r '.data.tasks[] | select(.task_status == "archive") | .task_id')

   # 批量恢復
   for task_id in $ARCHIVED_TASK_IDS; do
     curl -X PUT "http://localhost:8000/user-tasks/$task_id" \
       -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"task_status": "activate"}'
   done
   ```

## 方法三：直接操作數據庫（需要 ArangoDB 認證）

### 前提條件

- ArangoDB 正在運行
- 有正確的數據庫認證信息

### 步驟

1. **使用數據庫腳本**：

   ```bash
   python3 scripts/restore_tasks_db.py
   ```

2. **或手動使用 AQL 查詢**（在 ArangoDB Web UI 中）：

   ```aql
   // 1. 查看歸檔任務
   FOR task IN user_tasks
       FILTER task.user_id == "daniel@test.com"
       FILTER task.task_status == "archive"
       RETURN {
           _key: task._key,
           task_id: task.task_id,
           title: task.title,
           task_status: task.task_status
       }

   // 2. 批量恢復
   FOR task IN user_tasks
       FILTER task.user_id == "daniel@test.com"
       FILTER task.task_status == "archive"
       UPDATE task WITH { task_status: "activate" } IN user_tasks
       RETURN {
           task_id: task.task_id,
           title: task.title,
           task_status: "activate"
       }
   ```

## 快速恢復命令

如果 API 正在運行，最簡單的方式：

```bash
python3 scripts/auto_restore_tasks.py
```

這個腳本會：

1. 自動登錄
2. 查詢所有歸檔任務
3. 批量恢復為 activate 狀態
4. 顯示恢復結果

## 驗證恢復結果

恢復後，可以通過以下方式驗證：

```bash
# 1. 登錄
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "daniel@test.com", "password": "any"}' \
  | jq -r '.data.access_token')

# 2. 查詢任務（不包含歸檔的，應該能看到恢復的任務）
curl -X GET "http://localhost:8000/user-tasks" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data.tasks | length'
```

## 注意事項

1. **備份數據**：恢復前建議備份數據庫
2. **API 服務**：確保 API 服務正在運行
3. **認證信息**：確保使用正確的用戶認證信息
4. **批量操作**：如果任務很多，批量操作可能需要一些時間

## 相關文件

- `scripts/auto_restore_tasks.py` - 自動恢復腳本（推薦）
- `scripts/quick_restore_tasks.py` - 交互式恢復腳本
- `scripts/restore_archived_tasks.py` - 完整功能恢復腳本
- `scripts/restore_tasks_db.py` - 數據庫直接操作腳本
- `api/routers/user_tasks.py` - 任務 API 路由
