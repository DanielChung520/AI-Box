# 文件編輯 Agent v2.0 部署指南

**代碼功能說明**: 文件編輯 Agent v2.0 部署指南
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 概述

本文檔提供文件編輯 Agent v2.0 的部署指南，包括環境要求、依賴安裝、配置說明和部署步驟。

---

## 環境要求

### 系統要求

- **操作系統**: Linux, macOS, Windows
- **Python 版本**: Python 3.11+
- **內存**: 至少 4GB RAM（建議 8GB+）
- **存儲**: 至少 10GB 可用空間

### 依賴服務

- **ArangoDB**: 3.9+（用於審計日誌存儲，可選）
- **LLM 服務**: OpenAI API 或其他兼容的 LLM 服務

---

## 依賴安裝

### 1. Python 依賴

```bash
# 安裝核心依賴
pip install fastapi uvicorn pydantic

# 安裝 Markdown 解析庫
pip install markdown-it-py

# 安裝模糊匹配庫（可選，推薦）
pip install python-Levenshtein

# 安裝其他依賴
pip install -r requirements.txt
```

### 2. 可選依賴

```bash
# 用於語義漂移檢查（如果啟用）
pip install spacy
python -m spacy download zh_core_web_sm  # 中文模型

# 用於 PDF 轉換（如果使用轉換功能）
pip install pypdf2 reportlab
```

---

## 配置說明

### 1. 環境變量

創建 `.env` 文件或設置環境變數：

```bash
# ArangoDB 配置（用於審計日誌存儲，可選）
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_USER=root
ARANGO_PASSWORD=password
ARANGO_DB=ai_box

# LLM 服務配置
OPENAI_API_KEY=your-api-key-here

# 審計日誌配置
AUDIT_LOG_ASYNC_WRITE=true  # 是否使用異步寫入（默認 true）
AUDIT_LOG_BATCH_SIZE=10  # 批量寫入大小（默認 10）

# 性能配置
FUZZY_MATCH_THRESHOLD=0.7  # 模糊匹配相似度閾值（默認 0.7）
FUZZY_MATCH_MAX_SEARCH_BLOCKS=100  # 最大搜索 Block 數量（默認 100）
CONTEXT_MAX_BLOCKS=5  # 最大上下文 Block 數量（默認 5）
```

### 2. 應用配置

配置文件位置：`config/config.json`

```json
{
  "document_editing_agent": {
    "v2": {
      "fuzzy_matching": {
        "enabled": true,
        "similarity_threshold": 0.7,
        "max_search_blocks": 100
      },
      "advanced_validation": {
        "style_guides": ["enterprise-tech-v1"],
        "semantic_drift": {
          "ner_change_rate_max": 0.3,
          "keywords_overlap_min": 0.5
        }
      },
      "audit_logging": {
        "async_write": true,
        "batch_size": 10,
        "storage": "arango"  # "arango" 或 "memory"
      },
      "performance": {
        "context_cache_enabled": true,
        "context_max_blocks": 5
      }
    }
  }
}
```

---

## 部署步驟

### 1. 準備環境

```bash
# 1. 克隆項目
git clone <repository-url>
cd AI-Box

# 2. 創建虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 3. 安裝依賴
pip install -r requirements.txt
```

### 2. 配置數據庫（可選）

如果使用 ArangoDB 存儲審計日誌：

```bash
# 1. 啟動 ArangoDB（如果未運行）
docker run -d --name arangodb \
  -p 8529:8529 \
  -e ARANGO_ROOT_PASSWORD=password \
  arangodb/arangodb:latest

# 2. 運行 Schema 腳本（如果適用）
python scripts/migration/create_schema.py
```

### 3. 啟動服務

```bash
# 開發環境
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 生產環境（使用 Gunicorn）
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 4. 驗證部署

```bash
# 健康檢查
curl http://localhost:8000/health

# 測試 API
curl -X POST http://localhost:8000/api/v1/document-editing-agent/v2/files \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test.md",
    "task_id": "test-task",
    "content": "# Test\n\nContent"
  }'
