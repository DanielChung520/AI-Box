# 文件編輯 Agent v2.0 故障排查指南

**代碼功能說明**: 文件編輯 Agent v2.0 故障排查指南
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 概述

本文檔提供文件編輯 Agent v2.0 的故障排查指南，包括常見問題、錯誤分析和解決方案。

---

## 錯誤碼對照表

| 錯誤碼 | HTTP 狀態碼 | 說明 | 常見原因 |
|--------|------------|------|---------|
| `DOCUMENT_NOT_FOUND` | 404 | 文檔不存在 | 文件路徑錯誤、文件已刪除 |
| `VERSION_NOT_FOUND` | 404 | 版本不存在 | 版本 ID 錯誤 |
| `PERMISSION_DENIED` | 403 | 權限不足 | 用戶沒有權限訪問文件 |
| `INVALID_FORMAT` | 400 | 格式無效 | Intent DSL 格式錯誤 |
| `VALIDATION_FAILED` | 400 | 驗證失敗 | 樣式違規、語義漂移、外部參照 |
| `TARGET_NOT_FOUND` | 400 | 目標未找到 | 選擇器值錯誤、目標不存在 |
| `TARGET_AMBIGUOUS` | 400 | 目標模糊 | 多個匹配的目標 |
| `CONSTRAINT_VIOLATION` | 400 | 約束違規 | 長度超標、外部參照違規 |
| `INVALID_INTENT` | 400 | Intent 無效 | Intent DSL 結構錯誤 |
| `INVALID_SELECTOR` | 400 | 選擇器無效 | Target Selector 格式錯誤 |
| `INTERNAL_ERROR` | 500 | 內部錯誤 | 系統錯誤、依賴服務錯誤 |

---

## 常見問題與解決方案

### 1. TARGET_NOT_FOUND（目標未找到）

**問題描述**: 無法找到指定的目標 Block。

**可能原因**:

1. 選擇器值不正確（文本拼寫錯誤、級別錯誤等）
2. 目標不存在於文檔中
3. 文檔內容已更改

**解決方案**:

1. **檢查選擇器值**:

   ```json
   // 檢查文本是否正確
   {
     "type": "heading",
     "selector": {
       "text": "系統概述",  // 確保文本完全匹配
       "level": 1,
       "occurrence": 1
     }
   }
   ```

2. **使用模糊匹配**:
   - 系統會自動嘗試模糊匹配
   - 查看錯誤響應中的候選列表
   - 使用候選列表中相似度最高的目標

3. **檢查文檔內容**:
   - 確認目標確實存在於文檔中
   - 檢查文檔是否已更新

**錯誤響應示例**:

```json
{
  "code": "TARGET_NOT_FOUND",
  "message": "未找到精確匹配的標題，但找到 2 個相似的候選",
  "details": {
    "selector_type": "heading",
    "selector_value": "標題",
    "candidates": [
      {
        "block_id": "abc123",
        "content": "系統概述",
        "similarity": 0.85
      },
      {
        "block_id": "def456",
        "content": "系統概述（更新）",
        "similarity": 0.80
      }
    ]
  },
  "suggestions": [
    {
      "action": "使用模糊匹配候選",
      "example": "最相似的標題: 系統概述 (相似度: 85%)"
    }
  ]
}
```

---

### 2. VALIDATION_FAILED（驗證失敗）

**問題描述**: 內容驗證失敗。

**可能原因**:

1. 樣式違規（語氣、術語、格式）
2. 語義漂移過大（NER 變更率、關鍵詞交集比例）
3. 外部參照違規（外部 URL、未在上下文中的事實）
4. 長度超標（max_tokens）

**解決方案**:

1. **查看錯誤詳情**:

   ```json
   {
     "code": "VALIDATION_FAILED",
     "message": "樣式檢查失敗: 發現 2 個違規",
     "details": {
       "style_guide": "enterprise-tech-v1",
       "violations": [
         {
           "type": "tone_first_person",
           "message": "禁止使用第一人稱: 我",
           "position": 45,
           "suggestion": "使用第三人稱或客觀描述"
         }
       ]
     }
   }
   ```

2. **根據建議修正內容**:
   - 修正語氣問題（去除第一人稱、命令式）
   - 使用標準術語
   - 修正格式問題

3. **調整約束條件**:

   ```json
   {
     "constraints": {
       "max_tokens": 1000,  // 增加長度限制
       "style_guide": null,  // 禁用樣式檢查（如果不需要）
       "no_external_reference": false  // 允許外部參照
     }
   }
   ```

---

### 3. TARGET_AMBIGUOUS（目標模糊）

**問題描述**: 找到多個匹配的目標。

**可能原因**:

1. 有多個相同文本的標題
2. 選擇器不夠精確

**解決方案**:

1. **使用更精確的選擇器**:

   ```json
   {
     "type": "heading",
     "selector": {
       "text": "系統概述",
       "level": 1,
       "occurrence": 2  // 指定第 2 個匹配
     }
   }
   ```

2. **查看候選列表**:
   - 錯誤響應中包含所有匹配的候選
   - 選擇最合適的候選
   - 使用更精確的選擇器重新請求

---

### 4. 性能問題

**問題描述**: API 響應時間過長。

**可能原因**:

1. LLM 服務響應時間長
2. 大型文件處理
3. 模糊匹配性能問題
4. 審計日誌寫入性能問題

