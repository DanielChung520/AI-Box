# Data-Agent 文檔

## 當前版本

### v5.0.0 (2026-03-02)

**升級計劃書**：[Data-Agent-v5-升級計劃書.md](./Data-Agent-v5-升級計劃書.md)

### v4.0.0 (2026-02-20)

**主要規格書**：[Data-Agent-JP規格書v4.md](./Data-Agent-JP規格書v4.md)

## 目錄結構

```
Data-Agent/
├── Data-Agent-v5-升級計劃書.md    # v5 升級計劃書 (2026-03-02)
├── Data-Agent-JP規格書v4.md       # v4 規格書
└── archive/                       # 歸檔文件
    ├── Data-Agent-JP規格書.md      # 舊版規格書
    ├── Data-Agent-規格書.md        # 舊版規格書
    ├── SCHEMA_RAG_ARCHITECTURE.md
    ├── Oracle_to_DuckDB_Migration_Plan.md
    ├── ENVIRONMENT.md
    ├── CodeDictionary-回退指南.md
    ├── Data-Agent-意圖語義分析    ├── Data-Agent架構.md
-TextToSql-優化調整報告.md
    ├── README.md
    └── testing/                   # 測試報告歸檔
        └── [所有測試文件]
```

## 主要變更 (v4 → v5)

1. **簡化架構**：去掉狀態機、Concept、Binding，保留 SchemaRAG
2. **LLM 直接生成 SQL**：不再通過狀態機生成
3. **return_mode 參數**：支持 summary/list 模式
4. **多模塊支持**：預留擴展接口

## 主要變更 (v3 → v4)

1. **SSE 階段回報**：新增 `/execute/stream` 端點，即時回報各階段成果
2. **複雜 JOIN 限制**：新增鍵值驗證，防止全表掃描
3. **數據驗證**：新增後置檢查，簡單目標比對
4. **空結果確認**：區分"正常無數據"和"查詢問題"

## 廢棄模組

以下模組已廢棄，不再使用：
- `data_agent/agent.py`
- `data_agent/text_to_sql.py`
- `data_agent/nlp_to_sql.py`
- `mm_agent/sql_generator.py`
- `mm_agent/services/schema_registry.py`

請使用 `data_agent/services/schema_driven_query/` 模組。