```

---

## 配置說明詳細

### 模糊匹配配置

**配置項**:

- `fuzzy_matching.enabled`: 是否啟用模糊匹配（默認 true）
- `fuzzy_matching.similarity_threshold`: 相似度閾值（0-1，默認 0.7）
- `fuzzy_matching.max_search_blocks`: 最大搜索 Block 數量（默認 100）

**調整建議**:

- 如果性能是主要關注點，可以降低 `max_search_blocks`
- 如果需要更嚴格的匹配，可以提高 `similarity_threshold`

---

### 進階驗證配置

**樣式指南**:

- `style_guides`: 支持的樣式指南列表
- 當前支持：`enterprise-tech-v1`

**語義漂移檢查**:

- `ner_change_rate_max`: NER 變更率最大值（0-1，默認 0.3）
- `keywords_overlap_min`: 關鍵詞交集比例最小值（0-1，默認 0.5）

**調整建議**:

- 根據實際需求調整語義漂移檢查的閾值
- 如果驗證過於嚴格，可以適當放寬閾值

---

### 審計日誌配置

**存儲方式**:

- `storage`: 存儲方式（"arango" 或 "memory"）
  - `arango`: 使用 ArangoDB 存儲（生產環境推薦）
  - `memory`: 使用內存存儲（測試環境或開發環境）

**性能優化**:

- `async_write`: 是否使用異步寫入（默認 true，推薦）
- `batch_size`: 批量寫入大小（默認 10）

**調整建議**:

- 生產環境建議使用 ArangoDB 存儲
- 如果數據庫寫入性能是瓶頸，可以增加 `batch_size`

---

### 性能配置

**上下文緩存**:

- `context_cache_enabled`: 是否啟用上下文緩存（默認 true）
- `context_max_blocks`: 最大上下文 Block 數量（默認 5）

**調整建議**:

- 如果內存充足，可以啟用上下文緩存
- 根據實際需求調整 `context_max_blocks`

---

## 監控與運維

### 1. 日誌配置

配置日誌級別和輸出：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/document_editing_agent.log"),
        logging.StreamHandler()
    ]
)
```

### 2. 性能監控

監控以下指標：

- **API 響應時間**: 單次編輯延遲（目標 < 30 秒 P95）
- **目標定位延遲**: 包含模糊匹配（目標 < 200ms）
- **上下文裝配延遲**: （目標 < 300ms）
- **審計日誌寫入延遲**: （目標 < 50ms 增加）

### 3. 錯誤監控

監控以下錯誤：

- `TARGET_NOT_FOUND`: 目標未找到錯誤率
- `VALIDATION_FAILED`: 驗證失敗錯誤率
- `INTERNAL_ERROR`: 內部錯誤率

---

## 故障排查

### 常見問題

#### 1. 文件創建失敗

**症狀**: `POST /files` 返回 500 錯誤

**排查步驟**:

1. 檢查文件存儲服務是否正常
2. 檢查任務工作區是否存在
3. 檢查文件路徑權限
4. 查看錯誤日誌

#### 2. 編輯操作失敗

**症狀**: `POST /edit` 返回 400 錯誤

**排查步驟**:

1. 檢查 Intent DSL 格式是否正確
2. 檢查目標選擇器是否有效
3. 查看錯誤詳情和建議
4. 檢查文件是否存在

#### 3. 審計日誌寫入失敗

**症狀**: 審計日誌未記錄

**排查步驟**:

1. 檢查 ArangoDB 連接是否正常
2. 檢查數據庫權限
3. 查看錯誤日誌
4. 如果使用內存存儲，檢查內存使用情況

#### 4. 性能問題

**症狀**: API 響應時間過長

**排查步驟**:

1. 檢查 LLM 服務響應時間
2. 檢查數據庫查詢性能
3. 檢查文件大小（大型文件可能影響性能）
4. 查看性能監控指標

---

## 升級指南

### 從 v1.0 升級到 v2.0

1. **備份數據**: 備份現有文件和配置
2. **更新代碼**: 拉取最新代碼
3. **更新依賴**: 安裝新依賴
4. **運行遷移腳本**: 如果適用
5. **測試**: 運行測試確保功能正常
6. **部署**: 部署新版本
7. **監控**: 監控系統運行狀況

---

## 參考資料

- API 文檔：`docs/api/document-editing-agent-v2-api.md`
- 模組設計：`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯-Agent-模組設計-v2.md`
- 系統規格書：`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯-Agent-系統規格書-v2.0.md`
