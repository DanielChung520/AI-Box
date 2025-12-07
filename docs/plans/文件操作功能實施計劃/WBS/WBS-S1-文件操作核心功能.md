# WBS計劃 - 階段一：文件操作核心功能（S1）

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

## 階段概述

**目標**: 實現文件的基本操作（重命名、複製、移動、刪除、複製路徑）
**工作量**: 6 天（原4天 + 新增2天）
**優先級**: P0
**依賴**: S0

**更新說明**（2025-01-27）：
- 根據《文件操作功能檢核報告》補充刪除文件功能（S1.4）
- 補充複製路徑功能（S1.5）
- 補充數據驗證規則（S1.6）

---

## 任務分解

### S1.1 文件重命名功能（1 天）

**任務描述**: 實現文件重命名API

**實施位置**: `api/routers/file_management.py`

**API設計**:
- **端點**: `PUT /api/v1/files/{file_id}/rename`
- **請求體**: `{"new_name": "新文件名.txt"}`
- **響應**: 更新後的文件信息

**數據驗證規則**:
- 文件名長度不超過255字符
- 不能包含特殊字符：`/ \ : * ? " < > |`
- 不能使用系統保留名稱（如 `CON`, `PRN`, `AUX` 等）
- 必須包含有效的文件擴展名

**實現步驟**:
1. [ ] 在 `file_management.py` 中新增 `rename_file` 函數
2. [ ] 實現文件存在性檢查
3. [ ] 實現文件名驗證（使用數據驗證規則）
4. [ ] 實現權限檢查（重用 `get_file_permission_service()`）
5. [ ] 實現文件元數據更新（重用 `get_metadata_service().update()`）
6. [ ] 實現文件系統重命名（如果支持，重用 `get_storage()`）
7. [ ] 添加錯誤處理和日誌記錄
8. [ ] 添加審計日誌（重用 `@audit_log` 裝飾器）

**重用服務**:
- `get_metadata_service()` - 文件元數據服務
- `get_storage()` - 文件存儲服務
- `get_file_permission_service()` - 權限檢查服務

**驗收標準**:
- [ ] API可以成功重命名文件
- [ ] 文件名驗證正確（符合驗證規則）
- [ ] 權限檢查正確
- [ ] 錯誤處理完善
- [ ] 日誌記錄完整
- [ ] 現有功能不受影響

---

### S1.2 文件複製功能（2 天）

**任務描述**: 實現文件複製API

**實施位置**: `api/routers/file_management.py`

**API設計**:
- **端點**: `POST /api/v1/files/{file_id}/copy`
- **請求體**: `{"target_task_id": "目標任務ID（可選）"}`
- **響應**: 新文件的信息

**實現步驟**:
1. [ ] 在 `file_management.py` 中新增 `copy_file` 函數
2. [ ] 實現源文件讀取（重用 `get_storage().read_file()`）
3. [ ] 實現新文件ID生成（重用 `FileStorage.generate_file_id()`）
4. [ ] 實現文件保存（重用 `get_storage().save_file()`）
5. [ ] 實現元數據創建（重用 `get_metadata_service().create()`）
6. [ ] 實現可選的向量數據複製（重用 `get_vector_store_service()`）
7. [ ] 實現可選的圖譜數據複製（重用 `get_kg_extraction_service()`）
8. [ ] 添加錯誤處理和日誌記錄
9. [ ] 添加審計日誌

**重用服務**:
- `get_storage()` - 文件存儲服務
- `get_metadata_service()` - 文件元數據服務
- `get_vector_store_service()` - 向量存儲服務（可選）
- `get_kg_extraction_service()` - 圖譜提取服務（可選）

**驗收標準**:
- [ ] API可以成功複製文件
- [ ] 文件內容正確複製
- [ ] 元數據正確創建
- [ ] 可選的向量和圖譜數據正確複製
- [ ] 錯誤處理完善
- [ ] 現有功能不受影響

---

### S1.3 文件移動功能（1 天）

**任務描述**: 實現文件移動API

**實施位置**: `api/routers/file_management.py`

**API設計**:
- **端點**: `PUT /api/v1/files/{file_id}/move`
- **請求體**: `{"target_task_id": "目標任務ID"}`
- **響應**: 更新後的文件信息

**實現步驟**:
1. [ ] 在 `file_management.py` 中新增 `move_file` 函數
2. [ ] 實現源文件和目標任務檢查
3. [ ] 實現權限檢查（重用 `get_file_permission_service()`）
4. [ ] 實現文件元數據更新（重用 `get_metadata_service().update()`，更新 `task_id`）
5. [ ] 添加錯誤處理和日誌記錄
6. [ ] 添加審計日誌

**重用服務**:
- `get_metadata_service()` - 文件元數據服務
- `get_file_permission_service()` - 權限檢查服務

**驗收標準**:
- [ ] API可以成功移動文件
- [ ] 文件 `task_id` 正確更新
- [ ] 權限檢查正確
- [ ] 錯誤處理完善
- [ ] 現有功能不受影響

---

### S1.4 文件刪除功能（1 天 - 新增）

**任務描述**: 實現文件刪除API，包含多數據源清理

**實施位置**: `api/routers/file_management.py`

**API設計**:
- **端點**: `DELETE /api/v1/files/{file_id}`
- **響應**: 刪除結果

**多數據源清理邏輯**:
1. 文件實體（從文件系統）
2. 文件元數據（從 ArangoDB）
3. 向量數據（從 ChromaDB）
4. 知識圖譜關聯（從 ArangoDB）

