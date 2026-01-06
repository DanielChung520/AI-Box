# 文件上傳流程評估報告

## 文檔資訊

- **創建日期**: 2025-01-27
- **創建人**: Daniel Chung
- **最後修改日期**: 2025-01-27
- **版本**: 1.0
- **狀態**: 評估完成

## 問題概述

### 當前問題

1. **文件樹不自動刷新**
   - 文件上傳後，前端文件區顯示的目錄位置錯誤
   - 需要手動刷新頁面才能看到正確的文件位置
   - 影響用戶體驗

2. **向量與圖譜生成流程混亂**
   - 流程複雜，包含多個階段（分塊、向量化、存儲、KG提取）
   - 狀態管理分散（Redis + 元數據）
   - 前端需要輪詢獲取狀態
   - KG 提取可能自動續跑，狀態追蹤困難

3. **事件機制不一致**
   - 文件上傳後派發 `fileUploaded` 事件
   - FileTree 監聽 `fileTreeUpdated` 事件
   - 兩個事件沒有統一，導致文件樹不刷新

## 現有流程分析

### 文件上傳流程

```
1. 前端上傳文件 (FileUploadModal)
   ↓
2. 後端接收文件 (file_upload.py /upload)
   ↓
3. 保存文件到存儲 (FileStorage)
   ↓
4. 創建文件元數據 (FileMetadataService)
   ↓
5. 派發 fileUploaded 事件 (api.ts)
   ↓
6. 異步處理：分塊 + 向量化 + KG提取 (process_file_chunking_and_vectorization)
   ↓
7. 狀態更新到 Redis (processing:status:{file_id})
```

### 前端更新流程

```
1. FileManagement 頁面監聽 fileUploaded 事件
   ↓
2. 觸發 setRefreshKey 刷新文件列表
   ↓
3. FileTree 組件監聽 fileTreeUpdated 事件
   ❌ 問題：fileUploaded 事件沒有觸發 fileTreeUpdated
   ↓
4. 文件樹不刷新，顯示舊的目錄結構
```

### 向量與圖譜生成流程

```
1. 文件解析 (Parser)
   ↓
2. 分塊處理 (ChunkProcessor) - 0-50%
   ↓
3. 向量化 (EmbeddingService) - 50-90%
   ↓
4. 存儲到 ChromaDB (VectorStoreService) - 90%
   ↓
5. 知識圖譜提取 (KGExtractionService) - 90-100%
   ↓
6. 如果 KG 提取未完成，自動續跑
   ↓
7. 狀態更新到 Redis
```

## 問題根因分析

### 1. 事件機制不一致

**問題**：

- `fileUploaded` 事件在 `api.ts` 中派發
- `fileTreeUpdated` 事件在 `FileTree.tsx` 內部操作時派發
- 文件上傳後沒有派發 `fileTreeUpdated` 事件

**影響**：

- 文件樹不自動刷新
- 用戶需要手動刷新頁面

### 2. 狀態管理分散

**問題**：

- 文件元數據在 ArangoDB
- 處理狀態在 Redis
- 文件樹緩存在前端
- 多個數據源，同步困難

**影響**：

- 狀態不一致
- 前端需要多次查詢
- 難以追蹤完整狀態

### 3. 異步處理流程複雜

**問題**：

- 多個異步階段（分塊、向量化、KG提取）
- KG 提取可能自動續跑
- 狀態更新分散在多個地方
- 前端需要輪詢獲取狀態

**影響**：

- 流程難以追蹤
- 錯誤處理複雜
- 性能問題（輪詢）

## 整合方案

### 方案 A：完全整合（推薦）

**範圍**：

- 文件元數據管理（已在 ArangoDB）
- 處理狀態管理（遷移到 ArangoDB）
- 事件機制統一
- 文件樹同步機制

**優點**：

- 統一數據管理
- 狀態一致性更好
- 減少 Redis 依賴
- 查詢更靈活

**工作量**：3.5 天

### 方案 B：部分整合（快速修復）

**範圍**：

- 只修復事件機制問題
- 保持現有 Redis 狀態管理
- 優化前端刷新邏輯

**優點**：

- 工作量小（1.25 天）
- 風險低
- 快速修復問題

**缺點**：

- 沒有解決根本問題
- 狀態管理仍然分散

## 推薦方案：完全整合

### 技術方案設計

#### 1. 處理狀態數據模型

