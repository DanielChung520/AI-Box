# Task Analyzer 用戶指南

**創建日期**: 2026-01-12
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-12

---

## 概述

Task Analyzer 是 AI-Box 系統的核心組件，負責分析用戶的自然語言請求，理解任務意圖，並提供結構化的任務分析結果。

## 使用場景

### 1. 配置查詢

查詢系統配置、租戶配置或用戶配置。

**示例**:
```
查詢 GenAI 租戶策略配置
```

### 2. 日誌查詢

查詢審計日誌、安全日誌或任務日誌。

**示例**:
```
查詢審計日誌
查詢最近 10 條安全日誌
```

### 3. 複雜任務

執行需要多步驟的複雜任務。

**示例**:
```
分析用戶數據並生成報告，然後發送郵件通知
```

### 4. 文件操作

執行文件創建、編輯或生成操作。

**示例**:
```
創建一個新的配置文件
編輯現有文檔
```

## 配置指南

### 環境變數

Task Analyzer 需要以下環境變數：

- `ARANGO_HOST`: ArangoDB 主機地址
- `ARANGO_USER`: ArangoDB 用戶名
- `ARANGO_PASSWORD`: ArangoDB 密碼
- `ARANGO_DB`: ArangoDB 數據庫名稱
- `CHROMA_HOST`: ChromaDB 主機地址

### 配置文件

配置文件位於 `config/config.json`，包含以下配置項：

```json
{
  "task_analyzer": {
    "router_llm_model": "gpt-oss:120b-cloud",
    "rag_top_k": 5,
    "rag_similarity_threshold": 0.7
  }
}
```

## 常見問題解答

### Q1: 任務分析失敗怎麼辦？

**A**: 檢查以下幾點：
1. 確認任務描述清晰明確
2. 檢查系統日誌查看詳細錯誤信息
3. 確認數據庫連接正常
4. 確認 LLM 服務可用

### Q2: 如何提高任務分析準確率？

**A**: 
1. 使用清晰、具體的任務描述
2. 提供足夠的上下文信息
3. 避免使用模糊或歧義的表述

### Q3: 任務分析響應時間過長怎麼辦？

**A**:
1. 檢查網絡連接
2. 檢查 LLM 服務響應時間
3. 優化任務描述，避免過於複雜
4. 檢查系統負載

### Q4: 如何查看任務分析詳情？

**A**: 任務分析結果包含 `analysis_details` 字段，其中包含詳細的分析信息，包括：
- Intent 信息
- Router Decision
- Decision Result（包含 Task DAG）

## 最佳實踐

### 1. 任務描述

- 使用清晰、具體的語言
- 避免使用縮寫或專業術語（除非必要）
- 提供必要的上下文信息

### 2. 錯誤處理

- 始終檢查任務分析結果
- 處理可能的錯誤情況
- 實現重試機制（如適用）

### 3. 性能優化

- 緩存常見任務的分析結果
- 使用異步處理提高並發性能
- 監控系統性能指標

### 4. 安全性

- 驗證用戶權限
- 檢查任務風險等級
- 記錄審計日誌

## 示例代碼

### Python 示例

```python
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest

# 創建 Task Analyzer 實例
analyzer = TaskAnalyzer()

# 分析任務
request = TaskAnalysisRequest(
    task="查詢系統配置",
    context={"user_id": "user_123", "tenant_id": "tenant_123"},
    user_id="user_123"
)

result = await analyzer.analyze(request)

# 處理結果
if result.requires_agent:
    print(f"需要啟動 Agent: {result.suggested_agents}")
else:
    print("可以直接處理")
```

## 相關文檔

- [API 文檔](../api/task-analyzer-api.md)
- [部署指南](../运维文档/task-analyzer-deployment-guide.md)
- [設計說明書](../../系统设计文档/核心组件/語義與任務分析/AI-Box%20語義與任務工程-設計說明書-v4.md)