**實現步驟**:
1. [ ] 在 `file_management.py` 中新增 `delete_file` 函數
2. [ ] 實現文件存在性檢查
3. [ ] 實現權限檢查（重用 `get_file_permission_service()`）
4. [ ] 實現文件實體刪除（重用 `get_storage().delete_file()`）
5. [ ] 實現文件元數據刪除（重用 `get_metadata_service().delete()`）
6. [ ] 實現向量數據刪除（重用 `get_vector_store_service().delete()`）
7. [ ] 實現知識圖譜關聯刪除（重用 `get_kg_extraction_service().delete()`）
8. [ ] 實現事務處理（確保原子性，如果任何步驟失敗則回滾）
9. [ ] 添加錯誤處理和日誌記錄
10. [ ] 添加審計日誌

**重用服務**:
- `get_storage()` - 文件存儲服務
- `get_metadata_service()` - 文件元數據服務
- `get_vector_store_service()` - 向量存儲服務
- `get_kg_extraction_service()` - 圖譜提取服務
- `get_file_permission_service()` - 權限檢查服務

**驗收標準**:
- [ ] API可以成功刪除文件
- [ ] 所有數據源都正確清理（文件系統、ArangoDB、ChromaDB）
- [ ] 事務處理正確（原子性保證）
- [ ] 權限檢查正確
- [ ] 錯誤處理完善
- [ ] 現有功能不受影響

---

### S1.5 複製路徑功能（0.5 天 - 新增）

**任務描述**: 實現複製文件路徑到剪貼板的前端功能

**實施位置**: `ai-bot/src/components/FileTree.tsx` 或 `ai-bot/src/lib/api.ts`

**功能描述**:
- 複製文件的完整路徑（包括任務ID和文件ID）
- 格式：`task_id/file_id` 或完整URL路徑
- 使用 `navigator.clipboard.writeText()` API

**實現步驟**:
1. [ ] 在 `FileTree.tsx` 中實現 `handleCopyPath` 函數
2. [ ] 構建文件路徑字符串（包含任務ID和文件ID）
3. [ ] 使用 `navigator.clipboard.writeText()` 複製到剪貼板
4. [ ] 顯示成功提示（Toast 通知）
5. [ ] 添加錯誤處理（剪貼板API失敗時顯示錯誤提示）

**驗收標準**:
- [ ] 可以成功複製文件路徑到剪貼板
- [ ] 路徑格式正確
- [ ] 成功提示正常顯示
- [ ] 錯誤處理完善

---

### S1.6 數據驗證規則（文件）（0.5 天 - 新增）

**任務描述**: 實現文件相關的數據驗證規則

**實施位置**: `api/routers/file_management.py` 或新建 `api/utils/file_validator.py`

**驗證規則**:

1. **文件名規則**:
   - 長度限制：不超過255個字符
   - 字符限制：不能包含 `/ \ : * ? " < > |`
   - 保留名稱：不能使用系統保留名稱（如 `CON`, `PRN`, `AUX` 等）
   - 擴展名：必須包含有效的文件擴展名

2. **文件大小限制**:
   - 單個文件：最大100MB
   - 批量上傳：單次上傳總大小不超過500MB
   - 文件數量：單次上傳最多50個文件

3. **文件類型限制**:
   - **支持的文件類型**:
     - 文檔: `.md`, `.txt`, `.doc`, `.docx`, `.pdf`, `.rtf`
     - 表格: `.xls`, `.xlsx`, `.csv`
     - 圖片: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`
     - 代碼: `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c`, `.h`, `.html`, `.css`, `.json`, `.xml`
   - **不支持的文件類型**: 可執行文件（`.exe`, `.bat`, `.sh` 等）

**實現步驟**:
1. [ ] 創建 `file_validator.py` 文件（或直接在 `file_management.py` 中實現）
2. [ ] 實現 `validate_filename()` 函數
3. [ ] 實現 `validate_file_size()` 函數
4. [ ] 實現 `validate_file_type()` 函數
5. [ ] 在重命名、上傳等操作中應用驗證規則
6. [ ] 添加錯誤提示（驗證失敗時返回友好的錯誤信息）

**驗收標準**:
- [ ] 文件名驗證正確
- [ ] 文件大小驗證正確
- [ ] 文件類型驗證正確
- [ ] 驗證失敗時返回友好的錯誤信息
- [ ] 所有文件操作都應用驗證規則

---

## 階段交付物

- ✅ 文件重命名API實現完成
- ✅ 文件複製API實現完成
- ✅ 文件移動API實現完成
- ✅ 文件刪除API實現完成（多數據源清理）
- ✅ 複製路徑前端功能實現完成
- ✅ 數據驗證規則實現完成
- ✅ 單元測試完成
- ✅ 集成測試完成
- ✅ API文檔更新完成

---

## 測試要求

### 單元測試
- [ ] 測試文件重命名功能
- [ ] 測試文件複製功能
- [ ] 測試文件移動功能
- [ ] 測試文件刪除功能（多數據源清理）
- [ ] 測試複製路徑功能
- [ ] 測試數據驗證規則
- [ ] 測試錯誤處理

### 集成測試
- [ ] 測試與現有服務的集成
- [ ] 測試權限檢查
- [ ] 測試審計日誌
- [ ] 測試多數據源清理（刪除功能）

### 回歸測試
- [ ] 測試現有文件上傳功能
- [ ] 測試現有文件列表查詢
- [ ] 測試現有文件搜尋功能
- [ ] 測試現有文件下載功能
- [ ] 測試現有文件預覽功能

---

## 注意事項

- ⚠️ **禁止移動現有文件**
- ⚠️ **禁止修改現有代碼**（只新增）
- ⚠️ **禁止改變現有API路徑**
- ✅ **重用現有服務和函數**
- ✅ **新增功能使用新API路徑**
- ✅ **刪除文件時必須清理所有數據源**（文件系統、ArangoDB、ChromaDB）
- ✅ **所有文件操作都必須應用數據驗證規則**