```python
# ArangoDB Collection: file_processing_status
{
    "_key": "file_id",
    "file_id": "file_001",
    "status": "processing",  # pending, processing, completed, failed
    "progress": 75,  # 0-100
    "stages": {
        "chunking": {
            "status": "completed",
            "progress": 100,
            "chunk_count": 10,
            "started_at": "...",
            "completed_at": "..."
        },
        "vectorization": {
            "status": "processing",
            "progress": 50,
            "vector_count": 5,
            "started_at": "..."
        },
        "kg_extraction": {
            "status": "pending",
            "progress": 0,
            "remaining_chunks": [6, 7, 8, 9]
        }
    },
    "message": "正在向量化...",
    "created_at": "...",
    "updated_at": "..."
}
```

#### 2. 統一事件派發機制

```typescript
// 前端統一事件派發
class FileEventDispatcher {
  static dispatchFileUploaded(detail: {
    fileIds: string[];
    taskId: string;
  }) {
    // 派發 fileUploaded 事件
    window.dispatchEvent(new CustomEvent('fileUploaded', { detail }));
    // 同時派發 fileTreeUpdated 事件
    window.dispatchEvent(new CustomEvent('fileTreeUpdated', {
      detail: { taskId: detail.taskId, forceReload: true }
    }));
  }
}
```

#### 3. 文件樹自動刷新機制

```typescript
// FileTree 組件監聽多個事件
useEffect(() => {
  const handleFileTreeUpdate = () => {
    loadTree(); // 重新載入文件樹
  };

  // 監聽多個事件
  window.addEventListener('fileTreeUpdated', handleFileTreeUpdate);
  window.addEventListener('fileUploaded', handleFileTreeUpdate);

  return () => {
    window.removeEventListener('fileTreeUpdated', handleFileTreeUpdate);
    window.removeEventListener('fileUploaded', handleFileTreeUpdate);
  };
}, [loadTree]);
```

## 工作量評估

### 方案 A：完全整合

| 任務 | 工作量 | 負責人 |
|------|--------|--------|
| 處理狀態遷移到 ArangoDB | 1 天 | 後端開發 |
| 事件機制統一 | 0.5 天 | 前端開發 |
| 文件樹同步機制 | 0.5 天 | 前端開發 |
| 異步處理流程優化 | 1 天 | 後端開發 |
| 測試與驗證 | 0.5 天 | 測試工程師 |
| **總計** | **3.5 天** | |

## 風險評估

| 風險 | 影響 | 機率 | 緩解措施 |
|------|------|------|---------|
| 狀態遷移失敗 | 高 | 中 | 完整備份、分階段遷移 |
| 性能問題 | 中 | 中 | 性能測試、索引優化 |
| 前端兼容性 | 中 | 低 | 向後兼容、漸進式遷移 |

## 實施建議

### 階段 1（快速修復）：0.5 天

先修復事件機制問題：

- 文件上傳後派發 `fileTreeUpdated` 事件
- FileTree 監聽 `fileUploaded` 事件
- 快速解決用戶體驗問題

### 階段 2（完整重構）：在 WBS-3 中整合

- 處理狀態遷移到 ArangoDB
- 統一事件機制
- 優化異步處理流程

## 整合到遷移計劃

### 修改 WBS-3：數據遷移與服務開發

**新增任務 3.7: 文件上傳流程重構 (2 天)**

- 處理狀態遷移到 ArangoDB
- 事件機制統一
- 文件樹同步機制
- 異步處理流程優化

**總工期調整**：

- 原 WBS-3: 10 天
- 調整後: 12 天（+2 天）

### 修改 WBS-4：AI 治理與合規

**新增任務 4.6: 文件處理審計 (0.5 天)**

- 文件處理審計日誌
- 處理性能報告

**總工期調整**：

- 原 WBS-4: 8 天
- 調整後: 8.5 天（+0.5 天）

### 總工期調整

- 原總工期: 40 天
- 調整後: 42.5 天（+2.5 天）

## 結論

**建議將文件上傳流程重構整合到遷移計劃中**，理由：

1. ✅ **問題嚴重性**：影響用戶體驗，需要優先解決
2. ✅ **技術一致性**：與遷移目標一致（統一數據管理）
3. ✅ **工作量可控**：增加 2.5 天，在可接受範圍內
4. ✅ **長期收益**：減少技術債務，提升系統可維護性

**實施策略**：

- 先快速修復事件機制問題（0.5 天）
- 在 WBS-3 中完整重構（2 天）
- 在 WBS-4 中添加審計功能（0.5 天）

## 變更記錄

| 版本 | 日期 | 變更內容 | 變更人 |
|------|------|---------|--------|
| 1.0 | 2025-01-27 | 初始版本 | Daniel Chung |
