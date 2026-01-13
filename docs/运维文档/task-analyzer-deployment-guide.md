# Task Analyzer 部署指南

**創建日期**: 2026-01-12
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13
**版本**: v4.0

---

## 概述

本文檔說明如何部署和配置 Task Analyzer 系統。

**v4.0 架構變更**（2026-01-13）：

- ✅ **5層處理流程**：從 v3 的 4 層路由架構升級為 v4.0 的 5 層處理流程（L1-L5）
- ✅ **新增組件**：Intent Registry、Capability Registry、Policy Service、Execution Record Store Service
- ✅ **測試驗證完成**：階段七測試驗證已完成，測試框架已建立並可運行

## 環境要求

### 系統要求

- Python 3.11+
- ArangoDB 3.10+
- ChromaDB 0.4+
- 至少 4GB RAM
- 至少 10GB 磁盤空間

### 依賴服務

- ArangoDB（數據存儲）
  - Intent Registry 數據
  - Capability Registry 數據
  - Execution Record 數據
  - Policy Rules 數據
- ChromaDB（向量存儲）
  - RAG 向量數據（L3 能力映射層使用）
- LLM 服務（OpenAI、Anthropic、Ollama 等）
  - Router LLM（L1 語義理解層）
  - Task Planner LLM（L3 任務規劃層）

## 安裝步驟

### 1. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

### 2. 配置環境變數

創建 `.env` 文件：

