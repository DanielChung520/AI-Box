<!--
代碼功能說明: Ollama LLM 壓測與結果記錄
創建日期: 2025-11-26 00:45 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-26 00:45 (UTC+8)
-->

# Ollama LLM 壓測紀錄

本文件用於記錄 `scripts/performance/ollama_benchmark.py` 的測試流程與結果。執行壓測前請確認：

1. `config/services/ollama` 已設定正確節點/權重與路由策略。
2. `scripts/ollama_sync_models.py` 已同步 baseline/fallback 模型，並更新 `docs/deployment/ollama-models-manifest.json`。
3. FastAPI `/api/v1/llm/generate` 正常，並可由 `scripts/smoke_test.py` 選配 `SMOKE_TEST_LLM_PROMPT` 執行。

## 測試指令

```bash
python scripts/performance/ollama_benchmark.py \
  --endpoint http://localhost:8000/api/v1/llm/generate \
  --prompt "summarize: Ollama benchmark" \
  --requests 50 \
  --concurrency 5 \
  --model gpt-oss:20b
```

產生的 JSON 報告預設輸出至 `docs/performance/ollama-load-test-result.json`，可附於里程碑驗收。

## 最新結果（示例）

| 指標 | 數值 | 備註 |
|------|------|------|
| 成功請求 | 待測 | - |
| 失敗請求 | 待測 | - |
| 平均延遲 (ms) | 待測 | 以非串流模式計算 |
| P95 延遲 (ms) | 待測 | - |
| 節點策略 | weighted RR | 依 `config.services.ollama.router.strategy` |

> **說明**：目前在開發機上僅進行工具整合，實際壓測需於 `olm.k84.org` 或指定節點執行，並將結果回填本表。
