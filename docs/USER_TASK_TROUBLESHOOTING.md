# 用戶任務問題排查指南

## 功能說明
排查為什麼使用 daniel@test.com 登錄時看不到之前創建的任務
創建日期：2025-12-12
創建人：Daniel Chung
最後修改日期：2025-12-12

## 問題描述

使用 `daniel@test.com` 登錄時，之前創建的示範任務都不見了。

## 問題原因

### User ID 生成邏輯

在 `api/routers/auth.py` 第 80 行，`user_id` 的生成邏輯是：

```python
user_id = username if "@" in username else f"user_{username}"
```

這意味著：
- 如果 `username` 是 email（包含 `@`），則 `user_id = username`（即 email 本身）
- 如果 `username` 不是 email，則 `user_id = f"user_{username}"`

對於 `daniel@test.com`，`user_id` 應該是 `daniel@test.com`。

### 任務查詢邏輯

在 `api/routers/user_tasks.py` 第 68-72 行，任務查詢使用 `current_user.user_id`：

```python
tasks = service.list(
    user_id=current_user.user_id,
    limit=limit,
    offset=offset,
)
```

這意味著**任務是根據 `user_id` 進行隔離的**。只有 `user_id` 匹配的任務才會顯示。

### 可能的原因

1. **之前創建任務時使用了不同的 user_id**
   - 可能使用了 `dev_user`（開發模式）
   - 可能使用了其他格式的 `user_id`
   - 可能使用了不同的 email

2. **User ID 格式不一致**
   - 之前可能使用 `user_daniel` 而不是 `daniel@test.com`
   - 或者使用了其他格式

## 診斷步驟

### 1. 運行診斷腳本

```bash
# 診斷 daniel@test.com 的任務問題
python3 scripts/diagnose_user_tasks.py daniel@test.com
```

這個腳本會：
- 顯示預期的 `user_id`（`daniel@test.com`）
- 列出所有匹配的任務
- 列出所有不匹配的任務（按 `user_id` 分組）
- 提供修復建議

### 2. 手動查詢數據庫

如果腳本無法運行（需要 ArangoDB 認證），可以通過 API 查詢：

```bash
# 1. 登錄獲取 token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "daniel@test.com", "password": "any"}' \
  | jq -r '.data.access_token')

# 2. 查詢當前用戶的任務
curl -X GET http://localhost:8000/user-tasks \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'
```

## 解決方案

### 方案 1：修復現有任務的 user_id（推薦）

如果之前的任務應該屬於 `daniel@test.com`，可以運行修復腳本：

```bash
# 1. 先預覽（dry-run）
python3 scripts/fix_user_tasks.py --email daniel@test.com --dry-run

# 2. 如果預覽結果正確，實際執行修復
python3 scripts/fix_user_tasks.py --email daniel@test.com --no-dry-run

# 3. 如果只想修復特定 user_id 的任務
python3 scripts/fix_user_tasks.py \
  --email daniel@test.com \
  --old-user-id dev_user \
  --no-dry-run
```

### 方案 2：手動更新任務

如果需要手動更新，可以使用 ArangoDB 的 AQL 查詢：

```aql
// 1. 查看需要修復的任務
FOR task IN user_tasks
    FILTER task.user_id == "dev_user"  // 或其他舊的 user_id
    RETURN {
        _key: task._key,
        task_id: task.task_id,
        user_id: task.user_id,
        title: task.title
    }

// 2. 更新任務的 user_id（需要刪除舊文檔並創建新文檔，因為 _key 包含 user_id）
// 注意：這是一個複雜操作，建議使用修復腳本
```

### 方案 3：重新創建任務

如果任務不重要，可以：
1. 刪除舊任務
2. 使用正確的 `user_id` 重新創建

## 預防措施

### 1. 統一 User ID 格式

確保所有地方都使用相同的 `user_id` 生成邏輯：