```bash
# ArangoDB 配置
ARANGO_HOST=http://localhost:8529
ARANGO_USER=root
ARANGO_PASSWORD=your_password
ARANGO_DB=ai_box

# ChromaDB 配置
CHROMA_HOST=http://localhost:8000

# LLM 配置
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 3. 初始化數據庫

運行 Schema 創建腳本：

```bash
python scripts/migration/create_schema.py
```

### 4. 初始化 RAG 數據

運行 RAG 數據初始化腳本：

```bash
python scripts/init_rag_data.py
```

### 5. 初始化 v4.0 組件數據

**初始化 Intent Registry**：

```bash
# Intent Registry 數據已包含在 data/intents/core_intents.json
# 系統會自動加載，無需手動初始化
```

**初始化 Capability Registry**：

```bash
# Capability Registry 數據通過 Agent Registry 自動同步
# 無需手動初始化
```

**初始化 Policy Rules**：

```bash
# Policy Rules 通過 Policy Service 動態加載
# 無需手動初始化
```

## 配置說明

### 配置文件位置

配置文件位於 `config/config.json`。

### 主要配置項

```json
{
  "task_analyzer": {
    "router_llm_model": "gpt-oss:120b-cloud",
    "task_planner_llm_model": "gpt-4o",
    "rag_top_k": 5,
    "rag_similarity_threshold": 0.7,
    "policy_check_enabled": true,
    "execution_record_enabled": true,
    "intent_registry_path": "data/intents/core_intents.json",
    "capability_registry_enabled": true,
    "l1_latency_threshold_ms": 5000,
    "total_latency_threshold_ms": 30000
  }
}
```

### 配置項說明

| 配置項 | 類型 | 說明 | 默認值 |
|--------|------|------|--------|
| `router_llm_model` | string | Router LLM 模型名稱（L1 層） | `gpt-oss:120b-cloud` |
| `task_planner_llm_model` | string | Task Planner LLM 模型名稱（L3 層） | `gpt-4o` |
| `rag_top_k` | int | RAG 檢索 Top-K（L3 層） | `5` |
| `rag_similarity_threshold` | float | RAG 相似度閾值（L3 層） | `0.7` |
| `policy_check_enabled` | boolean | 是否啟用 Policy 檢查（L4 層） | `true` |
| `execution_record_enabled` | boolean | 是否啟用執行記錄（L5 層） | `true` |
| `intent_registry_path` | string | Intent Registry 數據文件路徑 | `data/intents/core_intents.json` |
| `capability_registry_enabled` | boolean | 是否啟用 Capability Registry | `true` |
| `l1_latency_threshold_ms` | int | L1 層級延遲閾值（毫秒） | `5000` |
| `total_latency_threshold_ms` | int | 總體處理時間閾值（毫秒） | `30000` |

## 監控和日誌

### 日誌配置

日誌文件位於 `logs/task_analyzer.log`。

### 監控指標

監控以下指標：

**v4.0 新增指標**：

- **L1 層級指標**：
  - L1 語義理解響應時間（目標：≤5秒 P95）
  - L1 語義理解成功率
  - L1 Fallback 使用率

- **L2 層級指標**：
  - L2 Intent 匹配響應時間
  - L2 Intent 匹配成功率
  - L2 Fallback Intent 使用率

- **L3 層級指標**：
  - L3 Task DAG 生成響應時間
  - L3 RAG 檢索命中率
  - L3 Capability 匹配準確率

- **L4 層級指標**：
  - L4 Policy 檢查響應時間（目標：≤100ms P95）
  - L4 Policy 檢查通過率
  - L4 風險評估準確率

- **L5 層級指標**：
  - L5 任務執行成功率
  - L5 任務執行平均時間
  - L5 執行記錄完整性

**通用指標**：

- 任務分析總體響應時間（目標：≤30秒 P95）
- 任務分析成功率
- LLM 調用次數和成本
- 系統資源使用率

### 日誌級別

- `DEBUG`: 詳細調試信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 錯誤信息
- `CRITICAL`: 嚴重錯誤

## 故障排查

### 問題 1: 數據庫連接失敗

**症狀**: 無法連接到 ArangoDB

**解決方法**:

1. 檢查 ArangoDB 服務是否運行
2. 檢查連接配置是否正確
3. 檢查網絡連接

### 問題 2: LLM 調用失敗

**症狀**: LLM API 調用失敗

**解決方法**:

1. 檢查 API Key 是否正確
2. 檢查網絡連接
3. 檢查 API 配額

### 問題 3: RAG 檢索失敗

**症狀**: RAG 檢索返回空結果

**解決方法**:

1. 檢查 ChromaDB 服務是否運行
2. 檢查 RAG 數據是否已初始化
3. 檢查檢索參數是否正確

### 問題 4: 性能問題

**症狀**: 響應時間過長

**解決方法**:

1. 檢查系統負載
2. 優化數據庫查詢
3. 優化 RAG 檢索參數
4. 考慮使用緩存

## 維護

### 定期維護任務

1. **清理舊數據**: 定期清理過期的執行記錄
2. **優化數據庫**: 定期優化數據庫索引
3. **更新模型**: 定期更新 LLM 模型
4. **備份數據**: 定期備份重要數據

### 備份策略

- 每日備份 ArangoDB 數據
- 每周備份配置文件
- 每月備份 RAG 向量數據

## 升級指南

### 升級步驟

1. 備份現有數據和配置
2. 停止服務
3. 更新代碼
4. 運行數據遷移腳本（如適用）
5. 更新配置文件
6. 重啟服務
7. 驗證功能

### 回滾步驟

如果升級失敗，可以回滾：

1. 停止服務
2. 恢復備份的數據和配置
3. 恢復舊版本代碼
4. 重啟服務

## 安全考慮

### 安全配置

1. **API Key 保護**: 使用環境變數存儲 API Key
2. **數據加密**: 敏感數據應加密存儲
3. **訪問控制**: 實施適當的訪問控制
4. **審計日誌**: 記錄所有重要操作

### 安全最佳實踐

- 定期更新依賴包
- 使用強密碼
- 限制網絡訪問
- 實施防火牆規則

## 相關文檔

- [API 文檔](../api/task-analyzer-api.md)
- [用戶指南](../用户指南/task-analyzer-user-guide.md)
- [設計說明書](../../系统设计文档/核心组件/語義與任務分析/AI-Box%20語義與任務工程-設計說明書-v4.md)
