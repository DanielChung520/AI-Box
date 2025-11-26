# Phase 3 - 工作流引擎驗收記錄

| 條目 | 說明 |
|------|------|
| 日期 | 2025-11-26 20:07 (UTC+8) |
| 建立人 | Daniel Chung |

## 1. 功能覆蓋

- ✅ `agents/workflows/langchain_graph_factory.py` 提供 `build_workflow()` 供 Task Analyzer 調用。
- ✅ `LangChainGraphWorkflow` 具備 LangGraph 狀態機、Router/Research 分叉節點與 Redis/Memory checkpoint。
- ✅ `services/api/telemetry/workflow.py` 將 workflow 事件輸出至 Prometheus (`/metrics`) 與結構化日誌。
- ✅ `config/config.example.json` 新增 `workflows.langchain_graph` 區塊，統一管理 workflow 參數。

## 2. 配置與啟動

1. 更新 `config/config.json` 的 `workflows.langchain_graph` 區段（可參考 example 檔）。
2. 若需 Redis checkpoint/context recorder，確保 `redis_url` 可達且 TTL 與 namespace 合理。
3. 啟動 API (`make run-api` 或 `python -m services.api.main`)，Prometheus 可透過 `/metrics` 抓取指標。

## 3. 測試與驗收

```bash
source venv/bin/activate
pytest tests/test_langchain_workflow.py
```

驗證項目：
- `test_langchain_workflow_standard_route`：確認標準路徑可完成並產出基本計畫/輸出。
- `test_langchain_workflow_deep_dive_route`：複雜任務會觸發 `deep_dive` 路徑並寫入 Research 記錄。

## 4. 指標觀測

- Prometheus Counter `workflow_executions_total{workflow, status, route}`。
- Prometheus Histogram `workflow_plan_steps` 可看到規劃步驟分佈。
- 事件同時寫入 `services/api/telemetry.workflow` logger，方便在 ELK/CloudWatch 內檢索。