```python
def get_user_id_from_email(email: str) -> str:
    """根據 email 生成 user_id（統一邏輯）"""
    return email if "@" in email else f"user_{email}"
```

### 2. 在創建任務時驗證

在 `api/routers/user_tasks.py` 的 `create_user_task` 函數中，已經有驗證邏輯：

```python
# 確保請求體中的 user_id 與當前用戶匹配
if request_body.user_id and request_body.user_id != current_user.user_id:
    return APIResponse.error(
        message="User ID mismatch",
        status_code=status.HTTP_403_FORBIDDEN,
    )

# 使用當前用戶的 user_id（如果請求體中沒有提供，自動填充）
if not request_body.user_id:
    request_body.user_id = current_user.user_id
```

這確保了任務總是使用當前認證用戶的 `user_id`。

### 3. 添加日誌記錄

在任務創建和查詢時記錄 `user_id`，方便排查問題：

```python
logger.info(
    "Task created",
    task_id=task.task_id,
    user_id=current_user.user_id,
    email=current_user.email,
)
```

## 常見問題

### Q1: 為什麼會出現 user_id 不匹配？

**A:** 可能的原因：
1. 之前使用開發模式（`dev_user`）創建了任務
2. 使用了不同的 email 登錄
3. 手動修改了數據庫中的 `user_id`

### Q2: 如何確認當前登錄用戶的 user_id？

**A:** 可以調用 `/auth/me` API：

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data.user_id'
```

### Q3: 修復腳本會影響其他用戶的任務嗎？

**A:** 不會。修復腳本只會更新指定 `user_id` 的任務，不會影響其他用戶。

### Q4: 如果修復後仍然看不到任務怎麼辦？

**A:** 檢查以下幾點：
1. 確認任務的 `task_status` 不是 `archive`（歸檔的任務不會顯示）
2. 檢查任務是否真的存在於數據庫中
3. 確認 API 返回的任務列表是否正確
4. 檢查前端是否有過濾邏輯

## 相關文件

- `api/routers/auth.py` - 用戶認證和 user_id 生成
- `api/routers/user_tasks.py` - 任務查詢邏輯
- `services/api/services/user_task_service.py` - 任務服務
- `scripts/diagnose_user_tasks.py` - 診斷腳本
- `scripts/fix_user_tasks.py` - 修復腳本

## 更新：2025-12-12

### 問題：任務被歸檔導致看不到

如果任務的 `task_status` 被設置為 `archive`，默認情況下不會在任務列表中顯示。

**解決方案**：

1. **通過 API 查詢歸檔任務**：
   ```bash
   # 查詢所有任務（包括歸檔的）
   curl -X GET "http://localhost:8000/user-tasks?include_archived=true" \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **恢復歸檔任務**：
   如果任務被誤歸檔，可以通過更新 API 恢復：
   ```bash
   curl -X PUT "http://localhost:8000/user-tasks/{task_id}" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"task_status": "activate"}'
   ```

3. **檢查任務狀態**：
   使用診斷腳本檢查任務的實際狀態：
   ```bash
   python3 scripts/check_user_tasks.py daniel@test.com
   ```

## 快速修復：恢復歸檔任務

如果任務被誤歸檔，可以使用恢復腳本：

```bash
# 1. 預覽歸檔的任務（不實際修改）
python3 scripts/restore_archived_tasks.py --email daniel@test.com --dry-run

# 2. 實際恢復所有歸檔的任務
python3 scripts/restore_archived_tasks.py --email daniel@test.com --no-dry-run
```

## 常見問題更新

### Q5: 為什麼任務明明存在但看不到？

**A:** 最常見的原因是任務被設置為 `archive`（歸檔）狀態。默認情況下，任務列表只顯示 `activate` 狀態的任務。

**解決方法**：
1. 使用 `include_archived=true` 參數查詢所有任務
2. 使用恢復腳本批量恢復歸檔任務
3. 或者手動更新單個任務的 `task_status` 為 `activate`
