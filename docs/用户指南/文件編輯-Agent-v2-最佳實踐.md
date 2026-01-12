# 文件編輯 Agent v2.0 最佳實踐

**代碼功能說明**: 文件編輯 Agent v2.0 最佳實踐
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 概述

本文檔提供文件編輯 Agent v2.0 的最佳實踐建議，幫助用戶更高效、更安全地使用系統。

---

## Intent DSL 編寫最佳實踐

### 1. 使用精確的選擇器

**推薦做法**:

```json
{
  "target_selector": {
    "type": "heading",
    "selector": {
      "text": "系統概述",
      "level": 1,
      "occurrence": 1
    }
  }
}
```

**不推薦做法**:

```json
{
  "target_selector": {
    "type": "heading",
    "selector": {
      "text": "概述"  // 太模糊，可能匹配多個標題
    }
  }
}
```

**理由**: 精確的選擇器可以減少匹配歧義，提高編輯準確性。

---

### 2. 合理使用模糊匹配

模糊匹配是備選方案，不應該依賴模糊匹配來定位目標。

**推薦做法**:

1. 首先使用精確匹配
2. 如果精確匹配失敗，系統會自動嘗試模糊匹配
3. 如果模糊匹配返回多個候選，選擇最相似的一個

**注意事項**:

- 模糊匹配的性能較慢（對於大型文檔）
- 模糊匹配可能匹配到錯誤的目標
- 應該盡量使用精確匹配

---

### 3. 合理設置約束條件

**推薦做法**:

```json
{
  "constraints": {
    "max_tokens": 500,  // 根據實際內容長度設置
    "style_guide": "enterprise-tech-v1",  // 只在需要時啟用
    "no_external_reference": true  // 根據需求啟用
  }
}
```

**不推薦做法**:

```json
{
  "constraints": {
    "max_tokens": 10000,  // 設置過大，失去約束意義
    "style_guide": "enterprise-tech-v1",  // 不需要時也啟用，增加驗證時間
    "no_external_reference": true  // 不需要時也啟用
  }
}
```

**理由**: 合理的約束條件可以平衡功能需求和性能。

---

## 性能優化建議

### 1. 避免頻繁的編輯操作

**推薦做法**:

- 將多個編輯操作合併為一個 Intent（如果可能）
- 使用 Draft State 收集多個編輯，然後一次性 Commit

**不推薦做法**:

- 頻繁調用編輯 API（每次只編輯一小部分）

**理由**: 減少 API 調用次數可以提高整體性能。

---

### 2. 合理使用進階驗證

進階驗證（樣式檢查、語義漂移檢查）會增加驗證時間。

**推薦做法**:

- 只在需要時啟用進階驗證
- 在開發階段啟用所有驗證
- 在生產環境中根據實際需求選擇性啟用

**不推薦做法**:

- 在所有編輯操作中都啟用所有驗證

---

### 3. 使用 Draft State 管理複雜編輯

對於複雜的編輯操作，使用 Draft State：

**推薦流程**:

1. 保存 Draft State
2. 進行多次編輯（所有編輯都在 Draft State 中）
3. 預覽和審查 Draft State
4. Commit 提交（或 Rollback 回滾）

**優點**:

- 可以回滾編輯
- 可以預覽最終結果
- 減少對主文件的影響

---

## 錯誤處理建議

### 1. 處理目標未找到錯誤

**推薦做法**:

1. 檢查選擇器值是否正確
2. 查看錯誤響應中的候選列表（如果提供了）
3. 使用更精確的選擇器
4. 檢查文檔內容是否已更改

**示例**:

```python
try:
    response = await edit_file(...)
except HTTPException as e:
    if e.status_code == 400:
        error_detail = e.detail
        if "TARGET_NOT_FOUND" in error_detail:
            # 處理目標未找到錯誤
            candidates = error_detail.get("candidates", [])
            if candidates:
                # 使用候選列表中的第一個
                # 或者提示用戶選擇
                pass
```

---

### 2. 處理驗證失敗錯誤

**推薦做法**:

1. 查看錯誤詳情，了解具體的違規內容
2. 根據建議修正內容
3. 如果驗證過於嚴格，可以調整約束條件

**示例**:

```python
try:
    response = await edit_file(...)
except HTTPException as e:
    if e.status_code == 400:
        error_detail = e.detail
        if "VALIDATION_FAILED" in error_detail:
            violations = error_detail.get("violations", [])
            for violation in violations:
                # 處理每個違規
                violation_type = violation.get("type")
                suggestion = violation.get("suggestion")
                # 根據建議修正內容
                pass
```

---

### 3. 實現重試機制

對於臨時性錯誤（如網絡錯誤），實現重試機制：

**推薦做法**:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def edit_file_with_retry(...):
    return await edit_file(...)
```

---

## 安全建議

### 1. 驗證輸入

**推薦做法**:

- 驗證用戶輸入的 Intent DSL
- 檢查文件路徑是否合法
- 驗證用戶權限

**示例**:

```python
# 驗證 Intent DSL 結構
if not isinstance(edit_intent, dict):
    raise ValueError("Invalid Intent DSL format")

# 驗證文件路徑
if not file_path.startswith("data/tasks/"):
    raise ValueError("Invalid file path")
```

---

### 2. 使用審計日誌

所有編輯操作都會記錄審計日誌，用於：

- 追蹤編輯歷史
- 審計和合規
- 調試和問題排查

**推薦做法**:

- 定期檢查審計日誌
- 監控異常操作
- 保留審計日誌用於合規審計

---

### 3. 權限控制

**推薦做法**:

- 確保用戶只能編輯自己有權限的文件
- 使用租戶隔離（多租戶環境）
- 驗證用戶身份和權限

---

## 開發建議

### 1. 使用類型提示

**推薦做法**:

```python
from typing import Dict, Any, Optional

async def edit_file(
    document_context: Dict[str, Any],
    edit_intent: Dict[str, Any],
) -> Dict[str, Any]:
    ...
```

---

### 2. 錯誤處理

**推薦做法**:

- 捕獲並處理所有可能的異常
- 提供有意義的錯誤信息
- 記錄錯誤日誌

**示例**:

```python
try:
    response = await edit_file(...)
except HTTPException as e:
    logger.error(f"Edit file failed: {e.detail}")
    # 處理錯誤
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    # 處理意外錯誤
```

---

### 3. 測試

**推薦做法**:

- 為每個 Intent DSL 編寫測試用例
- 測試錯誤場景
- 測試性能（對於關鍵路徑）

---

## 總結

遵循這些最佳實踐可以幫助您：

1. 更高效地使用文件編輯 Agent v2.0
2. 減少錯誤和問題
3. 提高系統性能和穩定性
4. 確保安全和合規

如有問題，請參考：

- 使用指南：`docs/用户指南/文件編輯-Agent-v2-使用指南.md`
- API 文檔：`docs/api/document-editing-agent-v2-api.md`
- 系統規格書：`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯-Agent-系統規格書-v2.0.md`
