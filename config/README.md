# 代碼功能說明: Config 設置說明
# 創建日期: 2025-11-25 22:46 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:46 (UTC+8)

本目錄集中管理 **非敏感** 的系統設置。流程：

1. 參考 `config.example.json` 建立 `config.json`（已在 `.gitignore` 忽略）。
2. `.env` 仍用於密碼、Token、憑證等敏感資訊；`config.json` 只放可版控的環境參數（埠號、資料夾路徑、Feature Flag 等）。
3. Docker/K8s/腳本在執行前可載入 `config.json`，再注入對應的環境變數或模板檔。

建議：
- 每個服務（API、MCP、ChromaDB、ArangoDB、未來 NoSQL）在 `config.json` 中保留 `host/port/volume` 等欄位。
- 若需新增欄位，請同步更新 `config.example.json` 與相關文檔。

## 新增：Ollama 服務設定

`services.ollama` 區塊集中管理本地 LLM 節點：

```json
"services": {
  "ollama": {
    "scheme": "http",
    "host": "olm.k84.org",
    "port": 11434,
    "health_timeout": 10,
    "request_timeout": 60,
    "default_model": "gpt-oss:20b",
    "embedding_model": "nomic-embed-text",
    "nodes": [
      {"name": "olm-primary", "host": "olm.k84.org", "port": 11434, "weight": 3},
      {"name": "olm-fallback", "host": "localhost", "port": 11435, "weight": 1}
    ],
    "router": {
      "strategy": "weighted",
      "cooldown_seconds": 45
    },
    "baseline_models": ["gpt-oss:20b", "qwen3-coder:30b"],
    "fallback_models": ["llama3.1:8b", "mistral-nemo:12b"],
    "download": {
      "data_root": "~/.ollama",
      "retry": {
        "max_attempts": 3,
        "backoff_seconds": 20
      },
      "allowed_window": "02:00-06:00 UTC+8",
      "max_parallel_jobs": 1
    }
  }
}
```

- `baseline_models`：預設需要長駐的主力模型，供 Agent pipeline 使用。
- `fallback_models`：作為降級備援的輕量模型。
- `default_model` / `embedding_model`：FastAPI LLM API 的預設推理與向量模型，可由 `.env` 覆寫。
- `nodes`：定義多個 Ollama 節點與權重，供負載均衡器使用。
- `router`：輪詢策略與冷卻秒數，對應 `services/api/clients/ollama_client.py` 的路由邏輯。
- `download`：`scripts/ollama_sync_models.py` 會讀取此設定執行模型同步，並遵守 retry/backoff 與可用時段（避免尖峰時間占用頻寬）。若只需產生 manifest，可加入 `--no-download` 參數。

### 批次任務設定

`jobs.ollama_sync` 提供排程建議：

```json
"jobs": {
  "ollama_sync": {
    "enabled": true,
    "schedule_cron": "0 3 * * *",
    "manifest_path": "docs/deployment/ollama-models-manifest.json"
  }
}
```

- `schedule_cron`：建議在每日 03:00（UTC+8）執行模型檢查與下載。
- `manifest_path`：同步完成後寫入的摘要路徑，方便審核/稽核。