**解決方案**:

1. **檢查 LLM 服務**:
   - 檢查 LLM API 響應時間
   - 檢查 API 配額和限制
   - 考慮使用更快的模型

2. **優化文件大小**:
   - 對於大型文件，考慮分段編輯
   - 使用更精確的選擇器，減少搜索範圍

3. **調整性能配置**:

   ```json
   {
     "fuzzy_matching": {
       "max_search_blocks": 50  // 減少搜索範圍
     },
     "performance": {
       "context_max_blocks": 3  // 減少上下文大小
     }
   }
   ```

4. **檢查審計日誌**:
   - 確保使用異步寫入（`async_write: true`）
   - 增加批量寫入大小（`batch_size: 20`）
   - 如果不需要審計日誌，可以禁用

---

### 5. 審計日誌寫入失敗

**問題描述**: 審計日誌未記錄或寫入失敗。

**可能原因**:

1. ArangoDB 連接失敗
2. 數據庫權限問題
3. 數據庫空間不足

**解決方案**:

1. **檢查 ArangoDB 連接**:

   ```bash
   # 檢查 ArangoDB 是否運行
   curl http://localhost:8529/_api/version

   # 檢查連接配置
   echo $ARANGO_HOST
   echo $ARANGO_PORT
   ```

2. **檢查數據庫權限**:
   - 確保用戶有寫入權限
   - 檢查 Collection 是否存在

3. **使用內存存儲（臨時方案）**:

   ```json
   {
     "audit_logging": {
       "storage": "memory"  // 使用內存存儲（不持久化）
     }
   }
   ```

4. **查看錯誤日誌**:
   - 查看應用日誌中的錯誤信息
   - 檢查數據庫錯誤日誌

---

## 日誌分析

### 日誌級別

- **INFO**: 正常操作日誌
- **WARNING**: 警告信息
- **ERROR**: 錯誤信息
- **DEBUG**: 調試信息（開發環境）

### 關鍵日誌

#### 編輯操作日誌

```
INFO: Document editing completed: task_id=task-123, intent_id=intent-123, patch_id=patch-123
```

#### 審計日誌記錄

```
INFO: Audit event logged: intent_received, intent_id=intent-123, patch_id=patch-123, doc_id=doc-123
```

#### 錯誤日誌

```
ERROR: Document editing error: task_id=task-123, error=TARGET_NOT_FOUND, message=未找到目標
```

### 日誌查詢

使用 grep 或日誌分析工具查詢日誌：

```bash
# 查詢錯誤日誌
grep "ERROR" logs/document_editing_agent.log

# 查詢特定任務的日誌
grep "task_id=task-123" logs/document_editing_agent.log

# 查詢性能問題
grep "performance" logs/document_editing_agent.log
```

---

## 性能問題排查

### 1. 測量各階段性能

在各個階段添加計時：

```python
import time

start = time.time()
# 執行操作
elapsed = time.time() - start
logger.info(f"Operation completed in {elapsed*1000:.2f}ms")
```

### 2. 性能指標目標

- **Intent 驗證**: < 100ms
- **目標定位**（包含模糊匹配）: < 200ms
- **上下文裝配**: < 300ms
- **LLM 生成**: < 20 秒（可配置）
- **審計日誌寫入**: 增加 < 50ms
- **整體編輯流程**: < 30 秒（P95）

### 3. 性能優化建議

如果性能不達標：

1. **檢查 LLM 服務**: LLM 生成通常是最大的性能瓶頸
2. **減少上下文大小**: 減少 `context_max_blocks`
3. **限制模糊匹配範圍**: 減少 `max_search_blocks`
4. **啟用緩存**: 確保上下文緩存已啟用
5. **使用異步審計日誌**: 確保 `async_write: true`

---

## 調試技巧

### 1. 啟用調試模式

設置日誌級別為 DEBUG：

```python
import logging
logging.getLogger("agents.builtin.document_editing_v2").setLevel(logging.DEBUG)
```

### 2. 查看審計日誌

查詢審計日誌以了解操作流程：

```python
from agents.core.editing_v2.audit_logger import AuditLogger

logger = AuditLogger()
events = logger.query_events(intent_id="intent-123")
for event in events:
    print(f"{event.event_type}: {event.timestamp}, duration={event.duration}")
```

### 3. 測試單個模組

單獨測試各個模組以定位問題：

```python
# 測試模糊匹配
from agents.core.editing_v2.fuzzy_matcher import FuzzyMatcher
matcher = FuzzyMatcher()
results = matcher.fuzzy_match_heading("標題", None, blocks)

# 測試驗證器
from agents.core.editing_v2.validator_linter import ValidatorLinter
validator = ValidatorLinter(parser)
validator.validate(content, constraints)
```

---

## 聯繫支持

如果問題無法解決，請：

1. **收集信息**:
   - 錯誤日誌
   - 請求參數
   - 系統配置
   - 性能指標

2. **提交問題報告**:
   - 問題描述
   - 重現步驟
   - 預期行為
   - 實際行為
   - 收集的信息

---

## 參考資料

- 部署指南：`docs/运维文档/文件編輯-Agent-v2-部署指南.md`
- API 文檔：`docs/api/document-editing-agent-v2-api.md`
- 使用指南：`docs/用户指南/文件編輯-Agent-v2-使用指南.md`
