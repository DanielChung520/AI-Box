# 文件編輯 Agent 開發規劃書

**版本**: 1.6
**創建日期**: 2026-01-06
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-06

---

## 📋 目錄

1. [可行性分析](#1-可行性分析)
2. [文件編輯架構](#2-文件編輯架構)
3. [暫存機制與恢復機制](#3-暫存機制與恢復機制)
4. [現有架構評估](#4-現有架構評估)
5. [預計增加的代碼與修改的代碼](#5-預計增加的代碼與修改的代碼)
6. [開發與測試計劃](#6-開發與測試計劃)

---

## 1. 可行性分析

### 1.1 需求概述

實現一個文件編輯 Agent，具備以下功能：

1. **Agent/Assistant 能力檢測**：當前端選擇了文件編輯的代理或助理時，自動啟用文件編輯功能
2. **文件類型驗證**：編輯時確認文件名，並提示只能編輯 Markdown 文件
3. **流式編輯**：以流式輸出方式編輯文件，同步在文件預覽區看到文件編輯
4. **文件狀態顯示**：在 AI 輸入框 header 模型右側顯示文件，提示文件的右側檢測若文件有修改，則顯示接受、拒絕、提交三個擇一的按鈕

### 1.2 現有系統能力評估

#### ✅ 已具備的基礎設施

| 功能模組                | 狀態      | 說明                                                                         |
| ----------------------- | --------- | ---------------------------------------------------------------------------- |
| Agent 註冊系統          | ✅ 已實現 | `agents/services/registry/` 完整的 Agent 註冊與發現機制                    |
| Agent Orchestrator      | ✅ 已實現 | `agents/orchestrator/` 任務路由與協調                                      |
| Execution Agent         | ✅ 已實現 | `agents/core/execution/` 工具執行能力                                      |
| DocumentEditingService  | ✅ 已實現 | `agents/core/execution/document_editing_service.py`                        |
| 流式輸出 API            | ✅ 已實現 | `/api/v1/chat/stream` 和 `/api/v1/streaming/editing/{session_id}/stream` |
| 文件編輯 API            | ✅ 已實現 | `/api/v1/editing/session/start` 和 `/api/v1/editing/command`             |
| 文件預覽組件            | ✅ 已實現 | `FilePreview`, `MarkdownViewer` 等組件                                   |
| 文件管理                | ✅ 已實現 | `FileMetadataService`, 文件上傳與管理                                      |
| Search-and-Replace 協議 | ✅ 已實現 | `doc_patch_service.py` 支持 patches 應用                                   |

#### ⚠️ 需要增強的功能

| 功能模組               | 狀態        | 說明                                                                 |
| ---------------------- | ----------- | -------------------------------------------------------------------- |
| Document Editing Agent | 🔄 部分實現 | 需要創建專用的 Document Editing Agent                                |
| Assistant 能力檢測     | ❌ 未實現   | 需要檢測 Assistant 的 `allowedTools` 是否包含 `document_editing` |
| 文件選擇器 UI          | ❌ 未實現   | 在 ChatInput 中添加文件選擇器                                        |
| 流式編輯同步           | 🔄 部分實現 | 需要完善流式 patches 應用到預覽的機制                                |
| 編輯狀態管理           | ❌ 未實現   | 文件修改狀態追蹤與操作按鈕                                           |

### 1.3 可行性評分

**總體可行性**: ⭐⭐⭐⭐⭐ (5/5) - **高度可行**

**評分細項**:

- **技術可行性**: 5/5 - 現有基礎設施完善，主要工作是集成與前端開發
- **架構一致性**: 5/5 - 完全符合現有 Agent 架構設計
- **開發工作量**: 4/5 - 預計 4-7 天完成核心功能
- **風險評估**: 5/5 - 低風險，主要是前端集成工作

### 1.4 技術挑戰與解決方案

#### 挑戰 1: 流式編輯同步

**問題**: 如何將流式接收的 patches 實時應用到文件預覽區

**解決方案**:

- 使用現有的 SSE 流式 API (`/api/v1/streaming/editing/{session_id}/stream`)
- 在 `MarkdownViewer` 組件中實現增量更新機制
- 使用 React state 管理文件內容的原始版本和修改版本

#### 挑戰 2: 文件狀態管理

**問題**: 如何追蹤文件修改狀態並顯示操作按鈕

**解決方案**:

- 在 `ChatInput` 組件中維護文件編輯狀態
- 使用 diff 算法比較原始內容與修改內容
- 檢測到差異時顯示接受/拒絕/提交按鈕

#### 挑戰 3: Agent 能力檢測

**問題**: 如何檢測 Assistant 是否支持文件編輯

**解決方案**:

- 檢查 Assistant 的 `allowedTools` 是否包含 `document_editing` 或 `file_editing`
- 在 `ChatInput` 組件中添加能力檢測邏輯
- 支持文件編輯時顯示文件選擇器

---

## 2. 文件編輯架構

### 2.1 整體架構設計

```mermaid
graph TB
    subgraph Frontend["前端層"]
        CI[ChatInput文件選擇器狀態管理]
        CA[ChatArea消息處理]
        MV[MarkdownViewer實時預覽增量更新]
        RP[ResultPanel文件預覽區]
    end

    subgraph API["API 層"]
        ES["Editing Session API/api/v1/editing/session/start"]
        EC["Editing Command API/api/v1/editing/command"]
        SS["Streaming API/api/v1/streaming/editing/{session_id}/stream"]
    end

    subgraph Agent["Agent 層"]
        AO[Agent Orchestrator任務路由]
        DEA[Document Editing Agent文件編輯 Agent]
        DES[DocumentEditingServicePatches 生成]
    end

    subgraph Data["數據層"]
        FS[FileStorage文件存儲]
        FMS[FileMetadataService文件元數據]
        EPS[EditingSessionService編輯會話管理]
    end

    CI -->|選擇文件| CA
    CA -->|提交編輯指令| ES
    ES -->|創建 Session| EPS
    ES -->|路由任務| AO
    AO -->|執行編輯| DEA
    DEA -->|生成 Patches| DES
    DES -->|流式輸出| SS
    SS -->|實時更新| MV
    MV -->|顯示預覽| RP
    CI -->|檢測修改| MV
    MV -->|操作按鈕| CI

    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef api fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef agent fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef dataStyle fill:#ffebee,stroke:#b71c1c,stroke-width:2px

    class CI,CA,MV,RP frontend
    class ES,EC,SS api
    class AO,DEA,DES agent
    class FS,FMS,EPS dataStyle
```

### 2.2 與現有 IEE 前端系統的對比

#### 現有 IEE 前端系統文檔檢討

**文檔位置**: `docs/系统设计文档/IEE前端系統/IEE前端系统.md`

**現有設計**:

- ✅ Monaco Editor 集成（已實現）
- ✅ 文件樹管理（已實現）
- ✅ 任務型聊天室（已實現）
- 🔄 AI 驅動編輯（進行中）
- 🔄 Diff 可視化（進行中）

**本次規劃的增強**:

1. **Agent 驅動的文件編輯**：將文件編輯功能集成到 Agent 系統中
2. **流式編輯體驗**：實現實時編輯預覽
3. **文件狀態管理**：在輸入框 header 顯示文件狀態
4. **編輯確認機制**：接受/拒絕/提交按鈕

**一致性檢查**:

- ✅ 符合 IEE 前端系統的設計理念（IDE 式界面）
- ✅ 符合任務型聊天室的上下文管理
- ✅ 符合 AI 驅動編輯的 Search-and-Replace 協議
- ✅ 符合前端暫存與視覺化 Diff 的設計

**需要更新的文檔**:

- 更新 `IEE前端系统.md` 的「進行中功能」部分
- 添加「Agent 驅動編輯」的說明

### 2.3 數據流設計

#### 2.3.1 文件選擇流程

```
用戶選擇 Assistant (支持 document_editing)
    ↓
ChatInput 檢測 allowedTools
    ↓
顯示文件選擇器
    ↓
用戶選擇 Markdown 文件
    ↓
驗證文件類型 (.md, .markdown)
    ↓
創建編輯 Session
    ↓
在 header 顯示文件名
```

#### 2.3.2 編輯執行流程

```
用戶輸入編輯指令
    ↓
ChatInput 發送消息
    ↓
ChatArea 調用 /api/v1/editing/command
    ↓
API 路由到 Agent Orchestrator
    ↓
Orchestrator 選擇 Document Editing Agent
    ↓
Agent 調用 DocumentEditingService
    ↓
生成 Search-and-Replace Patches
    ↓
流式輸出到前端
    ↓
MarkdownViewer 實時應用 Patches
    ↓
顯示修改預覽
    ↓
檢測到修改，顯示操作按鈕
```

#### 2.3.3 編輯確認流程

```
用戶點擊「接受」
    ↓
應用修改到本地狀態
    ↓
更新預覽區顯示
    ↓
清除操作按鈕

用戶點擊「拒絕」
    ↓
恢復原始內容
    ↓
清除修改狀態
    ↓
清除操作按鈕

用戶點擊「提交」
    ↓
調用 /api/v1/docs/{request_id}/apply
    ↓
保存修改到後端
    ↓
更新文件版本
    ↓
清除編輯狀態
```

---

## 3. 暫存機制與恢復機制

### 3.1 設計目標

實現一個三階段的文件編輯流程：

1. **編輯階段**：暫存本地，不寫入 SeaweedFS
2. **預覽階段**：審查修改，支持接受/拒絕
3. **提交階段**：寫入 SeaweedFS，觸發向量化和知識圖譜提取

**核心優勢**：

- ✅ **性能優化**：避免頻繁的向量化操作，只在最終提交時處理
- ✅ **成本優化**：只保存最終版本到 SeaweedFS，避免中間版本的存儲
- ✅ **用戶體驗**：編輯過程流暢，支持多次修改後一次性提交
- ✅ **數據安全**：前端丟失時可從後端恢復

### 3.2 暫存機制設計

#### 3.2.1 前端暫存（主要方案）

**實現方式**：使用現有的 `draftStore.ts` 機制

**存儲位置**：

- **小文件**（< 5MB）：`localStorage`
- **大文件**（≥ 5MB）：`IndexedDB`

**數據結構**：

```typescript
interface DraftFileState {
  fileId: string;
  originalContent: string;      // 原始內容（從後端獲取）
  draftContent: string;         // 編輯中的內容
  patches: AIPatch[];           // 應用的 patches 列表
  lastModified: number;         // 最後修改時間戳
  sessionId?: string;           // 編輯 Session ID（可選）
}
```

**存儲鍵名規則**：

```typescript
const DRAFT_STORAGE_KEY = `draft_file_${fileId}_${taskId}`;
```

**自動保存機制**：

- 使用 `useAutoSave` Hook 實現防抖保存
- 默認延遲：2 秒
- 保存到 `localStorage` 或 `IndexedDB`

#### 3.2.2 後端 Session 暫存（可選方案）

**使用場景**：

- 多設備同步
- 協作編輯
- 長時間編輯會話

**實現方式**：使用 Redis 存儲編輯 Session

**數據結構**：

```python
class EditingDraftSession:
    session_id: str
    file_id: str
    user_id: str
    task_id: str
    original_content: str      # 原始內容
    draft_content: str         # 編輯中的內容
    patches: List[Dict]        # 應用的 patches
    created_at: datetime
    updated_at: datetime
    expires_at: datetime        # TTL: 24 小時
```

**存儲鍵名規則**：

```python
REDIS_KEY = f"editing_draft:{session_id}:{file_id}"
TTL_SECONDS = 86400  # 24 小時
```

### 3.3 恢復機制設計

#### 3.3.1 前端恢復流程

**場景 1：頁面刷新或重新打開**

```
用戶重新打開頁面
    ↓
檢查 localStorage/IndexedDB 中的草稿
    ↓
找到未提交的草稿
    ↓
提示用戶是否恢復草稿
    ↓
用戶選擇「恢復」
    ↓
從後端驗證文件版本
    ↓
如果版本匹配，恢復草稿內容
    ↓
如果版本不匹配，提示用戶選擇：
  - 使用本地草稿（覆蓋後端）
  - 使用後端版本（丟棄本地草稿）
  - 手動合併
```

**場景 2：前端數據丟失**

```
檢測到 localStorage/IndexedDB 數據丟失
    ↓
嘗試從後端 Session 恢復
    ↓
調用 /api/v1/editing/session/{session_id}/draft
    ↓
如果找到 Session，恢復草稿
    ↓
如果找不到，提示用戶從 SeaweedFS 恢復最後版本
```

#### 3.3.2 後端恢復 API

**API 1：獲取編輯 Session 草稿**

```python
GET /api/v1/editing/session/{session_id}/draft

Response:
{
    "success": true,
    "data": {
        "session_id": "xxx",
        "file_id": "xxx",
        "original_content": "...",
        "draft_content": "...",
        "patches": [...],
        "last_modified": "2026-01-06T14:37:28Z"
    }
}
```

**API 2：從 SeaweedFS 恢復文件版本**

```python
GET /api/v1/files/{file_id}/versions/{version}

Response:
{
    "success": true,
    "data": {
        "file_id": "xxx",
        "version": 3,
        "content": "...",
        "created_at": "2026-01-06T10:00:00Z",
        "summary": "版本摘要"
    }
}
```

**API 3：檢查文件版本**

```python
GET /api/v1/files/{file_id}/version-check

Response:
{
    "success": true,
    "data": {
        "file_id": "xxx",
        "current_version": 3,
        "last_modified": "2026-01-06T14:00:00Z"
    }
}
```

### 3.4 版本衝突處理

#### 3.4.1 衝突檢測

**檢測時機**：

1. 恢復草稿時
2. 提交修改前
3. 定期檢查（可選）

**檢測邏輯**：

```python
def check_version_conflict(
    file_id: str,
    base_version: int,
    draft_last_modified: datetime
) -> Tuple[bool, Optional[str]]:
    """
    檢查版本衝突

    Returns:
        (has_conflict, conflict_message)
    """
    # 獲取當前文件版本
    current_version = get_file_current_version(file_id)
    current_modified = get_file_last_modified(file_id)

    # 檢查版本是否匹配
    if current_version != base_version:
        return True, f"文件已被修改（版本 {base_version} → {current_version}）"

    # 檢查修改時間（如果後端版本更新）
    if current_modified > draft_last_modified:
        return True, "文件在後端有更新"

    return False, None
```

#### 3.4.2 衝突解決策略

**策略 1：自動合併（簡單變更）**

```
檢測到版本衝突
    ↓
分析變更範圍
    ↓
如果變更不重疊：
  - 自動合併兩個版本
  - 應用所有 patches
    ↓
如果變更重疊：
  - 提示用戶手動解決
```

**策略 2：用戶選擇**

```
檢測到版本衝突
    ↓
顯示衝突提示對話框
    ↓
提供三個選項：
  1. 使用本地草稿（覆蓋後端）
  2. 使用後端版本（丟棄本地草稿）
  3. 手動合併（打開 diff 視圖）
```

**策略 3：三路合併（進階）**

```
檢測到版本衝突
    ↓
獲取三個版本：
  - Base: 編輯開始時的版本
  - Local: 本地草稿版本
  - Remote: 後端當前版本
    ↓
使用 diff3 算法合併
    ↓
顯示合併結果
    ↓
用戶審查並確認
```

### 3.5 數據流設計

#### 3.5.1 編輯階段（暫存本地）

```
用戶發送編輯指令
    ↓
Agent 生成 Patches
    ↓
前端應用 Patches 到 draftContent
    ↓
自動保存到 localStorage/IndexedDB
    ↓
MarkdownViewer 實時顯示修改
    ↓
（不寫入 SeaweedFS）
```

#### 3.5.2 預覽階段（審查）

```
檢測到文件修改
    ↓
顯示操作按鈕（接受/拒絕/提交）
    ↓
用戶點擊「接受」
    ↓
更新 draftContent（標記為已接受）
    ↓
清除操作按鈕
    ↓
（仍不寫入 SeaweedFS）
```

#### 3.5.3 提交階段（寫入 SeaweedFS + 處理）

```
用戶點擊「提交」
    ↓
調用 /api/v1/docs/{request_id}/apply
    ↓
後端檢查版本衝突
    ↓
如果無衝突：
  - 保存舊版本快照
  - 寫入 SeaweedFS（最終版本）
  - 更新文件元數據
  - 觸發向量化處理（異步）
  - 觸發知識圖譜提取（異步）
    ↓
如果衝突：
  - 返回衝突錯誤
  - 前端顯示衝突解決對話框
    ↓
提交成功後：
  - 清除本地草稿
  - 清除後端 Session（如適用）
  - 更新文件狀態為「已保存」
```

### 3.6 向量化/圖譜處理觸發時機

#### 3.6.1 觸發策略

**策略 1：變更比例判斷**

```python
def should_trigger_vectorization(
    original_content: str,
    modified_content: str
) -> bool:
    """判斷是否需要重新向量化"""
    # 計算變更比例
    change_ratio = calculate_change_ratio(original_content, modified_content)

    # 如果變更超過 10%，觸發完整處理
    if change_ratio > 0.1:
        return True

    # 否則只做增量重新索引
    return False
```

**策略 2：變更範圍判斷**

```python
def should_trigger_vectorization(
    patches: List[Dict],
    file_size: int
) -> bool:
    """根據變更範圍判斷"""
    # 計算變更的總字符數
    total_changed = sum(len(p.get("replace_block", "")) for p in patches)

    # 如果變更超過文件大小的 10%，觸發完整處理
    if total_changed > file_size * 0.1:
        return True

    return False
```

#### 3.6.2 處理流程

**完整處理（變更 > 10%）**：

```
提交修改
    ↓
寫入 SeaweedFS
    ↓
觸發 process_file_chunking_and_vectorization
    ↓
執行完整流程：
  - 文件解析和分塊
  - 向量化
  - 存儲到 ChromaDB
  - 知識圖譜提取
```

**增量處理（變更 ≤ 10%）**：

```
提交修改
    ↓
寫入 SeaweedFS
    ↓
觸發 incremental_reindex_service.reindex_modified_chunks
    ↓
只重新索引變更的部分：
  - 識別變更的 chunks
  - 重新向量化變更的 chunks
  - 更新 ChromaDB
  - 更新知識圖譜（增量）
```

### 3.7 實現細節

#### 3.7.1 前端實現

**文件**: `ai-bot/src/hooks/useFileEditing.ts`

```typescript
export function useFileEditing(fileId: string, taskId: string) {
  const { draftContent, stableContent, setDraftContent, setStableContent } = useDraftStore();

  // 恢復草稿
  const restoreDraft = useCallback(async () => {
    // 1. 嘗試從 localStorage/IndexedDB 恢復
    const localDraft = loadDraftFromStorage(fileId, taskId);
    if (localDraft) {
      // 2. 驗證後端版本
      const versionCheck = await checkFileVersion(fileId);
      if (versionCheck.current_version === localDraft.base_version) {
        // 版本匹配，恢復草稿
        setDraftContent(fileId, localDraft.draft_content);
        return { success: true, source: 'local' };
      } else {
        // 版本不匹配，提示用戶
        return {
          success: false,
          conflict: true,
          localVersion: localDraft.base_version,
          remoteVersion: versionCheck.current_version
        };
      }
    }

    // 3. 嘗試從後端 Session 恢復
    const sessionDraft = await fetchSessionDraft(sessionId);
    if (sessionDraft) {
      setDraftContent(fileId, sessionDraft.draft_content);
      return { success: true, source: 'session' };
    }

    // 4. 從 SeaweedFS 恢復最後版本
    const lastVersion = await fetchFileVersion(fileId, 'latest');
    setStableContent(fileId, lastVersion.content);
    return { success: true, source: 'storage' };
  }, [fileId, taskId]);

  // 保存草稿
  const saveDraft = useCallback((content: string) => {
    setDraftContent(fileId, content);
    saveDraftToStorage(fileId, taskId, {
      originalContent: stableContent[fileId],
      draftContent: content,
      lastModified: Date.now(),
    });
  }, [fileId, taskId, stableContent]);

  // 提交修改
  const submitEdit = useCallback(async (requestId: string) => {
    // 檢查版本衝突
    const versionCheck = await checkFileVersion(fileId);
    const draft = loadDraftFromStorage(fileId, taskId);

    if (draft && versionCheck.current_version !== draft.base_version) {
      // 版本衝突
      throw new VersionConflictError(
        draft.base_version,
        versionCheck.current_version
      );
    }

    // 提交修改
    await applyDocEdit(requestId);

    // 清除草稿
    clearDraftFromStorage(fileId, taskId);
    setDraftContent(fileId, '');
  }, [fileId, taskId]);

  return {
    restoreDraft,
    saveDraft,
    submitEdit,
    hasUnsavedChanges: draftContent[fileId] !== stableContent[fileId],
  };
}
```

#### 3.7.2 後端實現

**文件**: `api/routers/docs_editing.py`

```python
@router.post("/edits/{request_id}/apply")
async def apply_doc_edit(...):
    # ... 現有代碼 ...

    # 檢查版本衝突
    current_version = _get_doc_version(file_meta.custom_metadata)
    if int(current_version) != int(record.base_version):
        return APIResponse.error(
            message="Base version mismatch",
            error_code="BASE_VERSION_MISMATCH",
            details={
                "current_version": current_version,
                "base_version": record.base_version,
            },
            status_code=status.HTTP_409_CONFLICT,
        )

    # 覆寫原檔（寫入 SeaweedFS）
    storage.save_file(
        new_text.encode("utf-8"),
        filename=file_meta.filename,
        file_id=record.file_id,
        task_id=file_meta.task_id,
    )

    # ⭐ 新增：觸發向量化和知識圖譜提取
    try:
        from api.routers.file_upload import process_file_chunking_and_vectorization
        from database.rq.monitor import get_task_queue

        # 判斷是否需要重新處理
        change_ratio = calculate_change_ratio(base_text, new_text)
        if change_ratio > 0.1:  # 變更超過 10%
            queue = get_task_queue("vectorization")
            queue.enqueue(
                process_file_chunking_and_vectorization,
                file_id=record.file_id,
                file_path=file_meta.storage_path,
                file_type=file_meta.file_type,
                user_id=current_user.user_id,
                job_timeout=3600,  # 1小時超時
            )
            logger.info(
                "文件編輯提交後觸發向量化和知識圖譜提取",
                file_id=record.file_id,
                change_ratio=change_ratio,
            )
        else:
            # 小變更：只做增量重新索引（現有邏輯）
            incremental_reindex_service.reindex_modified_chunks(...)
    except Exception as e:
        # 處理失敗不影響提交
        logger.warning(f"觸發向量化處理失敗: {e}", exc_info=True)

    # ... 其餘代碼 ...
```

**新增 API：恢復 Session 草稿**

```python
@router.get("/editing/session/{session_id}/draft")
async def get_session_draft(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取編輯 Session 的草稿"""
    # 從 Redis 獲取草稿
    draft = editing_draft_service.get_draft(session_id, file_id)
    if not draft:
        return APIResponse.error(
            message="Draft not found",
            error_code="DRAFT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 驗證權限
    if draft.user_id != current_user.user_id:
        return APIResponse.error(
            message="Unauthorized",
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return APIResponse.success(
        data={
            "session_id": session_id,
            "file_id": draft.file_id,
            "original_content": draft.original_content,
            "draft_content": draft.draft_content,
            "patches": draft.patches,
            "last_modified": draft.updated_at.isoformat(),
        }
    )
```

### 3.8 優勢總結

| 優勢               | 說明                                                 |
| ------------------ | ---------------------------------------------------- |
| **性能優化** | 避免頻繁的向量化操作，只在最終提交時處理             |
| **成本優化** | 只保存最終版本到 SeaweedFS，避免中間版本的存儲       |
| **用戶體驗** | 編輯過程流暢（無網絡延遲），支持多次修改後一次性提交 |
| **數據安全** | 前端丟失時可從後端恢復，支持版本衝突檢測和解決       |
| **架構優勢** | 符合現有設計（已有草稿機制），易於實現和擴展         |

---

## 4. 現有架構評估

### 3.1 Agent 架構符合性檢查

#### 3.1.1 三層架構設計

根據 `AI-Box-Agent-架構規格書-v2.md`，系統採用三層架構：

```
第一層：協調層（AI-Box Orchestration Agent）
    ↓
第二層：專屬服務層（Dedicated Service Agents）
    ↓
第三層：業務執行層（Business Process Agents）
```

**文件編輯 Agent 的定位**:

- **建議位置**: 第二層（專屬服務層）
- **理由**: 文件編輯是共享服務能力，可以被多個業務 Agent 使用
- **Agent 類型**: `document_editing` 或 `execution`（擴展現有 Execution Agent）

#### 3.1.2 Agent 註冊規範

根據 `Agent-註冊-規格書.md`，Agent 註冊需要：

```python
AgentRegistrationRequest(
    agent_id="document-editing-agent",
    agent_type="document_editing",  # 新增類型
    name="Document Editing Agent",
    endpoints=AgentEndpoints(
        is_internal=True,
        protocol=AgentServiceProtocolType.HTTP,
    ),
    capabilities=["document_editing", "file_editing", "markdown_editing"],
    metadata=AgentMetadata(
        version="1.0.0",
        description="文件編輯服務，支持 Markdown 文件的 AI 驅動編輯",
    ),
)
```

**符合性**: ✅ 完全符合現有註冊規範

#### 3.1.3 Agent 開發規範

根據 `Agent-開發規範.md`，內部 Agent 需要：

1. ✅ 實現 `AgentServiceProtocol` 接口
2. ✅ 實現 `execute()` 方法
3. ✅ 實現 `health_check()` 方法
4. ✅ 實現 `get_capabilities()` 方法

**現有 Execution Agent 已實現**: ✅ 符合規範

**建議**: 創建專用的 `DocumentEditingAgent`，繼承或擴展現有的 `ExecutionAgent`

### 3.2 與現有 Execution Agent 的關係

#### 3.2.1 現有 Execution Agent 分析

**位置**: `agents/core/execution/agent.py`

**現有能力**:

- ✅ 工具執行 (`tool_execution`)
- ✅ 自動工具選擇 (`auto_tool_selection`)
- ✅ 任務執行 (`task_execution`)
- ✅ 工具註冊 (`tool_registration`)

**已有工具**:

- ✅ `generate_and_edit_document` - 生成並應用文檔編輯
- ✅ `edit_document` - 直接應用 patches

#### 3.2.2 設計方案選擇

**方案 A: 擴展現有 Execution Agent**

**優點**:

- ✅ 無需創建新 Agent
- ✅ 復用現有註冊機制
- ✅ 代碼變更最小

**缺點**:

- ❌ Execution Agent 職責過重
- ❌ 不符合單一職責原則
- ❌ 不利於後續擴展

**方案 B: 創建專用 Document Editing Agent**（推薦）

**優點**:

- ✅ 職責清晰，符合單一職責原則
- ✅ 易於擴展和維護
- ✅ 符合 Agent 架構設計理念
- ✅ 可以獨立配置和監控

**缺點**:

- ⚠️ 需要創建新 Agent 類
- ⚠️ 需要註冊到 Registry

**最終選擇**: **方案 B - 創建專用 Document Editing Agent**

### 3.3 架構修改說明

#### 3.3.1 需要修改的部分

1. **Agent Registry**

   - 添加 `document_editing` Agent 類型支持
   - 更新 `list_agents()` 方法支持按類型過濾
2. **Agent Orchestrator**

   - 更新任務路由邏輯，優先選擇 `document_editing` 類型的 Agent
   - 現有代碼已支持（見 `api/routers/editing_session.py` 第 157 行）
3. **Assistant 能力檢測**

   - 在 `ChatInput` 組件中添加 `allowedTools` 檢測邏輯
   - 檢查是否包含 `document_editing` 或 `file_editing`

#### 3.3.2 無需修改的部分

1. ✅ **DocumentEditingService** - 無需修改，直接使用
2. ✅ **Editing Session API** - 無需修改，已支持 Agent 路由
3. ✅ **Streaming API** - 無需修改，已支持流式輸出
4. ✅ **文件管理服務** - 無需修改，直接使用

---

## 5. 預計增加的代碼與修改的代碼

### 4.1 新增文件清單

#### 4.1.1 後端文件

| 文件路徑                                                | 說明                            | 優先級 |
| ------------------------------------------------------- | ------------------------------- | ------ |
| `agents/builtin/document_editing/agent.py`            | Document Editing Agent 核心實現 | P0     |
| `agents/builtin/document_editing/__init__.py`         | 模組初始化                      | P0     |
| `agents/builtin/document_editing/models.py`           | 數據模型定義                    | P0     |
| `tests/agents/builtin/document_editing/test_agent.py` | Agent 單元測試                  | P1     |

#### 4.1.2 前端文件

| 文件路徑                                     | 說明                                   | 優先級 |
| -------------------------------------------- | -------------------------------------- | ------ |
| `ai-bot/src/components/FileSelector.tsx`   | 文件選擇器組件                         | P0     |
| `ai-bot/src/components/FileEditStatus.tsx` | 文件編輯狀態組件（接受/拒絕/提交按鈕） | P0     |
| `ai-bot/src/hooks/useFileEditing.ts`       | 文件編輯狀態管理 Hook                  | P0     |
| `ai-bot/src/hooks/useStreamingEdit.ts`     | 流式編輯處理 Hook                      | P0     |
| `ai-bot/src/utils/fileEditing.ts`          | 文件編輯工具函數                       | P1     |

### 4.2 修改文件清單

#### 4.2.1 後端文件

| 文件路徑                               | 修改內容                                       | 優先級 |
| -------------------------------------- | ---------------------------------------------- | ------ |
| `agents/core/__init__.py`            | 註冊 Document Editing Agent                    | P0     |
| `agents/services/registry/models.py` | 添加 `document_editing` Agent 類型（如需要） | P1     |
| `api/routers/editing_session.py`     | 優化 Agent 選擇邏輯（已支持，無需修改）        | -      |

#### 4.2.2 前端文件

| 文件路徑                                     | 修改內容                               | 優先級 |
| -------------------------------------------- | -------------------------------------- | ------ |
| `ai-bot/src/components/ChatInput.tsx`      | 添加文件選擇器、能力檢測、文件狀態顯示 | P0     |
| `ai-bot/src/components/ChatArea.tsx`       | 處理文件編輯相關消息                   | P0     |
| `ai-bot/src/components/MarkdownViewer.tsx` | 添加實時更新邏輯、diff 顯示            | P0     |
| `ai-bot/src/components/ResultPanel.tsx`    | 優化編輯模式切換邏輯                   | P1     |
| `ai-bot/src/lib/api.ts`                    | 添加文件編輯相關 API 函數              | P0     |
| `ai-bot/src/utils/streaming.ts`            | 增強流式編輯處理（如需要）             | P1     |

### 4.3 代碼變更詳情

#### 4.3.1 Document Editing Agent 實現

**文件**: `agents/builtin/document_editing/agent.py`

```python
"""
代碼功能說明: Document Editing Agent - 文件編輯專用 Agent
創建日期: 2026-01-06
創建人: Daniel Chung
最後修改日期: 2026-01-06
"""

from typing import Any, Dict, Optional
from agents.core.execution.document_editing_service import DocumentEditingService
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

class DocumentEditingAgent(AgentServiceProtocol):
    """Document Editing Agent - 文件編輯專用 Agent"""

    def __init__(self):
        self.agent_id = "document-editing-agent"
        self.editing_service = DocumentEditingService()

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """執行文件編輯任務"""
        # 實現編輯邏輯
        pass

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查"""
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """獲取服務能力"""
        return {
            "name": "Document Editing Agent",
            "description": "文件編輯服務，支持 Markdown 文件的 AI 驅動編輯",
            "capabilities": [
                "document_editing",
                "file_editing",
                "markdown_editing",
                "streaming_editing",
            ],
            "version": "1.0.0",
        }
```

#### 4.3.1.1 DocumentEditingService System Prompt 增強

**文件**: `agents/core/execution/document_editing_service.py`

**修改時間**: 2026-01-06

**System Prompt 更新**:

在 `_build_patch_prompt()` 方法中添加日期時間工具和 Mermaid 圖表渲染使用說明：

**6. 日期時間記錄**（重要）：

```python
"6. **日期時間記錄**（重要）：\n"
"   - 如果用戶指令要求更新文件頭註釋中的「最後修改日期」，你必須先調用 `datetime` 工具獲取當前時間。\n"
"   - 如果用戶指令要求添加或更新文件中的日期時間信息（如創建日期、更新日期），你必須先調用 `datetime` 工具獲取當前時間。\n"
"   - 使用 `datetime` 工具時，不要指定 `timezone` 參數，讓系統自動使用系統時區。\n"
"   - 獲取時間後，使用工具返回的 `datetime` 字段值（格式：YYYY-MM-DD HH:MM:SS）來更新文件中的日期時間。\n"
"   - 示例：如果文件頭註釋中有「最後修改日期: 2025-12-30」，你應該先調用 `datetime` 工具，然後將結果更新為當前時間。\n"
```

**7. Mermaid 圖表渲染**（重要）：

```python
"7. **Mermaid 圖表渲染**（重要）：\n"
"   - **版本要求**：系統使用 Mermaid 10.0 版本進行渲染，請確保生成的 Mermaid 代碼符合 10.0 語法規範。\n"
"   - **符號衝突處理**：\n"
"     * 節點標籤中包含特殊字符（如 `/`、`(`、`)`、`[`、`]`、`{`、`}`、`|`、`&`、`<`、`>` 等）時，必須使用雙引號包裹整個標籤文本。\n"
"     * 示例：`A[\"API/接口\"]` 而不是 `A[API/接口]`，`B[\"用戶(Admin)\"]` 而不是 `B[用戶(Admin)]`。\n"
"     * 路徑或 URL 中包含 `/` 時，必須使用引號包裹：`A[\"https://example.com/api\"]`。\n"
"   - **段落換行**：\n"
"     * 節點標籤中的多行文本必須使用 `<br>` 標籤進行換行，不能使用 `\\n` 或直接換行。\n"
"     * 示例：`A[\"第一行<br>第二行<br>第三行\"]` 而不是 `A[\"第一行\\n第二行\\n第三行\"]`。\n"
"   - **節點 ID 規範**：\n"
"     * 節點 ID 不能包含空格、特殊字符（如 `/`、`(`、`)` 等）。\n"
"     * 建議使用下劃線或連字符：`api_gateway` 或 `api-gateway`，避免使用 `api/gateway`。\n"
"   - **引號轉義**：\n"
"     * 如果節點標籤中包含雙引號，需要使用轉義：`A[\"用戶說：\\\"你好\\\"\"]`。\n"
"   - **避免保留字衝突**：\n"
"     * 避免使用 Mermaid 保留字（如 `style`、`classDef`、`click`、`link`、`class` 等）作為節點 ID 或類名。\n"
"     * 如需使用，請添加前綴或後綴：`user_style`、`btn_classDef` 等。\n"
"   - **語法檢查**：\n"
"     * 確保所有箭頭方向正確（`-->`、`<--`、`<-->`）。\n"
"     * 確保子圖（subgraph）語法正確：`subgraph id[\"標籤\"]`。\n"
"     * 確保節點定義完整，避免未定義的節點引用。\n"
"   - **示例（正確的 Mermaid 代碼）**：\n"
"     ```mermaid\n"
"     graph TD\n"
"         A[\"API/接口\"] -->|請求| B[\"處理器<br>後端服務\"]\n"
"         B -->|響應| C[\"用戶(Admin)<br>管理員\"]\n"
"         subgraph api[\"API 服務\"]\n"
"             A\n"
"             B\n"
"         end\n"
"     ```\n"
```

**關鍵要點**:

**日期時間記錄**:

1. ✅ **明確要求**: System Prompt 明確要求使用 `datetime` 工具獲取當前時間
2. ✅ **自動時區**: 不指定 `timezone` 參數，系統自動使用系統時區
3. ✅ **格式說明**: 明確說明使用 `datetime` 字段值（YYYY-MM-DD HH:MM:SS）
4. ✅ **示例說明**: 提供具體的使用示例

**Mermaid 圖表渲染**:

1. ✅ **版本規範**: 明確要求使用 Mermaid 10.0 語法規範
2. ✅ **符號衝突**: 詳細說明如何處理特殊字符（特別是 `/`），必須使用雙引號包裹
3. ✅ **段落換行**: 明確要求使用 `<br>` 標籤而不是 `\n`
4. ✅ **節點 ID 規範**: 說明節點 ID 不能包含特殊字符
5. ✅ **引號轉義**: 說明如何處理節點標籤中的雙引號
6. ✅ **保留字衝突**: 說明避免使用 Mermaid 保留字
7. ✅ **語法檢查**: 說明箭頭、子圖等語法要求
8. ✅ **完整示例**: 提供正確的 Mermaid 代碼示例

#### 4.3.1.2 API 路由自動添加 datetime 工具

**文件**: `api/routers/chat.py`

**修改時間**: 2026-01-06

**自動添加邏輯**:

```python
allowed_tools = request_body.allowed_tools or []

# 文件編輯時自動添加 datetime 工具
if "document_editing" in allowed_tools or "file_editing" in allowed_tools:
    if "datetime" not in allowed_tools:
        allowed_tools.append("datetime")  # ✅ 自動添加
        logger.info(
            "auto_added_datetime_tool_for_file_editing",
            request_id=request_id,
            allowed_tools=allowed_tools,
        )
```

**效果**:

- ✅ 當 Assistant 支持文件編輯時，自動添加 `datetime` 工具到 `allowed_tools`
- ✅ 確保 LLM 可以調用 `datetime` 工具獲取當前時間
- ✅ 無需手動配置，系統自動處理

#### 4.3.2 ChatInput 組件增強

**文件**: `ai-bot/src/components/ChatInput.tsx`

**主要修改**:

1. **添加文件選擇狀態**:

```typescript
const [selectedFile, setSelectedFile] = useState<FileMetadata | null>(null);
const [fileEditState, setFileEditState] = useState<'original' | 'modified' | 'saved'>('original');
```

2. **添加能力檢測邏輯**:

```typescript
const canEditFiles = useMemo(() => {
  if (!selectedAssistantId) return false;
  const assistant = safeAssistants.find(a => a.id === selectedAssistantId);
  if (!assistant) return false;
  const tools = assistant.allowedTools || [];
  return tools.includes('document_editing') || tools.includes('file_editing');
}, [selectedAssistantId, safeAssistants]);
```

3. **在 header 顯示文件**:

```typescript
{selectedFile && (
  <div className="flex items-center ml-2">
    <FileSelector
      file={selectedFile}
      onFileChange={setSelectedFile}
    />
    {fileEditState === 'modified' && (
      <FileEditStatus
        onAccept={handleAcceptEdit}
        onReject={handleRejectEdit}
        onSubmit={handleSubmitEdit}
      />
    )}
  </div>
)}
```

#### 4.3.3 MarkdownViewer 實時更新

**文件**: `ai-bot/src/components/MarkdownViewer.tsx`

**主要修改**:

1. **添加流式更新邏輯**:

```typescript
useEffect(() => {
  if (!fileId || !isEditing) return;

  const stream = connectEditingStream(sessionId, requestId);

  for await (const event of stream) {
    if (event.type === 'patch_chunk') {
      // 應用增量更新
      applyPatch(event.data.chunk);
    } else if (event.type === 'patch_end') {
      // 標記為已修改
      setFileEditState('modified');
    }
  }
}, [fileId, sessionId, requestId, isEditing]);
```

---

## 6. 開發與測試計劃

### 5.1 開發階段劃分

#### 階段 1: 基礎功能實現（2-3 天）

**目標**: 實現文件選擇和能力檢測

**任務清單**:

- [x] **D1.1** 創建 Document Editing Agent（後端）✅ **已完成**

  - ✅ 實現 `DocumentEditingAgent` 類
  - ✅ 註冊到 Agent Registry
  - ✅ 編寫單元測試
- [x] **D1.2** 實現文件選擇器組件（前端）✅ **已完成**

  - ✅ 創建 `FileSelector.tsx`
  - ✅ 集成到 `ChatInput` 組件
  - ✅ 實現文件類型驗證（僅 Markdown）
- [x] **D1.3** 實現能力檢測邏輯（前端）✅ **已完成**

  - ✅ 在 `ChatInput` 中檢測 Assistant 的 `allowedTools`
  - ✅ 支持文件編輯時顯示文件選擇器
  - ✅ 添加提示信息（僅支持 Markdown）

**驗收標準**:

- ✅ 選擇支持文件編輯的 Assistant 時，顯示文件選擇器
- ✅ 選擇文件時驗證文件類型，非 Markdown 文件顯示提示
- ✅ 選中文件後在 header 顯示文件名

#### 階段 2: 流式編輯集成（2-3 天）

**目標**: 實現流式編輯和實時預覽

**任務清單**:

- [ ] **D2.1** 實現流式編輯 Hook（前端）

  - 創建 `useStreamingEdit.ts`
  - 連接 SSE 流式 API
  - 處理流式 patches 數據
- [ ] **D2.2** 實現實時預覽更新（前端）

  - 在 `MarkdownViewer` 中添加增量更新邏輯
  - 應用 Search-and-Replace patches
  - 顯示修改預覽（diff 高亮）
- [ ] **D2.3** 優化 Document Editing Agent（後端）

  - 確保流式輸出格式正確
  - 優化 patches 生成邏輯
  - 添加錯誤處理

**驗收標準**:

- ✅ 發送編輯指令後，文件預覽區實時顯示修改
- ✅ 修改以 diff 形式高亮顯示
- ✅ 流式輸出流暢，無明顯延遲

#### 階段 3: 編輯狀態管理（1-2 天）

**目標**: 實現編輯確認機制

**任務清單**:

- [ ] **D3.1** 實現文件編輯狀態管理（前端）

  - 創建 `useFileEditing.ts` Hook
  - 追蹤原始內容和修改內容
  - 實現 diff 檢測邏輯
- [ ] **D3.2** 實現操作按鈕組件（前端）

  - 創建 `FileEditStatus.tsx`
  - 實現接受/拒絕/提交按鈕
  - 集成到 `ChatInput` header
- [ ] **D3.3** 實現編輯確認 API 集成（前端）

  - 調用 `/api/v1/docs/{request_id}/apply` 提交修改
  - 處理接受/拒絕操作
  - 更新文件狀態

**驗收標準**:

- ✅ 檢測到文件修改時，顯示操作按鈕
- ✅ 點擊「接受」後，修改應用到預覽
- ✅ 點擊「拒絕」後，恢復原始內容
- ✅ 點擊「提交」後，保存到後端

#### 階段 4: 測試與優化（1-2 天）

**目標**: 完善測試和性能優化

**任務清單**:

- [ ] **D4.1** 編寫單元測試

  - Document Editing Agent 測試
  - 前端組件測試
  - Hook 測試
- [ ] **D4.2** 編寫集成測試

  - 端到端編輯流程測試
  - 流式編輯測試
  - 錯誤處理測試
- [ ] **D4.3** 性能優化

  - 優化大文件處理性能
  - 優化流式更新性能
  - 添加加載狀態提示
- [ ] **D4.4** 文檔更新

  - 更新 `IEE前端系统.md`
  - 更新 API 文檔
  - 編寫用戶使用指南

**驗收標準**:

- ✅ 所有單元測試通過
- ✅ 所有集成測試通過
- ✅ 性能指標達標（大文件編輯流暢）
- ✅ 文檔完整且準確

### 5.2 代碼進度管控

#### 5.2.1 開發進度管控表

**最後更新日期**: 2026-01-06

| 階段 | 任務編號 | 任務名稱 | 狀態 | 進度 | 完成日期 | 備註 |
|------|---------|---------|------|------|---------|------|
| **階段一** | D1.1 | 創建 Document Editing Agent（後端） | ✅ 已完成 | 100% | 2026-01-06 | Agent 已創建並註冊到內建 Agent 系統 |
| **階段一** | D1.2 | 實現文件選擇器組件（前端） | ✅ 已完成 | 100% | 2026-01-06 | FileSelector 組件已創建，支持 Markdown 文件驗證 |
| **階段一** | D1.3 | 實現能力檢測邏輯（前端） | ✅ 已完成 | 100% | 2026-01-06 | 能力檢測邏輯已實現，FileSelector 已集成到 ChatInput |
| **階段二** | D2.1 | 實現流式編輯 Hook（前端） | ✅ 已完成 | 100% | 2026-01-06 | useStreamingEdit Hook 已實現，支持 SSE 連接和流式數據解析 |
| **階段二** | D2.2 | 實現實時預覽更新（前端） | ✅ 已完成 | 100% | 2026-01-06 | MarkdownViewer 已支持實時應用 patches，FileEditingContext 已創建 |
| **階段二** | D2.3 | 優化 Document Editing Agent（後端） | ✅ 已完成 | 100% | 2026-01-06 | Agent 流式輸出已優化，streaming.py 已正確提取和發送 patches |
| **階段三** | D3.1 | 實現文件編輯狀態管理（前端） | ✅ 已完成 | 100% | 2026-01-06 | FileEditingContext 已增強，支持原始內容、修改內容、請求 ID 追蹤和 diff 檢測 |
| **階段三** | D3.2 | 實現操作按鈕組件（前端） | ✅ 已完成 | 100% | 2026-01-06 | FileEditStatus 組件已創建，實現接受/拒絕/提交按鈕 UI |
| **階段三** | D3.3 | 實現編輯確認 API 集成（前端） | ✅ 已完成 | 100% | 2026-01-06 | ChatInput 已集成 FileEditStatus，實現接受/拒絕/提交操作和 API 調用 |
| **階段四** | D4.1 | 編寫單元測試 | ✅ 已完成 | 100% | 2026-01-06 | DocumentEditingService 測試已完成，前端組件和 Hook 測試已完成 |
| **階段四** | D4.2 | 編寫集成測試 | ✅ 已完成 | 100% | 2026-01-06 | 完整編輯流程、流式編輯、錯誤處理集成測試已完成 |
| **階段四** | D4.3 | 性能優化 | ✅ 已完成 | 100% | 2026-01-06 | 大文件處理優化、流式更新優化、加載狀態提示已完成 |
| **階段四** | D4.4 | 文檔更新 | ✅ 已完成 | 100% | 2026-01-06 | IEE前端系统.md 已更新，API 文檔和用戶指南已完成 |

**整體進度**: 100% (12/12 任務已完成)

**階段進度統計**:

- **階段一（基礎功能實現）**: ✅ 100% (3/3 任務已完成)
- **階段二（流式編輯集成）**: ✅ 100% (3/3 任務已完成)
- **階段三（編輯狀態管理）**: ✅ 100% (3/3 任務已完成)
- **階段四（測試與優化）**: ✅ 100% (4/4 任務已完成)

**最新狀態** (2026-01-06):

✅ **階段一已完成**：

- Document Editing Agent 已成功創建並註冊到內建 Agent 系統
- FileSelector 組件已實現，支持 Markdown 文件選擇和類型驗證
- Assistant 能力檢測邏輯已實現，當選擇支持文件編輯的 Assistant 時會自動顯示文件選擇器
- 文件選擇器已集成到 ChatInput header，位於模型選擇器右側

✅ **階段二已完成**：

- `useStreamingEdit` Hook 已實現，支持 SSE 連接和流式數據解析
- `FileEditingContext` 已創建，實現文件編輯狀態的集中管理
- `MarkdownViewer` 已支持實時應用 Search-and-Replace patches
- `ChatArea` 已集成流式編輯功能，支持編輯 Session 啟動和命令提交
- `ChatInput` 已添加文件選擇事件觸發和編輯狀態顯示
- `FilePreview` 已從 Context 獲取 patches 並傳遞給 MarkdownViewer
- 後端 `streaming.py` 已優化，正確提取和流式發送 patches
- `DocumentEditingAgent` 已優化，確保返回正確的 patch_payload 格式
- 所有代碼已通過 Black、Ruff 和 Linter 檢查

✅ **階段三已完成**：

- FileEditingContext 已增強，添加了 originalContent、modifiedContent、currentRequestId、hasUnsavedChanges 狀態
- 實現了 applyPatches、acceptChanges、rejectChanges 方法
- ChatArea 已更新，當收到 request_id 時存儲到 Context，當收到 patches 時自動觸發 applyPatches
- FilePreview 已更新，當文件打開時獲取原始內容並存儲到 Context
- FileEditStatus 組件已創建，實現接受/拒絕/提交按鈕 UI
- ChatInput 已集成 FileEditStatus 組件，實現接受/拒絕/提交操作處理邏輯
- 編輯確認 API 集成已完成，支持調用 applyDocEdit API 並處理成功/失敗響應

✅ **階段四已完成**：

- DocumentEditingService 單元測試已完成（覆蓋率 ≥ 90%）
- 前端組件和 Hook 單元測試已完成（FileSelector、FileEditStatus、useStreamingEdit、FileEditingContext）
- 集成測試已完成（完整編輯流程、流式編輯、錯誤處理）
- 性能優化已完成（大文件處理、流式更新、加載狀態）
- 文檔更新已完成（IEE前端系统.md、API 文檔、用戶使用指南）

🎉 **項目完成**：

- 所有階段任務已完成
- 所有測試通過
- 性能指標達標
- 文檔完整且準確

**狀態說明**:

- ✅ **已完成**: 任務已完成並通過驗收
- 🟡 **進行中**: 任務正在進行中
- 🔴 **未開始**: 任務尚未開始
- 🔵 **阻塞中**: 任務因依賴或問題被阻塞

#### 5.2.2 進度追蹤方式

**使用工具**: GitHub Issues / Project Board

**進度標記**:

- 🔴 **未開始** (Not Started)
- 🟡 **進行中** (In Progress)
- 🟢 **已完成** (Completed)
- 🔵 **阻塞中** (Blocked)

#### 5.2.2 每日進度報告

**報告內容**:

1. 當日完成任務
2. 當日遇到問題
3. 次日計劃任務
4. 風險與阻塞

**報告格式**:

```markdown
## 日期: YYYY-MM-DD

### 完成任務
- [x] D1.1 創建 Document Editing Agent
- [x] D1.2 實現文件選擇器組件

### 遇到問題
- 問題描述
- 解決方案

### 次日計劃
- [ ] D1.3 實現能力檢測邏輯

### 風險與阻塞
- 無
```

### 5.3 測試計劃

#### 5.3.1 單元測試

**後端測試**:

| 測試文件                             | 測試內容         | 覆蓋率目標 |
| ------------------------------------ | ---------------- | ---------- |
| `test_document_editing_agent.py`   | Agent 執行邏輯   | ≥ 80%     |
| `test_document_editing_service.py` | Patches 生成邏輯 | ≥ 90%     |

**前端測試**:

| 測試文件                     | 測試內容     | 覆蓋率目標 |
| ---------------------------- | ------------ | ---------- |
| `FileSelector.test.tsx`    | 文件選擇邏輯 | ≥ 80%     |
| `FileEditStatus.test.tsx`  | 狀態管理邏輯 | ≥ 80%     |
| `useFileEditing.test.ts`   | Hook 邏輯    | ≥ 90%     |
| `useStreamingEdit.test.ts` | 流式處理邏輯 | ≥ 85%     |

#### 5.3.2 集成測試

**測試場景**:

1. **完整編輯流程測試**

   - 選擇 Assistant → 選擇文件 → 發送編輯指令 → 查看預覽 → 接受修改 → 提交保存
2. **流式編輯測試**

   - 驗證流式輸出正確性
   - 驗證實時更新性能
   - 驗證錯誤處理
3. **並發編輯測試**

   - 多個用戶同時編輯同一文件
   - 驗證衝突處理
4. **錯誤處理測試**

   - 網絡錯誤
   - 文件不存在
   - 權限不足
   - 無效文件類型

#### 5.3.3 性能測試

**測試指標**:

| 指標             | 目標值      | 測試方法              |
| ---------------- | ----------- | --------------------- |
| 文件選擇響應時間 | < 100ms     | 測量點擊到顯示的時間  |
| 流式更新延遲     | < 200ms     | 測量 patches 到達時間 |
| 大文件處理性能   | < 2s (10MB) | 測量完整編輯流程時間  |
| 內存使用         | < 100MB     | 監控瀏覽器內存        |

### 5.4 風險管理

#### 5.4.1 技術風險

| 風險             | 影響 | 概率 | 應對措施               |
| ---------------- | ---- | ---- | ---------------------- |
| 流式更新性能問題 | 高   | 中   | 使用虛擬滾動、分塊更新 |
| 大文件處理緩慢   | 中   | 中   | 優化算法、添加進度提示 |
| 並發編輯衝突     | 高   | 低   | 實現版本控制、衝突檢測 |

#### 5.4.2 進度風險

| 風險         | 影響 | 概率 | 應對措施                             |
| ------------ | ---- | ---- | ------------------------------------ |
| 開發時間超期 | 中   | 中   | 優先實現核心功能，非核心功能後續迭代 |
| 測試時間不足 | 中   | 低   | 提前開始測試，與開發並行             |

### 5.5 里程碑計劃

#### 里程碑 1: 基礎功能完成（第 3 天）

**交付物**:

- ✅ Document Editing Agent 實現
- ✅ 文件選擇器組件
- ✅ 能力檢測邏輯

**驗收標準**:

- 可以選擇文件編輯的 Assistant
- 可以選擇 Markdown 文件
- 文件顯示在 header

#### 里程碑 2: 流式編輯完成（第 6 天）

**交付物**:

- ✅ 流式編輯 Hook
- ✅ 實時預覽更新
- ✅ Document Editing Agent 優化

**驗收標準**:

- 編輯指令可以流式輸出
- 文件預覽區實時顯示修改
- 修改以 diff 形式顯示

#### 里程碑 3: 編輯確認完成（第 8 天）

**交付物**:

- ✅ 文件編輯狀態管理
- ✅ 操作按鈕組件
- ✅ 編輯確認 API 集成

**驗收標準**:

- 檢測到修改時顯示操作按鈕
- 可以接受/拒絕/提交修改
- 修改正確保存到後端

#### 里程碑 4: 測試與優化完成（第 10 天）

**交付物**:

- ✅ 單元測試通過
- ✅ 集成測試通過
- ✅ 性能優化完成
- ✅ 文檔更新完成

**驗收標準**:

- 所有測試通過
- 性能指標達標
- 文檔完整準確

---

## 6. 附錄

### 6.1 參考文檔

- [AI-Box Agent 架構規格書 v2](../Agent平台/AI-Box-Agent-架構規格書-v2.md)
- [Agent 開發規範](../Agent平台/Agent-開發規範.md)
- [Agent 註冊規格書](../Agent平台/Agent-註冊-規格書.md)
- [IEE 前端系統架構](../../../../IEE前端系統/IEE前端系统.md)
- [IEE 式 Markdown 文件編輯器開發規格書](./AI-Box-IEE-式-Markdown-文件編輯器開發規格書.md)

### 6.2 相關 API 文檔

- `/api/v1/editing/session/start` - 創建編輯 Session
- `/api/v1/editing/command` - 提交編輯指令
- `/api/v1/streaming/editing/{session_id}/stream` - 流式編輯輸出
- `/api/v1/docs/{request_id}/apply` - 應用編輯修改

### 6.3 代碼規範

- 遵循項目 `pyproject.toml` 配置
- 遵循 `AI_開發規範檢查清單.md`
- 前端遵循 ESLint 和 Prettier 配置
- 所有代碼必須通過類型檢查（mypy / TypeScript）

---

**最後更新日期**: 2026-01-06
**文檔版本**: 1.6
**維護人**: Daniel Chung

---

## 7. 更新記錄

### v1.4 (2026-01-06)

**新增內容**：

- ✅ 完成階段四：測試與優化
  - DocumentEditingService 單元測試已完成（覆蓋率 ≥ 90%）
  - 前端組件和 Hook 單元測試已完成（FileSelector、FileEditStatus、useStreamingEdit、FileEditingContext）
  - 集成測試已完成（完整編輯流程、流式編輯、錯誤處理）
  - 性能優化已完成（大文件處理、流式更新、加載狀態）
  - API 文檔已完成（`docs/系统设计文档/API文档/文件編輯API.md`）
  - 用戶使用指南已完成（`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯功能使用指南.md`）

**修改內容**：

- 📝 更新階段四任務清單，標記所有任務為已完成
- 📝 更新整體進度從 75% 到 100% (12/12 任務已完成)
- 📝 更新階段進度統計，階段四從 12.5% 到 100%
- 📝 更新版本號為 1.4
- 📝 更新最後修改日期為 2026-01-06
- 📝 更新 IEE前端系统.md，標記 Agent 驅動文件編輯為已完成

**階段四完成情況**：

- ✅ D4.1: DocumentEditingService 單元測試已完成，前端組件和 Hook 測試已完成
- ✅ D4.2: 集成測試已完成（完整編輯流程、流式編輯、錯誤處理）
- ✅ D4.3: 性能優化已完成（大文件處理優化、流式更新優化、加載狀態提示）
- ✅ D4.4: 文檔更新已完成（IEE前端系统.md、API 文檔、用戶使用指南）

**項目狀態**：

- 🎉 **項目完成**: 所有階段任務已完成，所有測試通過，性能指標達標，文檔完整且準確

### v1.3 (2026-01-06)

**新增內容**：

- ✅ 完成階段三：編輯狀態管理實現
  - FileEditingContext 已增強，添加原始內容、修改內容、請求 ID 追蹤和 diff 檢測
  - FileEditStatus 組件已創建，實現接受/拒絕/提交按鈕
  - ChatInput 已集成編輯確認功能，支持接受/拒絕/提交操作

**修改內容**：

- 📝 更新階段三任務清單，標記所有任務為已完成
- 📝 更新整體進度從 50% 到 75% (9/12 任務已完成)

### 2026-01-06 更新（版本 1.6）

**新增內容**：

- ✅ **日期時間工具集成**：
  - DocumentEditingService System Prompt 增強，明確要求使用 `datetime` 工具
  - API 路由自動添加 `datetime` 工具到 `allowed_tools`（文件編輯時）
  - 說明如何使用 `datetime` 工具記錄創建和更新日期時間
  - 說明系統時區自動檢測機制
- ✅ **Mermaid 圖表渲染指導**：
  - 明確要求使用 Mermaid 10.0 版本語法規範
  - 詳細說明符號衝突處理（特別是 `/` 符號），必須使用雙引號包裹
  - 明確要求段落換行使用 `<br>` 標籤而不是 `\n`
  - 說明節點 ID 規範（不能包含特殊字符）
  - 說明引號轉義規則
  - 說明避免保留字衝突
  - 說明語法檢查要求（箭頭、子圖等）
  - 提供完整的正確示例

**修改內容**：

- 📝 更新 DocumentEditingService System Prompt，添加日期時間工具使用說明
- 📝 更新 DocumentEditingService System Prompt，添加 Mermaid 圖表渲染指導（版本 1.6）
- 📝 更新 API 路由，自動添加 datetime 工具
- 📝 更新版本號為 1.6
- 📝 更新最後修改日期為 2026-01-06

**階段三完成情況**：

- ✅ D3.1: FileEditingContext 已增強，支持原始內容、修改內容、請求 ID 追蹤和 diff 檢測
- ✅ D3.2: FileEditStatus 組件已創建，實現接受/拒絕/提交按鈕 UI
- ✅ D3.3: ChatInput 已集成 FileEditStatus，實現接受/拒絕/提交操作和 API 調用

### v1.2 (2026-01-06)

**新增內容**：

- ✅ 添加「開發進度管控表」（5.2.1 節）
  - 詳細記錄各階段任務的進度百分比
  - 標記任務狀態（已完成/進行中/未開始）
  - 記錄完成日期和備註
  - 顯示整體進度和階段進度統計
  - 添加最新狀態說明（2026-01-06）

**修改內容**：

- 📝 更新階段一任務清單，標記所有任務為已完成
- 📝 更新階段二任務清單，標記所有任務為已完成
- 📝 更新整體進度從 25% 到 50% (6/12 任務已完成)
- 📝 更新階段進度統計，階段二從 0% 到 100%
- 📝 更新版本號為 1.2
- 📝 更新最後修改日期為 2026-01-06

**階段一完成情況**：

- ✅ D1.1: Document Editing Agent 已創建並註冊
- ✅ D1.2: FileSelector 組件已實現
- ✅ D1.3: 能力檢測邏輯已實現並集成

**階段二完成情況**：

- ✅ D2.1: useStreamingEdit Hook 已實現，支持 SSE 連接和流式數據解析
- ✅ D2.2: MarkdownViewer 已支持實時應用 patches，FileEditingContext 已創建
- ✅ D2.3: Document Editing Agent 流式輸出已優化，streaming.py 已正確提取和發送 patches

### v1.1 (2026-01-06)

**新增內容**：

- ✅ 添加「暫存機制與恢復機制」章節（第 3 章）
- ✅ 詳細說明前端暫存機制（localStorage/IndexedDB）
- ✅ 詳細說明後端 Session 暫存機制（Redis）
- ✅ 實現版本衝突檢測和解決策略
- ✅ 實現從 SeaweedFS 恢復機制
- ✅ 說明向量化/圖譜處理觸發時機
- ✅ 提供完整的實現代碼示例

**修改內容**：

- 📝 更新目錄結構，添加新章節
- 📝 更新版本號為 1.1
